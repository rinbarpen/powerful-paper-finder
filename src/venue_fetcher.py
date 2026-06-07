"""Venue paper fetcher — searches conference proceedings via Semantic Scholar API."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from src.ccf_venues import ALL_CCF_VENUES, VenueInfo

logger = logging.getLogger(__name__)

S2_API_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,authors,year,venue,externalIds,url,publicationDate,paperId"
MAX_RETRIES = 3
BACKOFF_BASE = 10
DELAY_NO_KEY = 3.5  # seconds between requests without API key (100 req/5min)
DELAY_WITH_KEY = 1.0  # seconds with API key (100 req/sec)


class VenueFetcher:
    def __init__(
        self,
        config: dict,
        venue_keys: Optional[list[str]] = None,
        years: Optional[list[int]] = None,
    ):
        venues_cfg = config.get("venues", {})
        ss_cfg = config.get("semantic_scholar", {})

        self._venue_keys = venue_keys or venues_cfg.get("list", [])
        if not self._venue_keys:
            self._venue_keys = list(CCF_A_VENUES.keys())

        self._years = years or venues_cfg.get("years", [datetime.now(timezone.utc).year])
        self._max_per_venue = venues_cfg.get("max_results_per_venue", 100)
        self._api_key = ss_cfg.get("api_key", "")
        self._delay = DELAY_WITH_KEY if self._api_key else DELAY_NO_KEY
        self._request_times: list[float] = []

    async def fetch(self) -> list[dict]:
        papers: list[dict] = []
        seen_ids: set[str] = set()

        for venue_key in self._venue_keys:
            venue_info = ALL_CCF_VENUES.get(venue_key)
            if venue_info is None:
                logger.warning(f"Unknown venue key '{venue_key}' — skipping")
                continue

            for year in self._years:
                logger.info(f"Fetching venue: {venue_key} ({year})")
                offset = 0
                while True:
                    result = await self._search_venue(venue_info, year, offset, self._max_per_venue)
                    if result is None:
                        break

                    batch = result.get("data", [])
                    if not batch:
                        break

                    for paper_data in batch:
                        mapped = self._map_to_paper(paper_data, venue_key, venue_info, year)
                        if mapped and mapped["id"] not in seen_ids:
                            seen_ids.add(mapped["id"])
                            papers.append(mapped)

                    next_offset = result.get("next")
                    if next_offset is not None:
                        offset = next_offset
                    else:
                        break

            # rate limiting handled inside _search_venue via _rate_limit()

        logger.info(
            f"VenueFetcher: fetched {len(papers)} unique papers "
            f"across {len(self._venue_keys)} venues"
        )
        return papers

    async def _search_venue(
        self,
        venue_info: VenueInfo,
        year: int,
        offset: int = 0,
        limit: int = 100,
    ) -> Optional[dict]:
        await self._rate_limit()

        query = f"venue:{venue_info.ss_venue_name}"
        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": S2_FIELDS,
            "year": f"{year}-{year}",
        }
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(S2_API_BASE, params=params, headers=headers)
                self._request_times.append(time.monotonic())

                if response.status_code == 429:
                    wait = BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        f"Rate limited for {venue_info.ss_venue_name} ({year}), "
                        f"retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code == 404:
                    logger.info(f"No results for {venue_info.ss_venue_name} ({year})")
                    return None

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP {e.response.status_code} for {venue_info.ss_venue_name} ({year}), "
                    f"attempt {attempt + 1}/{MAX_RETRIES}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
            except Exception as e:
                logger.warning(
                    f"Request failed for {venue_info.ss_venue_name} ({year}): {e}, "
                    f"attempt {attempt + 1}/{MAX_RETRIES}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))

        return None

    async def _rate_limit(self):
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < 60]
        if self._request_times:
            since_last = now - max(self._request_times)
            if since_last < self._delay:
                await asyncio.sleep(self._delay - since_last)

    def _map_to_paper(
        self,
        paper_data: dict,
        venue_key: str,
        venue_info: VenueInfo,
        year: int,
    ) -> Optional[dict]:
        abstract = (paper_data.get("abstract") or "").strip()
        if not abstract:
            return None

        title = (paper_data.get("title") or "").strip()
        if not title:
            return None

        external_ids = paper_data.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv", "")

        paper_id: str
        if arxiv_id:
            paper_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        else:
            paper_id = f"ss-{paper_data.get('paperId', 'unknown')}"

        authors = []
        for a in paper_data.get("authors", []):
            if isinstance(a, dict):
                name = a.get("name", "")
                if name:
                    authors.append(name)
            elif isinstance(a, str) and a:
                authors.append(a)

        pub_date_str = paper_data.get("publicationDate", "")
        if pub_date_str:
            try:
                published = datetime.strptime(pub_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                published = datetime(year, 6, 15, tzinfo=timezone.utc)
        else:
            published = datetime(year, 6, 15, tzinfo=timezone.utc)

        url = paper_data.get("url", "")
        if not url:
            pid = paper_data.get("paperId", "")
            if pid:
                url = f"https://www.semanticscholar.org/paper/{pid}"

        return {
            "id": paper_id,
            "title": title,
            "abstract": abstract.replace("\n", " "),
            "authors": authors,
            "categories": [],
            "published": published,
            "url": url,
            "source": "semantic_scholar",
            "venue": venue_key,
            "venue_full_name": venue_info.full_name,
            "ccf_level": venue_info.level,
            "year": year,
            "external_ids": external_ids,
        }
