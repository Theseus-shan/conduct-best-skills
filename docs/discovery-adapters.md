# Discovery adapter 开发与证据边界

当前实现使用 Python 标准库，按配置组合六类来源。用户操作见 [Discovery 使用指南](../skills/conduct-best-skills/references/discovery.md)。本模块只负责发现、规范化、静态检查和组合建议；安装、宿主加载和执行属于后续独立动作。

## 模块分工

| 文件 | 责任 |
| --- | --- |
| [discovery.py](../skills/conduct-best-skills/scripts/discovery.py) | CLI、配置、上下文、来源调度、去重、排序、组合、报告 |
| [discovery_core.py](../skills/conduct-best-skills/scripts/discovery_core.py) | YAML 子集解析、候选结构验证、来源身份、静态风险观察 |
| [discovery_sources.py](../skills/conduct-best-skills/scripts/discovery_sources.py) | 本地、OpenAI、Anthropic、两个目录、GitHub 搜索适配器及 GitHub 文件读取 |
| [discovery_io.py](../skills/conduct-best-skills/scripts/discovery_io.py) | HTTPS GET、请求/时间/重试预算、缓存和凭据隔离 |

## 适配器接口

适配器继承 `Adapter`，设置 `provider/level/external`，并实现 `discover(query, context, filters)`。返回值为规范化候选列表；失败使用 `DiscoveryError(code, safe_message)`，单条记录失败通过 `caught()`/`note()`记录安全诊断后继续。预算耗尽时保留已取得候选并记录 BUDGET；没有候选才上抛，不能换来源重新获得预算。

`check_availability()` 返回状态和说明。基类的 `AVAILABLE` 仅表明配置可检查，不表示已连通或已认证。`get_capabilities()` 声明该适配器能读取什么；`get_metadata(candidate)` 与 `resolve_source(candidate)` 分别提供已规范化记录和来源定位信息，不执行隐式网络请求。

接入一个新来源需要同时登记 provider、配置白名单及 `build_adapters()`映射，并给出可信的官方接口依据、请求预算和失败行为。不要实现从互联网下载 Python 插件后动态导入的扩展机制。网络请求统一走共享 `HttpClient`，不得在适配器内执行 `npx`、`git clone` 或外部 Skill 脚本。

## 统一候选结构

通过 `parse_skill(text, source, resources=None, associated=None)` 从实际文件生成候选，再由 `validate_candidate()`检查结构。未知扩展字段可以保留；关键枚举、字段类型、来源身份和有限 JSON 数值须通过校验。

| 字段 | 含义与边界 |
| --- | --- |
| `id`、`name`、`description` | 来源身份摘要和 Skill 自述；不是质量评分 |
| `source` | `provider/repository/path/revision/canonical_url`，可附 `plugin` |
| `capabilities/tags` | 原文声明的能力和标签；没有声明就保留空值 |
| `compatibility` | 规范、agent 声明、条件与静态观察；`unknown` 不等于兼容 |
| `requirements` | `tools/mcp_servers/dependencies/environment`，没有自动安装或环境验证 |
| `security` | 信任声明、审查状态、风险提示和所需权限；只有待审或阻断，不自动签发批准 |
| `provenance` | 发现时间、核查时间和读取方式；未实际核查时 `verified_at` 为 null |
| `license` | 原文声明或未知；不凭目录收录推断许可继承 |
| `raw/raw_associated` | 原 frontmatter 和已解析关联配置，作为不可信数据保存 |
| `inferred` | 推断字段、值和证据位置，明确区别于原文声明 |
| `resources/observations` | 资源路径与检查范围、缺失、截断、陈旧等观察 |

`resources=None` 表示没有完整检查资源清单；空数组表示已检查且未发现资源。两者不能混用，否则会把“不知道文件是否存在”误报成“文件缺失”。当前关联内容主要读取 `agents/openai.yaml`；资源路径清单不证明所有脚本内容已经审阅。

GitHub候选身份由仓库、大小写敏感的文件路径和已解析 revision 组成，同一版本可合并多个发现记录；同名不同仓库或不同版本不会合并成一个 Skill。元数据冲突会被标记，不通过第二个目录的出现次数提升信任。本地身份包含解析后的位置和元数据 digest；它不覆盖整个目录内容，因此不能用 `approved_ids` 自动批准脚本包。

## 格式解析与静态检查

解析器有意实现 YAML 子集：映射、列表、常见标量、引号字符串以及 `|`/`>`块字符串。支持范围内保留原始未知字段。frontmatter 需以 `---` 开始和结束，`name/description` 必须符合长度和类型约束；元数据大小、行数、嵌套深度均有限制。

不支持自定义标签、锚点、别名、流式映射、复杂键和 tab 缩进。重复键、错误缩进、未闭合字符串等明确报错，不猜测含义。这不是完整 YAML 解析器；遇到有效但不在子集内的第三方文件，应报告解析受限，而不是改写上游文件或宣称其有害。

静态规则记录提示注入、凭据外传、远程命令管道、破坏性命令、工具权限和平台限制等线索；部分高风险匹配会阻断候选。普通命令或网络示例可能只是合法文档，规则也可能漏掉真正问题。它们是审查辅助，不是安全认证。外部正文永远不能修改宿主指令、配置、来源白名单或批准记录。

## 各来源的实际映射

### 本地

读取显式目录或有限的标准 Skill 容器，遵守 `max_files/max_depth`，跳过依赖目录与未许可的符号链接目标。读取 `SKILL.md`、资源路径和 `agents/openai.yaml`，记录 `host_enabled: unknown`。文件在磁盘上不意味着宿主已启用它。

### OpenAI 与 Anthropic

OpenAI适配器读取 [openai/plugins](https://github.com/openai/plugins) 的插件清单和所属直接 Skill 目录，支持便携 `plugin.json` 与兼容 `.codex-plugin/plugin.json`；关联MCP/App信息仅作为依赖元数据。插件仍是安装单元，发现其中一个Skill不等于其App已经连接。

Anthropic适配器读取 [anthropics/skills](https://github.com/anthropics/skills) 的 `skills/` 文件。遇到 Claude 专用工具名与环境指令，保留条件并要求宿主映射，不能仅因为存在 `SKILL.md` 就认定 Codex 兼容。

这两个来源先读取公开仓库信息、解析 commit，再读取该 SHA 的树和文件。查询使用有上限的路径优先排序，不是对全仓库正文的完整语义检索。GitHub树截断或文件预算不足时保留不完整诊断。

### skills.sh

依据 [官方 API](https://skills.sh/docs/api)，调用 `/api/v1/skills/search`；参数是 `q/limit`，响应候选在 `data[]`。当前需要显式允许使用 `VERCEL_OIDC_TOKEN`；没有凭据时报告受限，不猜内部接口，也不自动执行[官方 CLI](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)。

目录中的 `id/name/slug/source/installUrl/installs` 是索引观察。适配器只接受能解析为 GitHub 来源的条目，再读取真正的 Skill 文件；well-known域名类型目前标为不支持。返回的安装量不是质量证据。

### SkillsMP

依据 [API文档](https://skillsmp.com/docs/api)、[开发者入口](https://skillsmp.com/developers)与[OpenAPI](https://skillsmp.com/openapi.json)，调用 `/api/v1/skills/search` 的关键词模式，读取 `success:true` 和 `data.skills`，分页按 `hasNext`及本地页数上限停止。`githubUrl`用于定位；`stars`和目录ID仅记录观察。服务的 `total`可能是不精确下界，不用于宣称穷尽全部结果。

可以匿名搜索；宿主明确允许时才读取 `SKILLSMP_API_KEY`。当前官方说明语义混合搜索是禁用试点，本模块不提供 `ai-search`。HTTP错误不自动重试，避免不确定计费状态重复请求。官方文档配额可能更新，应服从响应限流信息，不把旧搜索摘要写死为服务保证。[服务条款](https://skillsmp.com/terms)限制系统性大量下载，因此采用有界查询而非整站采集。

### GitHub 广域搜索

依据 [REST搜索文档](https://docs.github.com/en/rest/search/search)，有明确允许的 `GITHUB_TOKEN`时执行公开代码搜索并限定 `filename:SKILL.md`；否则退化为公开仓库搜索并记录 `ANONYMOUS_FALLBACK`。`incomplete_results`会形成诊断。仓库搜索匹配只是线索，必须继续确认实际Skill路径和固定版本。

`GitHubReader`验证仓库为公开，解析默认分支或指定ref到完整commit SHA，再读取树和raw文本。版本固定保证读取指向同一提交；它不等于签名验证、许可证核验或运行通过。URL中含歧义的分支/路径、非GitHub源或不支持的目录结构应明确降级，不搜索一个同名无关文件替代。

raw主机网络失败时，使用[官方 Contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content)读取同一公开仓库、路径与 commit，校验 file/base64 响应并限制解码大小，记录 `CONTENTS_FALLBACK`。不会改为读取默认分支或其他来源。

## 网络和缓存约束

只允许代码白名单内的公开HTTPS域名和GET，拒绝URL内凭据、非标准端口和重定向。共享预算限制请求总数、超时和重试；普通响应上限为2,000,000字节，GitHub目录树单独允许最多8,000,000字节。401/403/429不重试，带`Retry-After`时记录稍后重试提示；其他暂时性错误只在剩余预算内重试。来源出错与无结果必须区别报告。

缓存按搜索/元数据分区，文件名使用摘要，认证头身份参与缓存key但头值不落盘；服务反射凭据时丢弃响应。错误日志不保存远程错误正文。缓存JSON限制大小、版本和时间，目录必须在工作区内且不能通过重定向路径逃逸。离线或网络故障可使用有限期旧缓存，但须标记其证据已过期，不能因此批准执行。用户上下文只接受能力事实；公开关键词过滤是启发式检查，不能替代宿主的隐私判断。

## 扩展与验证

先按官方接口写合成fixture和 fake opener 测试，明确标注模拟数据；再独立执行获准的有界在线检查，记录时间、来源状态、实际请求数、响应结构与失败原因。接口文档存在、mock通过、真实请求成功是不同层次证据。认证未配置、网络被限制或API未实际调用时必须保留未验证状态，不补造成功记录。

新增适配器至少检查：合法候选与错误envelope、分页结束与上限、单项损坏隔离、预算停止、固定SHA、缺资源与未知资源的区别、跨目录重复、非GitHub来源、无凭据降级，以及外部内容不能改变批准状态。网络层还需检查超量响应、错误重试、密钥反射与缓存隔离、过期/损坏缓存和路径重定向。

可独立运行 [IO测试](../tests/test_discovery_io.py)：

```bash
python -m unittest discover -s tests -p test_discovery_io.py -v
```

Windows环境若无创建符号链接权限，相应测试应报告跳过；跳过不能记为已通过。完整测试发现使用 `python -m unittest discover -s tests -v`，避免导入其他模块的 `TestCase` 类导致重复计数。
