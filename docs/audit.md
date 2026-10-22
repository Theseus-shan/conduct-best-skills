# Repository audit / 仓库审查

## 当前增量：工作台与命令 / 2026-10-22

当前包包含总控和 13 个独立入口、项目偏好与任务覆盖、自然语言编辑、动态偏好地图、显式调用记录、反馈与复盘，以及本机 Codex 项目/近期聊天的快照同步。深色调用星图根据记录连接工作、任务、能力与结果；动画只表达方向。公开展示使用合成数据。

依据：[命令与偏好](commands-and-preferences.md)、[架构](architecture.md)、[工作台实现](../skills/conduct-best-skills/scripts/workbench.py)、[调用记录](../skills/conduct-best-skills/scripts/activity.py)、[验证](validation.md)。下文“没有存储引擎”等表述是历史审查快照；当前已有项目本地存储，仍无完整宿主事件拦截或自动学习。

## 历史审查快照

2026-10-22 多源发现轮次：在既有能力路由之前增加六类元数据来源、统一解析、去重、预算、缓存、静态初筛及组合建议。实际实现和接口限制见[设计分析](discovery-design.md)，验证见[Discovery 记录](discovery-validation.md)。下列历史快照中“不提供来源适配器”的描述不再代表当前包；仍不自动安装、执行或批准外部 Skill。

2026-10-22 后续轮次：新增实现/优化/继续路径、快速启动与批量检查、简短续接说明。31 项程序回归和三个独立上下文小任务试用的范围见 [可用性记录](usability-evaluation.md)；借鉴来源及未采用的假设见 [参考比较](reference-study.md)。

2026-10-22 更新：现已增加 [本地闭环工具](../skills/conduct-best-skills/references/runtime.md)，支持持久化任务契约、DAG 校验、能力过滤、实际检查执行、证据哈希与过期判定、未知操作记录、有限尝试及报告。回归和演示结果见[验证记录](validation.md)。下列历史快照中“没有执行工具/本地存储”的描述不再代表当前包；外部连接、专业判断、权限和模型效果仍不由此工具保证。

2026-10-20 补充：入口现按问题加载参考，未指定策略不再单独阻塞，完整契约仅用于需要它的复杂交接。旧版三组探索性 A/B 的核心结果双方均通过，未观察到增益；新版行为对照仍未运行。下文为原审查快照，历史环境和“无已完成报告”描述不代表当前状态。最新范围见 [验证记录](validation.md)。

Audit date: 2026-10-15 (Asia/Hong_Kong). Scope: the supplied workspace, before README implementation; no Git repository metadata or remote URL was present. No repository `AGENTS.md` was found. Original design files are private background and are not release dependencies.

## Positioning / 项目定位

**Project purpose:** help Codex understand the intended outcome, coordinate available capabilities, use relevant context, execute and refine within scope, verify results, and reuse authorized experience. The seven stages are the current implementation approach to that purpose.

**项目主旨：让 Codex 不只是完成你说的事，而是尽可能把你想做的事做到最好。** 七阶段是服务于这一主旨的实现路径。“最好”受用户确认目标、质量要求与资源边界约束；“越用越懂你”是依赖授权、存储与真实证据的长期方向。

One instruction-based coordinating Skill for research and development. It connects task intent, available capabilities and evidence-based delivery. Its distinction is the separation of goal agreement, capability eligibility, execution and verification, with proportional context and bounded recovery. It is not a specialist library or agent runtime.

一个总控入口、七阶段参考、两份交接/学习规则、一个 UI 元数据文件。没有运行时 SDK、连接器、后台服务或自动执行评估器。定位以现有规则为准，不扩大为全自动平台。

## Claim-to-source map / 功能证据表

“Rules implemented” means reviewed instruction text exists; it does **not** mean behavior tests passed.

| Candidate capability | Evidence | Status and boundary |
| --- | --- | --- |
| Context initialization | [Stage 1](../skills/conduct-best-skills/references/stage-1-context.md) | Rules implemented: L1–L3, source/version/conflict checks; behavior unverified |
| Task understanding | [Stage 2](../skills/conduct-best-skills/references/stage-2-goals.md) | Rules implemented: intent, assumptions, ambiguity and contract; behavior unverified |
| Goal optimization | [Stage 2](../skills/conduct-best-skills/references/stage-2-goals.md) | G0–G3 candidates only when valuable; A0–A2 approval based on impact; behavior unverified |
| Skill discovery | [Stage 3](../skills/conduct-best-skills/references/stage-3-planning.md) | S1–S4 progressive discovery rules; no registry or auto-installer |
| Skill matching | [Stage 3](../skills/conduct-best-skills/references/stage-3-planning.md) | Hard eligibility then fit/cost/preferences; no measured ranking performance |
| Tools and subagents | [Stages 3](../skills/conduct-best-skills/references/stage-3-planning.md) / [4](../skills/conduct-best-skills/references/stage-4-execution.md) | Conditional host-backed delegation and tools; no built-in isolation or adapters |
| Execution planning | [Stage 3](../skills/conduct-best-skills/references/stage-3-planning.md) | P1–P3, work graph, routing and gates; behavior unverified |
| Human decisions | [Entry](../skills/conduct-best-skills/SKILL.md), stages 1–3 | Reuse authorization; only affected work waits; no permission enforcement layer |
| Execution and verification | [Stage 4](../skills/conduct-best-skills/references/stage-4-execution.md), [5](../skills/conduct-best-skills/references/stage-5-verification.md), [6](../skills/conduct-best-skills/references/stage-6-refinement.md), [7](../skills/conduct-best-skills/references/stage-7-delivery.md) | Recovery, evidence, refinement and truthful delivery rules; behavior unverified |
| Memory and preferences | [Learning](../skills/conduct-best-skills/references/learning.md), [contracts](../skills/conduct-best-skills/references/contracts.md) | Optional authorized persistence rules; no storage engine or automatic collection |
| Portable packaging | [Checker](../scripts/check_package.py), [builder](../scripts/build_release.py) | Executable standard-library implementation; local results in [validation](validation.md) |
| Behavior evaluations | [Protocol](../evals/README.md), [catalog](../evals/cases.json) | 204 design cases, all NOT_RUN; no success rate |

## Release inventory / 发布边界

The existing repository provides MIT licensing, contribution/security guidance, an issue and PR template set, a Windows/Linux CI definition, a static checker and an allowlist packager. CI configuration is not evidence of a remote run. There were no recorded demo transcripts or completed behavior reports to reuse as success stories.

The README examples are explicitly marked evaluation recipes. Proposed next work is evidence collection, baseline comparison and compatibility validation, not an invented feature roadmap. No remote community URL, release badge, model compatibility certification or popularity metric is inferred.

已验证部分与未验证部分见[验证记录](validation.md)。维护者未来可通过真实执行轨迹提升证据等级，不能只把文案改为“已通过”。

## Purpose alignment review / 主旨口径审查

| 主旨 | 当前规则如何承接 | 对外说明边界 |
| --- | --- | --- |
| 理解真正想要的结果 | 阶段 2 区分原始请求、成功意图与目标优化机会 | 主动理解与协商，不宣称能无误推断隐含意图 |
| 知道何时用什么能力 | 阶段 3 发现、筛选与组合技能、工具及可选子代理 | 编排实际可用且获准的能力，不等于自动控制全部已安装能力 |
| 减少反复指导与纠错 | 阶段 4–6 依赖执行、有限恢复、根因修正与重验 | 在已授权范围内自主推进；尚无减少干预的量化证据 |
| 利用分散的重要上下文 | 阶段 1 按关联范围核查来源、版本与关键决策 | ChatGPT、Notion 等是可能的来源，不是本包内置连接器；不可访问时明确缺口 |
| 越用越懂用户 | 学习规则定义获准偏好、观测及有条件迁移 | 当前没有后台采集与存储引擎，不承诺每次任务都会自动学习 |
| 确认成果是否达到预期 | 阶段 5、7 将要求、产物版本、证据与交付状态关联 | 严格验证是规则要求，不是所有成果必然通过的保证 |

本轮口径调整将 README 的叙事从“七阶段机制介绍”前移到“用户结果与项目愿景”，架构与贡献说明同步承接。规则本身与主旨方向一致，无须为调整文案修改核心 Skill。现有行为案例尚未执行，因此上述对应关系只证明设计方向一致，不证明效果已实现。

## Harness 扩展审计范围

任务说明与调用版本绑定用于防止旧意图下的记录被误读为当前依据。当前阶段是显式关注标记，不是验证状态；执行面板只读已有项目契约。公开说明与截图使用合成数据，`.conduct/` 不进入发布白名单。程序回归和浏览器检查见 [validation.md](validation.md)，不据此认证 Agent 自主最优化能力。

## 实际工作图增量审查 / 2026-10-22

默认界面改为真实工作节点与依赖、产物预览、请求和历程；七阶段保留方法论角色。工作图、任务背景、执行契约分别维护，Agent 按当前授权对齐变更，不能把手动完成、请求落实或文件存在当作验收。接续协议覆盖 inbox 读取、落实后的证据回填、版本冲突和未处理项交接。公开展示只用合成夹具；程序与浏览器检查范围见 validation.md，不据此声称全量行为评估通过。
