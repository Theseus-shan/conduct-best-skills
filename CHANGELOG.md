# Changelog

## Unreleased

- 新增 13 个独立能力入口，保留总控与核心内子命令路由；完整 suite 包同时包含总控和所有入口。
- 新增工作空间显式偏好、任务覆盖、当前 prompt 临时排除和默认能力解析；不继承其他项目、不自动安装或伪造调用。
- 新增本机动态偏好框架图与编辑器，读取当前文件和最近同步上下文，支持版本冲突检查、无效配置提示和连接中断提示。
- 偏好编辑采用自然语言卡片，支持项目默认、任务覆盖、启停及常见工作类型句式；复杂表达交由 Agent 解释。
- 新增长期工作台、项目接续指引、实际调用记录、用户反馈与复盘导出；明确记录只覆盖 Agent 实际保存的事件。
- 接入 Codex 官方项目及近期聊天工具的最小快照，显示同步时间、项目来源和路径可用性；同步不修改目标项目、不推断历史调用。

- 新增六类 Skill 元数据来源适配器、分层发现引擎、来源与版本去重、能力匹配和互补组合，集成 `conduct.py discover` 及七阶段流程。
- 增加有界公开网络读取、默认本地策略、显式凭据使用、两类缓存、降级记录与静态兼容性/风险初筛；发现不自动安装、加载、执行或批准候选。
- 新增确定性接口与安全回归、Discovery 行为场景目录、来源依据和在线验证边界；安装包包含独立可运行的发现工具。

### Changed

- 参考 ARIS 与 Nature Skills，将入口改为实现、优化、继续三条自然语言路径；明确先跑通最小完整成果、按瓶颈选能力、保留优化基线和有依据地停止无效迭代。
- 工具按实际安装目录解析；小任务不启用记账，复杂任务由 Agent 配置，用户无需选择流程或填写契约。

- 未指定执行策略时按风险和规模自主推进，仅澄清重要取舍。
- 入口按具体问题路由；明确简单任务不加载全阶段、不填完整契约。
- 精简规划字段要求，增加可选的最小项目恢复记录，独立于偏好统计。
- 更新阶段 1/T03 的预期行为并保留原设计追溯；新增三组对照协议。
- 区分旧版探索性 A/B 试验、完整案例目录与新版待验证行为。

### Added

- `start`、`verify-ready`、`next`：单条件快速启动、按依赖批量检查和当前版本续接摘要。
- 可选短任务简报、参考项目分析及三项全新上下文试用记录；功能回归增至 31 项，新增入口纳入独立安装包检查。

- 随 Skill 分发标准库 CLI：任务依赖与验收映射校验、硬约束优先的能力路由、真实检查及日志、版本和依赖证据失效检测、未知操作核对、有限尝试和中断恢复。
- 合成任务的一键端到端演示、22 项功能回归、带源文件哈希的测试结果导出，以及解压安装包独立运行检查；CI 纳入这些检查。
- 双语 README 添加可运行入口，明确区分程序已测能力、宿主责任和仍待验收的 Agent 效果。

- 文档视觉改为白底学术示意图：重绘五类原图，新增上下文与获准经验复用图，中英文共 12 张 SVG。

- 中英文 README 增加以用户真实结果为核心的项目主旨，并统一架构、示例、审查与贡献说明的愿景和实现口径。

- 五张完整中文 SVG 与中文徽章，中文文档使用对应图片；译文纳入可重复生成流程。

- 英文主 README 与对应中文入口、原创路由主题 SVG 视觉系统。
- 架构、功能证据审查、验收配方、视觉规范和文档验证记录。
- 文档链接/锚点、SVG 与双语命令一致性检查；公开源码包纳入文档与图片。

- 七阶段总控 Skill、按需加载的阶段参考文件及 UI 元数据。
- AI 去模糊化、阶段交接契约、执行恢复、证据验证和有限修正流程。
- 获授权的使用统计、软偏好及有条件跨项目迁移规则。
- 204 项匿名设计验收案例，初始状态均为 NOT_RUN。
- README Mermaid 流程图、MIT 许可证、贡献与安全说明。
- 跨平台静态检查、GitHub Actions CI 和白名单发布包构建。

### Validation scope

静态检查只覆盖仓库与技能包结构，不代表已完成真实模型行为验收。尚未发布正式版本。

## Workbench presentation update / 2026-10-22

- 深蓝黑界面、稀疏星空与发光调用连线，光点沿工作、任务、能力、结果流动；支持暂停和减少动态效果，不冒充实时执行。
- 双语 README 加入真实前端截图和使用入口；更新架构、使用示例、验证、安全、贡献及视觉说明。
- 新增只读合成展示入口，用虚构项目/聊天/调用/反馈制作公开截图，避免发布真实工作台信息。

## Agent Harness cockpit — 2026-10-22

- Added seven-stage task cockpit with eight natural-language brief fields, revision-safe editing and project/task isolation.
- Bound invocation evidence to task intent; changed goals or acceptance flag older calls for review without deleting history.
- Added evidence-gap guidance and read-only project execution dependencies, check evidence, remaining attempts and unknown-operation status.
- Updated product positioning, skill continuation guidance, bilingual documentation and synthetic cockpit showcase. The companion remains host-driven with partial recorded history.
