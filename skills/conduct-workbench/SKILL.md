---
name: conduct-workbench
description: 打开并管理长期使用的本机工作台，总览已登记项目、工作、任务、偏好及技能、MCP 和工具调用。
---

# Conduct · 可视工作台

读取[共享约定](../conduct-best-skills/references/command-scope.md)和[工作台规范](../conduct-best-skills/references/workbench.md)。本入口依赖同级 `conduct-best-skills`，使用完整 suite 包安装；路径按实际 Skill 目录解析。

1. 定位当前工作空间和用户工作台索引；用户要求同步 Codex 项目或此前已授权接入时，使用宿主 `list_projects`、`list_threads`，按工作台规范更新最小快照。工具不可用时保留旧快照并说明；不读取私有数据库替代接口。
2. 登记当前明确项目并启动或复用可视服务。打开实际 URL，提供项目总览、偏好地图与调用复盘。自然语言编辑偏好，不要求用户填写代码。
3. 说明项目及聊天是最近一次同步的快照，调用履历由 Agent 显式记录。同步索引不在其他项目创建偏好或启用追踪。

当前 prompt 的明确范围优先；只处理用户指定项目。不存在的能力、历史与记录不得假定存在。
