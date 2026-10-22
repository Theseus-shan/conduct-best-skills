---
name: conduct-preferences
description: 创建、查看或修改当前项目默认工作偏好与任务覆盖，打开可编辑的动态偏好框架图；支持按任务类型默认调用指定 Skill。
---

# Conduct · 工作偏好

先读取[共享调用规则](../conduct-best-skills/references/command-scope.md)，再读取[本能力规范](../conduct-best-skills/references/preferences.md)。相对路径以本文件位置解析；本入口依赖同级 `conduct-best-skills`，应安装完整 suite 包。缺失时明确报告依赖缺口，不搜索其他项目来拼接规范。

1. 确认当前项目根和可选任务标识，读取现有偏好，只修改用户指定范围并保留其他规则。
2. 交付可编辑文件和本次生效范围；临时 prompt 覆盖不写回，其他项目不继承。
3. 请求查看框架图时启动或复用当前工作空间的本机动态视图，并打开实际 URL；修改偏好后刷新解析，不把配置显示成实际调用成功。

当前 prompt 的明确范围优先；本命令只负责上述工作。需要前置事实时做最少核查，不因加载共享规范自动启动七阶段全流程。只在用户明确要求组合步骤时继续相应后续能力。
