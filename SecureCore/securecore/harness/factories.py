"""Draft factory blueprints for SecureCore creator surfaces."""

from __future__ import annotations

from typing import Any


def factory_blueprints() -> list[dict[str, Any]]:
    return [
        {
            "kind": "logger",
            "title": "Logger Creation Draft",
            "purpose": "Create a coded sensor/logger contract that can emit observed events.",
            "required_fields": [
                "logger_id",
                "sensor_class",
                "runtime_language",
                "event_schema",
                "cursor_strategy",
                "privacy_level",
                "test_command",
            ],
            "allowed_languages": ["python", "rust", "cpp", "powershell"],
            "activation_gate": "tests pass, receipt path configured, operator approval",
            "forbidden": ["raw secret capture", "content logging by default", "silent activation"],
        },
        {
            "kind": "worker",
            "title": "Worker Creation Draft",
            "purpose": "Create a coded worker that performs bounded work for an approved capability.",
            "required_fields": [
                "worker_id",
                "capability_id",
                "runtime_language",
                "input_contract",
                "output_contract",
                "timeout_seconds",
                "test_command",
            ],
            "allowed_languages": ["python", "rust", "cpp", "powershell", "typescript", "javascript"],
            "activation_gate": "dry-run succeeds, policy allows capability, tests pass",
            "forbidden": ["prompt-only worker", "direct policy bypass", "unbounded runtime"],
        },
        {
            "kind": "agent",
            "title": "Agent Creation Draft",
            "purpose": "Create a coded agent manifest around an existing tested capability.",
            "required_fields": [
                "agent_id",
                "runtime_language",
                "entrypoint",
                "entrypoint_hash",
                "allowed_reads",
                "allowed_writes",
                "risk_tier",
                "test_command",
            ],
            "allowed_languages": ["python", "rust", "cpp", "powershell", "typescript", "javascript"],
            "activation_gate": "manifest validates, runner dry-run passes, approval gate satisfied",
            "forbidden": ["prompt_only_allowed=true", "missing entrypoint hash", "unstated writes"],
        },
    ]
