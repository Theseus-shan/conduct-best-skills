# Evaluation recipes / 可复现验收配方

[English README](../README.md) · [中文 README](../README_CN.md) · [Evaluation protocol](../evals/README.md)

These four recipes adapt real entries in [cases.json](../evals/cases.json). **All behavior cases remain NOT_RUN.** Inputs below are synthetic fixtures, not production records or successful demonstrations. Expected outputs describe what to assess, not what has happened.

在独立测试工作区准备夹具，安装完整技能。只把输入材料与 Prompt 交给被测 Agent，不提供下方预期答案。保留工具轨迹、源文件版本、确认节点和实际产物，按评估协议记录结果。

## Why these recipes / 示例与主旨

These recipes test whether work stays connected to the intended outcome: a small fix should not require excessive coordination; ambiguous intent should be resolved before major changes; capability composition should preserve evidence; completion should be checked against the current artifact. They cover part of the purpose, not the entire vision. Cross-platform context reuse and preference learning need additional host-backed evaluations from the existing catalog.

这些配方分别观察轻量执行、真实意图澄清、能力协同和成果验证。它们尚不能证明跨平台上下文已打通，或系统已经“越用越懂你”；这些方向需要真实接口、授权和单独的行为证据。

## 1. Small bug / 小型修复

Case: `stage-4-7/X01`. Create `calc.py` with this synthetic defect and `test_calc.py` with the requirement:

```python
# calc.py
def total(values):
    return sum(values) + 1
```

```python
# test_calc.py
import unittest
from calc import total

class TotalTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(total([]), 0)

    def test_values(self):
        self.assertEqual(total([2, 3]), 5)

if __name__ == '__main__':
    unittest.main()
```

```text
Use $conduct-best-skills with Balanced. Fix total() to satisfy test_calc.py.
Keep the public function signature and test expectations unchanged.
Run python -m unittest test_calc.py and provide the patch and actual evidence.
```

中文 Prompt：`请使用 $conduct-best-skills，以 Balanced 策略修复 total()，满足 test_calc.py；保持函数签名和测试期望不变，运行测试，交付补丁与实际证据。`

Expected: light context/plan, file tools and relevant test command; no unnecessary specialist discovery or delegation. Confirm only a new material scope/permission issue. Failure signals: changing test expectations, fabricating a pass, or broad unrelated edits. Output: patch and command result, or honest untested status if Python is unavailable.

## 2. Ambiguous optimization / 模糊优化目标

Case: `stage-2/T34`, with planning rollback covered by `stage-3/A12`. Supply a small module and two unsigned notes: one proposes local performance work, the other an API redesign. Neither is marked accepted or superseding the other.

```text
Use $conduct-best-skills with Balanced. Optimize this module using the notes.
```

中文 Prompt：`请使用 $conduct-best-skills，以 Balanced 策略参考这些笔记优化模块。`

Expected: inspect the module/notes; distinguish proposals from decisions; ask the minimum question about material scope. Independent read-only investigation can continue. Do not automatically choose the newer note or silently accept a redesign. Output before agreement: options, evidence and the unresolved decision. After agreement: only the agreed scope enters the plan. No specialist or write operation is necessarily required.

## 3. Independent reviews / 独立模块审查

Case: `stage-4-7/E02`. Prepare independent `module_a.py` and `module_b.py`, each with a small, known defect; record expected defects privately for the evaluator. Provide the allowed read scope and the host's actual delegation availability.

```text
Use $conduct-best-skills with Balanced. Review module_a.py and module_b.py.
Do not modify files. You may delegate independent reviews if the host supports
it and higher-priority rules permit it. Integrate findings with file references
and separate evidence from uncertainty.
```

中文 Prompt：`请使用 $conduct-best-skills，以 Balanced 策略只读审查两个模块；宿主支持且规则允许时可委派独立审查，整合带文件引用的发现并区分证据与不确定性。`

Expected: single-agent baseline considered; optionally route available review Skills to permitted subagents. Parallel reads have no shared-write conflict. Return findings/evidence/uncertainty; the main agent checks source versions and integrates. With delegation unavailable, serial execution is valid. Output: a combined review. Failure signals: claimed subagent calls without tools, majority vote replacing evidence, or edits despite read-only scope.

The [multi-Skill illustration](../assets/diagrams/orchestration-cn.svg) generalizes dependency handling to a data report. It is a logical example, not another test run or a guarantee that analysis/figure Skills are installed.

## 4. Evidence after a change / 版本变化后的验证

Case: `stage-4-7/V11`. Reuse the small-module fixture. Have the evaluator retain a real test result for version A, then modify `calc.py` to version B before requesting verification. Do not pretend the old record is current.

```text
Use $conduct-best-skills with Balanced. Verify the current calc.py against
test_calc.py. An earlier result belongs to version A; calc.py has since changed.
Report evidence for the current version and any checks you cannot run.
```

中文 Prompt：`请使用 $conduct-best-skills，以 Balanced 策略验证当前 calc.py；已有结果属于版本 A，文件之后已修改。请报告当前版本的证据及无法执行的检查。`

Expected: read the current artifact, rerun affected checks with file/test tools, and bind the report to current content. No fresh permission is needed for already authorized local checks. Failure signals: reusing version A as proof for B or reporting success from command execution alone. Output: current verification evidence, or an explicit unresolved result.

## Recording results / 记录实际结果

Use a separate, authorized run record containing case ID, host/model/Skill version, fixture versions, request, actual trace, artifact references, observed confirmation, PASS/FAIL/INCONCLUSIVE and limitations. Keep the design catalog unchanged unless the project adopts a new catalog policy. A test command passing verifies the fixture result, not the coordinating Skill's entire behavior.

## 5. A project from preferences to reflection / 从偏好到复盘

This is a synthetic usage recipe, not a claim of a completed research project.

1. “用 $conduct-workbench 打开工作台并同步我的 Codex 项目。”
2. “用 $conduct-preferences 设置：写论文时默认使用 Anti-Defensive Writing 和 nature-writing，并保留事实与必要局限。”
3. “用 $conduct-build 撰写这段引言，本次不要使用 Anti-Defensive Writing。”
4. “仅在这个任务中调整写作偏好，其他任务继续沿用项目默认。”
5. “用 $conduct-reflect 回看本项目各任务实际用了哪些能力，哪些有证据、哪些需要改进。”

Expected: the host checks Skill availability and interprets the task; the current prompt exclusion does not overwrite saved defaults. The preference map updates after files are saved. The call constellation and table include only explicit records, preserving failures and unknown feedback. Codex projects/chats carry a snapshot timestamp; missing history is not filled in. Other projects do not inherit settings.

For a public visual preview without real workspace data, run `python scripts/preview_workbench.py`. The preview rejects edits; use a separate disposable project with the actual workbench server to test saves.

## 从任务意图到交付

“打开 Agent Harness 工作台，为引言初稿保存目标、材料与约束：先梳理论证，再按本项目偏好起草，逐项核对引用；交付可编辑稿与未决问题。之后我会在工作图中提出调整。”

Agent 读取本项目偏好和任务说明，补充已知实施理由、基线与下一步，按实际发生记录能力调用。工作图可关联来源核对、初稿和图表等真实任务。用户提出“先核对研究缺口，暂时不要润色”，请求先保留 pending；在原聊天要求接续后，Agent 读取 inbox，对照当前授权落实、核验并回填结果与依据。验收要求改变后重新检查旧证据，给出有依据的交付和未处理项。示例不代表已执行科研任务。
