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
# Always exit 0; read the first line:
#   EVENT: request ...       -> lines "r-... pending ... prompt=<path>" : answer them (step 3)
#   EVENT: job-finished ...  -> "succeeded"/"FAILED" + inkos exit code  : verify results (step 4)
#   EVENT: timeout           -> nothing yet                              : call wait again
```

Keep each shell call short (`--timeout 90`); the job keeps running in the
background between calls. Repeat `wait` until `EVENT: job-finished`; the job's own
result is the `inkos exit=` value on that line, not the shell exit code. Several requests may be
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
- When a prompt names `=== TAG ===` output markers, `reply` warns if the answer
  has none of them. Check the required format before ignoring the warning.
- Reviews keep the severity an issue deserves. Never downgrade an unresolved
  problem (e.g. to `info`) because it is "outside this revision's scope"; report it
  at its real severity and say it was not addressed by this revision.
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
- State validation judges only conflicts between the chapter text and the
  projected state. Values the engine normalizes on save (a hook's
  `startChapter` keeps the smaller value, so design-time hooks stay at 0) are
  not contradictions; do not require reconciliation for them.
- Planning, writing, revision and state settlement can share the writer role.
- The bridge does not guess roles. `wait` shows the opening of each system
  prompt; read it (or the full prompt) to decide writer vs reviewer.
- Without subagents, two background workers (one writer, one reviewer) are a
  valid substitute: each `claim`s only requests of its own role and leaves the
  rest pending. `claim` is atomic, so two workers never answer the same request.

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

## Environment notes (from real runs)

- Node 22+ is required (InkOS uses `node:sqlite`; the 2.0 source needs 22.16+).
  Install one Node version with one tool. Two overlapping installs broke npm's own
  files once (`Class extends value undefined` during a build). Check `node -v` and
  `npm -v` before building.
- Role card folders: zh/en works use `roles/主要角色`·`roles/次要角色`; Korean (ko)
  works in the Korean fork use `roles/major`·`roles/minor`. The engine reads all four.
  Do not move cards by hand.

## Korean projects

For Korean setup, revision or review follow `소설설정-항목별기준.md` when it is
present: state each setting item's purpose, context, observable criteria and
limits; keep confirmed canon, plans and undecided author choices separate. For
light martial fiction see `현대한국-라이트무협-기준.md`; do not force
reincarnation, a fixed cultivation ladder, or a Korean historical setting.

In the Korean fork, novel projects live only in the container. Follow this policy
(also in `korean-port/RUNTIME.md`):

## 원고 보관 지침 (모든 실행 환경)
- 작품 폴더와 원고는 공개 포크에 커밋하지 않는다.
- 회차 하나를 끝낼 때마다, 그리고 세션 끝에:
  python3 tools/novel-drive.py pack <작품 폴더> <작품ID>_<YYYYMMDD-HHMM>_<마지막 회차>화.tar.gz
  → 이 환경의 Google Drive 연결로 "Inkos ko" 폴더에 올리고, 올린 파일 이름을 사용자에게 보고한다.
- 압축본 업로드가 안 되면(크기 제한, 연결 오류 등): 회차 원고와 상태 파일만 텍스트로 올리거나, 사용자에게 파일로 넘긴다. 실패 사실을 보고에 적는다.
- 세션 시작: "Inkos ko"에서 그 작품의 가장 최근 압축본을 받아 unpack하기 전에, 파일 이름과 마지막 회차를 사용자에게 보여주고 확인받는다.
- 한 작품을 두 환경에서 동시에 작업하지 않는다.

"Inkos ko" folder ID: `1FYkA9t5AiI3u31cL0uM8dSFjgf5LxnEU`. The OAuth `novel-drive.py push`/`pull`
sync is optional. If `push` exits 3 (overwrite protection), do not use `--force`;
stop and report to the user.
