# 当前 Codex 模式的操作细节

以下 `PY` 指已核对的 Python 3.10+ 绝对路径，`ENGINE` 指解压后的引擎根，`SKILL` 指本 Skill 根，`WS` 指某个 `ENGINE/out/<产品名>`。参数用绝对路径并正确引用；执行前替换占位值。每次明确输入与输出范围，不依赖当前工作目录猜路径。

## 新建与方案

在 ENGINE 内执行，**不要加 `--plan`**：

```sh
"<PY>" -m blueprint init "产品名" "/绝对路径/点子.md"
```

`init` 不调用模型。读取生成的 PRD，保留第 1 节原文、第 6 节待确认和版本结构。当前会话按 BLUEPRINT 五步分析，填 PRD 与方案。

读取原 `blueprint.knowledge.FEATURES` 获得精确特征 ID 与问题。可以在 ENGINE 内执行：

```sh
"<PY>" -c 'from blueprint.knowledge import FEATURES; import json; print(json.dumps([vars(x) for x in FEATURES],ensure_ascii=False,indent=2))'
```

特征文件是纯 JSON 对象，键为上述 ID：

```json
{
  "需要从实际FEATURES表取得的ID": {
    "value": "unknown",
    "evidence": "用户未说明"
  }
}
```

这是形状示例，不能原样执行。yes/no/later 都需引用需求事实；缺省项为 unknown。写入 WS/features.codex.v1.json 后运行：

```sh
"<PY>" "<SKILL>/scripts/local_tools.py" select --engine "<ENGINE>" --features "<WS>/features.codex.v1.json" --out "<WS>/selection.codex.v1.json"
```

输出是“当前会话判断 + 原固定规则”，不冒充原模型管线。s01/s02 恒选；s15 按可选组件数量推导，不靠当前会话随意点选。原引擎缺省未填项会变 unknown，不强求无意义地为每项编证据。

方案七层：交互、产品、Agent 编排、模型、能力集成、数据、基础设施。按需求说明每层的实际责任；不需要独立服务的层可以合并进同一进程。工具说明名称、输入、输出、副作用、权限与失败方式。将用户未给出的数字写为目标/待确认，不伪装为实测。

## 骨架与验证

新产品代码在 WS/skeleton/，最小交付应有启动入口、README、依赖声明和配置示例。无需 API 的工具型骨架可以采用标准库，并明确当前 Codex 是模型与调度宿主；这不等于一个离开 Codex 仍有模型能力的独立应用。

阅读相关组件实现，按需求实现机制，不整段复制全部 17 章。s13/s15 的 parts 和 common 有依赖，不能只复制一个 code.py。模板已知缺陷见 limitations.md。

```sh
"<PY>" "<SKILL>/scripts/local_tools.py" scan --engine "<ENGINE>" --project "<WS>/skeleton" --out "<WS>/inventory.codex.v1.json"
```

当前会话结合扫描结果读真实源码、逐项对照 FR 和成功标准，写差距报告。报告区分：已实现且已运行、仅源码存在、未见证据、明确不在范围。按项目运行完整关键路径，并记录命令、退出状态和关键结果；外部依赖未接入时保留未验证项。

扫描不会执行程序或证明质量；不要为了提高信号分数往代码里塞关键词。不要扫描整个 ENGINE 代表产品能力。已有项目在原位只读扫描，先创建独立目录 ENGINE/out/<任务名>-audit/ 再写产物；辅助程序要求输出父目录已存在，且拒绝覆盖现存文件。

## 需求迭代

在 ENGINE 内执行：

```sh
"<PY>" -m blueprint revise "<WS>" "新需求或需求文件绝对路径" --no-plan
```

检查 PRD 当前版本与 `prd/V旧版.md`。读取新增需求后，更新 PRD 对应各节和方案；生成新版本 features/selection/inventory，手工比较两版 `components`，把实际变化记录到迭代记录的“Codex 分析与实测”条目。`--no-plan` 不会给你生成组件差异，不能假称程序已完成差异分析。

增量改骨架，保留用户文件与未关联修改。消化完成后清理第 7 节对应新增需求并标“已消化”；版本号与快照只由原 `revise` 生成，不手造。

## 离线模拟与恢复

默认流程不用以下 mock 命令；仅在用户要求验证原程序时，在独立的演练工作区使用：

```sh
"<PY>" -m blueprint init "离线演练" "点子" --plan --mock
"<PY>" -m blueprint plan "<演练WS>/PRD.md" -o "<演练WS>" --mock --resume
# 此处先生成或放入演练代码骨架；只有默认 README 的 skeleton 无法 verify。
"<PY>" -m blueprint verify "<演练WS>" --mock
"<PY>" -m blueprint revise "<演练WS>" "新需求" --mock
```

mock 输出必须保留演示标签，不能顶替当前会话的真实分析。`verify` 本身只做静态审计，且没有 `--resume` 参数。若同一次原管线审计要恢复，使用 `audit skeleton --prd PRD.md -o verify --resume`（无 API 时仍须显式 `--mock`，仅演练）。

`revise` 先升版后推导；失败后先读当前版本，不能直接再执行 revise，否则会重复升版。可用原 PRD 的 plan --resume 恢复原管线，或在当前 Codex 模式直接补完方案。`--quick` 不更新 `方案.md` / `plan.json`，不要把旧方案拿来构建新需求。当前 Codex 模式用 `--no-plan`，不使用 quick。

中断后先读现有 PRD、迭代记录、方案和骨架，定位未完成步骤；本地辅助程序拒绝覆盖输出，使用下一版或下一轮的新文件名。不要重建已有工作区或覆盖用户改动。
