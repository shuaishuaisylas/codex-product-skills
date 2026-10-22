# 来源与第三方许可

## Agent Blueprint

- 上游项目：[hubooooooo/agent-blueprint](https://github.com/hubooooooo/agent-blueprint)。
- 研究来源：提供的 `agent-blueprint-main (1).zip`，未附 Git 元数据；不声称对应某个远端提交。
- 本仓库保留未修改的 [原始归档](skills/agent-blueprint/assets/agent-blueprint-source.zip)。SHA-256：`56c89c7836fb396240fbf0d90e904a338b7f660124165776f449b218fc6b178b`。
- 上游许可：MIT，Copyright (c) 2024 Hubo。许可原文保留在归档内，并另附 [可直接阅读的副本](skills/agent-blueprint/references/LICENSE.txt)。
- 本仓库适配：仅手动调用、当前 Codex 推理、本地选型与扫描辅助脚本、流程和限制说明。详见 [来源说明](skills/agent-blueprint/references/source.md)。
- 归档中的其他 Skills 是上游参考资料，不会随本仓库这三个 Skill 的安装而自动安装。

## AI Product Starter Kit

- 研究来源：提供的 `ai-product-starter-kit-main (1).zip`，未附 Git 元数据。
- 原附件 SHA-256：`524127b6e698f60c2cf2ea09855955391ebaf428783933a54d7b86fa7aa13a6e`。原附件未包含在本仓库。
- 上游许可：MIT，Copyright (c) 2025 hubooooooo；[许可原文](skills/prd-to-product/references/LICENSE.txt)。
- 本仓库将原开发规范整理为 `prd-to-product` 的手动工作流，增加逆向 PRD 交接、需求证据及真实验证边界。具体保留与改造见 [来源说明](skills/prd-to-product/references/source-notes.md)。

## GitHub to PRD

`github-to-prd` 为本仓库独立编写的需求还原工作流、文档模板和本地证据辅助脚本，不依赖 Agent Blueprint 引擎。其新增内容适用根目录 MIT 许可。

验证时使用了 MIT 许可的 [helloflask/watchlist](https://github.com/helloflask/watchlist)，固定提交 `5dd104f8c32a0b0df0e5bf45fa345950d7e971b7`。本仓库不分发该项目源码。
