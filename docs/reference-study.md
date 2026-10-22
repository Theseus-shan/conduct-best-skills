# 从 ARIS 与 Nature Skills 借鉴了什么

2026-10-22，基于用户提供的本地源码快照进行结构和使用方式比较。这里只报告实际读取文件中的做法，不验证其宣传效果，也不把其他项目的工具名、模型配置或授权规则直接带入本项目。

参考项目：[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)（本地 LICENSE 为 MIT）、[Nature Skills](https://github.com/Yuan1z0825/nature-skills)（本地 LICENSE 为 Apache-2.0）。本轮重新设计本项目的指令和代码，没有复制其脚本、模板正文或资产；参考目录不进入发布包。

## 观察与实际改动

| 已读来源（相对其仓库） | 有价值的做法 | 本项目的适配 |
| --- | --- | --- |
| ARIS `skills/skills-codex/research-implement-feature/SKILL.md` | 先贯通可运行路径，逐项增加功能；先说明会改变接口或含义的假设 | 实现路径先拿到真实输入到输出的结果，再扩展；普通实现细节无需记账 |
| ARIS `skills/skills-codex/research-pipeline/SKILL.md` | 流程输入输出与续接位置明确；信息性检查点继续推进 | 用实现/优化/继续三条路径和短交接记录承接自然语言任务；不增加逐阶段审批 |
| ARIS `skills/skills-codex/shared-references/resumable-runs.md` | 已执行和已验收分开，恢复从可信进度向前 | 保留已有版本证据机制，新增 `next` 和 `verify-ready`，跳过仍有效的 PASS、重验过期证据 |
| ARIS `tools/iteration_log.py` | 无进展时切换方向，进度信号不冒充质量判定 | 优化记录包含改前依据、变化、改后证据；重复失败无新信息时改变方法；不引入自评分门槛 |
| Nature `skills/nature-paper-card/SKILL.md`、`manifest.yaml` | 按证据和任务类型加载细节；脚本从已加载 Skill 的目录定位；输出与证据范围明确 | 脚本按实际 `SKILL_DIR` 解析，普通任务只读入口，复杂任务才读路径参考；无工具时保留真实简报 |
| Nature `skills/nature-proposal-writer/SKILL.md`、`references/stopping-rules.md` | 按工作模式分派，先内容后措辞，按证据缺口定向修正 | 优化先复现瓶颈，不用新增文档、措辞或代码量证明改善 |
| Nature `docs/skill-scope-smoke-evaluation.md` | 新上下文接收原始请求和材料，检查小请求不被扩展成大流程 | 对小型解释、当前版本恢复和从零实现进行独立试用；观察与程序回归分开报告 |

## 主要差距及解决方式

此前入口主要是流程原则，缺少“下一步具体做什么”的短路径；本地证据工具虽可运行，但最小使用也需要写完整 JSON。现在由 Agent 识别任务路径，用户只需给自然语言目标；一个条件的任务通过 `start` 建立契约，复杂依赖才使用完整配置。

此前“检查通过”容易成为优化的终点。现在明确区分功能正确、科学结论支持、使用体验和性能改善；优化先保留基线，交付时说清哪些改善已经观察到、哪些仍未知。没有用户研究，就不宣称用户喜爱度提高。

## 不直接照搬的部分

- 不固定购买服务、模型身份、评审数量或强制跨模型。选择依赖当前真实能力、任务价值和授权，评审身份不能替代证据。
- 不采用无条件“永不提问”。普通细化直接做，实质改变目标或权限仍需用户决定。
- 不给所有任务加常驻调度器、消息通知、完整科研流水线或多文件模板。仅在确实有需要且获准时启用。
- 不把新的指南自称为效果提升证据。程序检查、实际 Agent 试用与总体效果实验分别记录。

实现入口：[Skill](../skills/conduct-best-skills/SKILL.md)、[三条任务路径](../skills/conduct-best-skills/references/workflows.md)、[工具用法](../skills/conduct-best-skills/references/runtime.md)。实际验证见[验证记录](validation.md)。
