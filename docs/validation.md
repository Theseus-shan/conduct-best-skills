# Documentation and release validation / 文档与发布验证

## 实际工作图与请求接续 / 2026-10-22（当前增量）

- 完整程序回归：176 项，174 通过，2 项平台条件跳过。新增 12 项覆盖真实任务推导、用户编辑保留、无环依赖、项目与 revision 隔离、路径边界、请求幂等/处理依据、产物预览、手动完成语义和方案版本失效。
- 浏览器实测：默认工作图与节点切换、自然语言计划保存和刷新保留、空项目及项目隔离、文本产物预览、请求 pending、Agent 落实核验后回填结果及证据、旧 revision 冲突、只读演示拒绝保存。并发冲突保留原编辑且不覆盖新版本。
- 布局与动态：桌面和 390 × 844 浏览器视口检查，窄屏详情单列、工作图内部横向滚动，页面无整体横向溢出。四条真实依赖连线，注入明确标记的合成近期调用后，两条入边出现两次、每次两秒的动画。未进行跨浏览器或真实移动设备验收；减少动态效果由 CSS 媒体规则提供，未单独切换系统设置验收。
- 请求协议：总入口、共享入口、恢复、交付及项目指引要求在相关时点读取 inbox，在授权内落实并核验后回填依据；未处理项保持 pending 并交接。此为指令协议与合成操作路径检查，不是宿主自动唤醒或全量 Agent 行为评估。
- 展示和发布：中英文 README 使用重新截取的纯合成工作现场；工作图和测试进入显式发布白名单，解压包检查覆盖 workflow show/node/inbox。私有记录、路径、快照、handoff 和无关工作排除在发布范围之外。

此前驾驶舱及其他章节保留各轮历史范围。程序检查不等于 204 项 Agent 行为目录或 A/B 效果验证。

## Agent Harness 驾驶舱 / 2026-10-22（后续增量）

- 程序回归：164 项，162 通过、2 项平台条件跳过。新增 10 项覆盖任务说明读写隔离、非法输入、并发冲突、调用时版本绑定、旧日志兼容、HTTP 写入范围，以及执行面板只读/损坏状态。
- 前端：七阶段阅读视角、八项自然语言任务说明、缺口提示、能力与版本关系；项目级执行契约以只读方式显示依赖、证据、重试预算和未知操作。
- 浏览器检查：实际保存自然语言验收要求、旧调用变为待复核、外部修改触发冲突、新建无调用任务及跨项目编辑内容清空；未做跨浏览器或真实移动设备验收。
- 公开展示：新增合成任务驾驶舱截图；真实任务说明和项目索引不公开。说明完整度不代表成果验证，不自动判定全局最优。
- 边界：任务说明与执行契约分别维护；页面不运行工具。全量宿主调用采集、跨项目学习和实时项目订阅仍未实现。此前 154 项及其他历史数量保留为对应轮次记录。

## 工作台、命令与公开展示 / 2026-10-22（Asia/Hong_Kong）

- 程序回归：154 项，152 通过，2 项因平台条件跳过；包括自然语言偏好、项目隔离、任务覆盖、并发修改检测、调用状态/反馈及快照导入。
- 元数据与发布：14 个 Skill 入口校验；核心、完整 suite、源码三包的白名单、逐字节内容及解压后独立运行检查。
- 浏览器：自然语言偏好保存、任务停用覆盖、项目切换及聊天归属、结果/证据/反馈显示；深色调用星图、暂停控制和筛选使用合成演示单独检查。
- 公开展示：真实前端搭配虚构数据重新截图，不使用真实项目、聊天或本机目录；预览服务器不读取已有用户数据且拒绝写入。
- 边界：星图动画不是实时遥测；项目/聊天是快照，调用履历只含明确记录的事件。新星图未进行跨浏览器或真实移动设备验收。154 项程序检查不认证 204 项 Agent 行为目录，后者仍为 NOT_RUN。

原始测试日志和本机浏览器检查记录不公开；可用下方命令复验。历史日期和旧数量保留为当时范围，不代表当前版本。

## 多源发现 / 2026-10-22（较早轮次）

新增六类来源适配器、统一元数据、静态初筛、渐进检索、组合和缓存，并接入 `conduct.py discover` 及七阶段说明。当前程序回归、真实接口限制、独立上下文试用和安装包验证见 [Discovery 验证记录](discovery-validation.md)。以下31项及旧包数量均为上一轮历史，不替代最新结果。

## 可用性改进 / 2026-10-22（后续轮次）

参考用户提供的 ARIS 与 Nature Skills 快照后，增加实现/优化/继续三条任务路径，强化最小完整成果、改前改后证据、专业交接和无进展转向；脚本从实际 Skill 目录定位。新增 `start`、`verify-ready`、`next`，使简单任务无需手写契约，也能按依赖检查并简短续接。具体借鉴见 [reference-study.md](reference-study.md)。

31 项程序回归已通过，其中新增 9 项启动、依赖批量执行与续接检查。三个全新上下文完成简短科学解释、版本漂移后恢复、从零构建 CSV 工具；两项代码产物另以额外输入复验。观察、证据哈希和限制见 [usability-evaluation.md](usability-evaluation.md)。这些小样本不更新原 204 项目录，也不构成前后 A/B 或总体效果保证。

当前发布检查通过：13 份文档、147 个本地链接/锚点、12 张 SVG 与双语命令一致性；技能包 17 个文件，源码包 65 个文件。ZIP 内容与白名单及源文件逐字节一致；在隔离目录解压后，安装版演示及 `start → verify-ready → next` 均实际运行成功，解压源码检查通过。Python 3.10 仅做语法兼容检查。

以下 22 项回归、旧包文件数及早期结论均为各轮历史记录，不能替代当前轮次结果。

## 可执行闭环 / 2026-10-22（Asia/Hong_Kong）

本轮新增随 Skill 分发的 [conduct.py](../skills/conduct-best-skills/scripts/conduct.py) 与 [demo.py](../skills/conduct-best-skills/scripts/demo.py)。这是本地程序的功能验证，独立于仍为 NOT_RUN 的 204 项 Agent 行为目录，也不替代三组模型 A/B 实验。

已实际运行 22 项回归，覆盖真实检查失败与修复、文件/测试/契约漂移、证据日志修改或丢失、检查中变更、上游重验使下游过期、独立分支继续、可选条件失败披露、未知写入、超时、缺失可执行文件、有限尝试、锁与中断恢复、路由硬约束和 CLI 执行确认。第一次有效测试发现上游重验没有使下游过期，修复并增加依赖版本核验后全部通过。测试先前也遇到受限环境系统临时目录不可写，已将夹具移入项目的忽略目录；不以环境错误充当程序通过。

一键演示实际完成：UNTESTED → FAIL → PASS → STALE → BLOCKED → PASS。最后核对模拟用户新增函数保持原样、模拟外部记录数为 1、不可用高偏好候选被排除。演示使用固定补丁和合成外部状态，证明工具机制，不证明模型会自主完成同类任务。

复现与机器记录：

```text
python scripts/validate_runtime.py --output local/runtime-results.json
python skills/conduct-best-skills/scripts/demo.py --output local/new-demo
python scripts/check_package.py
python scripts/check_docs.py
python scripts/build_release.py
python scripts/check_release.py
```

`validate_runtime.py` 输出每条实际测试结果、环境及源文件 SHA-256；原始测试失败堆栈留在运行输出。发布检查比对 ZIP 白名单和逐字节内容，在隔离目录运行安装包演示与状态命令，并在解压源码中运行静态检查。Python 3.10 语法解析不等于在 3.10 解释器上执行；当前本地执行环境为 Windows / Python 3.14.7。Linux 和其他 Python 版本需由后续实际 CI 运行验证。

作用与边界：以前这些约束只有指令；现在启用工具后，过期/缺失证据不会返回当前 PASS，未完成依赖或未知操作会拒绝相应检查。宿主仍需设计有意义的检查、列全输入、核验外部观察，并完成专业实现。文件哈希不是防恶意篡改的审计系统，工具不是权限沙箱或自动学习服务。

## 当前规则修订 / 2026-10-20（Asia/Shanghai）

本轮调整策略选择、轻量路径与按问题读取参考，简化规划字段，增加最小恢复记录。阶段 1/T03 的预期同步修订，目录仍为 204 项 NOT_RUN。下文 2026-10-15 的记录是历史验证范围，其中“核心 Skill 未修改”和“没有 Git 元数据”不描述当前工作区。

本轮已运行：`scripts/check_package.py`、`scripts/check_docs.py`、skill-creator 的 `quick_validate.py` 和 `git diff --check`，全部通过。检查范围为结构、链接、元数据及文本差异，不是模型行为。

已阅读本地旧版 A/B 报告：三个简单任务各运行一次，基线和旧版 Skill 均通过核心任务，未观察到结果提升。原始结果的工具过程主要来自 Agent 自述，最终文件与部分测试另有独立核查；没有完整轨迹、随机顺序或精确成本数据。它不代表完整验收，也不能用于证明本次修订的效果。

新版三组对照按 [精简版评估协议](../evals/optimization.md) 执行，目前 NOT_RUN。没有将静态检查或对旧报告的阅读记为新的行为通过结果。

## 历史发布记录

Date: 2026-10-15 (Asia/Hong_Kong).

This record distinguishes static checks, rendering and actual agent behavior. It does not certify the 204 design cases. See [the audit](audit.md) for claim sources and [the evaluation protocol](../evals/README.md) for behavioral evidence requirements.

## Validation scope

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Core Skill preservation | PASS | SHA-256 comparison of all 11 files under `skills/` before and after: unchanged. |
| Package check | PASS | `python scripts/check_package.py`: seven stage files, portable references, 204 cases all NOT_RUN. |
| Documentation check | PASS | `python scripts/check_docs.py`: 10 documents, 102 local links/anchors, 5 SVGs, identical bilingual shell commands. |
| Build | PASS | `python scripts/build_release.py`: 40-file source ZIP and 12-file Skill ZIP; member lists and CRC integrity checked. |
| Archive portability | PASS | Extracted the source ZIP into a temporary directory and successfully rebuilt both packages there. Skill ZIP contents match the source Skill files byte-for-byte. |
| PowerShell installation | PASS | Exact README block run in a disposable fixture: 12 files copied; a second run refused the existing directory without changing file hashes. |
| Bash installation | PASS on Windows Git Bash | Exact README block: first install succeeded, repeat preserved the existing directory. Native Linux/macOS were not run. The shell needed its standard coreutils on PATH. |
| Runtime and syntax | PASS within scope | Commands ran on Python 3.14.7; all scripts also parsed with Python 3.10 grammar. Execution on Python 3.10 itself was not tested. |
| Visual assets | PASS within scope | Five SVGs rendered in local Chrome. Inspected contact sheet; fixed an orchestration connector crossing a caption. Browser text-bound checks found no labels extending past the canvas. |
| README layout | PASS in local preview | Both languages rendered with Marked and Chrome at 1100 px and 390 px. No document-level horizontal overflow or broken local images. Tables/code use horizontal scrolling. |
| Mermaid | PASS in local renderer | Both README architecture blocks and `workflow.mmd` rendered with Mermaid 11.12.0. Renderer downloaded only to temporary storage; no package dependency added. |
| GitHub production rendering | NOT RUN | Local Markdown/CSS preview approximates GitHub; it is not GitHub's sanitizer/Camo/rendering pipeline. Remote badges were substituted in the preview, so their availability was not visually verified. |
| Agent behavior and host discovery | NOT RUN | No fresh-host activation or end-to-end agent evaluation. The catalog remains unchanged; fixture recipes are not success records. |

Static validation can be repeated using the commands above. Rendering used existing local browser tooling and temporary previews outside the public package. At 390 px, the Hero name and slogan remain identifiable; detailed SVG labels require opening at full size. Adjacent prose and tables carry the same essential mechanisms.

## Content and privacy review

Reviewed all ten candidate capabilities against the source files listed in [audit.md](audit.md). Checked that both README versions preserve strategy precedence, conditional delegation, host dependencies, unverified behavior status, installation commands and limits. The four recipes map to existing case IDs and label every output as expected.

The publication scan is limited to allowlisted public files; it checks common credential forms, private/local addresses and machine-specific paths, alongside a manual review of the new prose. This is not a forensic or historical secret audit. URLs in new documentation are public reference projects, official documentation and static badge endpoints. No private workspace paths or user identity are included in the new documentation.

Result: no matches for the scanned credential, private-address or machine-path patterns in the 40 allowlisted public files. This limited result is not a guarantee that every possible secret format is detectable.

## Changes delivered

- Replaced `README.md`; added the matching `README_CN.md`.
- Added five original SVGs, a Mermaid lifecycle source and a standard-library visual generator.
- Added architecture, audit, examples, visual-design and validation documents under `docs/`.
- Added `scripts/check_docs.py`; extended the source-package allowlist and build checks.
- Updated `CONTRIBUTING.md` and `CHANGELOG.md`; regenerated both distribution archives.
- Kept all Skill instructions, metadata, policies and the behavior-case catalog unchanged.

## Publishing boundaries

No remote push or Release creation is part of this work. The supplied workspace has no Git metadata or configured remote, so repository ownership, remote CI status, Issues/Discussions availability and Git history cannot be verified here. Review only the public source archive for initial publication; private design sources and local state are excluded by the allowlist.

行为评估仍未运行，安装文件检查不等于宿主发现成功。发布前需要在干净宿主中完成发现/调用验证，按 P0 协议执行真实任务，并记录证据。任何未来性能或兼容性声明都应基于这些结果。

## 中文视觉更新 / Chinese visual follow-up

已新增五张中文 SVG，中文 README 和详细文档中的图示改用中文版本；项目名与 Codex 专有名称保留。中文徽章标签也已更新。英文图片继续保留。

本次复验：107 个本地链接/锚点、10 张 SVG、双语安装命令检查通过；五张中文图已在 Chrome 实际渲染并目视检查，文字未超出画布；中英文首页在 1100px 与 390px 下均无页面横向溢出或失效本地图片。公开源码包现为 46 个文件，独立技能包仍为 12 个文件，完整性检查通过。以上更新补充此前记录，不改变行为验收尚未执行的状态。

## 项目主旨口径更新 / Purpose alignment follow-up

中英文 README 增加用户痛点、项目愿景与核心主旨，明确七阶段是实现路径。架构、审查、示例、视觉叙事与贡献说明同步调整，保留当前实现、宿主条件和待验证效果之间的区分。核心 Skill、配置和验收案例未作修改。

本轮静态复验：10 份文档、109 个本地链接/锚点、10 张 SVG 与双语命令一致性检查通过。公开源码包 46 个文件、技能包 12 个文件，构建与完整性检查通过。本次修改不新增行为验收或性能证据。

## 学术图解重绘 / Academic schematic redesign

按 Nature Figure 的概念图设计方法重绘五类原有图片，新增上下文与获准经验复用图。中英文共 12 张 SVG，采用白底、直接标注、编号与方向箭头、克制的语义配色，并添加原创文档与目标图标。所有图片仍为定性项目机制示意，没有实验数值、效率承诺或运行实录。

本轮验证：六类中文图已逐图及整页查看；12 张 SVG 在浏览器中完成文字边界与节点内文字留白检查，发现并修正流程图通过标签靠近边框的问题，复验无超界项。双语 README 在 1100px 与 390px 下均无页面溢出或失效本地图片。静态检查通过：10 份文档、114 个本地链接/锚点、12 张 SVG、双语命令一致性。公开源码包更新为 48 个文件，独立技能包仍为 12 个文件。

本轮使用可重复生成的原生 SVG，无图像生成 API、外部素材或新增运行依赖。采用的是学术概念图设计方法，不声明科学数据验证、期刊投稿认证或 Nature 背书。核心 Skill 与 204 项未执行行为案例不变。

## 手绘叙事配图更新

新增一张原创、无内嵌文字的罗盘助手概念插画，放入中英文 README 的项目主旨区。插画已目视检查，参考图的角色、物件组合与构图未复用。以双语正文说明图意，避免暗示真实执行记录。更新后检查通过：117 个本地链接/锚点、12 张 SVG；公开源码包 49 个文件，技能包 12 个文件。插画由内置 imagegen 生成，提示词规格与来源记录见视觉说明。

## 按图意调整画风

前后对比与三种交互改用同一原创罗盘角色的手绘场景；流程、依赖、上下文与品牌横幅保留精确学术矢量。中英文 README 同步替换两处图片并补充译文图注，未增加首页内嵌图片数量。原 SVG 保留供详细查阅。

两张新插画已目视检查：对比不含效率数值，交互图保留用户决策与授权提示，没有将空白清单冒充验证成功。PNG 文件完整性检查通过。119 个本地链接/锚点、12 张 SVG 和双语命令检查通过；公开源码包现为 52 个文件，独立技能包仍为 12 个文件。精确生成提示词已随公开资源保存。本轮没有新增行为验收证据。
