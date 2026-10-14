# 阶段交接契约

以下是逻辑字段约定，不是要求每次写入文件的模板。简单任务可省略不适用字段；复杂任务保存前检查已有授权。未知值明确标为 unknown，不编造 ID、时间、版本或资源测量。

## 上下文

- Project Context Profile：project_id、topic_ids、用户主动关联的 sources（reference、scope、authorization、revoked）、confirmed_decisions。使用匿名内部 ID，不在技能包写入个人或真实项目资料。
- Task Context State：task_id、project_id、topic_id、request_reference、execution_strategy 及其来源、sources_read（reference、version、read_at、decision_effective_at、validity）、facts、assumptions、gaps、conflicts、context_status。
- 来源状态与决策状态独立；来源关联撤销后不继续作为自动读取依据。

## Task Contract

contract_id、contract_version、lifecycle_status、original_request、context_reference、execution_strategy、task_type、primary_goal、supporting_goals、scope、non_goals、constraints、deliverables、acceptance_criteria、assumptions、ambiguity_record（适用时）、proposed_improvements、approval_record、blocking_issues、alignment_status。

original_request 默认只留在对话内，若需文件持久化则依照任务保存范围；不得复制进统计库。每项重要信息附 AGREED / DERIVED / PROPOSED / REJECTED / UNRESOLVED 和来源。

验收条目：criterion_id、requirement、kind（Mandatory/Quality/Aspirational）、criterion、evidence_required、status。

歧义条目：原话引用、候选解释、证据引用、影响、采用解释、处理依据、RESOLVED/ASSUMED/OPEN、是否阻塞、复核条件。

审批条目：具体变更/操作、已获授权范围、依据、状态；不以整个计划的批准代替全部具体操作权限。

## Execution Blueprint

plan_id、plan_version、contract_reference/version、planning_depth、work_units、capability_map、skill_routing、tool_routing、agent_assignment、resource_plan、verification_checkpoints、fallback_gates、plan_status、approval_status、remaining_risks。

工作单元：id、objective、dependencies、required_capabilities、expected_output、acceptance_mapping、risk、owner、write_scope、verification_method。

资源计划分别列出用户硬限制、本次操作上限、观测缺口；保留 action/work_unit/task 恢复预算和独立质量迭代预算。无可靠 Token 接口时不得填假精确值。

## 执行、验证与交付

- Action：action_id、work_unit_id、capability、inputs_reference、allowed_scope、expected_effects、retry_safety、observation_method、actual_outcome、evidence_reference。
- Execution Record：contract/plan 版本、节点实际状态、已知副作用、未知操作、故障与恢复、剩余预算、Agent 状态、checkpoint_reference。
- Artifact Manifest：artifact_id、path_or_resource_reference、version_or_hash、producer、related_criteria、verification_reference。
- Verification Report：criterion_id → artifact/version → method → actual_result → evidence_reference → status；附缺陷、未验证事项与阶段状态。
- Refinement Record：defect_id、root_cause、change、affected_artifacts、before/after_version、reverification_scope、progress_evidence、budget_remaining、stop_reason。
- Delivery Package：实际目标完成情况、产物引用、验证证据、剩余问题、复现方式、task_completion、artifact_delivery、validation_status、delivery_status。

恢复时核对契约、计划、产物和外部操作当前状态。任何旧验证均不能自动应用到新版本。
