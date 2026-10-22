# 多源 Skill Discovery 使用指南

Discovery 帮助宿主找到相关 Skill、解释适用条件并规划组合。它读取本地元数据或公开来源，输出候选和能力缺口；找到候选不会安装、加载或执行它。简单任务已能用现有工具完成时，无需先搜索 Skill。

## 从真实缺口开始

先列任务需要的能力和宿主已经具备的能力，再查询缺少的部分。关键词使用可公开的能力名，例如 `csv`、`statistical analysis`、`figure`；不要传入用户原始提示、研究材料、代码、路径或凭据。关键词过滤只是启发式检查，不是数据防泄漏系统，宿主仍须判断这些词能否公开。

以下命令在仓库根目录运行。已安装的 Skill 应把脚本路径替换为实际 `SKILL_DIR/scripts/discovery.py`；`--workspace` 指向当前任务目录。Python 3.10+，仅使用标准库，不需要安装额外包。

```bash
python skills/conduct-best-skills/scripts/discovery.py --workspace . --root skills --keyword research --need research --output local/discovery.json
```

默认只检查本地来源，也不读取环境中的 API 凭据。`--root` 可以重复，指定一个 Skill 目录、Skill 集合目录或具体 `SKILL.md`。省略它时检查当前项目到仓库根目录的 `.agents/skills`、用户 `.agents/skills`、兼容目录 `.codex/skills`，非 Windows 环境还检查 `/etc/codex/skills`。这是有深度和文件预算的扫描，不会保证穷尽全部本机 Skill。默认跳过未明确允许目标位置的符号链接和 junction。

## 六类来源与渐进查询

默认顺序是 `local → openai → anthropic → skills-sh → skillsmp → github`。允许外搜后，找到足够的元数据覆盖就可以停止；报告会标明未执行的来源。要检查所有已启用来源，添加 `--all-sources`，请求和时间预算仍然生效。

| 来源 | 实际读取范围 | 主要限制 |
| --- | --- | --- |
| `local` | 本地 `SKILL.md`、资源路径、可用的 `agents/openai.yaml` | 本地存在不代表宿主已加载或已批准 |
| `openai` | `openai/plugins` 官方仓库中的插件清单和 Skill | 插件是安装单元；关联 App/MCP 是否连接仍需宿主确认 |
| `anthropic` | `anthropics/skills` 官方仓库 | Claude 专用工具需映射到宿主能力 |
| `skills-sh` | 官方 `/api/v1/skills/search`，再核对 GitHub 原文件 | 官方 API 需要 Vercel OIDC；当前适配器不解析 well-known 域名来源 |
| `skillsmp` | 官方关键词搜索，再核对 GitHub 原文件 | 可匿名查询，配额较低；不启用试点语义搜索 |
| `github` | GitHub 公开仓库或代码搜索 | 无 token 时仅仓库搜索；有 token 才使用代码搜索 |

```bash
python skills/conduct-best-skills/scripts/discovery.py --workspace . --root skills --keyword csv --need csv --allow-external --all-sources --output local/discovery-all.json
```

这个命令允许检查六类来源，但没有提供 OIDC 时 `skills-sh` 会如实报告 `CREDENTIAL_REQUIRED`。`--all-sources` 不会自动开通账号或补齐凭据。仅选部分来源可重复 `--source`：

```bash
python skills/conduct-best-skills/scripts/discovery.py --workspace . --keyword csv --allow-external --source local --source skillsmp --source github
```

`--source` 设置白名单，不改变查询顺序。顺序由配置的 `order` 控制。默认不读取 `GITHUB_TOKEN`、`SKILLSMP_API_KEY`、`VERCEL_OIDC_TOKEN`；只有宿主已获准使用对应凭据时才添加 `--allow-credentials`。本模块不会查找凭据文件、登录账号或执行 `npx`。

## 多能力组合与结果解释

重复 `--need` 表达一个任务的多个必要能力。宿主可以用 `--context` 提供可信、精简的能力事实：

```json
{
  "native_capabilities": ["csv"],
  "tools": [],
  "mcp_servers": [],
  "dependencies": [],
  "environment": ["Python 3.10+"],
  "platform": "windows",
  "denied_permissions": []
}
```

```bash
python skills/conduct-best-skills/scripts/discovery.py --workspace . --root skills --keyword figure --need csv --need figure --context local/discovery-context.json --output local/discovery-plan.json
```

上下文是宿主陈述，模块不会因此安装依赖或验证工具真的可调用。`approved_ids` 不能代替当前版本和关联资源的宿主审查，也不会形成自动批准；不要靠填入候选 ID 来解锁执行。

先看以下字段，而不是只看候选数：

- `sources`：哪些来源执行了、受限了、失败了或因已有覆盖而跳过。
- `composition.native`：宿主声明已经具备的必要能力。
- `composition.selected`：按元数据提出的候选组合；不代表已采用。
- `composition.missing`：仍没有候选覆盖的能力；`not_ready` 还包含已找到候选但未完成宿主审查的能力。
- `assessment.excluded`、`missing_requirements`：排除原因、缺工具/MCP/环境/依赖或仍需人工核对的项目。
- `conflicts`、`overlap`：组合中发现的固定依赖版本冲突、同一 Skill 不同版本冲突和能力重复。

组合采用贪心覆盖，不保证全局最优；依赖冲突只检查声明中的简单 `包名==版本`，不代替包管理器求解。能力匹配基于名称、描述、标签和声明词项，不是语义质量证明。即使报告的命令退出码为 0，也只说明发现流程产出了报告；需检查各来源状态和缺口，不能据此宣称任务完成。

排序采用可解释的字典序：先看硬性排除，再看覆盖数、缺少的条件、关键词匹配、是否记录版本、配置的来源顺序，最后用稳定 ID 消除不确定顺序。`ranking.key/factors` 保留实际排序依据；其中运行可用性维度在本版统一为待核查，不把 `approved_ids` 当成可执行依据。安装量和 star 仅作为来源观察，不自动提升信任，也不证明效果。

## 缓存、离线与刷新

外部响应和本地解析元数据缓存在工作区 `.conduct-discovery`。搜索默认有效期 1 小时，元数据通常 24 小时；仓库与分支解析等使用更短有效期。本地每次先重读元数据、核对资源清单，再根据内容和解析器版本使用缓存，不沿用过期文件。外部缓存按来源、请求、响应类型和认证作用域隔离。缓存不是授权记录，应加入 `.gitignore`，不要把报告中的本地路径和元数据直接当作公开发布物。

```bash
python skills/conduct-best-skills/scripts/discovery.py --workspace . --keyword csv --allow-external --source github --offline
python skills/conduct-best-skills/scripts/discovery.py --workspace . --keyword csv --allow-external --source github --refresh github
```

离线模式仍须启用需要查询缓存的外部来源。它不发送请求；没有缓存时返回明确状态。允许时可回退到过期不超过 7 天的缓存，报告标记 `STALE_FALLBACK`，候选不能据此直接采用。认证、权限或限流错误不会被缓存伪装成成功。`--refresh` 可重复，跳过指定来源的正常缓存命中；网络失败仍可能产生有标记的旧缓存回退。`--no-cache` 完全关闭缓存读写。

## 保存来源策略

配置由 `--config local/discovery-config.json` 读取，命令行覆盖对应项。下面是可调整的默认策略摘要；不认识的字段会报错。

```json
{
  "allow_external": false,
  "allow_credentials": false,
  "offline": false,
  "order": ["local", "openai", "anthropic", "skills-sh", "skillsmp", "github"],
  "allowed_sources": ["local", "openai", "anthropic", "skills-sh", "skillsmp", "github"],
  "max_level": 3,
  "max_candidates": 8,
  "max_files": 300,
  "max_depth": 4,
  "pages": 1,
  "max_requests": 30,
  "seconds": 60,
  "timeout": 10,
  "retries": 1,
  "cache_dir": ".conduct-discovery",
  "refresh": [],
  "sources": {},
  "stop_when_covered": true
}
```

`max_level` 对应本地 0、官方来源 1、聚合目录 2、广域 GitHub 搜索 3。`max_candidates` 是每来源候选上限，`pages` 是支持分页来源的页数上限。`sources` 接受各来源的 `enabled`，本地的 `roots/allowed_symlink_roots`，以及官方仓库的 `revision`。固定复现时可把 `revision` 设为审阅过的完整 commit SHA。`cache_dir: null` 关闭缓存。

请求预算包含重试。401/403/429 不自动重试；带 `Retry-After` 的错误记录稍后重试提示；SkillsMP HTTP 错误避免自动重试不确定计费请求。一个来源失败后，预算允许时继续检查其他来源。

## 从候选到真正采用

宿主查看原始 `SKILL.md`、关联脚本和资源，确认许可、工具映射、MCP/App连接、运行条件、权限和当前版本后，再在用户已经授权的范围内加载 Skill，或交给官方安装器完成需要的安装。若现有授权不足，只对具体缺少的权限请求确认。

远程 GitHub 来源先解析 commit SHA，再读取该版本文件；本地 digest 只覆盖检查过的元数据，并非整个脚本包。固定版本可以稳定来源，不能证明无害、兼容或有效。静态提示可能误报或漏报；应结合当前任务的实际检查。安装之后仍需重新检查加载状态和能力，不能把本次推荐直接转换成可执行授权。

接口与扩展细节见仓库中的 `docs/discovery-adapters.md`。官方文档核实、模拟接口测试和真实在线结果是三类不同证据；看到前两类不能声称全部外部服务已经在线验收。
