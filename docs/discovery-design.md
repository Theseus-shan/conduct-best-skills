# 多源 Skill Discovery 设计与来源依据

## 原有架构与扩展位置

现有七阶段为上下文初始化、目标理解、能力规划、执行、验证、定向修正、交付。阶段间用逻辑契约传递上下文、任务要求、工作节点和版本证据；简单任务不强制落盘。策略由当前请求、适用的已保存默认、风险相称的自主选择依次决定。

`conduct.py` 已提供 DAG 验收、版本漂移检查、有限重试、未知写入核对和候选能力硬过滤。此前的 `route` 消费宿主提供的能力目录，没有抓取来源、解析外部 Skill、搜索缓存或安装功能。MCP 与 Subagents 由宿主提供，Skill 仅指导其使用，不模拟这些连接。

本次新增发现基础设施，保留原验收执行器及七阶段质量门。Python 3.10+ 标准库实现，仍可独立打包；测试沿用 unittest，实时网络不进入常规 CI。旧 204 项行为目录不改写为已通过。

## 模块与决策

- `discovery_core.py`：规范元数据、保守 frontmatter 解析、来源身份及静态风险线索。
- `discovery_io.py`：公开 HTTPS GET、共享请求/时间预算、限次重试、两类缓存与降级。
- `discovery_sources.py`：六类来源各自处理目录、认证和返回格式。
- `discovery.py`：来源策略、分层检索、去重、可解释排序、能力组合和命令行入口。

来源适配器统一提供 `discover`、`get_metadata`、`resolve_source`、`check_availability`、`get_capabilities`。可用性配置检查不等于在线连通或调用成功。发现报告是规划输入，不能直接作为执行许可。

元数据中的原始声明与启发式观察分开；缺失事实保留未知。仓库、相对路径、不可变版本共同确定身份；同名不同作者不合并，fork 不冒充上游，同一 Plugin 的多个 Skill 分别记录。

排序采用公开的字典序比较，而非未经校准的质量分数：硬排除条件、能力覆盖、环境缺口、相关性、来源可追溯性和稳定 ID。安装量与来源名不能抵消风险。组合为有限贪心覆盖，报告缺口、重叠、版本和显式依赖冲突，不声称最优或完整语义理解。

## 官方事实与适配边界

调研日期：2026-10-22。文档访问和实际 API 请求分别记录，不以文档访问证明运行连通。

| 来源 | 文档依据与实现方向 |
| --- | --- |
| Local | [Codex Skills](https://learn.chatgpt.com/docs/build-skills)：项目祖先至仓库根的 `.agents/skills`、用户 `.agents/skills`、管理目录和宿主内置技能；同名不合并。支持显式多个路径，宿主内置位置由宿主提供，不猜测缓存路径。 |
| OpenAI | [官方仓库](https://github.com/openai/plugins)、[Plugin 格式](https://developers.openai.com/plugins/build/plugins)：当前仓库以 `.codex-plugin/plugin.json` 为主，新格式支持根 `plugin.json`；Plugin、其 Skill 与 MCP 配置分别保留。 |
| Anthropic | [官方仓库](https://github.com/anthropics/skills)、[Agent Skills 规范](https://agentskills.io/specification)：结构符合不等于 Codex 环境可运行；逐个保留许可证与依赖未知项。 |
| Skills.sh | [正式 API](https://skills.sh/docs/api)：`GET /api/v1/skills/search`，Vercel OIDC 认证。只接此文档接口，不运行 npx 或猜测内部接口；非 GitHub 来源报告受限。 |
| SkillsMP | [API 文档](https://skillsmp.com/docs/api)、[OpenAPI](https://skillsmp.com/openapi.json)、[条款](https://skillsmp.com/terms)：关键词接口支持匿名及授权密钥；以 `data.skills` 契约解析，配额以服务实际响应为准，不接禁用试点。 |
| GitHub | [Search API](https://docs.github.com/en/rest/search/search)、[限额](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)：匿名公开仓库搜索；授权后可代码搜索；先确认仓库公开，再固定 commit，读取候选文件验证。 |

调研所见 OpenAI 仓库版本为 `0722921d5542fc593105c27bd52630babd8b8c2a`，Anthropic 为 `dbd4588f9e1033efb41dad4bef2f7947c8993d44`。它们是调研快照，不固定为所有未来搜索版本。实际候选记录解析到的 revision；有截断、认证或版本解析失败时明确披露。

缓存、配置、授权与复现命令见[使用指南](../skills/conduct-best-skills/references/discovery.md)。测试及线上边界见[验证记录](discovery-validation.md)。
