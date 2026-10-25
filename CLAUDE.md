## Korean edition (fork rules)

This fork turns InkOS 2.0 into a Korean-novel edition. Before any work, read
`korean-port/PLAN.md` and `korean-port/OPERATING_RULES.md`, and continue from
PLAN's "진행 기록". You are the developer role: a Claude Code cloud session uses
its one assigned branch and marks the stage in each commit title (operating rules
v1.1), reports each stage in the `[보고]` format from OPERATING_RULES.md, and
do not start the next stage until the supervisor's `[승인]`. Update that log
(date, branch/commit, test results) at the end of every session.

- Never change zh/en behaviour; the upstream test suite must keep passing.
  Add explicit `ko` branches instead of `language !== "zh"` shortcuts.
- Put Korean code in new files (`korean-*.ts`, `packages/core/skills-ko/`)
  where possible; keep edits to upstream files small.
- No API keys, ever. Real generation tests run only through
  `tools/inkos-agent-bridge` (see its AGENTS.md); you answer the model calls.
- Claims of "done" need evidence: test output, saved files, bridge request list.
- Ask the user before deciding anything listed as 미정 in PLAN.md.
- Keep AGPL-3.0-only and the upstream copyright notices.
- Author choices are interactive by default: ask with `tools/novel-brief.py`
  (numbered questions), `pack --resume` before waiting, pass answers with
  `write next --context-file`; "N개 화 써줘" / "다섯 화 써줘" is batch mode (no questions). Rules:
  `korean-port/RUNTIME.md` "작가 선택".
- 실제 작품: 대화형은 질문을 기다리기 전에 재개용 압축본 전체를, 일괄은 회차마다 원고 `.md`를 Drive 'Inkos ko'에 올리고, 일괄이 끝나거나 멈출 때(경고·실패) 압축본을 올린다. 시험 작품(`test-`)은 올리지 않는다.
  Test works (IDs `test-…`) are never sent to the user, uploaded or committed.
