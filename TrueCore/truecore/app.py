"""TrueCore Application Factory.

This is where the organism comes alive. The app factory:
  1. Loads and validates config
  2. Initializes the database and JWT
  3. Creates all substrates (truth layers)
  4. Creates all agents (interpreters)
  5. Wires agents to substrates
  6. Initializes structured logging
  7. Registers real routes and trap routes
  8. Starts the agent processing pipeline

Every touch creates multiple coordinated records:
  raw -> normalized -> forensic -> agent interpretation -> escalation outcome
"""

import logging
import os
from pathlib import Path
import sys
import threading
import time

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    repo_root = Path(__file__).resolve().parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from flask import Flask

from truecore.config import load_settings, validate_settings
from truecore.core.db import db
from truecore.core.auth import jwt

# Substrates
from truecore.substrates.ingress import IngressSubstrate
from truecore.substrates.mirror import MirrorSubstrate
from truecore.substrates.evidence import EvidenceSubstrate
from truecore.substrates.telemetry import TelemetrySubstrate
from truecore.substrates.agent_decisions import AgentDecisionsSubstrate
from truecore.substrates.operator import OperatorSubstrate
from truecore.substrates.hid import HIDSubstrate

# Agents
from truecore.agents.watcher import WatcherAgent
from truecore.agents.profiler import ProfilerAgent
from truecore.agents.escalation import EscalationAgent
from truecore.agents.decoy_orchestrator import DecoyOrchestratorAgent
from truecore.agents.chain_auditor import ChainAuditorAgent
from truecore.agents.containment import ContainmentAdvisorAgent
from truecore.agents.cognitive import CognitiveAgent

# Control
from truecore.control.reaper import Reaper, ReaperPolicy
from truecore.control.command_bus import ControlBus

# Permissions
from truecore.permissions.registry import CallerRegistry
from truecore.permissions.gate import PermissionGate
from truecore.permissions.types import SubstrateWriter, SubstrateReader

# Future model/session plumbing
from truecore.openai_session import OpenAIKeyVault

# Logging
from truecore.log_streams.streams import LogRouter

# Routes
from truecore.routes.health import health_bp
from truecore.routes.auth import auth_bp
from truecore.routes.rbac import rbac_bp
from truecore.routes.events import events_bp
from truecore.routes.openai_session import openai_session_bp
from truecore.routes.ops import ops_bp
from truecore.email_sentinel.bridge import ImapHeaderBridge, StaticHeaderBridge
from truecore.email_sentinel.patterns import AlertPattern, DevicePool, UserDevice
from truecore.email_sentinel.routes import email_sentinel_bp, init_email_sentinel_routes
from truecore.email_sentinel.sandbox import EmailSandbox
from truecore.email_sentinel.service import EmailSentinelService
from truecore.control.routes import control_bp, init_control_routes

logger = logging.getLogger("truecore")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


def _agent_ticker(agents: list, interval: float = 30.0):
    """Background thread that ticks all agents periodically."""
    while True:
        time.sleep(interval)
        for agent in agents:
            try:
                agent.tick()
            except Exception as exc:
                logger.error("Agent tick failed for %s: %s", agent.name, exc)


def _create_email_sentinel(data_dir: str) -> EmailSentinelService | None:
    """Create the email sentinel without making app startup depend on email."""
    try:
        sandbox = EmailSandbox(Path(data_dir) / "email_sentinel")
        poll_interval = int(os.environ.get("TRUECORE_EMAIL_POLL_SECONDS", "10"))
        if os.environ.get("TRUECORE_EMAIL_IMAP_ENABLED", "").lower() == "true":
            bridge = ImapHeaderBridge(
                host=os.environ["TRUECORE_EMAIL_IMAP_HOST"],
                username=os.environ["TRUECORE_EMAIL_IMAP_USER"],
                password=os.environ["TRUECORE_EMAIL_IMAP_PASS"],
                mailbox=os.environ.get("TRUECORE_EMAIL_IMAP_MAILBOX", "INBOX"),
                ssl=os.environ.get("TRUECORE_EMAIL_IMAP_SSL", "true").lower() != "false",
            )
        else:
            bridge = StaticHeaderBridge([])
        patterns = [
            AlertPattern(
                pattern_id="generic_security_alert",
                kind="security",
                sender_domains=[
                    domain.strip().lower()
                    for domain in os.environ.get("TRUECORE_EMAIL_SECURITY_DOMAINS", "").split(",")
                    if domain.strip()
                ],
                subject_contains=["security", "alert"],
                require_auth_pass=True,
                severity="high",
            ),
            AlertPattern(
                pattern_id="generic_banking_alert",
                kind="banking",
                sender_domains=[
                    domain.strip().lower()
                    for domain in os.environ.get("TRUECORE_EMAIL_BANKING_DOMAINS", "").split(",")
                    if domain.strip()
                ],
                subject_contains=["alert"],
                require_auth_pass=True,
                severity="high",
            ),
        ]
        device_pool = DevicePool(
            [
                UserDevice(
                    device_id="local_placeholder",
                    channel="log_only",
                    destination="not_configured",
                    enabled=False,
                    severity_threshold="critical",
                )
            ]
        )
        return EmailSentinelService(
            bridge=bridge,
            sandbox=sandbox,
            patterns=patterns,
            device_pool=device_pool,
            poll_interval_seconds=poll_interval,
        )
    except Exception as exc:
        logger.error("Email sentinel unavailable: %s", exc)
        return None


def create_app() -> Flask:
    settings = load_settings()
    validate_settings(settings)
    _configure_logging()

    app = Flask(__name__, static_folder=None)
    app.config.update(settings)

    db.init_app(app)
    jwt.init_app(app)

    # ============================================================
    # SUBSTRATES - ground truth layers
    # ============================================================
    data_dir = os.path.join(os.path.dirname(__file__), settings.get("DATA_DIR", "data"))
    log_dir = os.path.join(os.path.dirname(__file__), settings.get("LOG_DIR", "logs"))

    substrates = {
        "ingress": IngressSubstrate(os.path.join(data_dir, "substrates")),
        "mirror": MirrorSubstrate(os.path.join(data_dir, "substrates")),
        "evidence": EvidenceSubstrate(os.path.join(data_dir, "substrates")),
        "telemetry": TelemetrySubstrate(os.path.join(data_dir, "substrates")),
        "agent_decisions": AgentDecisionsSubstrate(os.path.join(data_dir, "substrates")),
        "operator": OperatorSubstrate(os.path.join(data_dir, "substrates")),
        "hid": HIDSubstrate(os.path.join(data_dir, "substrates")),
    }

    # ============================================================
    # LOGGING - one stream per concern
    # ============================================================
    log_router = LogRouter(log_dir)

    # ============================================================
    # PERMISSIONS - register all callers, set gate on all substrates
    # ============================================================
    registry = CallerRegistry()
    gate = PermissionGate(registry)

    # Register every autonomous component with explicit permissions
    # No self-registration. The factory defines who can touch what.

    agent_names = [
        "watcher", "profiler", "escalation",
        "decoy_orchestrator", "chain_auditor", "cognitive", "containment",
    ]
    agent_entries = {}
    for aname in agent_names:
        agent_entries[aname] = registry.register(
            caller_id=f"agent:{aname}",
            caller_type="agent",
            module_path=f"truecore.agents.{aname}",
            allowed_write=["agent_decisions"],
            allowed_read=["ingress", "mirror", "evidence", "telemetry", "hid", "agent_decisions"],
        )

    reaper_entry = registry.register(
        caller_id="control:reaper",
        caller_type="control",
        module_path="truecore.control.reaper",
        allowed_write=["operator"],
        allowed_read=["agent_decisions", "hid"],
    )

    trap_entry = registry.register(
        caller_id="routes:traps",
        caller_type="routes",
        module_path="truecore.decoys.routes",
        allowed_write=["ingress", "mirror", "evidence", "telemetry"],
        allowed_read=[],
    )

    shun_entry = registry.register(
        caller_id="control:shun",
        caller_type="control",
        module_path="truecore.control.shun",
        allowed_write=["operator"],
        allowed_read=[],
    )
    # Set the gate on every substrate
    for sub in substrates.values():
        sub.set_permission_gate(gate)

    # Build writer/reader interfaces
    def _writer(caller_entry, substrate_name):
        return SubstrateWriter(substrates[substrate_name], caller_entry.caller_id, caller_entry.signing_key)

    # ============================================================
    # AGENTS - interpreters on substrate truth
    # ============================================================
    agents = {}

    # Each agent gets a SubstrateWriter for agent_decisions only
    # and SubstrateReaders for their watched substrates

    watcher_writer = _writer(agent_entries["watcher"], "agent_decisions")
    watcher = WatcherAgent(watcher_writer)
    watcher.watch(substrates["ingress"])
    agents["watcher"] = watcher

    profiler_writer = _writer(agent_entries["profiler"], "agent_decisions")
    profiler = ProfilerAgent(profiler_writer)
    profiler.watch(substrates["ingress"])
    profiler.watch(substrates["mirror"])
    agents["profiler"] = profiler

    escalation_writer = _writer(agent_entries["escalation"], "agent_decisions")
    escalation = EscalationAgent(escalation_writer)
    escalation.watch(substrates["agent_decisions"])
    escalation.watch(substrates["mirror"])
    agents["escalation"] = escalation

    decoy_orch_writer = _writer(agent_entries["decoy_orchestrator"], "agent_decisions")
    decoy_orch = DecoyOrchestratorAgent(decoy_orch_writer)
    decoy_orch.watch(substrates["mirror"])
    decoy_orch.watch(substrates["agent_decisions"])
    agents["decoy_orchestrator"] = decoy_orch

    chain_auditor_writer = _writer(agent_entries["chain_auditor"], "agent_decisions")
    chain_auditor = ChainAuditorAgent(
        chain_auditor_writer,
        watched_substrates=list(substrates.values()),
        evidence_substrate=substrates["evidence"],
    )
    agents["chain_auditor"] = chain_auditor

    cognitive_writer = _writer(agent_entries["cognitive"], "agent_decisions")
    cognitive = CognitiveAgent(cognitive_writer, hid_substrate=substrates["hid"])
    cognitive.watch(substrates["ingress"])
    cognitive.watch(substrates["mirror"])
    cognitive.watch(substrates["hid"])
    agents["cognitive"] = cognitive

    containment_writer = _writer(agent_entries["containment"], "agent_decisions")
    containment = ContainmentAdvisorAgent(containment_writer)
    containment.watch(substrates["agent_decisions"])
    containment.watch(substrates["mirror"])
    agents["containment"] = containment

    # Start all agents
    for agent in agents.values():
        agent.start()

    # Start agent ticker thread
    agent_list = list(agents.values())
    ticker = threading.Thread(target=_agent_ticker, args=(agent_list,), daemon=True)
    ticker.start()

    # ============================================================
    # FUTURE UI / CHAT / MEMORY PORTS - intentionally not installed
    # ============================================================
    openai_key_vault = OpenAIKeyVault()
    core_runtime_status = {
        "ui_runtime": "not_installed",
        "chat_runtime": "not_installed",
        "memory_runtime": "not_installed",
        "future_port": True,
    }
    email_sentinel = _create_email_sentinel(data_dir)

    # ============================================================
    # ROUTES - real and trap
    # ============================================================
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(rbac_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(openai_session_bp)
    app.register_blueprint(ops_bp)
    init_email_sentinel_routes(email_sentinel)
    app.register_blueprint(email_sentinel_bp)
    # ============================================================
    # REAPER - autonomous containment executor
    # ============================================================
    reaper_operator_writer = _writer(reaper_entry, "operator")
    reaper = Reaper(
        decisions_substrate=substrates["agent_decisions"],
        operator_writer=reaper_operator_writer,
        hid_substrate=substrates["hid"],
        policy=ReaperPolicy(
            min_confidence=0.7,
            shun_cooldown_seconds=300.0,
            auto_shun_enabled=_env_bool("TRUECORE_REAPER_AUTO_SHUN", False),
            auto_lock_enabled=_env_bool("TRUECORE_REAPER_AUTO_LOCK", False),
            auto_preserve_enabled=_env_bool("TRUECORE_REAPER_AUTO_PRESERVE", False),
            dry_run=_env_bool("TRUECORE_REAPER_DRY_RUN", True),
        ),
    )
    reaper.start()

    shun_operator_writer = _writer(shun_entry, "operator")
    control_bus = ControlBus(
        os.path.join(data_dir, "runtime", "control_bus"),
        substrates=substrates,
        agents=agents,
        log_router=log_router,
        reaper=reaper,
        operator_writer=shun_operator_writer,
        registry=registry,
        permission_gate=gate,
    )
    control_bus.start()

    # Control plane routes
    init_control_routes(substrates, agents, log_router, reaper, operator_writer=shun_operator_writer)
    app.register_blueprint(control_bp)

    # Trap routes (honeypot)
    if app.config.get("HONEYPOT_ENABLED", True):
        from truecore.decoys.routes import trap_bp, init_trap_routes
        init_trap_routes(
            ingress_writer=_writer(trap_entry, "ingress"),
            mirror_writer=_writer(trap_entry, "mirror"),
            evidence_writer=_writer(trap_entry, "evidence"),
            telemetry_writer=_writer(trap_entry, "telemetry"),
            log_router=log_router,
        )
        app.register_blueprint(trap_bp)

    # Store references on app for CLI access
    app.substrates = substrates
    app.agents = agents
    app.log_router = log_router
    app.reaper = reaper
    app.control_bus = control_bus
    app.registry = registry
    app.permission_gate = gate
    app.openai_key_vault = openai_key_vault
    app.core_runtime_status = core_runtime_status
    app.email_sentinel = email_sentinel

    with app.app_context():
        from truecore.core import models  # noqa: F401
        db.create_all()

    logger.info(
        "TrueCore organism alive: %d substrates, %d agents, %d log streams",
        len(substrates), len(agents), len(LogRouter.STREAM_NAMES),
    )

    return app


app = create_app()

if __name__ == "__main__":
    host = app.config["BIND_HOST"]
    port = int(app.config["BIND_PORT"])
    app.run(host=host, port=port, debug=False)
