#!/usr/bin/env python3
"""arXiv Paper Finder — daily arXiv paper collector with dual-model AI review.

Usage:
    python main.py                              # Full run with config.yml
    python main.py --mock                       # Test with mock data (no API calls)
    python main.py --max-results 5              # Limit papers fetched
"""

import argparse
import asyncio
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.fetcher import PaperFetcher
from src.venue_fetcher import VenueFetcher
from src.filter import PaperFilter
from src.reviewer import Reviewer
from src.scorer import aggregate_scores
from src.exporter import export, export_json
from src.venue_fetcher import VenueFetcher


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"run_{date_str}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config(config_path: str, mock: bool = False) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = f.read()

    def _resolve_env(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if mock:
            return "mock-key"
        logger = logging.getLogger("main")
        logger.warning(f"Env var {var_name} not set — skipping dependent config")
        return ""

    raw = re.sub(r"\$\{(\w+)\}", _resolve_env, raw)
    return yaml.safe_load(raw)


def _mock_papers() -> list[dict]:
    from datetime import datetime, timezone
    return [
        {
            "id": "2505.00001",
            "title": "Scaling Language Models with Sparse Attention Mechanisms for Long-Context Reasoning",
            "abstract": (
                "We introduce a novel sparse attention mechanism that achieves linear complexity "
                "while preserving retrieval accuracy. Our method, SparseFormer, uses learned sparsity "
                "patterns combined with a lightweight routing network to select relevant key-value pairs. "
                "Experiments across 8 long-context benchmarks show 2.3x speedup with <1% quality degradation."
            ),
            "authors": ["Alice Chen", "Bob Wang", "Charlie Liu"],
            "categories": ["cs.CL", "cs.LG"],
            "published": datetime.now(timezone.utc),
            "url": "https://arxiv.org/abs/2505.00001",
            "source": "arxiv",
        },
        {
            "id": "2505.00002",
            "title": "A Comprehensive Survey of Pruning Techniques in Deep Neural Networks",
            "abstract": (
                "We survey over 200 papers on neural network pruning from 2019-2025. The survey covers "
                "unstructured pruning, structured pruning, dynamic pruning, and post-training pruning. "
                "We provide a unified taxonomy and benchmark 15 representative methods on standard datasets."
            ),
            "authors": ["Diana Park", "Evan Zhou"],
            "categories": ["cs.LG", "cs.CV"],
            "published": datetime.now(timezone.utc),
            "url": "https://arxiv.org/abs/2505.00002",
            "source": "arxiv",
        },
        {
            "id": "2505.00003",
            "title": "DRAGON: Dynamic Retrieval-Augmented Generation with Online Neural Memory",
            "abstract": (
                "We propose DRAGON, a framework that dynamically decides when and what to retrieve from "
                "a continuously updated neural memory. Unlike static RAG systems, DRAGON learns to interpolate "
                "between parametric knowledge and retrieved information based on query uncertainty. "
                "On multi-hop QA and fact verification tasks, DRAGON outperforms static RAG by 12.3%."
            ),
            "authors": ["Frank Zhang", "Grace Kim", "Henry Patel", "Iris Wu"],
            "categories": ["cs.CL", "cs.AI"],
            "published": datetime.now(timezone.utc),
            "url": "https://arxiv.org/abs/2505.00003",
            "source": "arxiv",
        },
        {
            "id": "2505.00004",
            "title": "Improving Image Classification via Data Augmentation with Diffusion Models",
            "abstract": (
                "We present DiffAug, a data augmentation pipeline that leverages pre-trained diffusion "
                "models to generate realistic training samples. DiffAug uses classifier-guided generation "
                "to produce samples near decision boundaries, improving generalization on ImageNet by "
                "2.1% top-1 accuracy compared to standard augmentation baselines."
            ),
            "authors": ["Jack Lee", "Karen Sun"],
            "categories": ["cs.CV", "cs.AI"],
            "published": datetime.now(timezone.utc),
            "url": "https://arxiv.org/abs/2505.00004",
            "source": "arxiv",
        },
        {
            "id": "2505.00005",
            "title": "Towards Robust Federated Learning: A Game-Theoretic Approach to Incentive Alignment",
            "abstract": (
                "We frame federated learning participation as a Stackelberg game where the central server "
                "designs incentive mechanisms and clients respond strategically. Our mechanism achieves "
                "Nash equilibrium under rational agent assumptions, improving participation rates by "
                "35% while maintaining model quality. Theoretical guarantees are validated on CIFAR-100 and "
                "Federated EMNIST benchmarks."
            ),
            "authors": ["Mike Brown", "Nancy Davis", "Oscar Turner"],
            "categories": ["cs.LG", "cs.GT"],
            "published": datetime.now(timezone.utc),
            "url": "https://arxiv.org/abs/2505.00005",
            "source": "arxiv",
        },
        {
            "id": "2505.00006",
            "title": "LLM-as-Judge: An Empirical Study of Large Language Models for Automated Evaluation",
            "abstract": (
                "We systematically evaluate 12 LLMs as automated judges across text generation, "
                "summarization, and dialogue tasks. Our findings reveal that GPT-4 class models achieve "
                "0.82 Spearman correlation with human judges, but exhibit systematic biases towards "
                "verbose outputs and certain response formats. We propose debiasing strategies that "
                "improve alignment by 8%."
            ),
            "authors": ["Patricia Green"],
            "categories": ["cs.CL", "cs.AI"],
            "published": datetime.now(timezone.utc),
            "url": "https://arxiv.org/abs/2505.00006",
            "source": "arxiv",
        },
    ]


def _mock_review(papers: list[dict], model_names: list[str]) -> list[dict]:
    import random
    rng = random.Random(42)
    for i, paper in enumerate(papers):
        scores = {}
        reasons = {}
        for name in model_names:
            s = round(rng.uniform(5.0, 9.5), 1)
            scores[name] = s
            reasons[name] = _mock_reason(s)
        paper["model_scores"] = scores
        paper["model_reasons"] = reasons
        paper["keywords"] = ["深度学习", "注意力机制", "预训练"]
        paper["field"] = "自然语言处理"
        paper["general"] = i % 2 == 0
    return papers


def _mock_reason(score: float) -> str:
    if score >= 8.5:
        return "方法创新性强，理论分析扎实，实验充分，具有重要影响力"
    elif score >= 7.0:
        return "有一定创新性，实验设计合理，但在理论深度上可进一步挖掘"
    elif score >= 6.0:
        return "增量改进明显，但核心思路与现有工作较为接近"
    else:
        return "方法与其他工作重叠较多，创新性有限"


def _mock_venue_papers(years: list[int]) -> list[dict]:
    from datetime import datetime, timezone

    mocks = [
        {
            "id": "2212.08000",
            "title": "EfficientViT: Multi-Scale Linear Attention for High-Resolution Dense Prediction",
            "abstract": (
                "We present EfficientViT, a new family of high-resolution vision models "
                "with multi-scale linear attention. Unlike prior ViT models, EfficientViT "
                "achieves linear memory complexity with respect to image resolution while "
                "maintaining strong performance across segmentation and detection tasks."
            ),
            "authors": ["Xianing Chen", "Qi Zhang", "Han Hu"],
            "categories": [],
            "published": datetime(2025, 6, 15, tzinfo=timezone.utc),
            "url": "https://arxiv.org/abs/2212.08000",
            "source": "semantic_scholar",
            "venue": "CVPR",
            "venue_full_name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
            "ccf_level": "A",
            "year": years[0] if years else 2025,
            "external_ids": {"ArXiv": "2212.08000"},
        },
        {
            "id": "ss-mock-venue-001",
            "title": "A Novel Approach to 3D Scene Understanding from Single Images via Neural Radiance Fields",
            "abstract": (
                "We introduce a transformer-based approach that combines neural radiance fields "
                "with monocular depth estimation for robust 3D scene understanding from a single "
                "RGB image. Our method achieves state-of-the-art results on KITTI and NYUv2."
            ),
            "authors": ["Yue Wang", "Jian Sun"],
            "categories": [],
            "published": datetime(years[0] if years else 2025, 6, 16, tzinfo=timezone.utc),
            "url": "https://www.semanticscholar.org/paper/mock-venue-001",
            "source": "semantic_scholar",
            "venue": "CVPR",
            "venue_full_name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
            "ccf_level": "A",
            "year": years[0] if years else 2025,
            "external_ids": {},
        },
        {
            "id": "2306.01000",
            "title": "Scaling Data Generation for Vision-Language Models via Synthetic Captioning Pipelines",
            "abstract": (
                "We propose a scalable synthetic captioning pipeline that combines LLMs with "
                "diffusion models to generate high-quality image-text pairs. Our generated data "
                "improves CLIP-style training by 3.5% on zero-shot classification benchmarks."
            ),
            "authors": ["Ming Li", "Sarah Chen", "David Wu"],
            "categories": [],
            "published": datetime(2025, 12, 10, tzinfo=timezone.utc),
            "url": "https://arxiv.org/abs/2306.01000",
            "source": "semantic_scholar",
            "venue": "NeurIPS",
            "venue_full_name": "Conference on Neural Information Processing Systems",
            "ccf_level": "A",
            "year": years[0] if years else 2025,
            "external_ids": {"ArXiv": "2306.01000"},
        },
        {
            "id": "ss-mock-venue-002",
            "title": "Learning Robust Policies via Adversarial Multi-Agent Reinforcement Learning",
            "abstract": (
                "We formulate multi-agent policy learning as an adversarial game where agents "
                "must cooperate while defending against adversarial perturbations. Our approach "
                "achieves 2x robustness improvement over standard MARL baselines."
            ),
            "authors": ["Tom Brown", "Lisa Zhang"],
            "categories": [],
            "published": datetime(2025, 2, 22, tzinfo=timezone.utc),
            "url": "https://www.semanticscholar.org/paper/mock-venue-002",
            "source": "semantic_scholar",
            "venue": "AAAI",
            "venue_full_name": "AAAI Conference on Artificial Intelligence",
            "ccf_level": "A",
            "year": years[0] if years else 2025,
            "external_ids": {},
        },
    ]
    return mocks


def _deduplicate_papers(papers: list[dict]) -> list[dict]:
    seen_arxiv: dict[str, dict] = {}
    seen_title: dict[str, dict] = {}
    result: list[dict] = []

    for p in papers:
        ext_ids = p.get("external_ids", {}) or {}
        arxiv_id = ext_ids.get("ArXiv", "")
        if arxiv_id:
            normalized = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
            if normalized in seen_arxiv:
                existing = seen_arxiv[normalized]
                if p.get("source") == "semantic_scholar":
                    for i, item in enumerate(result):
                        if item is existing:
                            result[i] = p
                            break
                    seen_arxiv[normalized] = p
                continue
            seen_arxiv[normalized] = p

        title_key = p.get("title", "").strip().lower()
        if title_key:
            if title_key in seen_title:
                existing = seen_title[title_key]
                if len(p.get("abstract", "")) > len(existing.get("abstract", "")):
                    for i, item in enumerate(result):
                        if item is existing:
                            result[i] = p
                            break
                    seen_title[title_key] = p
                continue
            seen_title[title_key] = p

        result.append(p)

    return result


async def run(config: dict, mock: bool = False, start_date: str = None, end_date: str = None,
              source: str = None, venue_years: list[int] = None) -> None:
    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("arXiv Paper Finder — Starting run")
    if mock:
        logger.info("MOCK MODE — using simulated data")
    if start_date and end_date:
        logger.info(f"Date range: {start_date} ~ {end_date}")
    logger.info("=" * 60)

    effective_source = source or config.get("source", "arxiv")
    logger.info(f"Source: {effective_source}")

    all_papers: list[dict] = []

    if effective_source in ("arxiv", "all"):
        if mock:
            papers = _mock_papers()
            logger.info(f"Generated {len(papers)} mock arXiv papers")
        else:
            fetcher = PaperFetcher(config, start_date=start_date, end_date=end_date)
            papers = fetcher.fetch()
            for p in papers:
                p["source"] = "arxiv"
            logger.info(f"Fetched {len(papers)} arXiv papers")
        all_papers.extend(papers)

    if effective_source in ("venues", "all"):
        if mock:
            venue_papers = _mock_venue_papers(venue_years or [2025])
            logger.info(f"Generated {len(venue_papers)} mock venue papers")
        else:
            venue_fetcher = VenueFetcher(config, years=venue_years)
            venue_papers = await venue_fetcher.fetch()
            logger.info(f"Fetched {len(venue_papers)} venue papers")
        all_papers.extend(venue_papers)

    if effective_source == "all":
        before_dedup = len(all_papers)
        all_papers = _deduplicate_papers(all_papers)
        logger.info(f"Deduplication: {before_dedup} -> {len(all_papers)} papers")

    papers = all_papers

    if not papers:
        logger.warning("No papers. Exiting.")
        return

    if mock:
        model_names = [m["name"] for m in config.get("models", [])]
        papers = _mock_review(papers, model_names)
        logger.info("Mock review complete")
    else:
        filter_cfg = config.get("filter", {})
        if filter_cfg.get("api_key") and filter_cfg.get("api_base"):
            filterer = PaperFilter(config)
            papers = await filterer.filter_all(papers)
            if not papers:
                logger.warning("All papers filtered out. Exiting.")
                return
        reviewer = Reviewer(config)
        papers = await reviewer.review_all(papers)
        scored_count = sum(
            1 for p in papers
            if all(s is not None for s in p.get("model_scores", {}).values())
        )
        logger.info(f"Review complete: {scored_count}/{len(papers)} scored by both models")

    top_papers = aggregate_scores(papers, config)

    output_path = export(top_papers, config)
    json_path = export_json(top_papers, Path(config["output"]["dir"]))

    logger.info("=" * 60)
    logger.info(f"Run complete. Output: {output_path}")
    logger.info(f"JSON data: {json_path}")
    logger.info(f"Total papers: {len(papers)}")
    logger.info(f"Above threshold: {len(top_papers)}")
    if top_papers:
        logger.info("Top papers:")
        for i, p in enumerate(top_papers[:5], 1):
            logger.info(f"  {i}. [{p['final_score']}] {p['title'][:80]}")
    logger.info("=" * 60)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="arXiv Paper Finder with AI Review")
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )
    parser.add_argument(
        "--mock", action="store_true", help="Run with mock data (no API calls)"
    )
    parser.add_argument(
        "--max-results", type=int, default=None, help="Override max_results from config"
    )
    parser.add_argument(
        "--start-date", default=None, help="Start date YYYYMMDD (e.g. 20260301)"
    )
    parser.add_argument(
        "--end-date", default=None, help="End date YYYYMMDD (e.g. 20260531)"
    )
    parser.add_argument(
        "--source", default=None, choices=["arxiv", "venues", "all"],
        help="Override source selection from config",
    )
    parser.add_argument(
        "--venue-years", default=None,
        help="Comma-separated years for venue search, e.g. 2025,2026",
    )
    args = parser.parse_args()

    if args.mock:
        config_path = "config.yml.example"
        if not os.path.exists(config_path):
            print(f"Error: {config_path} not found")
            sys.exit(1)
        config = load_config(config_path, mock=True)
    else:
        if not os.path.exists(args.config):
            print(f"Error: Config file not found: {args.config}")
            print("Copy config.yml.example to config.yml and fill in your settings.")
            sys.exit(1)
        config = load_config(args.config)

    if args.max_results is not None:
        config["arxiv"]["max_results"] = args.max_results

    venue_years = None
    if args.venue_years:
        venue_years = [int(y.strip()) for y in args.venue_years.split(",")]

    setup_logging(Path("logs"))

    asyncio.run(run(
        config, mock=args.mock,
        start_date=args.start_date, end_date=args.end_date,
        source=args.source, venue_years=venue_years,
    ))


if __name__ == "__main__":
    main()
