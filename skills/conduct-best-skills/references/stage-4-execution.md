# Stage 4 · Intelligent Execution & Runtime Control · v1.0

输入为有效契约、已检查蓝图和操作授权。核对环境变化、未结束或结果未知的操作、资源与恢复条件，再执行就绪节点。

## 执行和记录

节点状态：PENDING / READY / RUNNING / WAITING / RETRY_PENDING / EXECUTED_UNVERIFIED / FAILED / BLOCKED / CANCELLED。依赖未满足不启动下游；失败只传播到真实依赖；独立工作可以继续。共享可写资源具有明确所有者。

关键 Action Contract 记录 action_id、work_unit_id、capability、inputs、allowed_scope、expected_effects、retry_safety、observation_method。只在任务必要范围内保留输入，不将正文或秘密复制进统计库。

维持目标、授权、数据、依赖、证据和资源完整性。记录真实调用结果、产物版本、错误及资源观察；不可确认的操作结果为 UNKNOWN，不直接当失败或成功。操作完成只标记 EXECUTED_UNVERIFIED。

## 风险分级恢复

| 风险 | 行为 |
| --- | --- |
| R0 只读、纯计算 | 在有限预算内重试 |
| R1 可修复局部错误 | 诊断后定向修复 |
| R2 写入未知或共享冲突 | 先查询实际状态、版本和副作用，再决定是否重试 |
| R3 不可逆、重大费用、敏感数据或新增权限 | 不盲目重试，检查必要授权 |

按 Action → Work Unit → Task 分别限制重试、修复、重规划和无进展次数，以及可观测资源。尊重用户硬上限；未指定时在开始重复恢复前选用有限且与风险相称的上限，说明它是本次操作限制，不冒充用户偏好。不能通过更换工具重置已耗预算。

按根因选择 Diagnose → Retry/Repair、Fallback、Replan 或 Escalate，不要求逐级尝试。写入超时不等于失败；支持幂等键时保留同一操作身份。工具链或依赖变化回阶段 3，目标/范围/资源承诺变化回阶段 2，资料问题回阶段 1。

## 检查点、委派与恢复

重要节点完成、重大写入前后、计划变更、等待或中断时评估获准的检查点。Light 保存状态、版本、引用和待办；Full 按需增加快照和外部状态。检查完整性，不自动创建大量文件。

委派结果先核对任务、证据与当前版本，不合并过时成果；单个 Agent 失败不丢弃其他有效工作。必要时在预算内重分配。

PAUSE 保留可恢复状态；CANCEL 停止新调度并核对运行操作；CLEANUP 仅按明确范围清理。无法确认远程停止时标记 STOP_UNCONFIRMED。恢复先核对记录、当前工作区和外部副作用，不重放已完成操作、不用旧快照覆盖用户新修改。

## 退出

输出 Execution Record、实际 Work Products、Artifact Manifest、未完成工作、可用恢复依据；已启用统计才产生相应事件。检查节点、操作、产物版本、权限冲突、Agent 状态和恢复信息可交接。

状态：EXECUTION_COMPLETE / EXECUTION_PARTIAL / EXECUTION_BLOCKED / EXECUTION_CANCELLED / EXECUTION_INTERRUPTED。COMPLETE 仅表示执行结束，必须交阶段 5 判定质量；无法继续或取消时可交阶段 7 移交已完成部分。
