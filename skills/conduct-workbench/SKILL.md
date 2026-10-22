---
name: conduct-workbench
description: 打开 Agent Harness 工作台，编辑七阶段任务说明与项目偏好，查看能力调用、执行依赖、验收证据及复盘。
---

# Conduct · Agent Harness 工作台

读取[共享约定](../conduct-best-skills/references/command-scope.md)和[工作台规范](../conduct-best-skills/references/workbench.md)。本入口依赖同级 `conduct-best-skills`，使用完整 suite 包安装；路径按实际 Skill 目录解析。

1. 定位当前工作空间和用户工作台索引；用户要求同步 Codex 项目或此前已授权接入时，使用宿主 `list_projects`、`list_threads`，按工作台规范更新最小快照。工具不可用时保留旧快照并说明；不读取私有数据库替代接口。
2. 登记当前明确项目并启动或复用可视服务。打开实际 URL，提供任务驾驶舱、项目总览、偏好地图与调用复盘。用自然语言维护目标、依据、方案、验收和交付要求，不要求用户填写代码；已有执行契约只读展示依赖与证据。
3. 说明项目及聊天是最近一次同步的快照，调用履历由 Agent 显式记录。同步索引不在其他项目创建偏好或启用追踪。

当前 prompt 的明确范围优先；只处理用户指定项目。不存在的能力、历史与记录不得假定存在。
