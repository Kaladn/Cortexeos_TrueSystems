# PATCH 01 — Mount genesis_cite plugin in bridges/clearbox_bridge_server.py
#
# FIND the end of the plugin-mounting section in clearbox_bridge_server.py.
# A good anchor is the chat_packs mount block (which ends with):
#
#     except ImportError:
#         LOGGER.info("Chat Packs plugin not available (optional)")
#
# ADD the following block immediately after it (before any other code):

    # ── Mount Genesis Citation plugin (optional, non-fatal) ─
    try:
        from genesis_cite.router import router as genesis_cite_router
        app.include_router(genesis_cite_router)
        _mounted_plugins.add("genesis_cite")
        LOGGER.info("Genesis Citation plugin mounted at /api/genesis")
    except ImportError:
        LOGGER.info("Genesis Citation plugin not available (optional)")

# ── Notes ──────────────────────────────────────────────────────────────────
#
# The genesis_cite plugin directory must be on sys.path or in a location
# where the bridge's import resolution can find it. The standard pattern is:
#   sys.path.insert(0, str(Path(__file__).parent.parent / "plugins"))
# which is already done for other plugins — no extra sys.path change needed.
#
# The plugin exposes these endpoints:
#   GET  /api/genesis/health                — plugin status + block count
#   GET  /api/genesis/list                  — all block tags + titles
#   GET  /api/genesis/cite/{tag}            — full block body
#   GET  /api/genesis/search?q=...          — BM25 search
#   POST /api/genesis/reload                — rebuild search index
#   GET  /api/genesis/ingestion/status      — INGESTION_LOG.md stats
#   POST /api/genesis/ingestion/mark        — mark block as INGESTED/SKIPPED/etc.
