## Korean edition (fork rules)

This fork turns InkOS 2.0 into a Korean-novel edition. Before any work, read
`korean-port/PLAN.md` and continue from its "진행 기록". Update that log
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
