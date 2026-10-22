# 每个工作空间的工作方式

本功能保存用户主动设置的显式偏好，不是使用统计或自动学习。通过本 Skill 开始一个有明确工作空间的任务时，创建缺失的空白项目偏好并给用户编辑入口；已有文件只读取、不重置。只读任务、禁止持久化或没有写权限时在对话内处理，不为创建配置阻塞核心任务。

## 文件与范围

- 项目默认：用户工作空间内 `.conduct/preferences.json`。
- 任务覆盖：同一工作空间内 `.conduct/tasks/<task-id>/preferences.json`。使用用户给定或已有稳定标识；普通单任务无需另建覆盖。多个任务标识无法区分时才澄清。
- 当前情况：`.conduct/preferences-context.json` 仅供动态视图展示最近同步的任务类型与临时排除项；它不是跨轮授权或偏好来源。每轮按当前请求重新生成，不继承上轮临时禁用。

只读取精确工作空间与指定任务的文件；不向上搜索父目录，不读取其他项目、全局默认或其他任务覆盖。用户通过自然语言编辑偏好，可以说“用 $conduct-preferences 修改当前项目/任务的工作方式”。修改后立即重新读取；删除项目规则不影响其他项目。

## 执行优先级

在更高优先级指令与实际权限内：当前 prompt 的明确选择/拒绝 > 当前任务覆盖 > 当前项目默认 > 一般自动选择。同 `id` 的任务规则替换项目规则；`enabled: false` 可在该任务中停用项目规则。不同 ID 的规则合并；实质冲突无法判定时只澄清冲突部分。临时“这次不用 X”只进入本次解析，不写回默认；“以后本项目不用 X”才修改项目规则。

`when` 是语义任务类型数组，例如 `paper-writing`、`coding`、`literature-review` 或 `*`。Agent 根据实际工作判断类型，允许多个类型；不能因为 prompt 提到“论文”就把安装工具的任务识别为论文写作。实际进入论文起草、修改或润色时再匹配写作规则。

命中规则时按 `skills` 顺序核查当前可用 Skill 的名称、描述或用户指定路径，读取其真实入口并应用，再执行该工作。不是只推荐或加分。显示名与注册名不一致时用元数据确认对应；存在歧义不能随便替代。缺失时明确报告配置目标尚不可用，继续不依赖它的工作；不自动安装，也不声称已经调用。用户要求该能力必不可少时，仅阻塞依赖部分。一般软偏好统计不得覆盖这里的显式默认。

## 示例：写作默认调用

以下只是示例，初始化不会启用它；用户主动加入后才生效：

```json
{
  "schema_version": 1,
  "workflow": {"language": "简体中文", "strategy": "Balanced"},
  "rules": [{
    "id": "paper-style",
    "when": ["paper-writing"],
    "skills": ["Anti-Defensive Writing"],
    "instruction": "起草或修改论文时消除防御性写作，保留必要的不确定性、局限、事实和引用。",
    "enabled": true
  }]
}
```

任务文件可用同一 ID 与 `enabled: false` 停用这条规则；当前 prompt 说不用时则不改文件。自定义语言、输出格式、策略等放在 `workflow` 的字符串字段中；Agent 按其实际含义执行，局部任务同名字段覆盖项目。命令范围不被偏好扩大。

## 本地工具与动态图

将 `<CORE>` 替换为实际共享核心目录，`<PROJECT>` 替换为用户工作空间。路径含空格时正常引用；由 Agent 执行，用户无需写命令或 JSON。

```text
python <CORE>/scripts/conduct.py --workspace <PROJECT> preferences init
python <CORE>/scripts/conduct.py --workspace <PROJECT> preferences init --task paper-a
python <CORE>/scripts/conduct.py --workspace <PROJECT> preferences show --task paper-a --type paper-writing
python <CORE>/scripts/conduct.py --workspace <PROJECT> preferences context --task paper-a --type paper-writing --exclude "Anti-Defensive Writing"
python <CORE>/scripts/conduct.py --workspace <PROJECT> preferences serve
```

`init` 只创建缺失配置；`show` 不写文件且不安装/加载 Skill。`context` 在获准保存状态时更新最近情况，Agent 应在开始工作、进入新的任务类型和偏好变更后调用，省略不再适用的临时排除。类型和当前 prompt 的语义由 Agent 判断，不由脚本猜测。文件格式错误时明确提示修正，不能悄悄退回旧配置或展示生效成功。

`serve` 仅在本机提供当前工作空间的动态页面，返回实际 URL。需要查看图时启动并通过宿主浏览器打开；同一任务已有活跃服务则复用。Windows 后台启动使用隐藏窗口。每次读取当前文件，约两秒刷新：工作空间 → 项目默认 → 任务覆盖 → 本次 prompt → 当前规则。页面用自然语言卡片编辑项目/任务偏好，支持示例、启停与范围选择。常见“做什么时默认使用哪些能力，并遵循什么要求”的句式可直接保存；不可靠的复杂表达交给 Codex 理解，不能静默猜测。保存前校验且拒绝覆盖已被别人修改的版本。页面切换任务用于查看，不会替换其他任务的默认。

服务关闭后页面显示连接中断，保留的旧图明确标为过期；无持久进程或无浏览器能力时交付解析结果与使用方法，不声称仍在实时同步。动态图跟踪文件和 Agent 最近同步的情况，不自动观察其他聊天，也不是实际调用日志。仅保存当前项目配置与最小上下文，不保存完整 prompt、凭据或跨项目用户画像。
