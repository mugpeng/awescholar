# Refactor TODO (2026-05-28)

Code review suggestions not yet implemented. Ordered by risk/effort, low to high.

## Todo

### 1. config.py 用 dataclass

当前 `load_config()` 返回 20+ key 的 dict，任何 typo 都是 runtime error。改成 `@dataclass` 或 Pydantic model，类型安全，IDE 补全也好。

**风险**: 低。改动集中在 `config.py` + 所有 `config["key"]` 调用点。
**收益**: 消灭一大类 typo bug。

### 2. types.py — 共享类型

当前 paper、filtered data、archive 都是裸 dict。先加 `TypedDict` 或轻量 Pydantic model 覆盖最高频的两个结构：

- `LoadedConfig` (替代 #1 也行)
- `PaperRecord` (search/annotate/filter 流转的 paper dict)

不用一次改全，先覆盖 config 和 paper record。

**风险**: 低。渐进式，不改行为。
**收益**: 类型提示 + 自文档化。

### 3. cli.py 拆 commands/

当前 342 行，`cmd_*` 函数混了参数处理、JSON 读写、DB 查询、路径生成、输出。建议：

```
commands/crawler.py   — cmd_search, cmd_annotate, cmd_filter, cmd_report, cmd_run
commands/updater.py   — cmd_update, cmd_readme, cmd_rss, cmd_search_record, cmd_add
cli.py                — argparse + dispatch only
```

**风险**: 中。涉及文件移动和 import 调整。
**收益**: cli.py 从 342 行降到 ~80 行，每个 command 文件职责清晰。

### 4. pipeline.py 拆编排和落盘

`run_pipeline()` 同时负责流程编排、DB 操作、JSON 文件读写、LLM 调用。短期可以只抽：

- `read_json(path)` / `write_json(path, data)`
- `load_db_papers(db_path)` / `save_artifact(path, data)`

不改变行为，resume/skip 逻辑会更容易测。

**风险**: 中。
**收益**: pipeline.py 可测性提升，I/O 集中管理。

### 5. record.py 的 I/O DI

`search_and_add()` 和 `add_interactive()` 直接用 `input()` 和 `print()`，无法测试。建议接受 `readline` 回调，默认 `input`；输出走 `status_cb`。

**风险**: 低-中。函数签名变化，但调用点少。
**收益**: 可测试，与全局 pattern 一致。

### 6. record.py 错误处理

`search_by_title` / `search_by_doi` 捕获所有异常后 `print + return None`，"not found" 和 "API 500" 无法区分。建议：

- 返回结构化结果（`Result` 类型或分情况返回）
- 或抛出可解释异常，让调用方决定怎么处理

**风险**: 低。
**收益**: 调用方和测试能区分失败原因。

### 7. search.py 拆 search 和 DB persistence

`search_papers()` 同时做 API 调用、DB upsert、返回 dict。pipeline.py 在 skip-search 路径已经绕过了这个函数。建议拆成纯搜索 + 独立持久化。

**风险**: 中。涉及 search.py + pipeline.py。
**收益**: 职责单一，skip-search 路径更干净。

### 8. RuntimeContext

统一 I/O 抽象：`RuntimeContext(write, error, input)`。当前 `status_cb` 只覆盖输出，不覆盖输入和错误输出。

**风险**: 低，但改动面广（所有模块）。
**收益**: CLI、测试、agent 调用都更干净。建议等 awescholar 需要被其他 agent 调用时再做。

### 9. utils.py 中 print() 改走 context

`update_readme()` 和 `generate_rss()` 里有直接 `print()`。如果做了 #8，这些走 `ctx.write()`；短期可以先加 `status_cb` 参数。

**风险**: 低。
**收益**: 输出可控，测试不污染 stdout。

### 10. db.py engine 缓存

`get_session()` 每次调用都 `create_engine` + `create_all`。CLI 场景没问题，但如果循环调用会泄漏连接。可以按 `db_path` 缓存 engine。

**风险**: 低。
**收益**: 避免潜在连接泄漏。
