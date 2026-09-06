use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;
use std::process::{Command, Output};
use time::{format_description::well_known::Rfc3339, OffsetDateTime};

const REQUEST_SCHEMA: &str = "truecomputer_action_request@1";
const RECEIPT_SCHEMA: &str = "truecomputer_action_receipt@2";
const SNAPSHOT_SCHEMA: &str = "truecomputer_desktop_snapshot@1";

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    schema: String,
    request_id: String,
    expected_active_window: WindowExpectation,
    action: Action,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WindowExpectation {
    address: String,
    class: String,
    title: String,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Action {
    FocusWindow { address: String },
    SwitchWorkspace { workspace: String },
    MovePointer { x: i64, y: i64 },
    TypeText { text: String },
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct Window {
    address: String,
    class: String,
    title: String,
    #[serde(default)]
    pid: i64,
    #[serde(default)]
    workspace: Value,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct Monitor {
    name: String,
    x: i64,
    y: i64,
    width: i64,
    height: i64,
    scale: f64,
    #[serde(default, rename = "activeWorkspace")]
    active_workspace: Value,
    #[serde(default)]
    focused: bool,
}

#[derive(Debug, Serialize)]
struct Snapshot {
    schema: &'static str,
    observed_at_utc: String,
    backend: &'static str,
    active_window: Window,
    cursor: Value,
    monitors: Vec<Monitor>,
    workspaces: Vec<Value>,
    windows: Vec<Window>,
}

fn main() {
    if let Err(error) = run() {
        println!("{}", json!({"ok": false, "error": error}));
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("inspect") if args.len() == 2 => {
            println!(
                "{}",
                serde_json::to_string_pretty(&snapshot()?).map_err(err)?
            );
            Ok(())
        }
        Some("validate") if args.len() == 3 => {
            let (request, bytes) = read_request(Path::new(&args[2]))?;
            let state = snapshot()?;
            validate(&request, &state)?;
            println!(
                "{}",
                serde_json::to_string_pretty(&plan(&request, &bytes)).map_err(err)?
            );
            Ok(())
        }
        Some("execute") => execute_args(&args),
        _ => Err(usage()),
    }
}

fn execute_args(args: &[String]) -> Result<(), String> {
    if args.len() != 6 || args[3] != "--receipt-dir" || args[5] != "--execute" {
        return Err(usage());
    }
    let request_path = Path::new(&args[2]);
    let receipt_dir = Path::new(&args[4]);
    let (request, bytes) = read_request(request_path)?;
    let receipt_path = receipt_dir.join(format!("{}.json", safe_id(&request.request_id)?));
    prepare_receipt(&receipt_path)?;
    let before = snapshot()?;
    validate(&request, &before)?;
    let started = now();
    let output = match perform(&request.action) {
        Ok(output) => output,
        Err(error) => {
            let receipt = receipt(
                &request,
                &bytes,
                &before,
                None,
                &started,
                "execution_not_started",
                None,
                json!({
                    "status": "not_verified",
                    "scope": "none",
                    "reason": "backend process could not be started",
                }),
            );
            write_json_atomic(&receipt_path, &receipt)?;
            return Err(format!(
                "backend process could not start; receipt written: {error}"
            ));
        }
    };
    if !output.status.success() {
        let after = snapshot().ok();
        let receipt = receipt(
            &request,
            &bytes,
            &before,
            after.as_ref(),
            &started,
            "execution_failed",
            output.status.code(),
            json!({
                "status": "not_verified",
                "scope": "action_outcome",
                "reason": "backend returned a nonzero exit status",
            }),
        );
        write_json_atomic(&receipt_path, &receipt).map_err(|error| {
            format!("action may have executed but receipt publication failed: {error}")
        })?;
        return Err("backend action failed; failure receipt written".into());
    }
    let after = match snapshot() {
        Ok(after) => after,
        Err(error) => {
            let receipt = receipt(
                &request,
                &bytes,
                &before,
                None,
                &started,
                "executed_outcome_unverified",
                output.status.code(),
                json!({
                    "status": "executed_but_outcome_unverified",
                    "scope": "action_outcome",
                    "reason": "post-action observation failed",
                }),
            );
            write_json_atomic(&receipt_path, &receipt).map_err(|write_error| {
                format!("action executed but receipt publication failed: {write_error}")
            })?;
            return Err(format!(
                "action executed but outcome is unverified; receipt written: {error}"
            ));
        }
    };
    let (status, verification) = match verify_postcondition(&request, &after) {
        Err(error) => (
            "executed_verification_failed",
            json!({
                "status": "verification_failed",
                "scope": "action_postcondition",
                "reason": error,
            }),
        ),
        Ok(()) => successful_verification(&request.action),
    };
    let receipt = receipt(
        &request,
        &bytes,
        &before,
        Some(&after),
        &started,
        status,
        output.status.code(),
        verification,
    );
    write_json_atomic(&receipt_path, &receipt)
        .map_err(|error| format!("action executed but receipt publication failed: {error}"))?;
    if status == "executed_verification_failed" {
        return Err("action executed but its postcondition failed; receipt written".into());
    }
    println!("{}", serde_json::to_string_pretty(&receipt).map_err(err)?);
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn receipt(
    request: &Request,
    bytes: &[u8],
    before: &Snapshot,
    after: Option<&Snapshot>,
    started: &str,
    status: &str,
    backend_exit_code: Option<i32>,
    verification: Value,
) -> Value {
    let execution_status = match status {
        "execution_not_started" => "not_started",
        "execution_failed" => "failed",
        _ => "executed",
    };
    json!({
        "schema": RECEIPT_SCHEMA,
        "request_id": request.request_id,
        "request_sha256": sha256(bytes),
        "action": action_summary(&request.action),
        "backend": backend_name(&request.action),
        "started_at_utc": started,
        "completed_at_utc": now(),
        "status": status,
        "execution": {
            "status": execution_status,
            "backend_exit_code": backend_exit_code,
        },
        "verification": verification,
        "precondition_window": window_identity(&before.active_window),
        "postcondition_window": after.map(|state| window_identity(&state.active_window)),
    })
}

fn successful_verification(action: &Action) -> (&'static str, Value) {
    match action {
        Action::TypeText { .. } => (
            "executed_outcome_unverified",
            json!({
                "status": "executed_but_outcome_unverified",
                "scope": "application_outcome",
                "verified": "backend exited zero and the expected window remained active",
                "unverified": "the application retained, interpreted, submitted, or acted on the text",
            }),
        ),
        Action::FocusWindow { .. } => verified("active window address equals the requested target"),
        Action::SwitchWorkspace { .. } => {
            verified("focused monitor reports the requested workspace")
        }
        Action::MovePointer { .. } => verified("post-action cursor coordinates equal the request"),
    }
}

fn verified(evidence: &'static str) -> (&'static str, Value) {
    (
        "completed_verified",
        json!({
            "status": "verified",
            "scope": "action_postcondition",
            "evidence": evidence,
        }),
    )
}

fn read_request(path: &Path) -> Result<(Request, Vec<u8>), String> {
    let bytes = fs::read(path).map_err(err)?;
    let request: Request = serde_json::from_slice(&bytes).map_err(err)?;
    if request.schema != REQUEST_SCHEMA {
        return Err(format!("schema must be {REQUEST_SCHEMA}"));
    }
    safe_id(&request.request_id)?;
    Ok((request, bytes))
}

fn snapshot() -> Result<Snapshot, String> {
    Ok(Snapshot {
        schema: SNAPSHOT_SCHEMA,
        observed_at_utc: now(),
        backend: "hyprland_ipc",
        active_window: hypr_json(&["-j", "activewindow"])?,
        cursor: hypr_json(&["-j", "cursorpos"])?,
        monitors: hypr_json(&["-j", "monitors"])?,
        workspaces: hypr_json(&["-j", "workspaces"])?,
        windows: hypr_json(&["-j", "clients"])?,
    })
}

fn hypr_json<T: for<'de> Deserialize<'de>>(args: &[&str]) -> Result<T, String> {
    let output = command("hyprctl", args)?;
    if !output.status.success() {
        return Err(format!(
            "hyprctl failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    serde_json::from_slice(&output.stdout).map_err(err)
}

fn validate(request: &Request, state: &Snapshot) -> Result<(), String> {
    if !window_matches(&request.expected_active_window, &state.active_window) {
        return Err("active window does not match expected_active_window".into());
    }
    match &request.action {
        Action::FocusWindow { address } => {
            valid_address(address)?;
            if !state
                .windows
                .iter()
                .any(|window| &window.address == address)
            {
                return Err("focus target is not an existing window".into());
            }
        }
        Action::SwitchWorkspace { workspace } => {
            if workspace.is_empty()
                || workspace.len() > 64
                || !workspace.chars().all(|character| {
                    character.is_ascii_alphanumeric() || matches!(character, '-' | '_')
                })
            {
                return Err("workspace must use 1..64 ASCII letters, digits, '-' or '_'".into());
            }
            let exists = state.workspaces.iter().any(|item| {
                item.get("name").and_then(Value::as_str) == Some(workspace.as_str())
                    || item.get("id").map(|id| id.to_string()) == Some(workspace.clone())
            });
            if !exists {
                return Err("workspace target is not an existing workspace".into());
            }
        }
        Action::MovePointer { x, y } => {
            let inside = state.monitors.iter().any(|monitor| {
                *x >= monitor.x
                    && *x < monitor.x + monitor.width
                    && *y >= monitor.y
                    && *y < monitor.y + monitor.height
            });
            if !inside {
                return Err("pointer target is outside active monitor bounds".into());
            }
        }
        Action::TypeText { text } => {
            if text.is_empty() || text.chars().count() > 4096 {
                return Err("text must contain 1..4096 characters".into());
            }
            if text.chars().any(char::is_control) {
                return Err("text may not contain control characters".into());
            }
        }
    }
    Ok(())
}

fn perform(action: &Action) -> Result<Output, String> {
    match action {
        Action::FocusWindow { address } => command(
            "hyprctl",
            &[
                "dispatch",
                &format!("hl.dsp.focus({{window=\"address:{address}\"}})"),
            ],
        ),
        Action::SwitchWorkspace { workspace } => command(
            "hyprctl",
            &[
                "dispatch",
                &format!("hl.dsp.focus({{workspace=\"{workspace}\"}})"),
            ],
        ),
        Action::MovePointer { x, y } => command(
            "hyprctl",
            &["dispatch", &format!("hl.dsp.cursor.move({{x={x}, y={y}}})")],
        ),
        Action::TypeText { text } => command("wtype", &[text]),
    }
}

fn verify_postcondition(request: &Request, state: &Snapshot) -> Result<(), String> {
    match &request.action {
        Action::FocusWindow { address } if state.active_window.address != *address => {
            Err("focus postcondition failed".into())
        }
        Action::SwitchWorkspace { workspace } => {
            let active = state
                .monitors
                .iter()
                .find(|monitor| monitor.focused)
                .and_then(|monitor| monitor.active_workspace.get("name"))
                .and_then(Value::as_str);
            if active == Some(workspace.as_str()) {
                Ok(())
            } else {
                Err("workspace postcondition failed".into())
            }
        }
        Action::TypeText { .. }
            if !window_matches(&request.expected_active_window, &state.active_window) =>
        {
            Err("active window changed while typing".into())
        }
        Action::MovePointer { x, y }
            if state.cursor.get("x").and_then(Value::as_i64) != Some(*x)
                || state.cursor.get("y").and_then(Value::as_i64) != Some(*y) =>
        {
            Err("pointer postcondition failed".into())
        }
        _ => Ok(()),
    }
}

fn command(program: &str, args: &[&str]) -> Result<Output, String> {
    let executable = match program {
        "hyprctl" => "/usr/bin/hyprctl",
        "wtype" => "/usr/bin/wtype",
        _ => return Err("backend executable is not allowlisted".into()),
    };
    Command::new(executable).args(args).output().map_err(err)
}

fn plan(request: &Request, bytes: &[u8]) -> Value {
    json!({
        "ok": true,
        "schema": "truecomputer_validated_plan@1",
        "request_id": request.request_id,
        "request_sha256": sha256(bytes),
        "action": action_summary(&request.action),
        "backend": backend_name(&request.action),
        "requires_execute_flag": true,
        "validated_at_utc": now(),
    })
}

fn action_summary(action: &Action) -> Value {
    match action {
        Action::FocusWindow { address } => json!({"kind": "focus_window", "address": address}),
        Action::SwitchWorkspace { workspace } => {
            json!({"kind": "switch_workspace", "workspace": workspace})
        }
        Action::MovePointer { x, y } => json!({"kind": "move_pointer", "x": x, "y": y}),
        Action::TypeText { text } => json!({
            "kind": "type_text",
            "character_count": text.chars().count(),
            "text_sha256": sha256(text.as_bytes()),
            "text_redacted": true,
        }),
    }
}

fn backend_name(action: &Action) -> &'static str {
    match action {
        Action::TypeText { .. } => "wtype_wayland_virtual_keyboard",
        _ => "hyprland_ipc",
    }
}

fn window_matches(expected: &WindowExpectation, actual: &Window) -> bool {
    expected.address == actual.address
        && expected.class == actual.class
        && expected.title == actual.title
}

fn window_identity(window: &Window) -> Value {
    json!({"address": window.address, "class": window.class, "title": window.title, "pid": window.pid})
}

fn valid_address(value: &str) -> Result<(), String> {
    let tail = value
        .strip_prefix("0x")
        .ok_or("window address must start with 0x")?;
    if tail.is_empty() || !tail.chars().all(|character| character.is_ascii_hexdigit()) {
        return Err("window address must be hexadecimal".into());
    }
    Ok(())
}

fn safe_id(value: &str) -> Result<&str, String> {
    if value.is_empty()
        || value.len() > 128
        || !value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || matches!(character, '-' | '_'))
    {
        return Err("request_id must use 1..128 ASCII letters, digits, '-' or '_'".into());
    }
    Ok(value)
}

fn prepare_receipt(path: &Path) -> Result<(), String> {
    let parent = path.parent().ok_or("receipt path has no parent")?;
    fs::create_dir_all(parent).map_err(err)?;
    if path.exists() {
        return Err("receipt already exists for request_id".into());
    }
    Ok(())
}

fn write_json_atomic(path: &Path, value: &Value) -> Result<(), String> {
    let parent = path.parent().ok_or("receipt path has no parent")?;
    let temp = parent.join(format!(
        ".{}.{}.tmp",
        path.file_name()
            .and_then(|v| v.to_str())
            .unwrap_or("receipt"),
        std::process::id()
    ));
    let payload = serde_json::to_vec_pretty(value).map_err(err)?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(err)?;
    file.write_all(&payload).map_err(err)?;
    file.sync_all().map_err(err)?;
    fs::rename(&temp, path).map_err(err)
}

fn sha256(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}

fn now() -> String {
    OffsetDateTime::now_utc()
        .format(&Rfc3339)
        .unwrap_or_else(|_| "unknown".into())
}

fn err(error: impl std::fmt::Display) -> String {
    error.to_string()
}

fn usage() -> String {
    "usage: truecomputer inspect | validate REQUEST.json | execute REQUEST.json --receipt-dir DIR --execute".into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_ids_are_path_safe() {
        assert!(safe_id("request-01_ok").is_ok());
        assert!(safe_id("../escape").is_err());
    }

    #[test]
    fn typed_text_is_redacted() {
        let summary = action_summary(&Action::TypeText {
            text: "secret-ish".into(),
        });
        assert_eq!(summary["character_count"], 10);
        assert!(summary.get("text").is_none());
        assert_eq!(summary["text_redacted"], true);
    }

    #[test]
    fn text_execution_does_not_claim_application_success() {
        let (status, verification) = successful_verification(&Action::TypeText {
            text: "delivered input".into(),
        });
        assert_eq!(status, "executed_outcome_unverified");
        assert_eq!(verification["status"], "executed_but_outcome_unverified");
        assert!(verification.get("unverified").is_some());
    }

    #[test]
    fn pointer_postcondition_can_be_verified_without_claiming_more() {
        let (status, verification) = successful_verification(&Action::MovePointer { x: 10, y: 20 });
        assert_eq!(status, "completed_verified");
        assert_eq!(verification["status"], "verified");
        assert_eq!(verification["scope"], "action_postcondition");
    }
}
