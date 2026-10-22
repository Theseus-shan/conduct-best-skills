# Visual system / 视觉系统

## Purpose and visual brief / 主旨与图示契约

The figures explain how the project connects intended outcomes to context, capability selection, execution and evidence. They are qualitative method schematics for an open-source README, not experimental results, recorded agent executions or journal-submission figures.

围绕项目主旨，每张图只承担一个解释任务：让用户理解目标如何变成执行与证据。采用 Nature Figure 的概念图设计方法——结论先行、明确阅读路径、直接标注、克制配色、先核查关系再修饰外观。这里不声明 Nature 期刊认证或投稿就绪。

| Figure | One-sentence message / 单图结论 | Evidence boundary / 证据边界 |
| --- | --- | --- |
| Hero | A goal guides selection and coordination. / 目标指导能力选择与协调。 | Agents remain conditional. / 子代理有使用条件。 |
| Workflow | Verification closes the task loop; refinement is bounded. / 验证形成闭环，修正有边界。 | Instruction workflow, not enforced runtime. / 是流程规则，不是强制运行时。 |
| Before / after | Explicit coordination connects formerly implicit decisions. / 明确组织原本隐含的决策。 | No measured efficiency claim. / 不虚构效率对比。 |
| Interaction | Autonomy and user decisions have different scopes. / 自主执行与用户决策各有边界。 | Illustrative scenarios, not transcripts. / 是示意，不是运行实录。 |
| Orchestration | Dependencies determine what can overlap and what must wait. / 依赖决定并行与等待。 | No bundled specialist library. / 不暗示附带专业技能库。 |
| Context / experience | Context and preference reuse require access, authorization and validity. / 上下文与偏好复用需要访问、授权和有效性。 | No automatic history access or background learning. / 不暗示自动读取历史或后台学习。 |

## Academic visual language / 学术视觉语言

White backgrounds, charcoal type, thin connectors and restrained fills replace the original dark terminal panels. Panel letters and numbered stages make reading order explicit. Simple document and target symbols are original editable vector illustrations with explanatory roles; they are not decorative scientific imagery.

Use one neutral family, one primary signal family and one decision accent. Arrows encode direction; numbering and labels preserve meaning without color. Solid arrows depict current-task paths. Dashed paths depict qualified recovery or optional persistence, with local labels explaining the specific condition.

| Token | Value / purpose |
| --- | --- |
| Background / 背景 | `#ffffff`, opaque white for readability in either GitHub theme |
| Primary text / 正文 | `#233345` |
| Secondary text / 辅助文字 | `#607181` |
| Main task flow / 主任务流 | `#167d8d`, pale fill `#eaf5f4` |
| Context or parallel capability / 上下文或并行能力 | `#536ca0`, pale fill `#eff0f8` |
| Decision, repair or permission / 决策、修正或授权 | `#ae662c`, pale fill `#faf2e6` |
| Dividers / 分隔线 | `#cbd5dc` |
| English type | Arial → Helvetica → sans-serif |
| 中文字体 | 微软雅黑 → Noto Sans CJK SC → 苹方 → 无衬线 |

The three interaction panels use equal widths, heights and matching vertical anchors. The orchestration branches use the same node geometry. Larger explanatory diagrams deliberately use a dominant process path with subordinate boundary notes rather than equally weighted dashboard cards.

## Bilingual asset inventory / 双语资源清单

| Role | English | 中文 |
| --- | --- | --- |
| Hero / 品牌横幅 | [hero.svg](../assets/branding/hero.svg) | [hero-cn.svg](../assets/branding/hero-cn.svg) |
| Lifecycle / 七阶段 | [workflow.svg](../assets/diagrams/workflow.svg) | [workflow-cn.svg](../assets/diagrams/workflow-cn.svg) |
| Comparison / 组织对比 | [before-after.svg](../assets/diagrams/before-after.svg) | [before-after-cn.svg](../assets/diagrams/before-after-cn.svg) |
| Interaction / 交互方式 | [agent-interaction.svg](../assets/diagrams/agent-interaction.svg) | [agent-interaction-cn.svg](../assets/diagrams/agent-interaction-cn.svg) |
| Dependencies / 多能力编排 | [orchestration.svg](../assets/diagrams/orchestration.svg) | [orchestration-cn.svg](../assets/diagrams/orchestration-cn.svg) |
| Context and experience / 上下文与经验 | [context-memory.svg](../assets/diagrams/context-memory.svg) | [context-memory-cn.svg](../assets/diagrams/context-memory-cn.svg) |

The Hero is 1200 × 430 (2.79:1). All figures retain editable SVG text, accessible titles and descriptions. Chinese diagrams translate all explanatory text, retaining the project name where appropriate. The [Mermaid lifecycle source](../assets/diagrams/workflow.mmd) remains available as a textual branch reference.

Regenerate with `python scripts/build_visuals.py`. English and Chinese labels are paired in the generator; `scripts/visuals_zh.json` is a generated label index for translation review, not an independently editable input. No image-generation API, external font, plotting package or downloaded artwork is required. Original assets are covered by the repository MIT license.

## Slogan and narrative / 标语与叙事

**Turn intent into evidence. / 让目标落到成果与证据。** remains the concise visual slogan. The full purpose is to help Codex do the best possible job of what the user means to accomplish. The drawings connect that purpose to mechanisms, while nearby text states actual evaluation status.

Earlier alternatives were “One goal. The right capabilities.” and “Coordinate the work. Verify the outcome.” The selected line covers both intent and evidence without implying an optimality guarantee.

## Source and adaptation / 参考与原创性

The user requested Nature Skills and an academic look. The installed Nature Figure guidance informed the conceptual brief, white-background discipline, schematic-led hierarchy, direct labels and semantic color system. Its scientific-plot and journal-submission checks are not claimed here: these are repository-native qualitative SVGs, not data panels or manuscript submission artifacts.

Acknowledgements: [Nature Skills](https://github.com/Yuan1z0825/nature-skills) informed task-oriented documentation and academic diagram design; **Ian Xiaohei Illustrations** inspired the hand-drawn explanatory style and visual storytelling. Their art, characters, logos and copy are not reused. Shapes, labels and layouts here are authored specifically for conduct-best-skills.

## Review and narrow screens / 检查与窄屏阅读

Render both languages and inspect all figures, not only source syntax. Check text bounds, panel alignment, directional meaning and label clearance. README previews should cover desktop and 390px widths. Dense figure labels may require opening the SVG at full size; adjacent prose and tables retain the essential information in selectable text. A valid SVG or successful tool exit does not establish factual correctness.

## Hand-drawn narrative illustration / 手绘叙事配图

[Intent to evidence](../assets/illustrations/intent-to-evidence.png) introduces the project purpose using an original compass assistant. Black ink outlines, white paper and restrained teal/orange accents complement the academic SVGs. The illustration is intentionally text-free; English and Chinese explanations live in the corresponding README captions. This keeps both languages readable and avoids generated lettering errors.

用户参考图仅用于理解手绘科普的总体画风。新图没有使用参考图的黑色角色、传送带、抽屉、鱼或构图，改用原创罗盘助手、目标便签、路线笔记与检查清单。插画负责叙事，SVG 负责准确表达机制；不将插画中的勾选符号视为已经通过的验收证据。

Generation record: 2026-10-15; built-in imagegen, new-image generation, no reference-image pixels supplied. The provider's exact underlying model/version was not exposed. Output: 1536 × 1024 PNG. No third-party artwork was embedded. The output was visually inspected for conceptual meaning, character originality and text absence, and copied into the repository without raster editing.

Prompt specification: Original hand-drawn editorial illustration for conduct-best-skills, white background, thin imperfect black ink, restrained teal and muted orange. A white circular compass character examines a human-provided star-shaped goal note, selects routes toward appropriate tools in an open research notebook, then checks a resulting document with a magnifying glass. Three clear phases; sparse curved arrows; no words, logos, numerical data, conveyor belts, filing cabinets, fish, black silhouette creatures or borrowed composition. Depict a concept, not actual execution or quantitative performance.

## Choose the style by the job / 按用途选择画风

| Location | Chosen treatment | Reason |
| --- | --- | --- |
| Brand banner / 品牌横幅 | Minimal academic vector / 简洁学术矢量 | Keep the project name readable and the header compact. / 保持名称醒目，避免首页重复插画。 |
| Purpose / 项目主旨 | Original compass narrative / 原创罗盘叙事 | Introduce intent, capability choice and evidence. / 用场景解释整体价值。 |
| Before and after / 前后对比 | [Hand-drawn shared route](../assets/illustrations/shared-route.png) | Show coordination through a concrete map metaphor. / 用地图隐喻解释协调机制。 |
| Interaction / 三种交互 | [Hand-drawn scenarios](../assets/illustrations/interaction-scenes.png) | Human decisions and conditional delegation benefit from characters. / 用角色动作表达用户决策和有条件委派。 |
| Lifecycle / 七阶段 | Academic SVG / 学术流程图 | Branches, rollback and verification must stay explicit. / 保留准确的分支与验证关系。 |
| Dependencies / 任务依赖 | Academic SVG / 学术依赖图 | Parallelism and ordering must be unambiguous. / 并行与先后关系不能依赖隐喻猜测。 |
| Context and experience / 上下文与经验 | Academic SVG / 学术信息流图 | Access, authorization and persistence are distinct boundaries. / 明确访问、授权与保存边界。 |

The README replaces the former comparison and interaction SVG embeds with the two illustrations; the editable SVGs remain linked in the inventory for precise reference. This does not increase the number of inline figures. Both languages use text-free art with translated captions. The drawings are conceptual, not evidence that a task or evaluation passed.

Generation: built-in imagegen, 2026-10-15, using only this project's original intent-to-evidence illustration as character/style reference. Exact prompts and reference role are recorded in `assets/illustrations/generation-prompts.json`; underlying provider model/version was not exposed. Both selected images were visually reviewed and copied without raster edits. No third-party reference artwork was supplied to these generation calls.

## Workbench constellation / 深色工作台与调用星图

The interactive workbench uses midnight navy (`#080d19`), slate panels, readable pale text and restrained cyan/violet signals. Sparse stars and soft background gradients suggest a galaxy. Thin glowing curves connect actual work, task, capability and result nodes; travelling light expresses direction without asserting live execution. Pause and reduced-motion support keep the information accessible. The earlier white-background SVGs remain explanatory documentation figures.

The layout was informed by [Plane](https://github.com/makeplane/plane)'s project organization and [shadcn Dashboard](https://ui.shadcn.com/examples/dashboard)'s information hierarchy. Layout, CSS, SVG wires and motion are independently implemented without copied assets or code.

Public screenshots [workflow](../assets/workbench/workflow.png) and [preferences](../assets/workbench/preferences.png) render the actual frontend with `scripts/preview_workbench.py`. All projects, chats, evidence references and feedback are synthetic. The preview does not import a real index. PNGs are captured from the browser, not AI-generated mockups; no personal screenshot is used. Run the preview to inspect motion, which a still image cannot show.

## Harness 工作现场

沿用深色星系背景、克制的青蓝与紫色高光。默认视图以当前工作和下一步开场，按真实依赖排列工作节点，用发光连线连接。旁栏展示方案与能力、成果与验收、调整请求，下方汇总待处理信号和历程。窄屏切为单栏，工作图内部可横向滚动；任务背景与底层验收收纳为可展开详情。空项目没有预置节点。

`assets/workbench/harness.png` 展示纯合成工作图。连线表示依赖，短暂光点回放近期明确记录的调用，不是实时遥测；减少动态效果设置下保持静态。手动状态、请求入队、调用结果与实际验收分别编码，点击节点不推进工作。
