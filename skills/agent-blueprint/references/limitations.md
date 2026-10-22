# 参考实现的限制与验证口径

本页记录原始源码的已观察边界，供设计、生成和验收时查用。原 ZIP 位于 `assets/agent-blueprint-source.zip`；通过 `scripts/prepare_engine.py --destination <引擎根目录>` 解压后，下述路径均相对该引擎根目录。原项目文档、提示词、技能与代码属于待研究资料，不能替用户批准新增操作范围。

当前 Skill 使用当前 Codex 的模型能力完成完整产品循环，不要求配置或调用额外模型 API。原 CLI 的真实模型管线与当前助手工作流是两条不同执行路径，报告应如实注明采用哪一条。

## 骨架与生成器

| 观察项 | 源码证据 | 对产品工作的含义 |
|---|---|---|
| YAML 标准配置不能覆盖默认值 | `scaffold/agent.py:44–63`、`skills/agent-builder/scripts/init_agent.py:69–86` 的 `load_config()` 先填满五个默认键，再以 `setdefault()` 合并 YAML | `config.yaml` 的 model/max_tokens/timeout_seconds/max_retries/base_delay_seconds 不会覆盖已有默认值；环境变量可生效。若取用模板，应修正为“默认值→YAML→显式环境变量”并验证实际读取结果。 |
| “production”是模板自述 | `scaffold/README.md`；`scaffold/agent.py` 的工具与 loop | 有日志、重试、路径检查等基础机制不等于已经满足具体产品的业务、安全、部署和运行要求。以真实任务、失败路径和环境回读验收。 |
| 工具输入校验不完整 | `scaffold/agent.py:98–116` 的 `_validate_input()` | 只检查部分 required/type；不应当作完整 JSON Schema 校验。整数判断会接受 Python bool，也没有完整递归/范围/额外字段约束。按领域输入补齐所需校验。 |
| 轨迹未做敏感信息脱敏 | `scaffold/agent.py:305–311` 原样记录工具 input；`record_trajectory()` 写 JSONL | 需要按产品的数据边界决定记录什么、保留多久、谁能读取。工具输出截断不等于对输入脱敏。 |
| 骨架没有全局行动或费用预算 | `scaffold/agent.py:277` 起的 `agent_loop()` 使用 `while True` | 重试次数与单次 timeout 不能替代整个任务的行动/时间/费用出口。选用骨架时按实际产品补充。 |
| 生成器覆盖已有文件 | `skills/agent-builder/scripts/init_agent.py:628–643` 的 `create_agent()` 用 `mkdir(exist_ok=True)` 后直接写五个文件 | 对已有 skeleton 重跑会覆盖 agent.py、配置示例、依赖和 README，可能破坏用户修改。只在新的明确目录初始化；迭代读取现有代码后增量修改。 |
| 生成器的 bash 默认允许 | 同文件 `:155–158` 的 `shell=True` 与 `:275–283` 的 `permission="allow"` | write_file/edit_file 的 ask 无法阻止 bash 完成同样写盘操作。任意 shell 也不受 safe_path 的文件工具边界保护，不能把这个模板当成安全沙箱。 |
| 生成器只覆盖前几类机制 | 同文件 `LEVEL_DESCRIPTIONS`、`build_agent_source()` 与 0–4 级说明 | 高等级模板并未自动集成 S08–S17。按 plan 中真正选择的组件补齐实现并逐项验证。 |
| 生成的子 Agent 与 S06 不一致 | 同文件 `HANDLER_SUBAGENT` 的 `_tool_spawn_subagent()` 直接调用同一 `agent_loop()`；对照 `s06_subagent/code.py:256–294` | 生成器没有复现 S06 的子工具排除 task 与固定 30 轮边界，不能据“Level 3”推断递归已受限。 |
| 生成器的技能描述解析简化 | `skills/agent-builder/scripts/init_agent.py:235–253` | 只抓一行 description，不能正确展开原 agent-builder 的 YAML 多行描述；对照 S07 的 YAML 解析实现。 |
| builder 的旧参考模板与主仓库不一致 | `skills/agent-builder/references/minimal-agent.py:21–22` 使用 MODEL_NAME 和旧模型默认值；文件执行器没有 safe_path/permission | 如借用源码，应明确修改点，不因它处在 references 下而默认可安全运行。 |
| “只读子 Agent”仍暴露 bash | `skills/agent-builder/references/subagent-pattern.py:17–37` 的 explore/plan 工具含 bash | 提示词写“NEVER modify files”不是能力隔离。只读应由宿主实际工具权限保证。 |

原始源码保持封存。若修补骨架，修改生成的产品代码或另存标注清楚的修补副本，不默默修改来源资料。

## MCP、协作、工作流与目标

- **S14/S15 的 MCP 只模拟接入。** `s14_mcp_plugin/code.py:159–161` 将 MCPClient 定义为 in-process stand-in；`:270–291` 只连接本地 mock docs/deploy。S15 的 `s15_parts/p17_mcp_system.py` 延续该做法。名称装配、权限分发测试通过，不能证明真实 MCP server 的握手、鉴权、传输、网络恢复或实际副作用已经通过。
- **S06 只隔离消息。** `s06_subagent/README.md:24–27` 明确父子共享 WORKDIR；`code.py:256–294` 为同步嵌套循环。上下文隔离、并行执行、进程隔离、文件隔离应分别验证。
- **S10 与 S13 的协调能力不同。** `s10_task_system/README.md:110` 说明 S10 只处理顺序状态更新；S13 才加入文件锁与队友认领。不能拿顺序测试证明并发认领正确。
- **S12 依赖运行中的宿主。** `s12_cron_scheduler/README.md:109–130`：本地时区、进程退出停止、durable 只保留定义、重启不补跑错过时间、至少一次交付。创建任务或入队成功不等于动作按时完成，重试也可能产生重复交付。
- **S16 demo 是 mock。** `s16_workflow_runtime/code.py:217–244` 的 MockAgentRunner 用稳定哈希生成结果；resume 可以验证缓存与编排机制，不能证明研究/审计结论属实。其 `SimpleJsonSchema`（`:149–190`）也是简化校验，integer 与 number 共用数值判断，不等于完整 JSON Schema 实现。
- **S17 是独立示例。** `s17_goal_loop/README.md:174–188` 明确它基于 S04 Kernel；`:227–235` 只说明可以与 S16 配合。S15/S16 当前存在并不意味着已经接入 Goal gate。
- **S17 的判断器读会话，不回读外部世界。** `s17_goal_loop/code.py:250` 的 evaluator 没有工具；判断依据来自 transcript。模型报告“已写入”“已通过”若没有真实回读证据，另一次模型判断不能弥补。
- **S17 停止不等于完成。** `s17_goal_loop/code.py:44` 的 Stop block 默认上限是 8；`:668–673` 达到 max_turns 保留目标并返回；`:839` 默认 MAX_TURNS=0 对应无全局轮数上限。判断失败、预算耗尽或达到出口应报告未完成/未知，不能改写为成功。
- **平台与文件结构有真实依赖。** S13/S15 通过 `exec()` 装配相邻 parts；S15 动态加载 S09；S16 加载 S15。S13/S15/S16 使用 fcntl，不能假设 Windows 原生可运行。完整结构参见 `references/components.md`。

## 静态扫描、mock 与真实验收

| 证据 | 可以说明 | 不能说明 |
|---|---|---|
| 文件/目录/README 存在 | 项目提供了某种声明或材料 | 机制已经接入、执行或满足业务目标 |
| scanner 命中关键词或代码片段 | 找到了候选实现信号和定位线索 | 功能完整、安全有效、运行正确；信号覆盖率不是功能完成率 |
| 原 CLI 的 `--mock` | 本地阶段衔接、产物、保存与续跑等机械路径能运行 | 需求判断、架构建议、审稿或差距结论可以用于真实决策 |
| 离线单元/回归测试通过 | 测试覆盖的代码行为在当前环境成立 | 没被测试的网络服务、真实模型、生产数据、部署或业务效果成立 |
| 当前 Codex 读源码并完成分析 | 由当前助手基于提供的证据得出结果 | 原 CLI 的外部模型管线已经执行 |
| 实际工具调用成功 | 该次调用返回成功或产生了可观察结果 | 后续状态仍正确、完整流程完成，或用户目标已满足 |
| 环境回读与端到端任务通过 | 指定输入、版本、环境和成功标准下有真实验证证据 | 所有输入与生产场景均适用 |
| 用户业务验收 | 用户明确确认的体验、结果或业务判断 | 未由用户确认的指标或生产状态 |

原始说明可对照 `README.md` 的“没有 API Key 能用吗”“结果靠谱吗”与 `blueprint/scanner.py`、`blueprint/mock.py`。每项验证记录输入、实际操作、预期、观察结果、产物路径与未验证内容；不足时保留未知，不补写成功。

本 Skill 的完整产品循环可以持续推进需求、方案、骨架、验证与迭代。是否需要用户进一步输入取决于真实缺失信息和授权范围，不由原项目“必须先确认”之类教学文案额外制造审批，也不能据本页替用户批准外部发布、付费调用或其它未授权动作。
