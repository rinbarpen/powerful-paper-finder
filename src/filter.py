"""PaperFilter — cheap/free model stage to quickly classify and prioritize papers."""

import asyncio
import json
import logging
from string import Template
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_FILTER_PROMPT = Template(
    """你是一位AI领域论文筛选助手。请快速判断这篇论文所属领域和对AI研究者的相关性。

标题: $title
摘要: $abstract

输出JSON（不要附加其他内容）：
{"domains": ["所属子领域列表，如NLP/CV/RL/MultiAgent/Theory/ML-Systems"], "relevance": <1-5分，对AI研究者的价值>, "primary_field": "<最相关领域>", "reason": "<一句话理由>"}"""
)


class PaperFilter:
    def __init__(self, config: dict):
        filter_cfg = config.get("filter", {})
        self.model_name = filter_cfg.get("model", "gpt-4o-mini")
        self.api_base = filter_cfg.get("api_base", "")
        self.api_key = filter_cfg.get("api_key", "")
        self.top_n = filter_cfg.get("top_n", 15)
        self.concurrency = filter_cfg.get("concurrency", 10)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        raw_template = filter_cfg.get("prompt_template", "")
        self._prompt = Template(raw_template) if raw_template else DEFAULT_FILTER_PROMPT

        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.api_base,
                api_key=self.api_key,
                timeout=30.0,
            )
        return self._client

    async def filter_all(self, papers: list[dict]) -> list[dict]:
        logger.info(
            f"Filter stage: classifying {len(papers)} papers with {self.model_name}..."
        )
        tasks = [self._classify_single(p) for p in papers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        passed = []
        for paper, result in zip(papers, results):
            if isinstance(result, Exception):
                logger.warning(f"Filter failed for {paper['id']}: {result}")
                paper["filter_relevance"] = 0
                paper["filter_domain"] = ""
                continue
            if result:
                paper["filter_relevance"] = result.get("relevance", 0)
                paper["filter_domain"] = result.get("primary_field", "")
                domains = result.get("domains", [])
                if isinstance(domains, list):
                    paper["filter_domains"] = ", ".join(domains)
                else:
                    paper["filter_domains"] = str(domains)
                paper["filter_reason"] = result.get("reason", "")
                passed.append(paper)
            else:
                paper["filter_relevance"] = 0
                paper["filter_domain"] = ""

        passed.sort(key=lambda p: p["filter_relevance"], reverse=True)
        kept = passed[: self.top_n]
        logger.info(
            f"Filter stage: {len(kept)}/{len(papers)} kept "
            f"(avg relevance={sum(p['filter_relevance'] for p in kept)/len(kept):.1f})"
        )
        return kept

    async def _classify_single(self, paper: dict) -> Optional[dict]:
        async with self.semaphore:
            client = self._get_client()
            prompt = self._prompt.safe_substitute(
                title=paper["title"], abstract=paper["abstract"]
            )
            for attempt in range(3):
                try:
                    response = await client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=300,
                    )
                    raw = response.choices[0].message.content.strip()
                    return self._parse(raw, paper["id"])
                except Exception as e:
                    logger.warning(
                        f"Filter attempt {attempt + 1} failed for {paper['id']}: {e}"
                    )
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
            return None

    def _parse(self, raw: str, paper_id: str) -> Optional[dict]:
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        end = -1
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
            relevance = int(parsed.get("relevance", 0))
            if not (1 <= relevance <= 5):
                relevance = 0
            return {
                "domains": parsed.get("domains", []),
                "relevance": relevance,
                "primary_field": parsed.get("primary_field", ""),
                "reason": parsed.get("reason", ""),
            }
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning(f"Failed to parse filter response for {paper_id}: {raw[:150]}")
            return None
