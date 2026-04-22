from __future__ import annotations

import asyncio
from contextlib import suppress
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.errors import raise_api_error
from app.db.session import get_db
from app.models import Mistake
from app.services.ai_analysis_service import AiAnalysisError, build_provider, get_ai_capability


router = APIRouter(prefix="/ai", tags=["ai"])
SSE_KEEPALIVE_SECONDS = 15.0


class VariantOut(BaseModel):
    variant_title: str
    variant_stem: str
    variant_hint: str


@router.get("/analyze/stream")
async def analyze_stream_route(
    mistake_id: int = Query(..., ge=1),
    model: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    capability = get_ai_capability()
    if not capability["enabled"]:
        raise_api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_analysis_disabled",
            "AI analysis is disabled.",
        )

    mistake = db.scalar(
        select(Mistake)
        .options(
            joinedload(Mistake.category),
            selectinload(Mistake.tags),
            selectinload(Mistake.review_logs),
        )
        .where(Mistake.id == mistake_id)
    )
    if mistake is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "mistake_not_found",
            "Mistake not found.",
            {"mistake_id": mistake_id},
        )

    provider = build_provider()

    async def event_stream():
        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

        async def produce_events() -> None:
            try:
                async for chunk in provider.analyze_stream(mistake, model=model):
                    await queue.put(("chunk", chunk))
                await queue.put(("done", None))
            except AiAnalysisError as exc:
                await queue.put(("error", exc))

        producer_task = asyncio.create_task(produce_events())
        try:
            while True:
                try:
                    event_type, payload = await asyncio.wait_for(queue.get(), timeout=SSE_KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    if producer_task.done() and queue.empty():
                        await producer_task
                        break
                    yield ": keepalive\n\n"
                    continue

                if event_type == "chunk":
                    body = json.dumps({"delta": payload}, ensure_ascii=False)
                    yield f"data: {body}\n\n"
                    continue

                if event_type == "done":
                    yield "data: [DONE]\n\n"
                    break

                if event_type == "error":
                    exc = payload
                    body = json.dumps({"code": exc.code, "message": exc.message}, ensure_ascii=False)
                    yield f"event: error\ndata: {body}\n\n"
                    break
        finally:
            if not producer_task.done():
                producer_task.cancel()
            with suppress(asyncio.CancelledError):
                await producer_task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-variant/{mistake_id}", response_model=VariantOut)
async def generate_variant_route(
    mistake_id: int,
    model: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> VariantOut:
    capability = get_ai_capability()
    if not capability["enabled"]:
        raise_api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_analysis_disabled",
            "AI analysis is disabled.",
        )

    mistake = db.scalar(
        select(Mistake)
        .options(
            joinedload(Mistake.category),
            selectinload(Mistake.tags),
            selectinload(Mistake.review_logs),
        )
        .where(Mistake.id == mistake_id)
    )
    if mistake is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "mistake_not_found",
            "Mistake not found.",
            {"mistake_id": mistake_id},
        )

    provider = build_provider()
    try:
        result = await provider.generate_variant(mistake, model=model)
        return VariantOut(**result)
    except AiAnalysisError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        )
