---
name: conduct-discover
description: 按任务查找和比较本地 Skills、工具及获准外部候选；只发现，不安装或调用候选。
---

# Conduct · 能力发现

先读取[共享调用规则](../conduct-best-skills/references/command-scope.md)，再读取[本能力规范](../conduct-best-skills/references/discovery.md)。相对路径以本文件位置解析；本入口依赖同级 `conduct-best-skills`，应安装完整 suite 包。缺失时明确报告依赖缺口，不搜索其他项目来拼接规范。

1. 先搜索本地与当前可见能力，只有存在缺口且允许外搜才扩展来源。
2. 交付候选来源、适用性、依赖和缺口；发现不等于已加载、可运行或已授权。

当前 prompt 的明确范围优先；本命令只负责上述工作。需要前置事实时做最少核查，不因加载共享规范自动启动七阶段全流程。只在用户明确要求组合步骤时继续相应后续能力。
