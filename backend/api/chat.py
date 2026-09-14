import json
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from db.database import get_db


router = APIRouter(prefix="/chat", tags=["chat"])

_ANSWER_CACHE: dict[str, tuple[float, str]] = {}
_LAST_REQUEST_AT = 0.0
_CACHE_TTL_SECONDS = 300
_MIN_REQUEST_INTERVAL_SECONDS = 2
_MAX_CACHE_ENTRIES = 100

CHAT_SCOPE = """
You are Ask Phoenix, the operations assistant for the Phoenix thermal-event
intelligence platform. Phoenix currently provides intelligence for the Dahej
industrial region in Gujarat, India.

Answer questions about the complete Phoenix problem statement and workflow:
NASA FIRMS MODIS/VIIRS thermal observations, FRP, brightness temperature,
confidence and timestamps; OpenStreetMap/Global Energy Monitor industrial
facilities; ESA WorldCover land cover; Sentinel-2/Landsat image confirmation;
facility-specific baselines; spatial-temporal event clustering; classification
of industrial fires, gas flares, agricultural burns, mining activity, wildfires
and unknown sources; persistent versus anomalous sources; risk scoring;
population exposure; emissions; wind/spread context; alerts; PostGIS storage;
the FastAPI API; and the React/Leaflet map.

Use the supplied live database context for Dahej-specific numbers and records.
You may explain Phoenix concepts, architecture, data sources, formulas,
workflow, limitations, and how to interpret fields even when a value is not
present in the context. Never invent a live event, number, facility, alert, or
current condition. Explain when data is historical/demo data or when the
database does not contain enough evidence. Distinguish classification (what
the source is) from anomaly_state (whether it is unusual for that site).

Keep answers concise and operational. Only refuse questions that are unrelated
to Phoenix, thermal-event intelligence, disaster response, geospatial
monitoring, or this project. Do not limit the user to a fixed list of example
questions.
"""


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=600)
    region: str = Field(default="dahej", pattern="^[a-z0-9-]+$")


class ChatResponse(BaseModel):
    answer: str
    region: str
    provider: str | None = None


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    return str(value)


def _load_context(db: Session) -> dict[str, Any]:
    event_summary = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS event_count,
                COUNT(*) FILTER (WHERE LOWER(COALESCE(severity, '')) IN ('critical', 'high')) AS high_risk_count,
                COUNT(*) FILTER (WHERE LOWER(COALESCE(anomaly_state, '')) NOT IN ('normal', 'persistent')) AS anomalous_count,
                COALESCE(SUM(population_exposed), 0) AS population_exposed,
                COALESCE(MAX(max_frp), 0) AS max_frp
            FROM thermal_events
            """
        )
    ).mappings().one()

    events = db.execute(
        text(
            """
            SELECT event_id, first_seen, classification, classification_confidence,
                   anomaly_state, severity, current_frp, max_frp, mean_frp,
                   baseline_frp, baseline_deviation, duration, landcover_class,
                   facility_type, classification_reasons, risk_score, risk_reasons,
                   population_exposed, emissions_estimate, wind_speed,
                   wind_direction, alert_status, alert_reasons
            FROM thermal_events
            ORDER BY COALESCE(risk_score, 0) DESC, first_seen DESC
            LIMIT 6
            """
        )
    ).mappings().all()

    facilities = db.execute(
        text(
            """
            SELECT facility_id, name, operator, facility_type, latitude, longitude,
                   current_risk, historical_event_count, anomalous_event_count,
                   cumulative_emissions, baseline_stats, last_incident
            FROM facilities
            ORDER BY COALESCE(current_risk, 0) DESC, anomalous_event_count DESC
            LIMIT 8
            """
        )
    ).mappings().all()

    return {
        "region": "Dahej Industrial Region, Gujarat, India",
        "summary": {key: _json_value(value) for key, value in event_summary.items()},
        "events": [
            {
                key: _json_value(value)
                for key, value in event.items()
                if key not in {"classification_reasons", "risk_reasons", "alert_reasons"}
            }
            for event in events
        ],
        "facilities": [
            {
                key: _json_value(value)
                for key, value in facility.items()
                if key != "baseline_stats"
            }
            for facility in facilities
        ],
    }


def _cache_key(question: str, region: str) -> str:
    return f"{region}:{' '.join(question.lower().split())}"


def _get_cached_answer(key: str) -> str | None:
    cached = _ANSWER_CACHE.get(key)
    if cached is None:
        return None

    created_at, answer = cached
    if time.monotonic() - created_at > _CACHE_TTL_SECONDS:
        _ANSWER_CACHE.pop(key, None)
        return None

    return answer


def _store_cached_answer(key: str, answer: str) -> None:
    if len(_ANSWER_CACHE) >= _MAX_CACHE_ENTRIES:
        oldest_key = min(_ANSWER_CACHE, key=lambda item: _ANSWER_CACHE[item][0])
        _ANSWER_CACHE.pop(oldest_key, None)
    _ANSWER_CACHE[key] = (time.monotonic(), answer)


async def _call_gemini(prompt: str, client: httpx.AsyncClient) -> str:
    """Try the configured Gemini model(s). Raises httpx.HTTPStatusError (e.g. 429
    on quota exhaustion) or httpx.RequestError on failure, so the caller can fall
    back to another provider."""
    model_names = [settings.gemini_model, "gemini-flash-latest", "gemini-2.5-flash-lite"]
    attempted_models: set[str] = set()
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{CHAT_SCOPE}\n\n{prompt}"}]},
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 180},
    }

    last_error: Exception | None = None
    for model_name in model_names:
        if not model_name or model_name in attempted_models:
            continue
        attempted_models.add(model_name)
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent"
        )
        try:
            response = await client.post(
                endpoint,
                params={"key": settings.gemini_api_key},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            parts = result["candidates"][0]["content"]["parts"]
            answer = next(part["text"] for part in parts if part.get("text")).strip()
            if answer:
                return answer
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code == 429:
                # Quota exhausted for this key - no point trying other Gemini
                # models, let the caller fall back to another provider.
                raise
            if exc.response.status_code == 404:
                continue
            raise
        except httpx.RequestError as exc:
            last_error = exc
            raise

    if last_error is not None:
        raise last_error
    raise HTTPException(status_code=502, detail="Gemini returned an invalid response.")


async def _call_groq(prompt: str, client: httpx.AsyncClient) -> str:
    """Free, fast fallback provider (Groq's OpenAI-compatible chat completions
    endpoint). Raises httpx.HTTPStatusError or httpx.RequestError on failure."""
    response = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={
            "model": settings.groq_model,
            "messages": [
                {"role": "system", "content": CHAT_SCOPE},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        },
    )
    response.raise_for_status()
    result = response.json()
    answer = result["choices"][0]["message"]["content"].strip()
    if not answer:
        raise HTTPException(status_code=502, detail="Groq returned an empty response.")
    return answer


@router.post("", response_model=ChatResponse)
async def ask_phoenix(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    if request.region != "dahej":
        raise HTTPException(
            status_code=400,
            detail="Ask Phoenix currently supports the Dahej region only.",
        )

    if not settings.gemini_api_key and not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "No chat provider is configured. Add GEMINI_API_KEY and/or "
                "GROQ_API_KEY to backend/.env."
            ),
        )

    global _LAST_REQUEST_AT
    cache_key = _cache_key(request.question, request.region)
    cached_answer = _get_cached_answer(cache_key)
    if cached_answer is not None:
        return ChatResponse(answer=cached_answer, region=request.region)

    now = time.monotonic()
    if now - _LAST_REQUEST_AT < _MIN_REQUEST_INTERVAL_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Please wait a moment before sending another Ask Phoenix question.",
        )
    _LAST_REQUEST_AT = now

    context = _load_context(db)
    prompt = (
        "Use the following live Phoenix context to answer the user. "
        "If the answer is not supported by this context, say so.\n\n"
        f"Live Phoenix context (JSON):\n{json.dumps(context, default=str)}\n\n"
        f"User question: {request.question.strip()}"
    )

    answer: str | None = None
    provider_used: str | None = None
    failures: list[str] = []

    async with httpx.AsyncClient(timeout=60) as client:
        if settings.gemini_api_key:
            try:
                answer = await _call_gemini(prompt, client)
                provider_used = "gemini"
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    failures.append("Gemini quota is exhausted for this key")
                else:
                    failures.append(f"Gemini returned {exc.response.status_code}")
            except httpx.RequestError:
                failures.append("Gemini is unreachable")

        if answer is None and settings.groq_api_key:
            try:
                answer = await _call_groq(prompt, client)
                provider_used = "groq"
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    failures.append("Groq quota is exhausted for this key")
                else:
                    failures.append(f"Groq returned {exc.response.status_code}")
            except httpx.RequestError:
                failures.append("Groq is unreachable")

    if answer is None:
        detail = (
            "; ".join(failures)
            if failures
            else "No configured chat provider could answer this request."
        )
        raise HTTPException(
            status_code=503,
            detail=f"Ask Phoenix could not get an answer right now ({detail}).",
        )

    _store_cached_answer(cache_key, answer)
    return ChatResponse(answer=answer, region=request.region, provider=provider_used)