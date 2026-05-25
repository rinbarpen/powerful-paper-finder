"""Score aggregation — per-model thresholds, combined filter, priority sort, top-N cap."""

import logging
from typing import List

logger = logging.getLogger(__name__)


def aggregate_scores(papers: List[dict], config: dict) -> List[dict]:
    models = config["models"]
    top_n = config["scoring"].get("top_n", 10)
    min_combined = config["scoring"].get("min_combined", 8.5)
    concurrency = config["scoring"].get("concurrency", 5)

    for paper in papers:
        total_weight = 0.0
        weighted_sum = 0.0
        for model_cfg in models:
            name = model_cfg["name"]
            score = paper.get("model_scores", {}).get(name)
            if score is not None:
                weighted_sum += score * model_cfg.get("weight", 0.5)
                total_weight += model_cfg.get("weight", 0.5)
        paper["final_score"] = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    passed = []
    for paper in papers:
        scores = paper.get("model_scores", {})
        gpt_score = scores.get(models[0]["name"]) if len(models) > 0 else None
        ds_score = scores.get(models[1]["name"]) if len(models) > 1 else None
        combined = paper["final_score"]

        gpt_ok = gpt_score is not None and gpt_score >= models[0].get("min_score", 7.0)
        ds_ok = ds_score is not None and ds_score >= models[1].get("min_score", 9.0)
        combined_ok = combined >= min_combined

        if gpt_ok or ds_ok:
            paper["pass_reason"] = _pass_label(gpt_ok, ds_ok)
            passed.append(paper)
        elif combined_ok:
            paper["pass_reason"] = "综合"
            passed.append(paper)

    passed.sort(key=lambda p: (
        not p.get("general", False),
        -p["final_score"],
    ))

    result = passed[:top_n]
    logger.info(
        f"Scoring complete: {len(passed)}/{len(papers)} pass filter, "
        f"top {len(result)} exported (general={sum(1 for p in result if p.get('general'))})"
    )
    return result


def _pass_label(gpt_ok: bool, ds_ok: bool) -> str:
    parts = []
    if gpt_ok:
        parts.append("GPT")
    if ds_ok:
        parts.append("DeepSeek")
    return "+".join(parts)
