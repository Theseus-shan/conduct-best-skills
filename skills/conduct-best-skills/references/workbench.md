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
