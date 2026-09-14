"""
Standalone preview server for clearbox_ai_social plugin.
Run from repo root:  python -m plugins.clearbox_ai_social._preview
Opens:  http://localhost:9090   (Clearbox-styled UI)
        http://localhost:9090/docs  (Swagger — still available)
Delete this file before production — it's just a preview tool.
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so plugin imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from plugins.clearbox_ai_social.api.router import router

_HERE = Path(__file__).resolve().parent

app = FastAPI(
    title="Clearbox AI Social — Preview",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(_HERE / "_preview_ui.html", media_type="text/html")


if __name__ == "__main__":
    print("\n  Preview UI:  http://localhost:9090")
    print("  Swagger:     http://localhost:9090/docs\n")
    uvicorn.run(app, host="127.0.0.1", port=9090)
