"""Web search providers.

Tavily (needs TAVILY_API_KEY; returns the relevant parts of each page, built for AI
answers) or Wikipedia (no key; encyclopedia articles only). Results are used as evidence
for one answer and never stored in the user's library.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)
# Wikimedia's policy requires a descriptive agent with contact details (403 otherwise)
USER_AGENT = (
    "PatentIntelligence/1.0 "
    "(https://github.com/saharsh-lab/Agentic-RAG-System-for-Patent-analysis; student project) "
    "httpx"
)


@dataclass
class WebResult:
    title: str
    url: str
    content: str  # the page text used as evidence
    score: float | None = None

    @property
    def site(self) -> str:
        return urlparse(self.url).netloc.removeprefix("www.")


class WebSearch:
    name = "web"
    label = "Web"

    def search(self, query: str, max_results: int) -> list[WebResult]:  # pragma: no cover
        raise NotImplementedError


class TavilySearch(WebSearch):
    name = "tavily"
    label = "Web (Tavily)"
    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: float = 20.0, http: httpx.Client | None = None):
        self._key = api_key
        self._http = http or httpx.Client(timeout=timeout)

    def search(self, query: str, max_results: int) -> list[WebResult]:
        try:
            response = self._http.post(
                self.URL,
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "query": query[:400],
                    "search_depth": "basic",  # 1 credit; returns the relevant chunks
                    "chunks_per_source": 3,
                    "max_results": max_results,
                    "include_answer": False,  # we write and verify our own answer
                },
            )
        except httpx.HTTPError as exc:
            raise AppError(
                f"Web search failed: {type(exc).__name__}", code="web_search_failed"
            ) from None
        if response.status_code in (401, 403):
            raise AppError(
                "Web search key rejected (check TAVILY_API_KEY).", code="web_search_auth"
            )
        if response.status_code == 429 or response.status_code == 432:
            raise AppError("Web search quota used up for now.", code="web_search_quota")
        if response.status_code >= 400:
            raise AppError(
                f"Web search failed (HTTP {response.status_code}).", code="web_search_failed"
            )
        results = []
        for item in response.json().get("results", []):
            content = _clean(item.get("content") or "")
            if item.get("url") and content:
                results.append(
                    WebResult(
                        item.get("title") or item["url"], item["url"], content, item.get("score")
                    )
                )
        return results


class WikipediaSearch(WebSearch):
    """No key needed: search, then the plain-text introduction of each article."""

    name = "wikipedia"
    label = "Wikipedia"
    API = "https://en.wikipedia.org/w/api.php"

    def __init__(self, timeout: float = 15.0, http: httpx.Client | None = None):
        self._http = http or httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def search(self, query: str, max_results: int) -> list[WebResult]:
        try:
            found = self._http.get(
                self.API,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query[:300],
                    "srlimit": max_results,
                    "format": "json",
                },
            ).json()
            titles = [hit["title"] for hit in found.get("query", {}).get("search", [])]
            if not titles:
                return []
            pages = self._http.get(
                self.API,
                params={
                    "action": "query",
                    "prop": "extracts|info",
                    "exintro": 1,
                    "explaintext": 1,
                    "inprop": "url",
                    "titles": "|".join(titles),
                    "format": "json",
                },
            ).json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(
                f"Web search failed: {type(exc).__name__}", code="web_search_failed"
            ) from None
        by_title = {
            page.get("title"): page for page in pages.get("query", {}).get("pages", {}).values()
        }
        results = []
        for title in titles:  # keep Wikipedia's ranking
            page = by_title.get(title) or {}
            text = _clean(page.get("extract") or "")[:2500]
            if text:
                results.append(WebResult(title, page.get("fullurl") or "", text))
        return results


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_web_search(settings: Settings) -> WebSearch | None:
    provider = settings.web_search_provider
    key = settings.tavily_api_key.get_secret_value()
    if provider == "off":
        return None
    if provider == "tavily" or (provider == "auto" and key):
        if not key:
            logger.warning("WEB_SEARCH_PROVIDER=tavily but TAVILY_API_KEY is empty")
            return None
        return TavilySearch(key)
    return WikipediaSearch()
