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

Revision in Korean projects: the latest chapter owns the runtime state, so
revising an earlier chapter saves only its file and index (ko prints a warning
that the state files may keep the old facts). Earlier chapters get only
`spot-fix` edits that change no facts (wording, register). When facts must
change, pass the correction to the next chapter with `write next <book>
--context "..."` and tell the author; never rewind or hand-edit state. In a
`--brief`, quote the sentence to fix instead of giving a line number (engine
line numbers skip the 2 heading lines).

Author choices (interactive by default): do not decide what the author decides.
Ask with `python3 tools/novel-brief.py` (numbered questions the user can answer
by number), and run `pack --resume` (storage policy below) before waiting for
an answer. Before `book create`: `novel-brief.py interview <brief.md>`; after
the design: `interview --work works/<ID>`; before each chapter: `next
works/<ID>`, then `direct works/<ID> --choice K -o FILE` and `write next <ID>
--context-file FILE` (the same text is appended to
`source/story/author_directions.md`). Items already answered in the brief or
that file are not asked again. Briefings come only from the work's files;
missing fields read "없음". "N화 써줘"의 해석: 회차 수를 말하면("다섯 화 써줘", "5개 화 써줘", "5화 더 써줘", "3화 연달아 써줘") 일괄로 쓰고 질문은 생략한다. 회차 번호만 말하면("3화 써줘") 그 한 회차만 평소대로 브리핑 질문을 하고 대화형으로 쓴다. 그 번호가 다음 회차가 아니면 쓰지 않고 "다음은 N화"라고 알려 확인을 받는다.
Batch mode: no questions, per chapter
`direct --plan -o FILE` then `write next --count 1 --context-file FILE`; stop
at a state-not-applied warning or a failed job, report a table (length, review
observations, state applied) at the end, and mark any temporary author choice
as "가정". Full rules: `korean-port/RUNTIME.md` "작가 선택".

In the Korean fork, novel projects live only in the container. Follow this policy
(also in `korean-port/RUNTIME.md`):

## 원고 보관 지침 (모든 실행 환경)

실제 작품: 대화형은 질문을 기다리기 전에 재개용 압축본 전체를, 일괄은 회차마다 원고 `.md`를 Drive 'Inkos ko'에 올리고, 일괄이 끝나거나 멈출 때(경고·실패) 압축본을 올린다. 시험 작품(`test-`)은 올리지 않는다.

### 실제 작품 (사용자가 실제로 쓰는 작품)
- 작품 폴더와 원고는 공개 포크에 커밋하지 않는다.
- 압축본 만들기: `python3 tools/novel-drive.py pack <작품 폴더> <작품ID>_<YYYYMMDD-HHMM>_<마지막 회차>화 --resume`
  → `.tar.xz`(그 환경의 Python에 `lzma`가 없으면 경고하고 `.tar.gz`). `unpack`은 두 형식을 모두 알아본다.
- 올리는 때:
  - 대화형: 질문하고 답을 기다리기 전마다 압축본 전체(기다리는 동안 VM이 회수돼도 상태를 잃지 않게).
  - 일괄: 회차가 끝날 때마다 그 회차 원고 `.md` 하나. 압축본은 일괄이 끝날 때와 멈출 때(상태 미반영 경고·작업 실패).
  - 세션 끝: 마지막으로 올린 압축본 뒤에 바뀐 것이 있으면 압축본.
- Drive 파일 이름(시각은 올린 시각, UTC):
  - 압축본: `<작품ID>_<YYYYMMDD-HHMM>_<마지막 회차>화.tar.xz`(gz면 `.tar.gz`). 조각은 `<압축본 이름>.part<N>of<M>`, 목록은 `<압축본 이름>.parts.json`.
  - 원고: `<작품ID>_<회차 네 자리>화_<YYYYMMDD-HHMM>.md`(예: `철쭉골-대장간-막내_0004화_20261026-0930.md`). 내용은 `chapters/<회차 네 자리>_<제목>.md` 그대로.
    같은 회차를 다시 올리면 시각만 다른 새 파일이 된다. 지우지 않는다.
- 받기(다음 세션): 가장 늦은 압축본을 받아(조각이면 `join`) 확인한 뒤 `unpack`한다. 그 압축본의 마지막 회차보다 뒤 회차의 원고 `.md`가 Drive에 있으면
  그 회차는 원고만 있고 상태가 없다. 사용자에게 알리고 어떻게 할지 묻는다(그 원고를 참고해 다시 쓰기 등). 엔진 상태를 손으로 만들지 않는다.
- 기본: 이 환경의 Google Drive 연결 도구로 에이전트가 직접 "Inkos ko" 폴더에 올린다. 연결 도구가 한 번에 받는 양(약 12KB)보다 크면
  아래 "조각 업로드"대로 나눠 올린다. Drive 업로드는 각 에이전트의 연결 도구가 하는 일이며, 포크 코드에 Drive 기능을 더 넣지 않는다.
- 보조: 사용자에게 파일로 건넨다 — 사용자가 원할 때, 또는 Drive 업로드가 실패했을 때.
- 쓴 경로와 파일 이름(원본 크기·sha256 포함)을 사용자에게 보고한다. 어느 경로도 안 되면 실패 사실과 이유를 보고에 적는다.
- 세션 시작: 받은 압축본을 unpack하기 전에 파일 이름, 마지막 회차, sha256을 사용자에게 보여주고 확인받는다.
- 한 작품을 두 환경에서 동시에 작업하지 않는다.

### 시험 작품 (`test-`)
1. 개발·실행 시험에서 검증용으로 만든 작품이다. 새로 만드는 시험 작품의 ID는 `test-`로 시작한다(예: `test-6-murim`; ID는 제목에서 만들어지므로 제목을 `test-…`로 시작).
2. 시험 작품은 밖으로 내보내지 않는다: 사용자에게 파일로 보내지 않고, Drive에 올리지 않고, 커밋하지 않는다. `pack --resume`은 같은 VM 안에서 재개를 검증할 때만 쓴다.
3. 예외: 사용자가 요청한 경우, 또는 감독이 보관 경로 자체를 시험하라고 지시한 경우에만 내보낸다.
4. 증거는 짧게: 보고와 VERIFICATION에는 원고를 몇 줄 이하로 인용하고 분량·크기·sha256으로 남긴다.

### 파일로 건네고 다음 세션에서 받기
- 건네기(Claude Code): 압축본을 파일 보내기 도구(`SendUserFile`, 첨부 형식)로 보낸다. 사용자는 Claude 앱 대화에서 파일 카드를 눌러 휴대폰에 저장한다.
- 받기(다음 세션): 사용자가 새 세션 대화에 그 압축본(`.tar.xz` 또는 `.tar.gz`)을 첨부한다. Claude Code 클라우드 세션에서는 `/root/.claude/uploads/<세션ID>/<접두어>-<파일명>`에 놓인다.
  `sha256sum`으로 보고했던 값과 맞춘 뒤 `python3 tools/novel-drive.py unpack <파일> <작품 폴더>`로 푼다.

### 조각 업로드 (Drive 연결 도구가 내용을 호출 안에 직접 받는 경우)
- 나누기: `python3 tools/novel-drive.py split <압축본> [폴더]` → `<압축본>.part1ofN` … `<압축본>.partNofN`(기본 12,000바이트, base64 약 16,000자)과
  목록 파일 `<압축본>.parts.json`(압축본 이름·크기·sha256, 조각마다 이름·크기·sha256).
- 올리기: 목록 파일과 조각 N개를 모두 "Inkos ko"에 올린다(바이너리는 `application/octet-stream`, 변환 끔). Drive가 돌려준 크기를 목록과 맞춘다.
- 받기: 목록 파일과 조각을 한 폴더에 받은 뒤
  `python3 tools/novel-drive.py join <압축본>.parts.json` — 조각마다, 그리고 이은 결과의 크기·sha256을 목록과 대조하고 하나라도 다르면 멈춘다.
  스크립트가 없을 때: `cat <압축본>.part1ofN … <압축본>.partNofN > <압축본>` 후 `sha256sum <압축본>`을 목록의 `sha256`과 비교한다.

"Inkos ko" folder ID: `1FYkA9t5AiI3u31cL0uM8dSFjgf5LxnEU`. The OAuth `novel-drive.py push`/`pull`
sync is optional and not used by the app (선택, 앱이 쓰지 않음). If `push` exits 3 (overwrite protection), do not use `--force`;
stop and report to the user.
