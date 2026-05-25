# arXiv Paper Finder

每日自动检索 arXiv 最新论文，经双模型 AI 评审评分，精选高创新性研究并生成排行榜。

## 功能特性

- 📥 **自动检索** — 每日从 arXiv 指定分类拉取最新论文
- 🤖 **双模型评审** — 通过两个 LLM 独立评分，加权综合排名
- 📊 **Excel 导出** — 生成格式化的评分排行榜（带条件高亮）
- 🌐 **Web 界面** — 在线浏览论文排行榜，支持搜索与筛选
- ⏰ **自动部署** — GitHub Actions 定时运行，自动更新 Pages

## 在线演示

项目部署在 GitHub Pages：`https://rinbarpen.github.io/powerful-paper-finder/`

*（需要首次 GitHub Actions 运行成功后生效）*

## 快速开始

### 环境要求

- Python 3.11+
- 两个 LLM API 的访问地址和密钥

### 安装

```bash
git clone https://github.com/rinbarpen/powerful-paper-finder.git
cd powerful-paper-finder
pip install -e .
```

### 配置

复制配置文件并填入 API 信息：

```bash
cp config.yml.example config.yml
```

`config.yml` 中支持通过环境变量引用敏感信息：

```yaml
models:
  - name: "gpt-5.5"
    api_base: "${OPENAI_BASE_URL}"
    api_key: "${OPENAI_API_KEY}"
    weight: 0.5
    min_score: 7.0
  - name: "DeepSeek-V4-Pro"
    api_base: "${DEEPSEEK_BASE_URL}"
    api_key: "${DEEPSEEK_API_KEY}"
    weight: 0.5
    min_score: 9.0
```

运行前设置环境变量：

```bash
export OPENAI_BASE_URL=https://api.vveai.com/v1
export OPENAI_API_KEY=sk-your-key-here
export DEEPSEEK_BASE_URL=https://api.vveai.com/v1
export DEEPSEEK_API_KEY=sk-your-key-here
```

### 运行

```bash
# 完整运行（连接 arXiv 和 LLM API）
python main.py

# 使用 Mock 数据测试（无需 API）
python main.py --mock

# 限制检索数量
python main.py --max-results 10

# 指定日期范围
python main.py --start-date 20260301 --end-date 20260531
```

### 输出

- `output/arxiv_top_papers_{date}.xlsx` — 格式化的 Excel 排行榜
- `output/papers_data.json` — Web 前端使用的 JSON 数据
- `logs/run_{date}.log` — 运行日志

## 自动部署

本项目使用 GitHub Actions 实现全自动运行：

1. **定时触发** — 每天北京时间 09:00 自动执行
2. **手动触发** — 在 Actions 页面点击 Run workflow
3. **自动部署** — 运行后自动更新 GitHub Pages

### GitHub Secrets 配置

需要在仓库 Settings → Secrets and Actions 中配置：

| Name | 说明 |
|------|------|
| `OPENAI_API_KEY` | 第一个模型的 API Key |
| `OPENAI_BASE_URL` | 第一个模型的 API 地址 |
| `DEEPSEEK_API_KEY` | 第二个模型的 API Key |
| `DEEPSEEK_BASE_URL` | 第二个模型的 API 地址 |

### GitHub Pages 启用

仓库 Settings → Pages → Source 选择 **gh-pages** 分支。

## 配置参考

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `arxiv.categories` | 检索分类列表 | cs.AI, cs.CL, cs.CV, cs.LG, cs.MA, stat.ML |
| `arxiv.max_results` | 每分类最大检索数 | 200 |
| `arxiv.days_back` | 回溯天数 | 1 |
| `scoring.min_combined` | 综合得分最低阈值 | 8.5 |
| `scoring.top_n` | 最终输出论文数 | 10 |
| `scoring.concurrency` | LLM 并发请求数 | 5 |

## 技术栈

- **Python** — arXiv API + AsyncOpenAI + openpyxl
- **GitHub Actions** — 定时调度 + Pages 部署
- **Vanilla JS** — 纯静态前端，无框架依赖

## 许可证

[MIT](LICENSE)
