"""arXiv paper fetcher — queries arXiv API for papers in specified categories and date range."""

import logging
import time
from datetime import datetime
from typing import List, Optional

import arxiv

logger = logging.getLogger(__name__)

# arXiv rate-limit handling: per-category retry with progressive backoff
CATEGORY_RETRIES = 3
BACKOFF_BASE = 30  # seconds — start at 30s, then 60s, 120s


class PaperFetcher:
    def __init__(self, config: dict, start_date: Optional[str] = None, end_date: Optional[str] = None):
        self.categories = config["arxiv"]["categories"]
        self.max_results = config["arxiv"]["max_results"]
        self.start_date = start_date
        self.end_date = end_date

    def _create_client(self, page_size: int, delay: float) -> arxiv.Client:
        client = arxiv.Client(
            page_size=min(page_size, 100),
            delay_seconds=delay,
            num_retries=5,
        )
        client._session.trust_env = False
        return client

    def fetch(self) -> List[dict]:
        seen_ids: set[str] = set()
        papers: List[dict] = []

        for cat_idx, cat in enumerate(self.categories):
            query = f"cat:{cat}"
            if self.start_date and self.end_date:
                query += f" AND submittedDate:[{self.start_date}0000 TO {self.end_date}2359]"
                logger.info(f"Fetching category: {cat} ({self.start_date} ~ {self.end_date})")
            else:
                logger.info(f"Fetching category: {cat}")

            for attempt in range(CATEGORY_RETRIES):
                try:
                    delay = 5.0 + attempt * 5  # 5s, 10s, 15s between pages
                    client = self._create_client(self.max_results, delay)
                    search = arxiv.Search(
                        query=query,
                        max_results=self.max_results,
                        sort_by=arxiv.SortCriterion.SubmittedDate,
                    )
                    for result in client.results(search):
                        if result.get_short_id() in seen_ids:
                            continue
                        seen_ids.add(result.get_short_id())
                        papers.append(
                            {
                                "id": result.get_short_id(),
                                "title": result.title.strip(),
                                "abstract": result.summary.strip().replace("\n", " "),
                                "authors": [a.name for a in result.authors],
                                "categories": list(result.categories),
                                "published": result.published,
                                "url": result.entry_id,
                            }
                        )
                    break
                except arxiv.HTTPError as e:
                    if "429" in str(e):
                        wait = BACKOFF_BASE * (2 ** attempt)
                        logger.warning(
                            f"Category {cat} got 429, attempt {attempt + 1}/{CATEGORY_RETRIES}, "
                            f"waiting {wait}s..."
                        )
                        time.sleep(wait)
                    else:
                        logger.error(f"HTTP error fetching {cat}: {e}")
                        break
                except Exception as e:
                    logger.error(f"Failed to fetch category {cat}: {e}")
                    break

            if cat_idx < len(self.categories) - 1:
                time.sleep(5)

        logger.info(f"Fetched {len(papers)} unique papers across {len(self.categories)} categories")
        return papers
