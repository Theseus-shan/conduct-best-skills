# Stage 2 · Task Understanding & Goal Definition · v1.1

输入为有效上下文、原始请求和已有确认记录；输出是逻辑 Task Contract，不强制生成文件。

## 意图与 AI 去模糊化

依次区分 Explicit Request、Success Intent、Project Purpose、Optimization Opportunity。识别任务属于探索、审查、开发、实验、写作或组合任务；保留用户原话，不能把建议改写为用户要求。

检查对象及版本、行为意图、目标优先级、范围、交付和验收的歧义：

- 先核对现有证据和确认记录。指代可唯一定位、普通细化不改变任务实质时自行消解。
- 可逆、非关键且不改变授权的缺口可携带假设继续，说明适用范围和复核条件。
- 存在会改变目标、范围、研究路线、资源或验收的互斥解释且无证据消解时，提出最少必要问题，只暂停受影响工作。
- 不编造“提升 50%”等指标、期限或事实；高置信度不替代证据。尚未选工具属于阶段 3 的实现选择；开放研究不强制预设算法或结论。

重要歧义记录原话、候选解释、证据、影响、采用解释及依据；状态 RESOLVED / ASSUMED / OPEN。RESOLVED 不自动代表用户 AGREED。

## 诊断、协商与契约

从一致性、价值、可行性、可验证性、完整性、风险成本诊断目标。只生成有实质收益的候选：G0 原目标、G1 必要细化、G2 增强、G3 替代；不强制凑齐、不用复杂度或无依据评分代表质量。

根据影响决定确认级别，与 G0–G3 独立：A0 普通细化自动处理；A1 可选增强仅建议、原任务继续；A2 实质改变目标、路线、范围、重要交付、资源或验收，须复用或取得明确确认。部分接受只纳入已接受部分；沉默不等于同意，已拒绝方向不反复推销。

契约字段见 [contracts.md](contracts.md)。区分 scope / non_goals、硬约束 / 软偏好 / 假设。每条验收采用 Requirement → Criterion → Evidence → Status，区分 Mandatory、Quality、Aspirational。科研审查可以交付严格反例或有依据的不确定性，不编造肯定结果、不承诺录用。

信息状态：AGREED / DERIVED / PROPOSED / REJECTED / UNRESOLVED。契约生命周期：DRAFT → ACTIVE；关键变更标记 REVISION_REQUIRED，确认新版本后旧版 SUPERSEDED。普通明确请求直接构成授权依据，不要求重新批准原请求。

## 质量门与回退

检查意图、核心目标、范围、交付、验收证据、必要确认、一致性及关键歧义：

- GOAL_READY：全部明确。
- GOAL_READY_WITH_ASSUMPTIONS：仅剩可逆、非关键且不改变授权的假设。
- GOAL_BLOCKED：关键歧义、冲突或必要授权未解决。

执行中出现目标漂移或验收冲突，局部重开协商并保留版本与确认依据。资料失效先返回阶段 1。未接受建议不进入 ACTIVE 契约；不得降低标准掩盖失败。
