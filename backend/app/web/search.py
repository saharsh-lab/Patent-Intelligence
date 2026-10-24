"""Web search providers.

Tavily (needs TAVILY_API_KEY; returns the relevant parts of each page, built for AI
answers) or Wikipedia (no key; encyclopedia articles only). Results are used as evidence
for one answer and never stored in the user's library.
"""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)
# Wikimedia's policy requires a descriptive agent with contact details (403 otherwise)
USER_AGENT = (
    "PatentIntelligence/1.0 "
    "(https://github.com/saharsh-lab/Patent-Intelligence; student project) "
    "httpx"
)


# A site that does not accept a connection within this is down or blocked: give up, so
# the other sources can answer. Observed (2026-10-22): Wikipedia unreachable from this
# network; 15 s timeouts plus a retry held every answer up by 31 s.
CONNECT_SECONDS = 5.0


def _retry(call):
    """One retry after a dropped connection or a slow reply, but not after a connection
    attempt that used up its timeout: that site is unreachable (on this network the
    failure arrives as ConnectError after the timeout, not as ConnectTimeout)."""
    started = time.monotonic()
    try:
        return call()
    except (httpx.ConnectTimeout, httpx.ConnectError):
        if time.monotonic() - started >= CONNECT_SECONDS * 0.8:
            raise
        time.sleep(1.0)
        return call()
    except httpx.TransportError:
        time.sleep(1.0)
        return call()


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
    # Matches words, not questions: search with key words. Observed (2026-10-22): for
    # "How do solid-state batteries work?" every Wikipedia passage used was about
    # solid-state drives.
    keyword_search = False

    def search(self, query: str, max_results: int) -> list[WebResult]:  # pragma: no cover
        raise NotImplementedError


class TavilySearch(WebSearch):
    name = "tavily"
    label = "Web (Tavily)"
    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: float = 20.0, http: httpx.Client | None = None):
        self._key = api_key
        self._http = http or httpx.Client(timeout=httpx.Timeout(timeout, connect=CONNECT_SECONDS))

    def search(self, query: str, max_results: int) -> list[WebResult]:
        try:
            response = _retry(
                lambda: self._http.post(
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
            )
        except httpx.HTTPError:
            raise AppError(
                "Could not reach the web search service.", code="web_search_unreachable"
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
    """No key needed: search, then the full text of the best articles, split into
    passages by section. The introduction alone often lacks the answer (2026-10-11: "how
    do wireless chargers detect metal objects?" — the detection method is in the body of
    "Inductive charging", not its introduction)."""

    name = "wikipedia"
    label = "Wikipedia"
    keyword_search = True
    API = "https://en.wikipedia.org/w/api.php"
    FULL_ARTICLES = 3  # the API returns one full article per request
    PASSAGE_CHARS = 900
    PASSAGES_PER_ARTICLE = 20
    SKIP_SECTIONS = {
        "see also",
        "references",
        "external links",
        "further reading",
        "notes",
        "bibliography",
        "sources",
        "citations",
        "footnotes",
    }

    def __init__(self, timeout: float = 15.0, http: httpx.Client | None = None):
        self._http = http or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=CONNECT_SECONDS),
            headers={"User-Agent": USER_AGENT},
        )

    def _get(self, **params) -> dict:
        return _retry(lambda: self._http.get(self.API, params={**params, "format": "json"})).json()

    def search(self, query: str, max_results: int) -> list[WebResult]:
        try:
            found = self._get(
                action="query", list="search", srsearch=query[:300], srlimit=max_results
            )
            titles = [hit["title"] for hit in found.get("query", {}).get("search", [])]
            # One request per article: fetched at the same time, kept in Wikipedia's order
            with ThreadPoolExecutor(max_workers=self.FULL_ARTICLES) as pool:
                pages = list(
                    pool.map(
                        lambda title: self._get(
                            action="query",
                            prop="extracts|info",
                            explaintext=1,
                            inprop="url",
                            titles=title,
                        ),
                        titles[: self.FULL_ARTICLES],
                    )
                )
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(
                f"Web search failed: {type(exc).__name__}", code="web_search_failed"
            ) from None
        results = []
        for data in pages:  # keep Wikipedia's ranking
            for page in data.get("query", {}).get("pages", {}).values():
                title, url = page.get("title") or "", page.get("fullurl") or ""
                for section, text in self.passages(page.get("extract") or ""):
                    label = f"{title} — {section}" if section else title
                    results.append(WebResult(label, url, text))
        return results

    @classmethod
    def passages(cls, extract: str) -> list[tuple[str, str]]:
        """Split an article ("== Heading ==" lines between paragraphs) into passages of
        about PASSAGE_CHARS, each labelled with its section; reference lists are skipped."""
        out: list[tuple[str, str]] = []
        section, buffer = "", ""

        def flush():
            nonlocal buffer
            if buffer.strip():
                out.append((section, _clean(buffer)))
            buffer = ""

        for line in extract.splitlines():
            heading = re.fullmatch(r"\s*(=+)\s*(.*?)\s*\1\s*", line)
            if heading:
                flush()
                level, name = len(heading.group(1)), heading.group(2)
                if level == 2:
                    section = name
                elif section.split(" — ")[0].lower() not in cls.SKIP_SECTIONS:
                    section = f"{section.split(' — ')[0]} — {name}" if section else name
                continue
            if section.split(" — ")[0].lower() in cls.SKIP_SECTIONS or not line.strip():
                continue
            if buffer and len(buffer) + len(line) > cls.PASSAGE_CHARS:
                flush()
            buffer += " " + line
        flush()
        return out[: cls.PASSAGES_PER_ARTICLE]


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
