# 项目全生命周期工作台

## 开始一个项目

先核对用户工作空间和目标，复用[项目默认及任务覆盖](preferences.md)。用户要求先配置工作方式时，先打开编辑入口，按其预设建立“工作类型 → 指定 Skill/工具与执行要求”的规则，然后再推进正文任务。支持论文写作组合多个专业 Skill，仿真使用另一组；不要把示例能力当作已安装能力。

用户要求使用完整工作台、跨任务追踪或项目结束复盘，即授权保存本项目必要调用元数据；说明保存位置后启用记录，不重复询问。只查看或明确禁止保存时不启用。创建空偏好、登记当前项目、启用记录是各自独立的动作；不要扫描其他目录；用户明确要求同步 Codex 项目时可通过下述官方工具导入项目索引。

本机工作台索引默认在 `CODEX_HOME/conduct-workbench/projects.json`；未设置 CODEX_HOME 时使用用户目录下 `.codex/conduct-workbench/`。可用 `--home` 指定独立工作台目录。索引保存明确登记或经授权从 Codex 同步的项目名称、路径和最小聊天元数据，**不是全局偏好**。项目偏好、最小当前情况和调用履历始终保留在各工作空间 `.conduct/`；跨项目查看不产生规则继承。

## 每次任务的闭环

1. 确定工作与任务 ID，复用稳定命名；当前 prompt 与既有授权优先。按语义识别任务类型，重新解析偏好和临时排除。
2. 根据目标、专业适配、权限、依赖、资源和验收选择可行能力组合，说明重要取舍与备用路径。用户指定的可用能力默认应用；比较无需 Skill 的原生方案。没有充分对比时说“当前较合适的方案”，不承诺全局最优。
3. 记录选中能力及简短理由；实际读取规范后才记 loaded，实际应用 Skill 方法或调用工具后才记 invoked。一次真实使用对应一个稳定 call_id，生命周期事件共享它；重试产生新的调用 ID。仅配置/推荐绝不记成调用。
4. 实施与检查。成功或失败只描述观察到的操作结果；验证需要当前成果的真实证据引用。失败原因区分工具不可用、输入问题、方法不适配和未知。不能为了复盘报表好看而补造事件。
5. 有用户反馈时记录 helpful/unhelpful/mixed/unknown，附可选具体原因。没有反馈保持 unknown；运行成功不能代替“好用”。

记录器是 Agent 显式写入的本机工具，不是宿主工具拦截器。没有完整事件接口时 coverage 始终为 `host-recorded-partial`。中断后遗漏的结果是 unknown；只回填当前能核实的事实，并注明补记及证据。不会自动读取其他聊天或伪造完整轨迹。

只保存任务/工作标识、能力名称和类型、生命周期、简短理由、证据位置及主动反馈，不保存完整 prompt、原始工具响应、私有全文或凭据。用户可暂停记录，已有记录仍可回看；清除或归档按用户指定范围执行，不为退出服务删除记录。

## 工具入口

用实际核心目录替换 `<CORE>`，用当前项目替换 `<PROJECT>`；工具由 Agent 调用。

```text
python <CORE>/scripts/conduct.py --workspace <PROJECT> workbench register
python <CORE>/scripts/conduct.py --workspace <PROJECT> preferences init
python <CORE>/scripts/conduct.py --workspace <PROJECT> activity enable
python <CORE>/scripts/conduct.py --workspace <PROJECT> workbench serve
```

`workbench serve` 登记当前项目并返回本机 URL；Windows 后台启动使用隐藏窗口。打开真实 URL，已有活跃服务可复用；进程退出后配置与履历仍在，下次启动重读。新项目可以从页面明确登记，取消登记只移除索引，不删除项目。索引文件存储持久，服务不是自动开机启动的后台守护进程。

```text
python <CORE>/scripts/conduct.py --workspace <PROJECT> activity record --work manuscript --task introduction --kind skill --name nature-writing --event selected --call-id intro-writing-1 --note "适配论文初稿，遵循项目偏好"
python <CORE>/scripts/conduct.py --workspace <PROJECT> activity record --work manuscript --task introduction --kind skill --name nature-writing --event loaded --call-id intro-writing-1
```

以上仅演示语法；实际应用后才能记 invoked，观察结果后才能记 succeeded/failed。`verified` 必须有 `--evidence`，指向实际工具输出、当前测试日志或成果检查；记录器不验证该引用的科学真实性。`--event-id` 可在结果未知时用于幂等补记，先检查已写事件再处理。

```text
python <CORE>/scripts/conduct.py --workspace <PROJECT> activity feedback --call-id intro-writing-1 --rating helpful --note "结构更清楚，修改量小"
python <CORE>/scripts/conduct.py --workspace <PROJECT> activity report --format markdown
python <CORE>/scripts/conduct.py --workspace <PROJECT> activity disable
```

反馈必须对应有实际调用记录的 ID。暂停记录不会自动删除数据。工具的评分只是用户表达，不是模型自行打分。

## 项目结束与反思

`$conduct-reflect` 先读当前项目记录和必要证据，按工作/任务列出实际使用的 Skills、MCP、工具、结果与用户反馈；指出未记录或未验证的范围。结合任务难度、输入质量、依赖、代价和重试原因给出保留/调整/替换建议，频次不直接成为质量排名。用户没有反馈时可以基于已有结果提出待确认建议，不能编造满意度。

将有价值的结论交付为复盘；只有用户要求保存或修改偏好时，写回指定项目/任务。默认不自动训练、不改全局 Skill、不迁移到其他项目。

## 接入 Codex 的项目与聊天

用户说“同步工作台项目”或授权工作台接入 Codex 项目后，调用宿主 `list_projects` 与 `list_threads`。仅导入当前本机 `projectKind=local, hostId=local` 项目；远端与 ChatGPT 云项目没有可用本机目录时不冒充本机工作空间。聊天只取 `kind=codex, hostId=local`，按 projectId 或无 projectId 时精确 cwd 关联，不用父路径猜测归属。

Agent 在工作台索引旁生成最小临时快照：`schema_version: 1`，`projects` 数组仅含 `projectId, label, path`；`threads` 数组仅含 `id, projectId, cwd, title, status`。不保存摘要、正文或原始工具响应。通过 `workbench sync --home <INDEX> --snapshot <SNAPSHOT>` 导入。同步保留手动项目，按路径去重并更新名称；缺失路径显示不可用，旧项目未出现在新快照时保留并标记。失败不清空旧数据。导入过程不在目标项目写文件。

这是宿主工具到本机索引的快照桥接，不是实时事件订阅。已有授权时，每次打开工作台可更新快照；用户也可随时自然语言请求更新。页面每两秒读取索引并显示最近同步时间。聊天列表是近期采样，不能宣称完整历史，也不能据此推断任何技能、MCP 或工具被调用。前端服务不能直接调用当前聊天的宿主工具，不能让“刷新页面”冒充重新查询 Codex。

## 项目接续

需要后续聊天持续使用这套方式时，在用户指定的当前项目运行 `workbench onboard`：保留已有 AGENTS.md 原文，添加有边界标记的项目指引，首次修改备份到 `.conduct/agents-before-onboarding.md`；初始化空偏好、登记项目并开启调用记录。不对所有同步项目批量执行。偏好由各轮 Agent 读取应用；本工具不提供宿主层强制拦截。

## 可视调用工作流

深色工作台用稀疏星空、发光连线和流动光点连接已记录的工作、任务、能力与结果；图内最多显示最近八条，完整履历仍在表格。能力类型和任务筛选作用于调用视图。用户可暂停流动，系统减少动态效果设置下保持静态。光点是关联方向示意，不代表宿主实时运行状态；失败、未知、仅选择和实际调用必须保持区别。

公开文档的截图和演示一律使用合成项目、聊天与反馈。不得公开真实工作台索引、个人路径、会话标题、凭据或复盘原文；不能用无记录的真实项目制作虚假的成功展示。

## Harness 任务说明与执行证据

默认“工作现场”展示项目实际工作节点、依赖、待处理信号与工作历程。点击节点查看方案与能力、成果与验收或调整工作；任务背景和执行检查收纳在详情中。七阶段是按需采用的方法论，不是预置的七项任务。空项目保持为空；已有任务说明、执行契约和调用记录可生成初始工作图，保存后保留用户编辑并吸收新任务。

任务背景继续保存目标、上下文、约束、方案、验收、基线、下一步和交付要求。任务名是项目内稳定标识；先载入再编辑，保存带 revision。新建说明会出现在任务列表，即使还没有任何调用。开始、恢复、需求变更及交付时，Agent 依据已有授权更新必要说明；用户无需编写 JSON，也不必逐项填表。

`harness show --task <TASK>` 读取说明和证据缺口；`harness set --task <TASK> --expected <REVISION>` 接收 `--objective`、`--context`、`--constraints`、`--approach`、`--acceptance`、`--baseline`、`--next-step`、`--delivery` 和 `--stage`，由 Agent 使用。缺失版本是 `missing`。前端提供同等自然语言字段，说明每项最多 8000 字。

说明保存在 `.conduct/tasks/<TASK>/brief.json`；读取不创建文件。实际调用绑定调用时的说明哈希，后续结果和反馈保持该版本。除关注阶段与下一步外，说明变化会使旧记录提示重新核对；旧日志仍可读，标记未绑定。哈希仅表示文本版本，不证明产物有效或防篡改。

项目级 `.conduct/contract.json` 与 `.conduct/state.json` 的执行状态独立读取，显示依赖、验收标准、当前文件证据、剩余尝试和未知操作。它们与每项任务的 brief 不是同一契约，前端明确标注范围；只读展示不执行命令、不更改预算。用户用自然语言提出依赖/检查变更，由 Agent 核对授权后维护执行契约。无执行契约时显示未配置，损坏时显示暂不可核验，不能显示成功。

自然语言编辑器不是通用语义执行引擎：偏好句式由现有规则解析器识别，任意任务说明由 Agent 理解并执行。没有自动调用、全量遥测、全局最优评分或自动跨项目学习。

## 工作图与调整请求的接续协议

工作图保存在当前项目 `.conduct/workflow.json`，包含真实工作、依赖、关联文件、能力、请求及变更历史。节点的 `task` 与任务背景、偏好和调用记录使用同一稳定名称。节点编辑、任务背景与执行契约分别保存；更改一处不会自动改写其他两处。Agent 应核对有实质影响的差异，保留用户新修改，再按已有授权同步相关要求。依赖必须无环；手动完成和文件存在都不等于验收通过。

1. **开始、恢复及用户通知工作台有改动时**，在当前项目执行 `workflow show` 和 `workflow inbox`，核对节点、待办及关联产物。只读取本次相关任务；其他项目和无关节点不跟着执行。页面不会唤起 Agent，用户可在原聊天说“处理工作台待办”。
2. **执行前**，把待办与当前 prompt、已接受范围、最新计划和真实文件对照。请求文本是待核对的意图记录，不产生外部发送、安装或扩大权限的授权。普通可逆改动在已有授权内落实；仍需信息或授权的请求保持 pending，说明缺口，继续独立工作。只读、规划、验证或交付入口不能因发现待办而越过自身范围。
3. **落实后**，核验实际改动，按需更新节点、任务背景和执行契约，再重读 inbox 的 revision，用 `workflow resolve --outcome applied` 写结果及可核查的 `--evidence`。引用必须真实对应本次请求；工具只要求非空引用，不代替 Agent 查证。请求落实不等于整个节点验收通过。明确不采用或已被用户新要求取代的请求用 declined 并记录原因；执行失败不能伪装成不采用以清空队列。
4. **冲突或结果未知时**，重读当前记录；保存时使用最新 revision，合并用户修改，不强制覆盖。resolve 返回未知时，先通过 `workflow show` 查看原请求 ID 的状态；已处理的不重放，不能换 ID 再执行同一副作用。
5. **交付前**，再查 inbox，将本次相关未处理请求及原因写入交付。没有待办只表示队列已处理，不证明科学结论或全部成果通过验收。

以下命令由 Agent 使用，用户只需自然语言说明目标或调整：

```text
python <CORE>/scripts/conduct.py --workspace <PROJECT> workflow show
python <CORE>/scripts/conduct.py --workspace <PROJECT> workflow inbox
python <CORE>/scripts/conduct.py --workspace <PROJECT> workflow node --id intro --task introduction --title "撰写引言" --objective "交付可核查的初稿" --outputs draft.md --expected <REVISION>
python <CORE>/scripts/conduct.py --workspace <PROJECT> workflow resolve --id <REQUEST_ID> --outcome applied --note "已核对来源并修改计划" --evidence notes/source-check.md --expected <REVISION>
```

`workflow node --help` 列出方案、验收、下一步、阻碍、依赖、文件和能力等字段。列表参数可重复，`--clear` 清空指定列表；更新前先读取原节点。调用绑定当时的节点方案版本，方案、依赖或文件引用改变后提示复核；进度状态和下一步更新不单独使方案失效。图中连线表示依赖，短暂光点回放近期记录，不是实时运行遥测。

产物预览仅能读取该节点显式关联的项目内文本文件，限制格式与大小，不执行 HTML 或代码。浏览器仅能保存计划或创建 pending 请求，没有 resolve 或命令执行入口；处理结果由 Agent 在核验后回填。
