# 17 个组件的能力与源码地图

本页用于按需求读取参考实现，不要求把 17 个组件全部装进产品。原始 ZIP 保存在 `assets/agent-blueprint-source.zip`；使用 `scripts/prepare_engine.py --destination <引擎根目录>` 解压后，下面的路径均相对该引擎根目录。

当前工作使用 Codex 自身的模型能力分析、设计、生成和验证，不需要另配模型 API。章节中的客户端、启动命令与外部模型调用属于原项目参考实现；读取源码不表示要启动它们。

## 按需求选读

| 章节 | 实际能力 | 何时需要 | 优先读取的源码与边界 |
|---|---|---|---|
| s01 Agent Loop | 调用模型、执行工具、回填结果，反复循环 | 所有需要多轮行动的 Agent | `s01_agent_loop/code.py`：`agent_loop`、`run_bash`。没有工具调用即返回，只能说明模型停止。 |
| s02 Tool Use | bash/read/write/edit/glob 的工具定义与 handler 分发 | 接触文件、命令、API 或业务操作 | `s02_tool_use/code.py`：`TOOL_HANDLERS`、`safe_path`。文件路径约束不等于 bash 沙箱。 |
| s03 Permission | deny list、规则匹配、人工许可三关 | 有敏感或高影响动作 | `s03_permission/code.py`：`check_deny_list`、`check_rules`、`check_permission`。这是规则示例，不是完整安全隔离。 |
| s04 Hooks | PreToolUse/PostToolUse/UserPromptSubmit/Stop 生命周期插点 | 审计、拦截、日志、结果检查 | `s04_hooks/code.py`：`register_hook`、`trigger_hooks`、`permission_hook`、`agent_loop`。 |
| s05 TodoWrite | 会话内结构化计划和进度，限制单个进行中事项 | 多步骤任务需要防止遗漏和偏离 | `s05_todo_write/code.py`：`TodoManager`、`run_todo_write`。状态保存在内存，最多 20 条。 |
| s06 Subagent | 用新的消息列表完成子任务，只回传最终文本 | 子任务会产生大量探索内容 | `s06_subagent/code.py`：`run_subagent`、`SUB_TOOLS`、`execute_tool`。同步嵌套，最多 30 轮，共用文件工作区，子工具不含 task。 |
| s07 Skill Loading | YAML 元数据目录、按需读取完整技能正文 | 领域资料较多，不能全部塞进提示词 | `s07_skill_loading/code.py`：`SkillLoader`、`build_system_prompt`。章节实现允许模型按适用性加载；本 Skill 的手动调用策略由宿主管理。 |
| s08 Context Compact | 工具结果预算、snip、micro、历史摘要和超长输入补救 | 长会话或大工具结果挤占上下文 | `s08_context_compact/code.py`：`ContextCompactor`、`agent_loop`。维护工具调用/结果配对；超长输入错误的补救最多一次。 |
| s09 Memory | 单文件记忆、选择/召回、提取、去重与整理 | 经用户授权需要跨会话保留事实或偏好 | `s09_memory/code.py`：`should_store_memory`、`select_relevant_memories`、`extract_memories`、`consolidate_memories`。区分 persistent 与 current_task；原示例会自动提取记忆，不应据此替用户授权写入。 |
| s10 Task System | 磁盘任务、owner、状态、blockedBy 依赖检查 | 任务需要跨会话恢复或按依赖执行 | `s10_task_system/code.py`：`Task`、`TaskStore`、`claim_task`、`complete_task`。S10 主要展示顺序状态更新。 |
| s11 Background Tasks | 显式后台 bash、bg_id、完成结果回收、进程组清理 | 有可独立推进的慢操作 | `s11_background_tasks/code.py`：`BackgroundManager`、`should_run_background`、`collect_background_results`。返回 bg_id 只代表启动。 |
| s12 Cron Scheduler | Cron 校验、任务持久化、到期入队、空闲交付 | 产品明确需要按时触发 | `s12_cron_scheduler/code.py`：`CronJob`、`validate_cron`、`poll_due_jobs`、`queue_processor_loop`。依赖宿主进程、本地时间、至少一次交付，不补跑停机期间任务。 |
| s13 Agent Teams | 独立队友循环、mailbox、原子认领、任务工作目录、worktree 和控制协议 | 多个任务可并行且需要协调与工作区隔离 | `s13_agent_teams/code.py` 是装配入口；按需读 `s13_parts/p01_task_system.py`、`p02_task_bound_worktrees.py`、`p06_messagebus_and_team_protocols.py`、`p08_teammate_runtime.py`、`p09_lead_team_tools.py`。结果与 IDLE 是两个事件。 |
| s14 MCP Tools | 发现工具、工具名前缀、工具池装配和宿主权限 | 需要接外部工具协议生态 | `s14_mcp_plugin/code.py`：`MCPClient`、`connect_mcp`、`assemble_tool_pool`、`permission_hook`。当前只有进程内 mock docs/deploy，不含真实 MCP 传输。 |
| s15 Integrated Harness | 将工具、权限、hooks、计划、任务、记忆、子 Agent、团队、压缩、后台与调度接入一个循环 | 多种机制确实需要协同 | `s15_integrated_harness/code.py` 给出分节地图；实现位于 `s15_parts/`。优先读 `p04_prompt_assembly.py`、`p11_hooks_and_permission_checks.py`、`p20_tool_definitions.py`、`p22_agent_loop.py`，再选读机制分节。MCP 仍是 mock。 |
| s16 Workflow Runtime | agent/parallel/pipeline 编排、结构化结果、预算、进度、journal 与 resume | 一批步骤可预先写成稳定编排 | `s16_workflow_runtime/code.py`：`WorkflowTool`、`ExecutionState`、`WorkflowJournal`、`Budget`、`install_workflow_tool`。在 S15 工具层挂载；demo 用 `MockAgentRunner`。 |
| s17 Goal Loop | 会话级目标、独立判断器、Stop gate、续轮与退出上限 | 需要在模型停止后判断整个目标是否满足 | `s17_goal_loop/code.py`：`PromptGoalEvaluator`、`GoalController`、`AgentSession`。它是基于 S04 的独立示例，不是已经合并进 S15/S16 的功能。判断器只读会话，没有外部核验工具。 |

## 实际依赖关系

- S01–S04 形成基础循环、工具、权限与 hooks 主线。后续多个章节从这个基线单独增加一种机制，并非按编号无条件累积全部功能。
- S05 的 TODO 服务当前会话；S10 的任务状态可落盘；S13 加入并发协作、认领与工作区管理。三者不能相互替代。
- S08 管当前上下文容量；S09 管经授权需要跨会话保留的信息。摘要不是永久记忆，永久记忆也不能替代任务状态。
- S06 的上下文隔离不等于并行或文件隔离；S13 的团队和 worktree 才展示更完整的协作机制。
- S15 是综合装配例。`s15_parts/p00_preamble.py` 的 `load_memory_runtime()` 会动态加载 `s09_memory/code.py`。
- S16 的 `load_integrated_host()` 加载 S15，并通过扩展注册挂载 Workflow。运行完 Workflow 不等于业务目标已经完成。
- S17 是另一份独立机制例。将其与 S15/S16 组合，需要实际接入、验证和证据；不能从目录存在直接推断已经集成。

## 共用层与生成器

| 位置 | 用途 | 取用方法 |
|---|---|---|
| `common/bootstrap.py` | `.env`、Anthropic 客户端、模型名解析、凭证检查、友好错误与交互循环 | 理解原章节怎样启动即可。章节不能只拷走一个 code.py；本次 Codex 工作流不使用它发模型请求。 |
| `scaffold/agent.py` | 配置、日志、重试/超时、工具 registry、权限点、路径检查和轨迹记录 | 作为可修改的骨架参考；先读 `references/limitations.md` 中配置合并与验收限制。 |
| `scaffold/config.example.yaml`、`scaffold/requirements.txt` | 原始配置与依赖示例 | 属于骨架运行环境，不是当前 Skill 的必需设置。 |
| `skills/agent-builder/SKILL.md` | 原作者的五步推导、八问、组件选型与产品循环说明 | 作为方法资料，不复制其宽泛自动触发条件或默认生产级结论。 |
| `skills/agent-builder/scripts/init_agent.py` | 生成 0–4 级 Agent 模板 | 只覆盖 loop/tools/TODO/subagent/skill loading；存在覆盖与权限限制，不对已有 skeleton 直接重跑。 |
| `skills/agent-builder/references/` | 最简 Agent、工具、子 Agent 和 PRD 推导示例 | 按需借鉴，不能直接当成已验证产品。 |
| `skills/code-review/`、`skills/pdf/`、`skills/mcp-builder/` | S07 技能加载教学资料 | 保留在源码包，按需读；不因为研究项目而安装或触发这些技能。 |

## 选型时要形成的证据

每个拟选组件写清楚：需求中的哪条事实需要它、缺少它会造成什么、取用哪些机制、暂不取用哪些机制，以及用什么可观察结果证明它确实工作。若当前只读过源码或跑过 mock，按实际证据标记，不能写成已完成真实业务验证。
