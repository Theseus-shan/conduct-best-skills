# Stage 3 · Planning & Capability Orchestration · v1.1

前提为阶段 1 和 2 可继续、有效契约、策略及权限资源约束。只做规划和必要的只读可行性探测；用户只要求计划时不进入执行。

## 规划与路由

先按[项目与任务偏好](preferences.md)解析当前 prompt、任务覆盖和项目默认。命中且通过适配/权限核查的显式能力应默认选用并加载；偏好不可用时报告缺口。下面的历史统计排序只用于尚未由显式规则确定的选择。

1. 选择 P1 少量节点与必要检查、P2 依赖与能力映射、P3 详细任务图与故障分支。规划深度不等于上下文加载深度，也不等于执行策略。
2. 将契约拆为有目的的工作单元：ID、目标、依赖、能力需求、产物、验收映射、风险。复杂依赖形成 DAG，简单任务可单节点。
   实现任务优先安排从真实输入到可用输出的最小路径，再扩展功能；优化任务先保留相关基线。操作方法见 [workflows.md](workflows.md)，不为简单任务扩展计划规模。
3. 按 S1 可见能力元数据 → S2 可访问技能目录 → S3 与缺口相关可信外部来源 → S4 必要的扩展公开来源发现能力。需要程序化发现时使用[多源发现工具](discovery.md)：默认 Local → OpenAI/Anthropic → Skills.sh/SkillsMP → GitHub，来源顺序、白名单和预算可调整。核对候选组合的缺口、依赖冲突和来源限制，仅有实际收益且允许外搜时扩展；不要递归调用总控自身搜索。
4. 联合评估模型、Skill、工具/MCP、Agent 的可行组合。先检查专业适配、权限、依赖、版本、硬约束及必要验收；再比较可靠性、成本、效率。非强制专业流程比较无 Skill 基线。
5. 有获准历史偏好时按 [learning.md](learning.md) 检索；偏好仅排序合格候选，不能复活被硬条件排除的能力。
6. 为关键工具做只读 preflight：存在性、依赖、连接、目标资源、版本、副作用及结果可观测性。操作标记 READ_ONLY / MUTATING / HIGH_IMPACT。
7. 设计失败路线：等效工具、原生能力、有限重试、状态核对、缺口报告。降级标记 FULL_EQUIVALENT / ACCEPTABLE_DEGRADED / CONDITIONAL / NOT_FEASIBLE；不得降低必要标准假装可行。

能力状态为 DISCOVERED / AVAILABLE / SELECTED / UNAVAILABLE / EXTERNAL_CANDIDATE / REJECTED。关键外部候选及时说明来源、缺口、收益与成本并协商；非阻塞建议放在交付或计划摘要中。不得仅凭搜索结果自动安装。

## 委派与计划门

先评估单 Agent；只有实际环境支持、允许委派且独立性、专业互补或独立核查收益超过成本时使用 Subagents，不规定数量。子契约包括目标、必要上下文、约束、工具、写入及资源边界、产物、证据和成功/失败标准。相同资源写入须协调或隔离；上下文隔离不等于文件隔离。回传 Findings、Evidence、Uncertainty、Unresolved Issues、Output References、Completion Status，主 Agent 核查后综合，冲突不投票。

计划仅保留当前任务需要的信息：工作依赖、选用能力、预期产物、验证方式和实际存在的风险或等待项。仅多方交接需要完整 Blueprint，字段见 [contracts.md](contracts.md)。检查每项必要要求都有工作与验证安排，能力和依赖可行；没有协作、外部写入或复杂恢复时不为这些维度补空字段。

- PLAN_READY / PLAN_READY_WITH_RISKS：硬检查通过，剩余风险不破坏必要验收。
- PLAN_BLOCKED：关键能力、资源、授权或依赖缺失且无合格替代。
- 审批另记 NOT_REQUIRED / PENDING_APPROVAL / APPROVED / DECLINED；PLAN_READY 不覆盖 PENDING_APPROVAL。

范围和资源未实质变化且已有授权时自行通过，复杂计划简要呈现不等于再次审批。改变契约、重大资源取舍、未授权高影响操作或用户要求先审计划时，等待必要确认。

局部方法变化可自主重规划；关键工具链、依赖、分工、资源或风险变化重过计划门；目标变化回阶段 2，资料失效回阶段 1。保留有效成果、契约约束、变更原因和受影响节点。
