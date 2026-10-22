# 证据台账与运行记录

这些文件由当前 Codex 根据实际读取与执行填写。本地脚本不会调用模型或生成需求，只检查版本、定位与结构。

## 来源快照

`snapshot_repo.py` 要求 Git 与 Python 3.10+。记录仓库根的提交、范围、文件 SHA-256、行数和固定版本链接。二进制、符号链接等跳过项不支持行号引用；需要截图等证据时另存为运行产物并说明来源。脚本不联网、不运行仓库代码；输出须在源码仓库外且文件尚不存在。

默认拒绝 tracked 文件改动；未跟踪文件不纳入快照并记录数量。使用 `--allow-dirty` 研究本地修改时，明确本地内容身份，远端源码链接为空。`--repo-url` 可以指定已核对的 `https://github.com/owner/repo`；URL 本身不证明当前 checkout 来源真实，仍需核对 origin 与固定提交。

## evidence.json

```json
{
  "schema_version": 1,
  "requirements": [
    {
      "id": "FR-001",
      "statement": "填写从项目还原的具体需求",
      "status": "source_supported",
      "sources": [
        {"path": "src/example.py", "start_line": 1, "end_line": 8, "kind": "code"}
      ],
      "runtime": [],
      "open_question_ids": []
    }
  ],
  "questions": [
    {"id": "Q-001", "question": "尚未能确认的问题", "reason": "缺少哪类证据以及它影响什么"}
  ]
}
```

形状示例不能原样作为证据。来源 path 是相对于仓库根的真实路径，不含绝对路径或 `..`；start/end 为本次实际读取的有效行号，不用函数名猜行号。kind 使用 code、documentation、test；现有测试只能说明测试规格，真正执行另列 RUN。

| status | 含义与要求 |
|---|---|
| runtime_verified | 本次真实运行与结果检查支持该需求，附源码/测试定位和全部对应 passed 的运行案例；没有跑过的分支不连带升级 |
| source_supported | 实现源码或测试规格支持，未完成本次运行核验；来源标明 code/test，测试规格不冒充实现事实 |
| documented_only | 目前只确认文档有此声明，附文档来源；没有验证实现 |
| conflict | 文档、实现或运行之间存在矛盾，关联待确认问题；保留两处不同源码/文档定位，或一处定位加一条已实际执行的运行证据（passed/failed，not_run不算） |
| unknown | 现有证据不足，保留关联 Q，不补写肯定结论 |

所有需求 ID 与问题 ID 应唯一，建议 FR-001/Q-001。statement 不能空；Q 引用必须存在。未知问题不要求虚构来源。无关联的全局问题可以保留，例如经营目标和真实使用规模。

## 运行案例 JSON

保存在研究目录内，例如 `runtime/cases.json`：

```json
{
  "schema_version": 1,
  "cases": [
    {
      "id": "RUN-001",
      "status": "passed",
      "request": "本次实际操作、HTTP请求或命令",
      "expected": "从证据形成的可观察预期",
      "observed": "本次实际观察与断言结果",
      "artifacts": ["runtime/response.html"]
    }
  ]
}
```

案例 status 只用 passed、failed、not_run。负向输入被正确拒绝时案例为 passed；请求返回 400/403 不自动算测试失败。独立模型、自定义 stub 或 mock 若用于局部验证要说明；不能用它们给未接入的真实项目全链路背书。

需求通过如下引用关联运行案例：

```json
"runtime": [{"artifact": "runtime/cases.json", "case_id": "RUN-001"}]
```

artifact 相对于 `--artifacts` 根，必须是其内部现存的普通 JSON 文件，不能用路径逃逸或符号链接。案例需有 expected/observed，不把退出码 0 当作需求成立的唯一依据。重要结论附响应、数据库/文件回读、原日志等原始产物，避免只有助手自述。

## 机器检查的范围

`validate_evidence.py` 检查：Git HEAD 与 manifest、被记录文件哈希、引用路径/行号/类型、状态所需证据、问题引用、运行案例存在与状态。失败返回非零并保存报告；重复输出使用新文件名，不能覆盖旧报告。

该检查不理解源码语义、不亲自重跑案例，也不保证期望或观察字段是真实的。Codex 仍需核对原始日志与内容是否支持需求，检查 Markdown 与 JSON 是否一致。对于“能运行但文档遗漏”的情况，应同时保存源码与运行证据，无需为了章节齐全编造需求。
