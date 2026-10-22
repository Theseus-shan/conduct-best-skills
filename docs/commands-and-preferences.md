# 独立命令、工作空间偏好与动态框架图

每项能力有独立 Skill 入口；总控仍可按自然语言自动组织工作。采用 ARIS 本地 `skills/skills-codex/` 的按能力分目录结构，保留本项目自己的阶段规范与权限边界。这里的 `$conduct-*` 是 Codex Skill 调用入口，不是新注册的 shell 命令或原生斜杠命令。参见 [OpenAI 的 Skill 目录规范](https://developers.openai.com/plugins/build/skills)和[显式调用说明](https://developers.openai.com/blog/eval-skills)。

## 命令选择

| 命令 | 目的与边界 |
| --- | --- |
| `$conduct-best-skills` | 按目标组织完整工作，或根据正文限定范围 |
| `$conduct-context` | 核查上下文、来源和决策，不实施改动 |
| `$conduct-goals` | 明确目标、范围与验收，不进入实现 |
| `$conduct-plan` | 规划依赖和能力组合，交付计划后停止 |
| `$conduct-discover` | 发现并比较能力，不自动安装或调用候选 |
| `$conduct-build` | 实现需求，贯通真实路径并验证 |
| `$conduct-improve` | 保留基线，改进项目并给出前后证据 |
| `$conduct-resume` | 核对当前状态，从可信进度继续 |
| `$conduct-verify` | 核查已有产物，不自动修复 |
| `$conduct-refine` | 根据缺陷定向修复并重新验证 |
| `$conduct-deliver` | 整理成果、依据和移交，不自动发布 |
| `$conduct-preferences` | 编辑项目默认/任务覆盖，打开动态偏好图 |
| `$conduct-workbench` | 打开工作台，同步 Codex 项目与近期聊天 |
| `$conduct-reflect` | 按任务复盘能力使用、证据与用户反馈 |

例如：`$conduct-plan 为当前项目制定实验实现计划，先不要写代码。`

只安装核心时，使用 `$conduct-best-skills plan ...`、`$conduct-best-skills preferences ...` 等内置路由形式。独立入口依赖同级共享核心，不能只复制单个包装目录。全部命令保留正常自动发现；没有设置 explicit-only。

## 安装完整命令集

运行 `python scripts/build_release.py` 后，完整包为 `dist/conduct-best-skills-suite.zip`。将其中的 14 个同级文件夹放入宿主实际使用的技能目录。首次安装可直接解压；已有同名技能先备份并检查差异，不能盲目覆盖本地定制。

传统 `conduct-best-skills-skill.zip` 仍只包含核心，自带偏好工具和总控内路由；`conduct-best-skills-source.zip` 包含源码、全部入口、测试和文档。新建聊天后确认宿主发现所需入口；当前聊天的技能目录列表不保证自动刷新。

## 每个项目有自己的工作方式

开始工作时由 Agent 定位用户正在运行的工作空间，创建缺失的空白项目配置并提供编辑入口。已有配置保持不变；明确只读或禁用持久化时不创建。用户无需手写 JSON，直接用自然语言修改即可：

```text
$conduct-preferences 在当前项目中，只要起草、修改或润色论文，
默认调用 Anti-Defensive Writing，保留必要的科学局限和不确定性。

$conduct-preferences 仅在 paper-a 任务中停用上述写作规则。

$conduct-build 完成这个论文段落的重写，但本次不要用 Anti-Defensive Writing。

$conduct-preferences 打开当前工作空间的偏好框架图。
```

配置位于项目内 `.conduct/preferences.json`；任务覆盖位于 `.conduct/tasks/<task-id>/preferences.json`。同 ID 的任务规则替换项目规则，不同 ID 合并。当前 prompt 的明确选择优先；临时禁用不改默认。其他工作空间、父目录和其他任务覆盖都不读取。

一条规则包含稳定 ID、任务类型 `when`、能力列表 `skills`、执行要求 `instruction` 和开关 `enabled`。`workflow` 保存语言、策略或输出偏好。工具负责精确合并、类型匹配、排除和来源记录；Agent 负责识别实际工作类型、把能力显示名解析到真实 Skill、加载并应用其规范。不存在的 Skill 只报告不可用，不自动安装或冒充调用。

详细字段与例子见[偏好规范](../skills/conduct-best-skills/references/preferences.md)。Anti-Defensive Writing 是用户可配置的示例目标，不随本包提供，也不在空白项目中默认启用。

## 动态图与编辑

用 `$conduct-preferences` 打开图时，Agent 在本机启动视图并打开实际 URL。框架图展示项目默认 → 任务覆盖 → 当前 prompt → 当前规则，并列出每条规则的来源、触发类型、指定能力及启用、未命中、停用或被覆盖状态。

编辑器可切换项目与任务范围、插入写作示例，以自然语言保存偏好和启停规则；用户无需编辑代码。常见句式直接识别，复杂表达由 Codex 解释后保存。保存前验证格式和已载入版本；他人先修改文件时拒绝覆盖并提示重载。文件变化约两秒内更新图，不需重新生成图片。

当前 prompt 无法被一个独立本机页面自动感知。Agent 在开始任务、切换类型或收到临时覆盖时用 `preferences context` 同步最小上下文，图上显示最后同步时间。这个文件只是最近情况，解析新的任务不会把它当成默认。筛选和切换任务只改变查看范围。

服务只监听 `127.0.0.1`，不发布网站、不读取聊天、无第三方前端依赖。进程退出后停止刷新并提示图已过期。代码解析通过不代表真实宿主已经遵循默认能力调用；该部分仍需要实际使用观察。

## 本轮检查

回归覆盖项目/父目录/任务隔离、覆盖优先级、临时禁用不污染默认、任务类型匹配、配置重读、无效数据、版本冲突、已有配置保留、本机 HTTP 编辑与刷新，以及偏好先于执行状态创建。安装包另验证三个归档的字节一致性和解压后的独立运行。真实宿主自动发现与所有模型行为不是这些程序检查的认证范围。

## 长期工作台

说“用 $conduct-workbench 打开工作台并同步我的 Codex 项目”，Agent 通过 Codex 官方项目/聊天工具接入本机项目，无需逐个登记。页面展示同步时间、近期聊天、各项目的工作与任务、实际能力调用及反馈。项目与聊天是快照；自然语言请求再次同步，页面随后自动更新。云项目和远端目录目前不纳入本机工作空间。同步只写索引，不批量修改其他项目。

需要新聊天继续遵循工作方式时，Agent 对当前指定项目使用 `workbench onboard`，保留并备份已有 AGENTS.md，再添加本项目接续指引。项目偏好不会变成全局设置。调用由 Agent 显式记录，区分选中、加载、实际调用、成功、失败、验证与用户反馈；未记录的历史不能自动补全。用户可暂停记录或通过 `$conduct-reflect` 导出有证据的复盘，频次不等于质量。

界面信息层级参考 [Plane](https://github.com/makeplane/plane) 的项目工作组织与 [shadcn Dashboard](https://ui.shadcn.com/examples/dashboard) 的概览卡片；本项目独立编写布局、样式和交互，未复制其代码或资产。

## 深色调用星图

“工作总览”和“调用与复盘”使用星空底色，将工作、任务、Skills / MCP / 工具以及记录结果连接成发光线路。光点沿连线运动，表达关联方向；不会把成功、失败或未知结果改成“正在运行”。图中最多展示当前范围最近八次调用，完整记录保留在表格中。“调用与复盘”的能力类型及任务筛选同时作用于图与表格。

使用“暂停流动”可停止动画；系统开启减少动态效果时，连线保持静态。窄屏采用图内横向滚动。无记录时展示空状态，不生成虚构调用。

公开 README 截图由 `python scripts/preview_workbench.py` 启动真实前端并用合成数据渲染。它不读取真实索引、项目或聊天；保存操作被拒绝。生产工作台继续使用 `workbench serve`。

## 用自然语言维护完整任务

打开工作台默认进入“工作现场”。点击实际工作节点，在“方案与能力”“成果与验收”“调整工作”之间切换；“编辑计划”保存自然语言方案、标准、下一步、能力和关联文件，可勾选前置工作。新项目用“＋ 新工作”建立真实工作。“任务背景”保留目标、材料、约束、基线及交付要求；它与工作图、执行契约分别保存，Agent 核对差异后同步。

例如：“这篇论文先梳理研究缺口，再起草引言；保留事实与引用，交付时附引用核对清单。把这些作为当前任务说明。”Agent 可据此维护说明，不要求用户填写配置代码。任务规则仍在偏好地图编辑，调用反馈仍在调用与复盘填写。

“现在需要处理”汇总待办、缺失输入、阻碍、失败与旧版调用，已有执行契约显示检查与恢复状态。保存采用版本检查，冲突时保留编辑内容，重新载入并合并新要求。用户在“调整工作”中写一句话，保存后回到 Codex 说“处理工作台待办”；Agent 读取 `workflow show/inbox`，落实并核验后用 `workflow resolve` 记录结果与依据。未解决项保持 pending，页面不会自动唤起 Agent。

`conduct.py workflow show|node|inbox|resolve` 和 `harness show|set` 都是 Agent 辅助入口，用户无需记忆 CLI 或编写 JSON。详细规则见[工作台接续协议](../skills/conduct-best-skills/references/workbench.md#工作图与调整请求的接续协议)。
