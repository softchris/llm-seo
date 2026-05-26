"""FastAPI application — serves the API and the static web UI."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analyzer.scorer import analyze

PORT = 9001

app = FastAPI(title="LLM SEO Analyzer")


class AnalyzeRequest(BaseModel):
    url: str


@app.post("/api/analyze")
async def run_analysis(req: AnalyzeRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(400, "URL is required")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        report = await analyze(url)
    except Exception as exc:
        raise HTTPException(502, f"Failed to analyze: {exc}")
    return report


# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
