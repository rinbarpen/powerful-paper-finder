"""Dual-model LLM reviewer — concurrent calls to both models for innovation scoring."""

import asyncio
import json
import logging
import re
from string import Template
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = Template(
    """你是$model_name，一位资深的AI领域审稿专家。请对以下学术论文的创新性进行评审。

论文标题: $title
论文摘要: $abstract

请从以下维度评分（1-10分）：
1. 研究问题的前瞻性
2. 方法论的创新程度
3. 理论贡献的深度
4. 潜在影响力

请严格按照以下JSON格式回复，不要附加其他内容：
{"score": <综合得分>, "reason": "<中文简短评审理由，100字以内>"}"""
)


class Reviewer:
    def __init__(self, config: dict):
        self.models = config["models"]
        self.concurrency = config["scoring"].get("concurrency", 5)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self._clients: dict[str, AsyncOpenAI] = {}
        raw_template = config["scoring"].get("prompt_template", "")
        self._prompt = Template(raw_template) if raw_template else DEFAULT_PROMPT

    def _get_client(self, model_cfg: dict) -> AsyncOpenAI:
        key = model_cfg["name"]
        if key not in self._clients:
            self._clients[key] = AsyncOpenAI(
                base_url=model_cfg["api_base"],
                api_key=model_cfg["api_key"],
                timeout=60.0,
            )
        return self._clients[key]

    async def review_all(self, papers: list[dict]) -> list[dict]:
        tasks = [self._review_single(paper) for paper in papers]
        results = await asyncio.gather(*tasks)
        return results

    async def _review_single(self, paper: dict) -> dict:
        async with self.semaphore:
            tasks = [
                self._call_model(model_cfg, paper) for model_cfg in self.models
            ]
            model_results = await asyncio.gather(*tasks, return_exceptions=True)

        scores = {}
        reasons = {}
        all_keywords = []
        fields = []
        general_votes = []
        for model_cfg, result in zip(self.models, model_results):
            if isinstance(result, Exception):
                logger.error(f"Model {model_cfg['name']} failed for {paper['id']}: {result}")
                scores[model_cfg["name"]] = None
                reasons[model_cfg["name"]] = f"Error: {result}"
            elif result is not None:
                scores[model_cfg["name"]] = result.get("score")
                reasons[model_cfg["name"]] = result.get("reason", "")
                all_keywords.extend(result.get("keywords", []))
                if result.get("field"):
                    fields.append(result["field"])
                general_votes.append(result.get("general", False))
            else:
                scores[model_cfg["name"]] = None
                reasons[model_cfg["name"]] = "No response"

        paper["model_scores"] = scores
        paper["model_reasons"] = reasons
        paper["keywords"] = list(dict.fromkeys(all_keywords))
        paper["field"] = fields[0] if fields else ""
        paper["general"] = any(general_votes)
        return paper

    async def _call_model(self, model_cfg: dict, paper: dict) -> Optional[dict]:
        client = self._get_client(model_cfg)
        prompt = self._prompt.safe_substitute(
            model_name=model_cfg["name"],
            title=paper["title"],
            abstract=paper["abstract"],
        )

        for attempt in range(3):
            try:
                response = await client.chat.completions.create(
                    model=model_cfg["name"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500,
                )
                raw = response.choices[0].message.content.strip()
                return self._parse_response(raw, model_cfg["name"])
            except Exception as e:
                logger.warning(
                    f"Model {model_cfg['name']} attempt {attempt + 1} failed for {paper['id']}: {e}"
                )
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
        return None

    def _parse_response(self, raw: str, model_name: str) -> Optional[dict]:
        parsed = self._extract_json(raw, model_name)
        if parsed is None:
            return None
        try:
            score = float(parsed["score"])
            if not (1 <= score <= 10):
                return None
            return {
                "score": score,
                "reason": parsed.get("reason", ""),
                "keywords": parsed.get("keywords", []),
                "field": parsed.get("field", ""),
                "general": parsed.get("general", False),
            }
        except (KeyError, ValueError):
            logger.warning(f"Failed to parse {model_name} response: {raw[:200]}")
            return None

    def _extract_json(self, raw: str, model_name: str) -> Optional[dict]:
        start = raw.find("{")
        if start == -1:
            logger.warning(f"No JSON found in {model_name} response: {raw[:200]}")
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
            logger.warning(f"Unterminated JSON in {model_name} response: {raw[:200]}")
            return None
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {model_name} response: {raw[start:end + 1][:200]}")
            return None
