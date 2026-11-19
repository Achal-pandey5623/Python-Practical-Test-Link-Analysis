import hashlib
import json
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import LinkAnalysisRequest, LinkAnalysisResponse
from app.services.llm_service import analyze_page
from app.services.website_extractor import WebsiteFetchError, fetch_website

app = FastAPI(title="AI Website Link Analysis API", version="1.0.0", description="Extracts website content and creates structured business, competitor, SEO, service, and audience insights.")
_cache: dict[str, tuple[float, dict]] = {}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/link-analysis", response_model=LinkAnalysisResponse)
async def link_analysis(request: LinkAnalysisRequest):
    settings = get_settings()
    url = str(request.url)
    key = hashlib.sha256(f"{url}|{settings.llm_model}".encode()).hexdigest()
    cached = _cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    try:
        page = await fetch_website(url, settings)
    except WebsiteFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        result = await analyze_page(url, page, settings)
    except RuntimeError as exc:
        status = 503 if "not configured" in str(exc) else 502
        raise HTTPException(status_code=status, detail=str(exc)) from None
    result_dict = result.model_dump(mode="json")
    _cache[key] = (time.monotonic() + max(settings.cache_ttl_seconds, 0), result_dict)
    return JSONResponse(content=result_dict)
