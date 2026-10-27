@AGENTS.md

## Claude Code specifics

- Run `inkos-agent wait ... --timeout 90` as a normal Bash call (under the
  2-minute default). Do not use `run_in_background` for `wait`; the InkOS job
  itself is already detached by `inkos-agent job start`.
- Subagents: `.claude/agents/inkos-writer.md` and `.claude/agents/inkos-reviewer.md`.
  Launch one per pending request with the Agent/Task tool, passing only
  `request id: r-...`. Launch independent requests in parallel.
- Write answer files under `runtime/answers/` (ignored by git), never inside the
  InkOS book folders.
- On Windows use `inkos-agent.cmd` (same arguments) if `inkos-agent` is not on PATH.
