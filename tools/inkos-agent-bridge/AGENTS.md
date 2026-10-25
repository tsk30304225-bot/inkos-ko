# InkOS through the agent session (no API)

This project runs InkOS without any model API. InkOS sends its model calls to a
local OpenAI-compatible bridge on `127.0.0.1:4568`; **you (the agent in this
session) are the model**. Each call becomes a request file; you read it, write
the answer, and `inkos-agent reply` returns it to InkOS.

Never add, request, read or print API keys. Never point InkOS at a remote model
endpoint. If something seems to need an API, stop and tell the user.

## 1. Start

```bash
inkos-agent doctor            # inkos binary, project, proxy, modelOverrides
inkos-agent start             # bridge in the background (idempotent)
```

`doctor` must not report `modelOverrides ... bypasses the bridge`; such an
override would make InkOS call a real API. Ask the user before changing it.

The project directory is `$INKOS_AGENT_PROJECT`, `--project DIR`, or the cwd.
Short commands without model calls (`book list`, `status`, `export`) can run in
the foreground: `inkos-agent run -- book list --json`.

## 2. The loop for anything that calls the model

```bash
JOB=$(inkos-agent job start -- write next <book-id> --count 1)
inkos-agent wait --job $JOB --timeout 90
#   exit 0 -> lines "r-... pending ... prompt=<path>"   : answer them (step 3)
#   exit 3 -> job finished (exit code + log tail shown) : verify results (step 4)
#   exit 4 -> nothing yet                               : call wait again
```

Keep each shell call short (`--timeout 90`); the job keeps running in the
background between calls. Repeat `wait` until exit 3. Several requests may be
pending at once; they are independent and can be answered in any order.

Prefer explicit CLI actions (`book create`, `write next`, `revise`, `review`,
`export`, ...) over `inkos interact`/agent chat: with the chat agent you would
also be answering InkOS's own coordinator prompts, which doubles the work.

## 3. Answering one request

```bash
inkos-agent claim r-XXXX --by <your-name>        # avoid double answers
inkos-agent show r-XXXX                          # readable prompt (or read the prompt= path)
inkos-agent reply r-XXXX --text-file answer.md   # final assistant text
inkos-agent reply r-XXXX --tool NAME --args-file args.json   # tool call(s), repeatable
inkos-agent fail  r-XXXX --message "why"         # cannot answer honestly
```

Rules for the answer:

- You are the InkOS agent described by the system messages (architect, planner,
  writer, auditor, settler, reviser...). Do that job and only that job.
- Output exactly what that agent must return. Keep the protocol intact: `===
  SECTION ===` / `=== CHAPTER_CONTENT ===` tags, parser headings, JSON keys and
  enum values, required tool calls (`tool_choice`), `response_format` schemas.
  `reply` rejects non-JSON for JSON formats and missing required tool calls.
- No talk about the bridge, the queue, yourself, or "here is the answer".
- Respect the requested length. For Korean (`language: ko`) the unit is
  `ko_chars`: NFC characters excluding whitespace and Markdown metadata.
  `max_tokens` in the prompt header is a hard upper bound.
- Never invent observations, passing reviews, scores, saved files or usage. A
  review states only what the supplied text supports.
- When a request was already `answered`, `abandoned` or `expired`, leave it.
  `abandoned` means InkOS stopped waiting (cancel, crash, retry).
- Use `fail` instead of a fake answer. `--retryable` lets InkOS retry the call.
- Decide quickly when you will `fail`: within ~4 minutes InkOS gets a real HTTP
  error. Later, InkOS reads it as an empty response and re-sends the same call
  as a new request (up to 2 times); fail those too if the reason still holds.
- Only the claimant can answer a claimed request (`--by` must match), and each
  request accepts exactly one `reply`/`fail`.

## 4. After a job finishes

Check the exit code and log (`inkos-agent job log $JOB`), then confirm the
result in the saved files (chapters, index, state, snapshots) through InkOS
(`inkos-agent run -- status <book-id>`, `review`, `export`). Report to the user
what was saved, not what you intended. Do not approve, publish, upload, or
notify anyone unless the user asked for that exact action. Do not edit InkOS
state files by hand to get around a failed pipeline step.

## 5. Subagents (when your tool has them)

The main session coordinates; subagents answer requests.

- Give a subagent only the request id and the role (`writer` or `reviewer`).
  It runs `claim`, `show`, writes its answer file, and runs `reply` itself.
- Review/audit requests must go to a different subagent than the one that wrote
  the chapter under review, so the review is independent.
- Planning, writing, revision and state settlement can share the writer role.
- The role guess (`role~...`) in `wait` output is a keyword heuristic; the
  system prompt decides.

## 6. Limits to tell the user about

- Work stops when this session ends; there is no unattended background writer.
  A pending request waits up to `INKOS_AGENT_MAX_WAIT_S` (default 6 h).
- Token usage is reported as 0: the bridge cannot measure the agent's tokens.
- In cloud sandboxes `inkos-agent` removes HTTP(S)_PROXY for InkOS so it can
  reach 127.0.0.1; outbound InkOS features (web search, remote cover APIs) then
  have no proxy. `--keep-proxy` keeps it (needs the Korean patch's loopback fix).
- Cover/image calls only work if the project's cover service points at the
  bridge and you supply an image file (`reply --image file.png`); otherwise
  leave covers unconfigured.
- Studio ignores env settings. Only for Studio: `inkos-agent studio-config`
  (backs up `inkos.json` to `inkos.pre-agent.json`), `inkos-agent start
  --studio`; undo with `inkos-agent restore`.

## Korean projects

For Korean setup, revision or review follow `소설설정-항목별기준.md` when it is
present: state each setting item's purpose, context, observable criteria and
limits; keep confirmed canon, plans and undecided author choices separate. For
light martial fiction see `현대한국-라이트무협-기준.md`; do not force
reincarnation, a fixed cultivation ladder, or a Korean historical setting.
