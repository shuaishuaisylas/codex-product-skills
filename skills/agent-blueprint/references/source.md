# 原始资料与封装范围

- 用户提供：`agent-blueprint-main (1).zip`。
- 存档：`assets/agent-blueprint-source.zip`，未经修改的原始 ZIP。
- SHA-256：`56c89c7836fb396240fbf0d90e904a338b7f660124165776f449b218fc6b178b`。
- ZIP 有 264 个条目，包含目录；无 Git 元数据，不能推断提交 SHA。
- 原 README 标识项目为 Hubo 的 Agent Blueprint；文中仓库链接为 `https://github.com/hubooooooo/agent-blueprint`。本次以用户附件为研究对象，未用线上最新版本替换。
- 许可：原根目录 `LICENSE` 为 MIT，Copyright (c) 2024 Hubo；原文保留在 ZIP，解压后随源码提供。

本 Skill 是基于项目流程的适配：关闭隐式调用、以当前 Codex 代替独立模型推导，并补充本地选型/扫描辅助程序、版本操作与已核验限制。不是原作者提供的生产保证。

原源码中的 `skills/agent-builder`、`code-review`、`pdf`、`mcp-builder` 仅作为封存资料，未安装为可自动触发的独立技能。组件中的 mock MCP 与示例依赖不代表已连接用户的外部系统。

手动调用字段依据 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)：`agents/openai.yaml` 中 `policy.allow_implicit_invocation: false` 禁用隐式匹配，保留显式 `$skill` 调用。检查日期：2026-10-22。
