---
name: conduct-resume
description: 核对当前文件、已有记录与过期证据，从可信进度继续中断任务并保留用户新修改。
---

# Conduct · 恢复工作

先读取[共享调用规则](../conduct-best-skills/references/command-scope.md)，再读取[本能力规范](../conduct-best-skills/references/workflows.md)。相对路径以本文件位置解析；本入口依赖同级 `conduct-best-skills`，应安装完整 suite 包。缺失时明确报告依赖缺口，不搜索其他项目来拼接规范。

1. 使用“继续”路径；区分偏好文件与真正的执行状态，有 contract.json/state.json 才按 runtime.md 使用 next/status。
2. 已使用工作台时核对 `workflow show/inbox`，按[接续协议](../conduct-best-skills/references/workbench.md#工作图与调整请求的接续协议)处理范围内待办并核验回填；未处理项保留。再从最早必要未完成处继续并验证；未知写入先核对，不能重放副作用或覆盖新修改。

当前 prompt 的明确范围优先；本命令只负责上述工作。需要前置事实时做最少核查，不因加载共享规范自动启动七阶段全流程。只在用户明确要求组合步骤时继续相应后续能力。
