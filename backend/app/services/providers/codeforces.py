from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import httpx
import markdownify as md_converter
from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

from app.schemas.problem_import import ProblemUrlPreviewResponse
from app.services.providers.base import ProblemImportError


_CF_URL_PATTERNS = (
    ("problemset", re.compile(r"^/problemset/problem/(?P<contest>\d+)/(?P<index>[a-z0-9]+)/*$", re.I)),
    ("contest", re.compile(r"^/contest/(?P<contest>\d+)/problem/(?P<index>[a-z0-9]+)/*$", re.I)),
    ("gym", re.compile(r"^/gym/(?P<contest>\d+)/problem/(?P<index>[a-z0-9]+)/*$", re.I)),
)

_USER_AGENT = "Mozilla/5.0 (compatible; CodeRecall/1.0)"


def _parse_codeforces_url(url: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "codeforces.com":
        raise ProblemImportError("invalid_url", "URL must be a Codeforces problem link.", 400)

    for kind, pattern in _CF_URL_PATTERNS:
        match = pattern.match(parsed.path)
        if match:
            return match.group("contest"), match.group("index").upper(), kind

    raise ProblemImportError("invalid_url", "Could not extract Codeforces problem id from URL.", 400)


def _map_rating_to_difficulty(rating: Optional[int]) -> int:
    if rating is None:
        return 3
    if rating <= 1000:
        return 1
    if rating <= 1500:
        return 2
    if rating <= 1900:
        return 3
    if rating <= 2400:
        return 4
    return 5


def _warning_response(
    *,
    provider: str = "codeforces",
    source_url: str,
    external_id: str,
    title: str,
    warning: str,
) -> ProblemUrlPreviewResponse:
    return ProblemUrlPreviewResponse(
        provider=provider,
        source_url=source_url,
        external_id=external_id,
        title=title,
        difficulty_raw="unrated",
        difficulty=3,
        tags=[],
        stem_markdown="",
        warnings=[warning],
    )


def _preprocess_mathjax(statement: Tag) -> None:
    for script in statement.find_all("script"):
        type_ = script.get("type", "")
        latex = script.string or ""
        if "mode=display" in type_:
            script.replace_with(NavigableString(f"$${latex}$$"))
        elif type_.startswith("math/tex"):
            script.replace_with(NavigableString(f"${latex}$"))


def _extract_tags_and_rating(soup: BeautifulSoup) -> tuple[list[str], Optional[int]]:
    tags: list[str] = []
    rating: Optional[int] = None

    for tag_box in soup.select(".tag-box"):
        text = tag_box.get_text(" ", strip=True)
        if not text:
            continue
        if text.startswith("*") and text[1:].isdigit():
            rating = int(text[1:])
        else:
            tags.append(text)

    return tags, rating


async def fetch_preview(url: str, client: httpx.AsyncClient) -> ProblemUrlPreviewResponse:
    contest, index, kind = _parse_codeforces_url(url)
    external_id = f"{contest}{index}"
    source_url = f"Codeforces {external_id}"

    try:
        response = await client.get(url, headers={"User-Agent": _USER_AGENT})
    except httpx.TimeoutException as exc:
        raise ProblemImportError("provider_timeout", "Codeforces request timed out.", 504) from exc
    except httpx.HTTPError as exc:
        raise ProblemImportError("provider_unavailable", "Could not reach Codeforces.", 502) from exc

    if response.status_code == 403 and kind == "gym":
        return _warning_response(
            source_url=f"Codeforces Gym{external_id}",
            external_id=f"gym{external_id}",
            title=f"Codeforces Gym {external_id}",
            warning="Gym/私有比赛无法获取题面，请手动填写",
        )

    if response.status_code == 404:
        raise ProblemImportError("problem_not_found", "Problem not found on Codeforces.", 404)

    if response.status_code not in (200, 301, 302):
        raise ProblemImportError("provider_error", f"Codeforces returned {response.status_code}.", 502)

    soup = BeautifulSoup(response.text, "lxml")
    statement = soup.select_one(".problem-statement")
    if statement is None:
        return _warning_response(
            source_url=source_url,
            external_id=external_id,
            title=f"Codeforces {external_id}",
            warning="题面抓取失败，请手动填写",
        )

    _preprocess_mathjax(statement)
    title_node = statement.select_one(".title")
    title = title_node.get_text(" ", strip=True) if title_node else f"Codeforces {external_id}"
    stem_markdown = md_converter.markdownify(str(statement), heading_style="ATX").strip()
    tags, rating = _extract_tags_and_rating(soup)
    difficulty_raw = str(rating) if rating is not None else "unrated"

    return ProblemUrlPreviewResponse(
        provider="codeforces",
        source_url=source_url,
        external_id=external_id,
        title=title,
        difficulty_raw=difficulty_raw,
        difficulty=_map_rating_to_difficulty(rating),
        tags=tags,
        stem_markdown=stem_markdown,
        warnings=[],
    )
