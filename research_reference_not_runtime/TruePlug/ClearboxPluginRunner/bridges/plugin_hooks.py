"""plugin_hooks.py — Pre/post hook dispatch for connected plugins.

Plugins that support chain hooks expose optional async functions:
    async def plugin_pre(ctx: dict) -> dict
    async def plugin_post(ctx: dict) -> dict

If a plugin doesn't implement hooks, it's silently skipped.
ctx flows through each hook in pipeline_order, accumulating modifications.
"""
from __future__ import annotations

import importlib
import logging
import time

LOGGER = logging.getLogger("ForestAI.plugin_hooks")


def _get_hook(plugin_id: str, hook_name: str):
    """Try to import plugin_id.api.router and return its hook function, or None."""
    try:
        mod = importlib.import_module(f"{plugin_id}.api.router")
        fn = getattr(mod, hook_name, None)
        if fn and callable(fn):
            return fn
    except (ImportError, AttributeError):
        pass
    return None


async def run_pre_hooks(
    enabled_plugins: list[str],
    mounted_plugins: set[str],
    request_ctx: dict,
) -> dict:
    """Run plugin_pre hooks in pipeline order. Returns modified context.

    request_ctx shape:
        {
            "user_message": str,
            "hub_model": str,
            "tools_enabled": bool,
            "hub_messages": list[dict],  # mutable — plugins can inject/modify
            "extra": dict,               # plugin-specific data
        }
    """
    ctx = dict(request_ctx)
    for pid in enabled_plugins:
        if pid not in mounted_plugins:
            continue
        fn = _get_hook(pid, "plugin_pre")
        if fn is None:
            continue
        try:
            t0 = time.time()
            ctx = await fn(ctx) or ctx
            ms = int((time.time() - t0) * 1000)
            LOGGER.debug("plugin_pre %s completed in %dms", pid, ms)
        except Exception as exc:
            LOGGER.warning("plugin_pre %s failed: %s", pid, exc)
    return ctx


async def run_post_hooks(
    enabled_plugins: list[str],
    mounted_plugins: set[str],
    response_ctx: dict,
) -> dict:
    """Run plugin_post hooks in pipeline order. Returns modified context.

    response_ctx shape:
        {
            "user_message": str,
            "hub_model": str,
            "hub_reply": str,
            "tools_used": list[dict],
            "contributions": list[dict],  # mutable — plugins can annotate
            "extra": dict,
        }
    """
    ctx = dict(response_ctx)
    for pid in enabled_plugins:
        if pid not in mounted_plugins:
            continue
        fn = _get_hook(pid, "plugin_post")
        if fn is None:
            continue
        try:
            t0 = time.time()
            ctx = await fn(ctx) or ctx
            ms = int((time.time() - t0) * 1000)
            LOGGER.debug("plugin_post %s completed in %dms", pid, ms)
        except Exception as exc:
            LOGGER.warning("plugin_post %s failed: %s", pid, exc)
    return ctx
