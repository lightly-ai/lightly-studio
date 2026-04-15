"""Translate natural language to a DSL filter query via OpenAI."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

translate_query_router = APIRouter()

_OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

_SYSTEM_PROMPT = """\
You are a query DSL translator for an image dataset filtering tool.
Convert the user's natural language description into a DSL filter expression.

Available fields (use the exact IDs below):
  tag          (text)   — image tag / label name
  file_name    (text)   — image file name
  created_at   (date)   — creation date, format YYYY-MM-DD
  width        (number) — image width in pixels
  height       (number) — image height in pixels

DSL syntax rules:
  field: value              text equality        e.g.  tag: production
  field: -value             text NOT equal       e.g.  tag: -test
  field: contains value     text contains        e.g.  file_name: contains png
  field: -contains value    text NOT contains    e.g.  tag: -contains draft
  field: >number            greater than         e.g.  width: >1920
  field: >=number           greater or equal     e.g.  width: >=1920
  field: <number            less than            e.g.  height: <720
  field: <=number           less or equal        e.g.  width: <=3840
  field: >"YYYY-MM-DD"      date comparison      e.g.  created_at: >"2024-01-01"
  expr and expr             logical AND          e.g.  tag: train and width: >1920
  expr or expr              logical OR           e.g.  tag: train or tag: val
  (expr and expr)           grouping

Examples:
  "images wider than 4K"          →  width: >3840
  "tagged production"             →  tag: production
  "not tagged test"               →  tag: -test
  "PNG files"                     →  file_name: contains png
  "recent large images"           →  created_at: >"2024-01-01" and width: >1920
  "HD or 4K images"               →  width: >=1280 or width: >=3840
  "production images wider than fullHD"  →  tag: production and width: >1920

Reply with ONLY the DSL expression, nothing else. \
If the query cannot be translated, reply with an empty string.\
"""


class TranslateQueryRequest(BaseModel):
    text: str


class TranslateQueryResponse(BaseModel):
    query: str


@translate_query_router.post("/translate_query", response_model=TranslateQueryResponse)
async def translate_query(request: TranslateQueryRequest) -> TranslateQueryResponse:
    """Translate a natural language string into a SVAR filter DSL expression."""
    if not _OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {_OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": request.text},
                ],
                "temperature": 0,
                "max_tokens": 200,
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="OpenAI API error")

    query = response.json()["choices"][0]["message"]["content"].strip()
    return TranslateQueryResponse(query=query)
