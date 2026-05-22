<div align="center">
  <h1>awescholar: Scientific Literature Curator</h1>
  <p><strong>自动化科学文献发现与策展。</strong></p>
  <p>搜索、标注、筛选和报告学术论文 — 并将结果合并到你的 Awesome 列表中。</p>
  <p>
    <a href="./README.md">English</a> ·
    <strong>简体中文</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.1.2-7C3AED?style=flat-square" alt="Version">
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
# 设置 API key（添加到 ~/.zshrc 或 ~/.bashrc 可持久保存）
export GLM_API_KEY="sk-..."
export SEMANTICSCHOLAR_API_KEY="your-key"   # 可选，不设则使用免费 tier

# 编辑 config.json 设置模型名称、base_url、搜索词等

# 运行完整流水线
awescholar --config config.json crawler run

# 或直接传入搜索词
awescholar --config config.json crawler run "perturbation prediction|single cell" --date 2025-01-01:2025-05-30
```

## 配置

```json
{
    "model_profiles": {
        "glm": {
            "api_key": "${GLM_API_KEY}",
            "base_url": "https://open.bigmodel.cn/api/paas/v4"
        },
        "deepseek": {
            "api_key": "${DEEPSEEK_API_KEY}",
            "base_url": null
        }
    },
    "model": {
        "profile": "glm",
        "name": "glm-5.1"
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
        "limit": 20,
        "research_interests": null
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
        "merge_new_to_old": false,
        "data_json_path": null
    },
    "categories": ["Foundation Models", "Drug Discovery", "Perturbation Study"]
}
```

`${VAR}` 模式在加载时从环境变量展开。复制 `config.example.json` 并填入你的值 — 或直接设置环境变量，跳过配置文件。

**`model.name`** — 只写模型名称，如 `glm-5.1`、`deepseek-chat`、`gpt-4o`。`openai/` 前缀会自动添加，不要手动写。

**`model_profiles`** — 可复用的 profile 映射。每个 profile 定义 `api_key` 和 `base_url`，通过 `model.profile` 或 `agent_models.*.profile` 引用，避免重复填写凭证。

**`agent_models`** — 按 agent 覆盖模型（annotator, filterer, reporter）。每个条目可用 `profile` 引用 `model_profiles`，或直接设置 `name`/`api_key`/`base_url`：
```json
"agent_models": {
    "annotator": { "profile": "deepseek", "name": "deepseek-chat" },
    "filterer":  { "profile": "glm", "name": "glm-5.1" },
    "reporter":  { "profile": "glm", "name": "glm-5.1" }
}
```

**`filter.research_interests`** — 可选字符串，描述研究兴趣，传给 filterer 做相关性加权。

**`pipeline`** — 控制流水线跳过/复用中间结果：
- `skip_search`: 从数据库加载论文而不是搜索
- `use_updater_json`: 复用已有的 `updater.json`（跳过搜索+标注）
- `use_filtered_json`: 复用已有的 `updater_filter.json`（直接生成报告）
- `existing_json_path`: 自定义 updater JSON 路径
- `merge_new_to_old`: 流水线结束后将筛选结果自动合并到项目数据 JSON
- `data_json_path`: `merge_new_to_old` 使用的项目数据 JSON 路径；当 `merge_new_to_old` 为 `true` 时必须设置

`existing_json_path` 和 `data_json_path` 是两个不同文件。`existing_json_path` 指向标注阶段的中间文件（`updater.json`），用于复用或写入 annotate 结果。`data_json_path` 指向长期维护的项目数据 JSON，在启用 `merge_new_to_old` 后接收筛选后的论文。

**`search.query`** — 如果设置了，`crawler run` 可以不传 CLI query 参数。

支持的 LLM 提供商：任何 OpenAI 兼容 API（通过 `base_url`），如 GLM、DeepSeek、Gemini、Mistral、本地端点。

## 命令

```bash
awescholar -v                                         # 显示版本

# 论文发现流水线
awescholar crawler search "query"                     # 搜索 Semantic Scholar
awescholar crawler annotate                           # 标注数据库中的论文
awescholar crawler annotate --input papers.json       # 从 JSON 标注（跳过 DB）
awescholar crawler filter --limit 20                  # 选择 top 论文
awescholar crawler filter --input updater.json        # 从自定义 JSON 筛选
awescholar crawler report                             # 生成报告（输出到 stdout）
awescholar crawler report updater_filter.json -o report.md  # 从自定义 JSON 生成报告
awescholar crawler run ["query"]                      # 完整流水线（如 config 已设 query 则可省略）

# 存档管理
awescholar updater update --direction new2old --archive data.json   # 合并到存档
awescholar updater readme --archive data.json         # 生成 README 表格
awescholar updater rss --archive data.json            # 生成 RSS 订阅
awescholar updater search --archive data.json --by title           # 按标题搜索并添加
awescholar updater add --archive data.json            # 交互式添加单条记录
```

每个子命令都支持 `--input`（report 用位置参数）指定输入文件，无需重跑完整流水线即可独立执行任意步骤。

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
