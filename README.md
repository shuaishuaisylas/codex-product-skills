# Codex Product Skills

三个手动调用的中文 Codex Skill，覆盖 **Agent 点子到方案、开源项目逆向 PRD、PRD 到前后端产品**。

使用当前 Codex 会话完成分析、设计与开发，无需另接开发用模型 API。需求来源、待确认项和实际验证结果贯穿交付过程。

## 选一个入口

| Skill | 适合什么时候用 | 主要产物 |
| --- | --- | --- |
| [agent-blueprint](skills/agent-blueprint/SKILL.md) · Agent 产品蓝图 | 有 Agent 点子或 PRD，需要选型、架构、骨架与迭代 | 需求版本、选型理由、方案、可运行骨架、检查报告 |
| [github-to-prd](skills/github-to-prd/SKILL.md) · GitHub 项目逆向 PRD | 想研究一个开源项目，弄清它实际做了什么 | 现状 PRD、源码与运行证据、冲突、待确认项 |
| [prd-to-product](skills/prd-to-product/SKILL.md) · PRD 到前后端产品 | 已有 PRD，希望完成实现、联调和本地交付 | 前后端代码、真实联调结果、验收记录、启动与续接说明 |

三个 Skill 可以独立使用。研究已有产品时，可先用 `github-to-prd` 还原现状，再明确本次目标，交给 `prd-to-product` 开发。原项目的缺陷、建议和未决问题会保留，不会自动变成新需求。

## 安装

在 Codex 中发送：

```text
$skill-installer
请从 shuaishuaisylas/codex-product-skills 安装这三个 Skill：
- skills/agent-blueprint
- skills/github-to-prd
- skills/prd-to-product
保留仅手动触发配置；如有同名已安装版本，先核对差异，不覆盖我的修改。
```

也可以下载本仓库，将 `skills/` 下需要的完整文件夹放入 `~/.agents/skills/`。项目内使用时，放入该项目的 `.agents/skills/`。不要只复制 `SKILL.md`：引用资料、配置和辅助脚本需要一起保留。

安装后在技能列表中手动选择，或输入下方调用名。若列表未刷新，可重新打开 Codex。安装路径和显式调用机制见 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)。

## 手动调用示例

**从 Agent 点子开始：**

```text
$agent-blueprint
我想做一个本地资料查找助手。请按完整产品流程完成需求、方案、骨架与验证，
直接使用当前 Codex，不接独立模型 API；不确定的业务问题保留待确认。
```

**研究开源项目：**

```text
$github-to-prd
请研究 https://github.com/helloflask/watchlist，固定提交版本，
还原现状 PRD，保留源码和运行证据、待确认项，并实际验证主要流程。
```

**根据 PRD 开发：**

```text
$prd-to-product
请按这份 PRD 完成前后端实现、联调、测试和本地交付。
直接使用当前 Codex，不接独立模型 API。保留需求来源、未决问题与验收记录。
```

## 调用与运行边界

- 三个 Skill 的 `agents/openai.yaml` 均设置 `policy.allow_implicit_invocation: false`，仅手动调用。
- `agent-blueprint` 和 `github-to-prd` 的本地辅助脚本需要 Python 3.10+；后者研究 Git 仓库时还需要 Git。辅助脚本不调用模型 API。
- Skill 使用当前 Codex 的能力；若要交付的产品自身需要在线生成、识别等模型能力，仍需另行明确产品运行时。未接入时保留未验证状态。
- 逆向 PRD 区分文档声明、源码支持、运行验证、冲突和未知；证据结构检查不替代内容复核。
- 开发流程默认交付到本地可运行，实际检查与用户验收分别记录。

## 验证与来源

这些 Skill 已经过本地流程演练，包括真实开源项目 Watchlist 的逆向 PRD，以及从演示 PRD 开发前后端需求验收看板。范围与限制见 [验证说明](docs/validation.md)。

`agent-blueprint` 基于 Hubo 的 Agent Blueprint，内含固定原始源码归档；`prd-to-product` 基于 AI Product Starter Kit 的开发规范改造。原文件、封装层与改造内容的来源见 [第三方声明](THIRD_PARTY_NOTICES.md)。

本仓库新增内容采用 [MIT License](LICENSE)。第三方内容保留原作者署名与许可。
