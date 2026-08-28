"""plugins/winutil/tools.py — AI tool definitions for the WinUtil plugin.

These definitions follow the Forest AI tool_defs schema:
  {name, description, parameters: {type, properties, required}, handler}

The handler is an async callable invoked by the tool system when the AI
selects a tool. Each handler calls the FastAPI service layer internally,
so the tool execution and the HTTP API share the same logic.

Original WinUtil — Copyright 2022 CT Tech Group LLC (MIT License)
Plugin wrapper — Clearbox AI Studio / ForestAI team
"""
from __future__ import annotations

import json
import logging
from typing import Any

LOGGER = logging.getLogger("winutil.tools")


# ── Tool handler implementations ────────────────────────────────────────────

async def _handle_list_apps(params: dict) -> str:
    from winutil import config_reader as cfg
    category = params.get("category")
    search = params.get("search")
    foss_only = bool(params.get("foss_only", False))
    apps = cfg.list_apps(category=category, search=search, foss_only=foss_only)
    if not apps:
        return "No apps found matching the criteria."
    lines = [f"Found {len(apps)} app(s):"]
    for a in apps[:30]:  # cap at 30 for AI context
        foss_tag = " [FOSS]" if a["foss"] else ""
        lines.append(f"  • {a['name']} (id: {a['id']}, category: {a['category']}){foss_tag}")
        if a["description"]:
            lines.append(f"    {a['description'][:100]}")
    if len(apps) > 30:
        lines.append(f"  ... and {len(apps) - 30} more. Use 'search' to narrow results.")
    return "\n".join(lines)


async def _handle_install_app(params: dict) -> str:
    from winutil import config_reader as cfg, ps_runner as ps
    app_id = params.get("app_id", "")
    method = params.get("method", "auto").lower()

    app = cfg.get_app(app_id)
    if not app:
        return f"App '{app_id}' not found in the WinUtil catalog. Use list_apps to find the correct ID."

    app_name = app.get("content", app_id)
    winget_id = app.get("winget", "")
    choco_id = app.get("choco", "")

    if method == "auto":
        method = "winget" if winget_id and winget_id != "na" else "choco"

    if method == "winget":
        if not winget_id or winget_id == "na":
            return f"'{app_name}' has no winget ID. Try method='choco'."
        result = ps.winget_install(winget_id)
    else:
        if not choco_id or choco_id == "na":
            return f"'{app_name}' has no Chocolatey ID. Try method='winget'."
        result = ps.choco_install(choco_id)

    if result.get("admin_required"):
        return f"Installing '{app_name}' requires administrator privileges. Please restart the server as admin."
    if result["ok"]:
        return f"Successfully installed '{app_name}' via {method}."
    return f"Failed to install '{app_name}': {result['stderr'] or result['stdout']}"


async def _handle_uninstall_app(params: dict) -> str:
    from winutil import config_reader as cfg, ps_runner as ps
    app_id = params.get("app_id", "")
    app = cfg.get_app(app_id)
    if not app:
        return f"App '{app_id}' not found in WinUtil catalog."
    winget_id = app.get("winget", "")
    app_name = app.get("content", app_id)
    if not winget_id or winget_id == "na":
        return f"'{app_name}' has no winget ID — cannot auto-uninstall."
    result = ps.winget_uninstall(winget_id)
    if result["ok"]:
        return f"Successfully uninstalled '{app_name}'."
    return f"Failed to uninstall '{app_name}': {result['stderr'] or result['stdout']}"


async def _handle_list_tweaks(params: dict) -> str:
    from winutil import config_reader as cfg
    category = params.get("category")
    search = params.get("search")
    tweaks = cfg.list_tweaks(category=category, search=search)
    if not tweaks:
        return "No tweaks found matching the criteria."
    lines = [f"Found {len(tweaks)} tweak(s):"]
    for t in tweaks[:25]:
        lines.append(f"  • [{t['id']}] {t['name']} ({t['category']})")
        if t["description"]:
            lines.append(f"    {t['description'][:120]}")
    if len(tweaks) > 25:
        lines.append(f"  ... and {len(tweaks) - 25} more. Use 'search' to filter.")
    return "\n".join(lines)


async def _handle_apply_tweaks(params: dict) -> str:
    from winutil import config_reader as cfg, ps_runner as ps
    tweak_ids: list[str] = params.get("tweak_ids", [])
    undo: bool = bool(params.get("undo", False))
    action = "Undid" if undo else "Applied"

    if not tweak_ids:
        return "No tweak IDs provided. Use list_tweaks to find tweak IDs."

    lines = []
    all_ok = True
    for tweak_id in tweak_ids:
        tweak = cfg.get_tweak(tweak_id)
        if not tweak:
            lines.append(f"  ✗ {tweak_id}: not found")
            all_ok = False
            continue
        name = tweak.get("Content", tweak_id)

        # Registry
        reg_entries = cfg.get_tweak_registry_entries(tweak_id)
        reg_ok = True
        if reg_entries:
            reg_results = ps.apply_registry_entries(reg_entries, undo=undo)
            reg_ok = all(r.get("ok") for r in reg_results)
            if any(r.get("admin_required") for r in reg_results):
                lines.append(f"  ✗ {name}: requires administrator — run server as admin")
                all_ok = False
                continue

        # Script
        scripts = cfg.get_tweak_undo_scripts(tweak_id) if undo else cfg.get_tweak_invoke_scripts(tweak_id)
        script_ok = True
        if scripts:
            sr = ps.apply_invoke_scripts(scripts)
            script_ok = sr["ok"]
            if sr.get("admin_required"):
                lines.append(f"  ✗ {name}: requires administrator for script execution")
                all_ok = False
                continue
            if not script_ok:
                lines.append(f"  ✗ {name}: script error — {sr['stderr'][:100]}")
                all_ok = False
                continue

        if reg_ok and script_ok:
            lines.append(f"  ✓ {action} '{name}'")
        else:
            lines.append(f"  ✗ {name}: partial failure")
            all_ok = False

    summary = f"{action} {len(tweak_ids)} tweak(s):" if all_ok else f"Completed with errors ({len(tweak_ids)} tweak(s)):"
    return summary + "\n" + "\n".join(lines)


async def _handle_list_features(params: dict) -> str:
    from winutil import config_reader as cfg
    search = params.get("search")
    features = cfg.list_features(search=search)
    if not features:
        return "No features found."
    lines = [f"Found {len(features)} feature(s):"]
    for f in features[:20]:
        lines.append(f"  • [{f['id']}] {f['name']}")
        lines.append(f"    {f['description'][:100]}")
    if len(features) > 20:
        lines.append(f"  ... and {len(features) - 20} more.")
    return "\n".join(lines)


async def _handle_install_feature(params: dict) -> str:
    from winutil import config_reader as cfg, ps_runner as ps
    feature_ids: list[str] = params.get("feature_ids", [])
    if not feature_ids:
        return "No feature IDs provided. Use list_features to find IDs."

    lines = []
    for feature_id in feature_ids:
        feat = cfg.get_feature(feature_id)
        if not feat:
            lines.append(f"  ✗ {feature_id}: not found")
            continue
        feature_names = feat.get("feature", [])
        invoke_scripts = cfg.get_feature_invoke_scripts(feature_id)
        result = ps.enable_feature(feature_names, invoke_scripts=invoke_scripts or None)
        if result.get("admin_required"):
            lines.append(f"  ✗ {feat.get('Content', feature_id)}: requires administrator")
        elif result["ok"]:
            lines.append(f"  ✓ Enabled '{feat.get('Content', feature_id)}'")
        else:
            lines.append(f"  ✗ {feat.get('Content', feature_id)}: {result['stderr'][:100]}")

    return "Feature install results:\n" + "\n".join(lines) + "\n\nNote: A reboot may be required."


async def _handle_list_dns(params: dict) -> str:
    from winutil import config_reader as cfg
    providers = cfg.list_dns_providers()
    lines = ["Available DNS providers:"]
    for p in providers:
        if p["name"] == "DHCP":
            lines.append("  • DHCP — automatic (ISP default)")
        else:
            lines.append(f"  • {p['name']} — {p['primary']} / {p['secondary']}")
    return "\n".join(lines)


async def _handle_set_dns(params: dict) -> str:
    from winutil import config_reader as cfg, ps_runner as ps
    provider_name = params.get("provider", "")
    if not provider_name:
        return "Specify a DNS provider. Use list_dns to see options."

    if provider_name.upper() == "DHCP":
        result = ps.reset_dns_dhcp()
        if result.get("admin_required"):
            return "Setting DNS requires administrator privileges."
        return "DNS reset to DHCP (automatic) on all active adapters." if result["ok"] else f"Failed: {result['stderr']}"

    provider = cfg.get_dns_provider(provider_name)
    if not provider:
        return f"Provider '{provider_name}' not found. Use list_dns to see options."

    result = ps.set_dns(provider["primary"], provider["secondary"],
                        primary6=provider.get("primary6", ""), secondary6=provider.get("secondary6", ""))
    if result.get("admin_required"):
        return "Setting DNS requires administrator privileges."
    if result["ok"]:
        return f"DNS set to {provider['name']} ({provider['primary']} / {provider['secondary']}) on all active adapters."
    return f"Failed to set DNS: {result['stderr']}"


async def _handle_fix_operation(params: dict) -> str:
    from winutil import ps_runner as ps
    operation = params.get("operation", "")
    _ops = {
        "update": (ps.fix_windows_update, "Windows Update fix"),
        "network": (ps.fix_network, "Network stack reset"),
        "winget": (ps.fix_winget, "winget repair"),
        "system": (ps.fix_system_repair, "System repair (DISM + SFC)"),
        "ultimate_performance": (ps.enable_ultimate_performance, "Ultimate Performance power plan"),
    }
    if operation not in _ops:
        return f"Unknown operation '{operation}'. Choose from: {', '.join(_ops.keys())}"

    fn, label = _ops[operation]
    result = fn()
    if result.get("admin_required"):
        return f"{label} requires administrator privileges. Please restart the Clearbox AI server as admin."
    if result["ok"]:
        note = " Reboot recommended." if operation in ("update", "network", "system") else ""
        return f"{label} completed successfully.{note}"
    return f"{label} encountered errors: {result['stderr'][:200] or result['stdout'][:200]}"


async def _handle_system_status(params: dict) -> str:
    from winutil import config_reader as cfg, ps_runner as ps
    status = cfg.config_status()
    is_admin = ps.is_admin()
    lines = [
        "WinUtil Plugin Status:",
        f"  WinUtil directory: {status['winutil_dir']}",
        f"  WinUtil present: {'Yes' if status['winutil_present'] else 'No — check winutil-main directory'}",
        f"  Apps available: {status['apps_count']}",
        f"  Tweaks available: {status['tweaks_count']}",
        f"  Features available: {status['features_count']}",
        f"  DNS providers: {status['dns_providers']}",
        f"  Admin privileges: {'Yes — all operations available' if is_admin else 'No — registry/DNS/feature/repair ops restricted'}",
    ]
    if not is_admin:
        lines.append("  TIP: Restart Clearbox AI Studio as Administrator to unlock all features.")
    return "\n".join(lines)


# ── Tool definitions (schema + handler) ─────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "winutil_list_apps",
        "description": (
            "Browse the WinUtil application catalog. Lists installable Windows apps "
            "from Chris Titus Tech's curated database (200+ apps). Filter by category "
            "(e.g. 'Utilities', 'Development', 'Multimedia Tools', 'Pro Tools') or search term."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (e.g. 'Utilities', 'Development', 'Document', 'Multimedia Tools')"
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter apps by name or description"
                },
                "foss_only": {
                    "type": "boolean",
                    "description": "Only show free and open-source apps",
                    "default": False
                },
            },
            "required": [],
        },
        "handler": _handle_list_apps,
    },
    {
        "name": "winutil_install_app",
        "description": (
            "Install a Windows application via winget (preferred) or Chocolatey. "
            "Use winutil_list_apps first to find the correct app_id. "
            "Runs silently with no UI interaction required."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The WinUtil app ID (lowercase key from the catalog, e.g. '7zip', 'vscode', 'firefox')"
                },
                "method": {
                    "type": "string",
                    "enum": ["auto", "winget", "choco"],
                    "description": "Package manager to use. 'auto' tries winget first, falls back to choco.",
                    "default": "auto"
                },
            },
            "required": ["app_id"],
        },
        "handler": _handle_install_app,
    },
    {
        "name": "winutil_uninstall_app",
        "description": "Uninstall a Windows application via winget. Use the app_id from the WinUtil catalog.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The WinUtil app ID (e.g. '7zip', 'vscode', 'firefox')"
                },
            },
            "required": ["app_id"],
        },
        "handler": _handle_uninstall_app,
    },
    {
        "name": "winutil_list_tweaks",
        "description": (
            "Browse available Windows system tweaks from WinUtil. "
            "Tweaks include privacy settings, performance optimizations, UI changes, "
            "service management, and telemetry disabling. Filter by category or search."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (e.g. 'Essential Tweaks', 'Advanced Tweaks - CAUTION')"
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter tweaks by name or description"
                },
            },
            "required": [],
        },
        "handler": _handle_list_tweaks,
    },
    {
        "name": "winutil_apply_tweaks",
        "description": (
            "Apply or undo one or more Windows system tweaks. "
            "Tweaks modify registry entries and run PowerShell scripts. "
            "Many tweaks require administrator privileges. "
            "Use winutil_list_tweaks to find tweak IDs (format: 'WPFTweaks...')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tweak_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tweak IDs to apply (e.g. ['WPFTweaksActivity', 'WPFTweaksHiber'])"
                },
                "undo": {
                    "type": "boolean",
                    "description": "If true, reverses the tweaks (restores original values)",
                    "default": False
                },
            },
            "required": ["tweak_ids"],
        },
        "handler": _handle_apply_tweaks,
    },
    {
        "name": "winutil_list_features",
        "description": (
            "List available Windows optional features from WinUtil, such as "
            ".NET Framework, Hyper-V, WSL, legacy media, sandbox, and more."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Search term to filter features"
                },
            },
            "required": [],
        },
        "handler": _handle_list_features,
    },
    {
        "name": "winutil_install_feature",
        "description": (
            "Enable one or more Windows optional features (e.g. Hyper-V, WSL, .NET 3.5). "
            "Requires administrator privileges. A reboot may be needed after enabling."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "feature_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of WinUtil feature IDs to enable (e.g. ['WPFFeaturesdotnet', 'WPFFeatureshyperv'])"
                },
            },
            "required": ["feature_ids"],
        },
        "handler": _handle_install_feature,
    },
    {
        "name": "winutil_list_dns",
        "description": "List available DNS providers (Google, Cloudflare, Quad9, AdGuard, OpenDNS, etc.) with their server addresses.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": _handle_list_dns,
    },
    {
        "name": "winutil_set_dns",
        "description": (
            "Set the DNS server on all active network adapters. "
            "Supports Google, Cloudflare (standard/malware-blocking/adult), "
            "Quad9, AdGuard, OpenDNS, or DHCP (automatic). Requires admin."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "DNS provider name (e.g. 'Google', 'Cloudflare', 'Quad9', 'DHCP'). Use winutil_list_dns to see all options."
                },
            },
            "required": ["provider"],
        },
        "handler": _handle_set_dns,
    },
    {
        "name": "winutil_fix",
        "description": (
            "Run Windows repair and maintenance operations:\n"
            "  • update — Reset Windows Update (stops services, clears cache, runs DISM + SFC)\n"
            "  • network — Reset network stack (Winsock, IP, DNS, ARP)\n"
            "  • winget — Re-register Microsoft App Installer (winget)\n"
            "  • system — Full system repair (DISM RestoreHealth + SFC)\n"
            "  • ultimate_performance — Activate Ultimate Performance power plan\n"
            "Most operations require administrator privileges."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["update", "network", "winget", "system", "ultimate_performance"],
                    "description": "The repair operation to run"
                },
            },
            "required": ["operation"],
        },
        "handler": _handle_fix_operation,
    },
    {
        "name": "winutil_status",
        "description": "Check the WinUtil plugin status: admin rights, config availability, and app/tweak counts.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": _handle_system_status,
    },
]

# Flat dict for quick lookup by tool name
TOOL_MAP: dict[str, dict] = {t["name"]: t for t in TOOLS}
