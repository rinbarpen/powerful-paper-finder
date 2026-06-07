---
name: paper-finder
description: 拉取 arXiv 最新论文 → 免费模型筛选 → GPT-5.5+DeepSeek 双模型评审 → 筛选评分 ≥7 的论文 → 输出 Excel
---
# arXiv Paper Finder

主动触发式 arXiv 论文筛选 + AI 评审工具。

## Usage

在 Claude Code 中输入 `/paper-finder` 即可运行，或:

```bash
# 简单模式（自动设置参数）
python run.py

# 自定义模式
python main.py --max-results 50

# Web 前端（浏览器操作）
python app.py
# 打开 http://localhost:8020
```

## Pipeline

1. **Fetch**: 从 arXiv 拉取 6 个分类的最新论文（cs.AI, cs.CL, cs.CV, cs.LG, cs.MA, stat.ML）
2. **Filter**: 用 OpenRouter 免费模型快速分类 + 相关性评分，取 top 15
3. **Review**: GPT-5.5 + DeepSeek-V4-Pro 双模型深度评审创新性
4. **Export**: 导出 Excel 到 `output/` 目录

## Requirements

环境变量: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`
