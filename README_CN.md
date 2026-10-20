<div align="center">

![conduct-best-skills：让目标落到成果与证据。](assets/branding/hero-cn.svg)

# conduct-best-skills

**Turn intent into evidence. · 让目标落到成果与证据。**

面向科研与开发的总控 Skill：围绕你真正想要的结果，连接上下文、能力与执行，让成果有据可验。

[![MIT](https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF%E8%AF%81-MIT-55d6be)](LICENSE)
[![指令型 Skill](https://img.shields.io/badge/%E7%B1%BB%E5%9E%8B-%E6%8C%87%E4%BB%A4%E5%9E%8B%E6%8A%80%E8%83%BD-92b4ff)](skills/conduct-best-skills/SKILL.md)
[![早期版本](https://img.shields.io/badge/%E7%8A%B6%E6%80%81-%E8%A1%8C%E4%B8%BA%E9%AA%8C%E6%94%B6%E5%BE%85%E8%BF%90%E8%A1%8C-f2be68)](evals/README.md)

[English](README.md) · 简体中文

[项目主旨](#项目主旨) · [快速开始](#快速开始) · [工作流程](#工作机制) · [使用实例](#使用实例) · [技术架构](docs/architecture.md)

</div>

## 项目主旨

你是否也遇到过这些情况？

- Codex 执行了你的 Prompt，却没有充分理解你真正想要的结果。
- 安装了很多 Skills、MCP 和工具，你仍不知道什么时候该用什么，Codex 也未必能选好、组合好。
- 复杂任务推进到一半，仍需要你反复指导、纠错和重新规划。
- ChatGPT、Notion 和项目文件里有重要上下文，却未能充分进入当前任务。
- 每次开始新任务，都要重新说明自己的工作习惯和偏好。
- 任务执行结束了，却难以判断成果是否真正达到预期。

**如果有一个 Skill，能够帮助 Codex 主动理解你的目标、合理编排可用能力、自主推进执行与修正、严格验证成果，并在你授权的范围内积累经验，让它越用越懂你，会怎么样？**

这就是 conduct-best-skills 想要实现的未来：

> **让 Codex 不只是完成你说的事，而是尽可能把你想做的事做到最好。**

![原创手绘示意：小罗盘助手理解目标、选择合适能力，再核查成果证据。](assets/illustrations/intent-to-evidence.png)

*先理解目标，再选择能力，最后凭证据交付。原创概念插画，不代表实际执行记录或成果保证。*

这里的“最好”，以你确认的目标、质量要求和资源边界为准。理解意图意味着结合证据主动澄清与提出建议；实质改变目标时，决定权仍在你手中。

当前版本将这一愿景落为七阶段流程规则。跨平台上下文需要宿主提供可用连接及相应授权；跨任务经验积累需要获准存储和可靠记录。这些规则的实际效果仍待行为验收，不能将愿景理解为已经实现全自动连接、学习或结果保证。

**Skill** 是 Agent 按需读取的一组指令文件。本仓库提供**一个总控 Skill**及七个阶段参考文件。模型、工具和可选子代理由宿主提供；专业方法由另行安装的专业 Skills 提供。

> **当前为早期指令型实现。** 包结构与文档已完成本地检查；204 项设计验收场景仍为 `NOT_RUN`。旧版三组探索性 A/B 试验双方均通过核心任务，未观察到结果提升；本轮精简规则尚待对照验证。下文描述的是已经写入的流程规则，不代表已经验证的自主运行系统。详见[验证记录](docs/validation.md)。

## 快速开始

需要能够发现本地 Skills、读取项目文件的 Codex 环境。只有检查与打包命令需要 Python 3.10+，无需额外 Python 包或本项目专用 API Key。专业工具可能有独立依赖。

下载并解压本仓库，在**仓库根目录**打开终端。首次项目级安装选择以下一组命令；目标目录已经存在时不会覆盖。

**PowerShell**

```powershell
$skillTarget = '.agents/skills/conduct-best-skills'
if (Test-Path -LiteralPath $skillTarget) { throw 'Skill already exists; review before updating.' }
New-Item -ItemType Directory -Force '.agents/skills' | Out-Null
Copy-Item -LiteralPath 'skills/conduct-best-skills' -Destination $skillTarget -Recurse
Copy-Item -LiteralPath 'LICENSE' -Destination "$skillTarget/LICENSE"
Test-Path -LiteralPath "$skillTarget/SKILL.md"
```

**Bash / macOS / Linux**

```bash
skill_target='.agents/skills/conduct-best-skills'
if [ -e "$skill_target" ]; then
  printf '%s\n' 'Skill already exists; review before updating.'
else
  mkdir -p .agents/skills &&
  cp -R skills/conduct-best-skills "$skill_target" &&
  cp LICENSE "$skill_target/LICENSE" &&
  test -f "$skill_target/SKILL.md" && printf '%s\n' 'Skill files installed.'
fi
```

在该项目中新建 Codex 对话，确认可用 Skills 中出现 `conduct-best-skills`，然后发送：

```text
请使用 $conduct-best-skills，以 Balanced 策略读取本仓库的 README 和 Skill 入口。
说明项目用途与实现边界，并引用实际读取的文件。不要修改文件。
```

预期产物是一份简短、有来源依据的说明。检查宿主是否实际加载了 Skill；文件存在不等于发现成功或行为正确。如果没有出现，请参照[官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)检查项目路径与宿主设置。

技能包无需额外配置。可以用自然语言指定 **Quality First、Balanced、Adaptive 或 Custom**。当前明确策略优先于用户主动保存的默认值；两者都没有时，按风险和规模自主选择方式。只有重要的质量、时间或成本取舍无法消解时才询问，普通任务直接推进。简单任务无需展示七阶段或填写完整契约。

| 环境 | 证据与支持边界 |
| --- | --- |
| 支持本地 Skill 发现的 Codex | 目标宿主；提供 `SKILL.md` 与 `agents/openai.yaml`。Windows 复制布局已检查；新宿主发现与行为未认证。 |
| 其他支持 Skills 的 Agent | Markdown 理论上可适配；安装、调用和运行行为未验证。 |
| Windows / Linux 打包 CI | 已配置双平台工作流；本地执行了 Windows 检查，不声称远程 CI 已通过。 |

## 为什么需要总控 Skill？

为了接近这个愿景，总控 Skill 将“理解你想实现什么”贯穿能力选择、执行和验收。它把原本需要你反复衔接的环节组织成共同流程，让每一步都能说明它对最终结果的价值。

![组织方式对比：从手动衔接任务、能力和检查，到用共同目标连接路由、执行和证据。](assets/illustrations/shared-route.png)

*左：用户手动衔接零散信息；右：围绕共同目标组织能力与检查。比较组织方式，不表示已测得效率提升。*

| 缺少共同流程时，你可能需要…… | 这套规则如何组织这些工作 |
| --- | --- |
| 还没明确任务就先选 Skill | 先明确范围与验收，再选择能力 |
| 在每一步重复交代上下文 | 按需读取已关联且可访问的来源，交接明确约束与决策 |
| 在新任务中重复说明习惯 | 在已有保存授权及真实记录支持下，复用适用偏好 |
| 手动协调独立任务与依赖任务 | 映射依赖、资源所有权和验证节点 |
| 判断“做完”是否代表“正确” | 将必要要求关联到产物版本与证据 |

这里比较的是组织机制，不是经过测量的效率或质量提升。

## 工作机制

![七阶段：上下文、目标、规划、执行、验证、修正和交付。](assets/diagrams/workflow-cn.svg)

1. **上下文：**读取适用规则和相关来源，根据风险与缺口加深核查。
2. **目标：**区分原始请求、假设和建议，定义成功条件。
3. **规划：**发现可用 Skills、工具和 Agent，先过滤硬约束，再比较成本与适配性。
4. **执行：**遵守依赖与写入所有权；写入结果未知时先核对状态，再考虑重试。
5. **验证：**用可追溯证据检查真实产物是否满足必要条件。
6. **修正：**定位根因，保留有效成果，在有限预算内修复并重验受影响结果。
7. **交付：**给出产物、证据和剩余问题，准确说明完成状态。

明确且已授权的工作自动继续。目标实质变化或权限缺失需要用户决定，只有受影响的工作等待。资料变化回到上下文，目标变化回到目标阶段，能力变化回到规划。替代方案不能降低必要标准；否则准确移交阻塞或部分成果。[详细转移规则与可编辑 Mermaid 源码](docs/architecture.md)。

## 核心能力

| 能力 | 已写入的实际规则 |
| --- | --- |
| 与风险相称的上下文加载 | L1–L3 深度；核查来源、版本和决策状态，不扫描整个账户 |
| 目标协商 | 普通细化可继续；可选增强只建议；实质变化必须获得明确同意 |
| 能力选择 | 可见元数据 → 可访问目录 → 有实质缺口时扩展外部发现，不自动安装 |
| 有条件的协同编排 | 默认单 Agent；收益明确、环境支持且获准时委派，明确依赖与写入边界 |
| 证据与恢复 | 区分执行与验证；有限恢复、版本感知检查和定向修正 |
| 可选偏好 | 获准偏好只对合格候选排序；持久化与观测依赖真实宿主接口 |

以上六项均为**规则已实现，完整行为验收尚未完成**。旧版已有三组探索性 A/B 试验，双方核心任务均通过，未观察到结果提升；不代表本轮精简规则已验证。包检查证明结构有效，不能证明模型一定遵守规则。[功能与来源对应审查](docs/audit.md)。

### 上下文如何进入任务，经验如何复用

![相关上下文经过授权、可访问性与版本核查后进入任务；经验仅在获准保存且适用时供后续任务复用。](assets/diagrams/context-memory-cn.svg)

实线表示当前任务的信息流，虚线表示可选的保存与复用。ChatGPT、Notion 等来源需要真实宿主连接或用户提供的材料；偏好复用也需要授权、可靠记录与适用性核查。

## 与 Agent 如何交互

![三种手绘交互场景：明确任务、范围协商和有条件委派；不是可操作界面。](assets/illustrations/interaction-scenes.png)

*从左到右：A 明确任务直接推进；B 关键歧义由用户决定；C 获准后按需协作。钥匙代表授权，空白清单表示仍需验证。*

**A · 明确任务。** 范围清楚的小型修复可直接推进相关上下文、实现与测试，无须重复批准同一范围。

**B · 模糊目标。** “改进这个模块”可能意味着局部修复或重新设计。Agent 先核对证据，再询问仍未解决的实质选择，同时继续独立且已授权的调查。

**C · 多种能力。** 环境支持且允许时，独立工作可以并发；依赖任务等待输入。主 Agent 核查回传证据后再整合。图中场景是规则示意，并非成功运行实录。

## 使用实例

以下是基于[案例目录](evals/cases.json)的可复现**验收配方**，不是成功案例；对应行为场景均仍为 `NOT_RUN`。

| 任务输入 | 关键决策与能力 | 确认边界 | 预期交付 |
| --- | --- | --- | --- |
| “Balanced：修复这个小 Bug，运行相关检查。” | 轻量规划，文件工具与适用测试（`stage-4-7/X01`） | 范围或权限变化 | 补丁和真实测试依据 |
| “Balanced：改进这个模块。” | 辨别局部优化与重设计（`stage-2/T34`） | 关键歧义需要目标协商 | 明确范围与计划 |
| “Balanced：审查两个独立模块；支持且允许时使用子代理。” | 分开读取范围，整合证据（`stage-4-7/E02`） | 委派必须获准 | 带来源引用的综合发现 |
| “Balanced：按最新修改验证这个产物。” | 检查绑定当前版本（`stage-4-7/V11`） | 已授权检查不重复确认 | 当前产物的新验证证据 |

详见[夹具、完整 Prompt 与失败检查](docs/examples.md)。本包不附带或保证任何特定专业 Skill 或连接器。

## 架构与设计理念

```mermaid
flowchart TD
    U[用户目标与授权] --> H[宿主 Agent：Codex]
    C[相关上下文与获准偏好] --> H
    S[conduct-best-skills 指令] -. 指导 .-> H
    H --> K[可用专业 Skills]
    H --> T[宿主工具与 MCP 连接]
    H --> A[可选且获准的子代理]
    K --> E[产物与证据]
    T --> E
    A --> E
    E --> V[主 Agent 验证与交付]
```

这是**逻辑架构**。实际运行时，宿主读取 Markdown，通过自己的接口执行操作。阶段和契约是约定，不是可执行服务或强制状态机。

设计区分**上下文深度与规划深度、建议与已接受目标、操作成功与成果验证通过。** 每个额外 Skill、Agent 或重试都应服务于任务要求，简单任务可以只在对话中完成。

| 仓库区域 | 用途 |
| --- | --- |
| [skills/conduct-best-skills/](skills/conduct-best-skills/) | 一个入口、七阶段参考、契约、学习规则与 UI 元数据 |
| [evals/](evals/) | 204 项设计场景与人工行为评估协议 |
| [docs/](docs/) | 架构、验收配方、证据审查、视觉设计和验证记录 |
| [assets/](assets/) | 原创可编辑 SVG 与 Mermaid 流程源码 |
| [scripts/](scripts/) | 标准库检查、视觉生成与白名单 ZIP 打包 |

## 局限与下一步

本包不包含后台调度器、权限拦截器、事件采集器、Agent 隔离层或存储引擎。它不能保证远程取消，不能读取不可访问的历史，也不能让缺失工具变得可用。记忆、检查点和跨项目偏好复用需要真实接口及授权。执行指令目前使用中文；双语 README 不代表 Skill 正文已经英文化。

通向这一愿景，需要用真实任务证据逐步验证目标理解、能力组合、上下文复用与偏好积累是否有效。

**建议后续推进，尚未交付的内容：**公开匿名 P0 行为证据；将代表性场景与无 Skill 基线重复对比；记录宿主发现与兼容性结果。当前不宣称效率提升、特定模型成功率或自动学习保证。

## 构建与参与贡献

```sh
python scripts/check_package.py
python scripts/check_docs.py
python scripts/build_release.py
```

构建生成 `dist/conduct-best-skills-source.zip`（含文档与视觉的公开源码）与 `dist/conduct-best-skills-skill.zip`（独立 Skill 和许可证）。明确白名单排除私有设计材料与本地状态。将 **Skill 包**解压到宿主技能目录，保留 `conduct-best-skills/` 文件夹；source 包用于整个仓库。

请阅读[贡献指南](CONTRIBUTING.md)、[安全说明](SECURITY.md)、[验收协议](evals/README.md)和[变更记录](CHANGELOG.md)。仓库包含 Issue/PR 模板。行为评估仍为 NOT_RUN；静态验证通过不代表实际行为效果已经验证。

## 反馈与建议

欢迎通过 [Issues → New issue](https://github.com/shan2223/conduct-best-skills/issues/new/choose) 提交使用反馈、Bug 和优化建议。提交前请先搜索已有 Issue；相同问题可以在原讨论中补充证据。

- **Bug 反馈**：选择 Bug report 模板，说明任务场景、预期结果、实际表现、复现步骤、Skill 版本与运行环境，并尽量提供脱敏后的最小示例。
- **优化建议**：选择 Feature request 模板，说明希望解决的问题、期望达到的结果，以及如何判断改进有效。
- **代码与文档贡献**：欢迎先开 Issue 讨论，再提交 Pull Request；具体要求见[贡献指南](CONTRIBUTING.md)。

请勿在公开 Issue 或 PR 中上传 API Key、私人对话、个人信息或未公开项目资料。安全与隐私问题请按[安全说明](SECURITY.md)处理。

## 致谢与许可证

感谢 [Nature Skills](https://github.com/Yuan1z0825/nature-skills) 为任务导向示例、安装说明与学术图解提供参考；感谢 **Ian Xiaohei Illustrations** 带来的手绘科普与视觉叙事灵感。本项目未复用其图片或文案，详见[设计说明](docs/visual-design.md)。

代码、文档和原创视觉资源采用 [MIT License](LICENSE)。
