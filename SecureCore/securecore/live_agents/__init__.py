"""Staging package for SecureCore agents intended for live promotion.

Modules placed here are not runtime-active until explicitly registered by the
application factory.
"""

from .manifest import load_agent_manifest, validate_agent_manifest

__all__ = ["invoke", "load_agent_manifest", "materialize", "validate_agent_manifest"]


def __getattr__(name: str):
    if name == "materialize":
        from .creator import materialize
        return materialize
    if name == "invoke":
        from .generated_runtime import invoke
        return invoke
    raise AttributeError(name)
