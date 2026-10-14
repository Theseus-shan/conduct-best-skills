# Documentation and release validation / 文档与发布验证

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
