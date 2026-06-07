#!/usr/bin/env python3
"""Web frontend for arXiv Paper Finder — http://localhost:8020"""

import json
import os
import subprocess
import time
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="arXiv Paper Finder")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(exist_ok=True)
    files = sorted(output_dir.glob("*.xlsx"), key=os.path.getmtime, reverse=True)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "files": [f.name for f in files[:20]]},
    )


def _run_pipeline():
    env = os.environ.copy()
    env["NO_PROXY"] = "*"
    proc = subprocess.Popen(
        [str(BASE_DIR / ".venv" / "bin" / "python"), "main.py", "--max-results", "50"],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in proc.stdout:
        yield f"data: {json.dumps({'line': line.strip()})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


@app.get("/run")
async def run():
    return StreamingResponse(_run_pipeline(), media_type="text/event-stream")


@app.get("/output/{filename}")
async def download(filename: str):
    filepath = BASE_DIR / "output" / filename
    if filepath.exists():
        return FileResponse(filepath, filename=filename)
    return HTMLResponse("File not found", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
