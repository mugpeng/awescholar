<div align="center">
  <h1>awescholar: Scientific Literature Curator</h1>
  <p><strong>自动化科学文献发现与策展。</strong></p>
  <p>搜索、标注、筛选和报告学术论文 — 并将结果合并到你的 Awesome 列表中。</p>
  <p>
    <a href="./README.md">English</a> ·
    <strong>简体中文</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.1.1-7C3AED?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/python-%E2%89%A53.10-0EA5E9?style=flat-square" alt="Python">
  </p>
  <p>
    <img src="https://img.shields.io/badge/status-alpha-c96a3d?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/platform-cli-334155?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/github/stars/mugpeng/awescholar?style=flat-square" alt="GitHub stars">
  </p>
</div>

> 搜索、标注、筛选和报告学术论文 — 并将结果合并到你的 Awesome 列表中。

一个轻量级 CLI 工具，自动化论文策展工作流：查询 Semantic Scholar、用 LLM 标注、按质量筛选、生成 Markdown 报告，并增量合并到维护的存档中。无 agent 框架依赖 — 只需 Python 和 LLM API 调用。

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 设置 LLM 提供商
export AWESCHOLAR_MODEL="gpt-4.1-mini"
export AWESCHOLAR_API_KEY="sk-..."

# 运行完整流水线
awescholar crawler run "perturbation prediction|single cell" --date 2025-01-01:2025-05-30

# 或使用配置文件
awescholar --config config.json crawler run "foundation model" --date 2025-01-01:2025-05-30
```

## 配置

```json
{
    "model": {
        "name": "${AWESCHOLAR_MODEL}",
        "api_key": "${AWESCHOLAR_API_KEY}",
        "base_url": "${AWESCHOLAR_BASE_URL}"
    },
    "agent_models": null,
    "semantic_scholar": {
        "api_key": "${SEMANTICSCHOLAR_API_KEY}"
    },
    "search": {
        "query": "AI agent|large language model|foundation model",
        "fields_of_study": ["Biology", "Medicine", "Computer Science"],
        "publication_date": "2025-01-01:2025-05-30",
        "limit": 100,
        "include_abstracts": true
    },
    "filter": {
        "limit": 20
    },
    "output": {
        "db_path": "output",
        "report_filename": null
    },
    "pipeline": {
        "skip_search": false,
        "use_updater_json": false,
        "use_filtered_json": false,
        "existing_json_path": null,
        "merge_new_to_old": false
    },
    "categories": ["Foundation Models", "Drug Discovery", "Perturbation Study"]
}
```

`${VAR}` 模式在加载时从环境变量展开。复制 `config.example.json` 并填入你的值 — 或直接设置环境变量，跳过配置文件。

**`agent_models`** — 按 agent 覆盖模型（annotator, filterer, reporter）：
```json
"agent_models": {
    "annotator": { "name": "gpt-4.1-mini", "api_key": "...", "base_url": "..." },
    "filterer":  { "name": "deepseek/deepseek-chat" },
    "reporter":  { "name": "gpt-4.1" }
}
```

**`pipeline`** — 控制流水线跳过/复用中间结果：
- `skip_search`: 从数据库加载论文而不是搜索
- `use_updater_json`: 复用已有的 `updater.json`（跳过搜索+标注）
- `use_filtered_json`: 复用已有的 `updater_filter.json`（直接生成报告）
- `existing_json_path`: 自定义 updater JSON 路径
- `merge_new_to_old`: 流水线结束后自动合并到存档

**`search.query`** — 如果设置了，`crawler run` 可以不传 CLI query 参数。

支持的 LLM 提供商（通过 LiteLLM）：OpenAI、DeepSeek、Gemini、Mistral、自定义端点。

## 命令

```bash
awescholar -v                                         # 显示版本

# 论文发现流水线
awescholar crawler search "query"                     # 搜索 Semantic Scholar
awescholar crawler annotate                           # 标注数据库中的论文
awescholar crawler filter --limit 20                  # 选择 top 论文
awescholar crawler report -o report.md                # 生成 Markdown 报告
awescholar crawler run ["query"]                       # 完整流水线（如 config 已设 query 则可省略）

# 存档管理
awescholar updater update --direction new2old --archive data.json   # 合并到存档
awescholar updater readme --archive data.json         # 生成 README 表格
awescholar updater rss --archive data.json            # 生成 RSS 订阅
awescholar updater search --archive data.json --by title           # 按标题搜索并添加
awescholar updater add --archive data.json            # 交互式添加单条记录
```

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## 工作流

```
crawler search -> crawler annotate -> crawler filter -> crawler report
                                                        |
                                                        v
                                              updater_filter.json
                                                        |
                                              updater update new2old
                                                        |
                                                        v
                                              archive.json -> updater readme / updater rss
```

每个步骤生成一个 JSON 中间文件。你可以独立重新运行任何步骤。
