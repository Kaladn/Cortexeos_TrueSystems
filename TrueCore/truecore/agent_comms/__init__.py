"""Typed agent handoff contracts.

Agents do not gossip. Agents hand off work through shaped packets.
"""

from .handoff import (
    AgentHandoffContractError,
    build_agent_handoff_packet,
    build_agent_handoff_reply,
    validate_agent_handoff_packet,
    validate_agent_handoff_reply,
)

__all__ = [
    "AgentHandoffContractError",
    "build_agent_handoff_packet",
    "build_agent_handoff_reply",
    "validate_agent_handoff_packet",
    "validate_agent_handoff_reply",
]
