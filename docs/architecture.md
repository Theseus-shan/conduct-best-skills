# Architecture / 技术架构

[English README](../README.md) · [中文 README](../README_CN.md)

## Purpose before mechanism / 先有目标，再有机制

The architecture serves the outcome the user wants: understand intent, bring in relevant context, select suitable capabilities, execute and repair, and deliver evidence. Authorized preferences can inform later tasks when the host provides storage and observations. The seven stages organize these responsibilities; they are not the product's end goal.

架构围绕“尽可能把用户想做的事做到最好”组织：先理解目标与上下文，再选择能力并执行、修正和验证。每个阶段都应降低与成果有关的不确定性，而不是增加形式化步骤。跨任务经验复用以已有授权、真实记录和适用性为前提；实质性目标变化仍由用户决定。

## What actually runs / 实际运行边界

The host agent reads [SKILL.md](../skills/conduct-best-skills/SKILL.md), then the relevant stage references. The package supplies no executable scheduler, registry, tool adapter, permission middleware, process manager or memory database. `agents/openai.yaml` is display metadata and a default prompt, not a subagent declaration.

宿主读取总控指令，再按需加载阶段文件。总控 Skill 与子 Skill 都是指令；工具和子代理属于宿主能力。七阶段是逻辑质量门，不是七个常驻进程，也不是七个独立可安装技能。

## Lifecycle / 生命周期

![Seven-stage workflow](../assets/diagrams/workflow-cn.svg)

Editable branch-level source: [workflow.mmd](../assets/diagrams/workflow.mmd). The overview merges exceptional exits; the following rules explain their scope.

| Trigger / 触发条件 | Transition / 处理 |
| --- | --- |
| Relevant sources are sufficient | Continue; disclose nonblocking gaps. Increase context depth only where needed. / 非阻塞缺口不妨碍继续，按需深化。 |
| Ordinary reversible detail within scope | Resolve from evidence or state a limited assumption. / 普通可逆细节自行处理。 |
| Material goal, scope, route, resource or acceptance change | Stage 2; obtain or reuse explicit agreement. Silence is not consent. / 实质变化须确认，沉默不是同意。 |
| Relevant capability missing | Stage 3; assess a qualified fallback. External discovery does not authorize installation. / 评估替代能力，发现不等于获准安装。 |
| Independent work and supported, permitted delegation | May overlap with explicit ownership; otherwise stay single-agent. / 有条件并行，否则保持单 Agent。 |
| Dependency or shared-write conflict | Serialize dependent work or isolate ownership. Context isolation is not filesystem isolation. / 依赖串行，共享写入需协调。 |
| Write outcome unknown | Query current state before retry; preserve operation identity if supported. / 先核对状态，避免重复副作用。 |
| Verification finds a gap | Stage 6 locates the root cause; return to stage 1, 2, 3, 4 or 5 as appropriate. Reverify affected artifacts. / 定向回退并重验。 |
| Budget exhausted, no progress, infeasibility, missing authority or cancellation | Stop affected work and preserve valid results; do not label partial delivery complete. / 停止相关工作并准确移交。 |

## Three independent choices / 三个独立维度

- **Execution strategy:** Quality First, Balanced, Adaptive or Custom. Current request → applicable user-saved default → autonomous choice proportionate to risk and size; ask only about unresolved material tradeoffs. The package does not assign numeric budgets to these labels.
- **Context depth:** L1 necessary rules/materials; L2 related dependencies and decisions; L3 deeper evidence, assumption and version checks.
- **Planning depth:** P1 a few work nodes; P2 dependencies and capability mapping; P3 a detailed task graph and failure branches.

策略、上下文深度与规划深度不能混为一谈。Quality First 不代表无限资源；简单任务也不需要生成一套完整报告。

## Selection and delegation / 能力选择与委派

Discovery proceeds from visible metadata to accessible catalogs, then relevant trusted external sources only when a meaningful gap warrants expansion. Matching first checks domain fit, availability, permissions, dependencies, versions and necessary acceptance criteria. Cost and approved preferences rank only eligible candidates. A no-Skill baseline is considered for workflows that do not require a specialist.

发现、可用、选中、加载、调用、操作成功与成果验证是不同状态，不能互相代替。新安装、外部连接、历史调用次数和用户偏好均不能凭空假定。

![Illustrative multi-Skill task graph](../assets/diagrams/orchestration-cn.svg)

This data-report scenario is a **logical composition example**, not a recorded run. Analysis and method review may overlap; report production depends on reconciled findings. Specialist names are roles, not promised installed packages. A single host agent can execute the same dependency graph serially.

Delegated work carries a sub-contract: goal, minimum relevant context, constraints, allowed tools, ownership/write scope, output, evidence and failure criteria. Returned findings are checked for version validity and evidence; disagreements are not settled by majority vote.

## Evidence and state / 证据与状态

The [contracts](../skills/conduct-best-skills/references/contracts.md) define logical handoffs:

`Context → Task Contract → Execution Blueprint → Execution Record + Artifact Manifest → Verification Report → Delivery Package`

These fields can stay in the conversation. File persistence requires applicable authorization; simple tasks need not produce every named document. A verification row connects requirement → artifact/version → method → actual evidence → status. An operation finishing is `EXECUTED_UNVERIFIED`, not `VERIFIED`.

Necessary checks must be supported before verified delivery. Otherwise report partial, blocked or inconclusive delivery, or cancellation with handoff. A rigorous counterexample may successfully complete a review task even when the reviewed proposition is false.

## Preferences / 偏好

![获准的上下文与经验复用](../assets/diagrams/context-memory-cn.svg)


[Learning rules](../skills/conduct-best-skills/references/learning.md) specify optional observations and preference use. No collector ships here. Saving requires permission and actual storage support; absent observations stay unknown. Cross-project transfer is limited to authorized, relevant aggregate experience and cannot transfer private source content or permissions. Current instructions and hard eligibility always take priority.

没有持久化接口时，核心任务仍可执行。行为校准、完整事件覆盖与自动清理都不能仅凭规则文件宣称已经实现。
