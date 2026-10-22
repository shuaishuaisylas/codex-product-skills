# 来源与改造

来源：用户附件 `ai-product-starter-kit-main (1).zip`；MIT，Copyright (c) 2025 hubooooooo；许可见 [LICENSE.txt](LICENSE.txt)。归档SHA256 `524127b6e698f60c2cf2ea09855955391ebaf428783933a54d7b86fa7aa13a6e`。无Git元数据，不声称远端提交。

原件10文件：README、开始看这里、AGENTS、CLAUDE、.gitignore、LICENSE、PRD模板、三份手册；没有业务代码、锁文件或测试。原包是执行规范，不能宣称原包自身启动为产品。

保留：AGENTS第0/3/7/8节的体检、决策、六阶段与续接；通用手册V2.1第1/6/9/10节的路径、适配、接口/恢复/真实验证；前端V1.0第8–12/16–18/21–24节的状态、契约、布局和联调；部署V1.1第7/8部分的发布/收尾验收。

改造：
1. 常驻AGENTS改为仅手动Skill，不复制全局指令。
2. 模型Key和真实模型检查按产品运行时需求触发，开发用当前Codex。
3. 完整开发授权下阶段检查后继续，不重复请求开始。
4. 默认本地交付；云平台/认证限制上线时实时核实。
5. 部署第2/3节的AK/SK交聊天和六项FullAccess改为受控凭证与最小权限。
6. 部署第10节“网址能打开就算上线”与AGENTS业务验收冲突，采用真实业务/权限/恢复验证。
7. 用户简洁证据索引与原始日志都保留，增加NOT_RUN及有原因的N/A。
8. 数据库迁移须验数据/回退，不只改连接串；预留实例不当持久存储。
9. 新增逆向PRD的FR/E/Q来源映射和目标裁决，不自动复制现状缺陷/建议。

官方核对：手动调用 https://learn.chatgpt.com/docs/build-skills ；框架兼容按官方文档，如 https://nextjs.org/docs/app/getting-started/installation 。链接只用于查证，不授权安装或发布。
