# 7-f 검증 — 프로젝트 경로를 셸 변수에 기대지 않기

2026-10-26, 브랜치 `claude/eeum-n0rsol`. 감독 [지시] 7-f. 엔진·Studio는 그대로다. 바꾼 코드는 브리지(`inkos_agent.py`, `install.sh`)뿐이다.

배경(Codex 재확인, 28ef5cb): 설치는 통과했다(pnpm 9.15.9 via corepack, `.modules.yaml` pnpm@9.15.9).
그러나 Codex는 명령마다 새 셸을 열어 `export INKOS_AGENT_PROJECT`가 다음 명령에 이어지지 않았다. 그래서 `book create` job이 저장소 루트에서 돌아 "inkos.json not found in /workspace/inkos-ko"로 실패했다.

## 한 일

1. 기록: `install.sh --project DIR`(setup이 부름)가 절대 경로를 `${INKOS_AGENT_STATE:-tools/inkos-agent-bridge/runtime}/project`에 쓴다.
   임시 파일에 쓴 뒤 이름을 바꾸는 방식이다. `runtime/`은 브리지 `.gitignore`에 있다(`git check-ignore`: `runtime/	runtime/project`).
2. 프로젝트 결정: `--project` → `INKOS_AGENT_PROJECT` → `runtime/project` → 현재 폴더(맨 앞 `--project`는 원래 있던 옵션).
   고른 곳에 `inkos.json`이 없으면 뒤 순위로 넘어가지 않는다. `doctor`·`start`·`job start`·`run`은 job을 만들지 않고 exit 3으로 끝나며 아래를 출력한다:
   `프로젝트를 찾지 못함: <경로> (inkos.json 없음, <고른 곳>에서 고름), 시도한 곳: --project=…; INKOS_AGENT_PROJECT=…; <runtime/project>=…; current folder=…`
   `doctor`는 다른 항목을 다 출력한 뒤 exit 3이고, `project` 줄에 어디서 골랐는지(`from …`)를 적는다.
3. `INKOS_BIN`: 원래는 `INKOS_BIN` → PATH의 `inkos`였다. "이미 그렇다"가 아니어서 고쳤다.
   이제 `INKOS_BIN` → `~/.local/bin/inkos`(실행 가능할 때) → PATH의 `inkos` 순이다.

## 시험

새 파일 `tools/inkos-agent-bridge/tests/test_project_file.py`(14/14).
- 브리지 폴더를 임시로 복사하고, setup처럼 전체 환경에서 `install.sh --project <novel>`을 한 번 돌린다.
- 그 뒤 모든 명령을 `env -i HOME=<tmp/home> PATH=/usr/bin:/bin INKOS_AGENT_PORT=<빈 포트>`로, `inkos.json`이 없는 "저장소 루트" 폴더에서 실행한다.
  포트 변수는 이 VM의 4568 브리지를 건드리지 않으려고 넣었다.
- `~/.local/bin/inkos` 자리의 가짜 InkOS는 실행된 폴더와 인자를 출력한다.

출력(같은 방식의 데모):
```
project ready: <tmp>/novel (recorded in <tmp>/bridge/runtime/project)
== 기록 파일 있음 (cwd=<tmp>/repo, inkos.json 없음)
$ env -i HOME=… PATH=/usr/bin:/bin inkos-agent start
bridge ready: http://127.0.0.1:45877/v1
$ … job start -- status
j-20261026-062404-6dcfb66e rc=0
$ … job log
fake-inkos cwd=<tmp>/novel args=status
== 기록 파일 없음
$ … job start -- status
error: 프로젝트를 찾지 못함: <tmp>/repo (inkos.json 없음, current folder에서 고름), 시도한 곳: --project=(없음); INKOS_AGENT_PROJECT=(없음); <tmp>/bridge/runtime/project=(없음); current folder=<tmp>/repo. --project DIR 또는 INKOS_AGENT_PROJECT를 주거나, install.sh --project DIR로 <tmp>/bridge/runtime/project에 기록한다
rc=3; jobs 파일 수 3 → 3
```
시험이 더 확인하는 것:
- `doctor`가 `project … (ok, from <runtime/project>)`와 `inkos binary : ~/.local/bin/inkos (2.0.0)`를 출력한다.
- `run -- status`가 기록된 프로젝트에서 돈다. `INKOS_AGENT_PROJECT`를 주면 그쪽이 먼저다.
- 기록이 없으면 `run`·`doctor`·`start`도 exit 3이고, 저장소 루트에서 InkOS가 실행된 일이 없다.

설치 스크립트 시험에 "기록 파일 = 프로젝트 절대 경로"를 더했다(56 → 57).

## 문서

- ENV_TEST 2절과 브리지 AGENTS.md: 명령마다 새 셸이 열리는 환경(Codex 등)에서는 export가 이어지지 않는다. 7-f부터는 프로젝트와 InkOS에 export가 없어도 된다.
  AGENTS.md는 결정 순서와 exit 3도 적었다.
- RUNTIME: 설치 4번에 기록 파일, "작업 시작과 끝"의 export 줄에 주석, pnpm shim 절에 "셸에 예전 `INKOS_PNPM_PIN_CMD`가 남아 있으면 다시 확인하지 않음" 한 줄(7-e 승인 때의 기록).

## 남은 점 (보고의 결정필요)

`INKOS_LOCALE=ko`도 같은 export 줄에 있어 새 셸에서는 사라진다. CLI는 `INKOS_LOCALE` → `LC_ALL`/`LC_MESSAGES`/`LANG` → `zh` 순으로 안내 문구 언어를 정한다(`packages/cli/src/localization.ts:50-56`).
그래서 Codex의 새 셸에서는 CLI 안내 문구가 중국어(또는 LANG에 따른 언어)가 될 수 있다. 원고 언어(작품 설정)와는 별개다.
7-f 본 커밋(c79b06e)에서는 고치지 않았고, 아래 보완에서 (b)로 처리했다.

## 보완: CLI 언어도 기록 (결정필요 답 (b), 사용자 결정)

- `install.sh --locale ko`(setup이 넘김)가 `runtime/locale`에 `ko`를 쓴다. 값은 영문자·`_`·`-`만 받고, 틀리면 아무것도 쓰기 전에 exit 2로 멈춘다.
- 브리지는 InkOS를 띄울 때(`run`, `job start`, `start --studio`) 셸에 `INKOS_LOCALE`이 없으면 기록된 값을 넣는다. 셸 값이 먼저다. 기록이 없으면 아무것도 넣지 않는다(zh/en 설치는 그대로).
  `doctor`는 `locale : ko (from …/runtime/locale)` 줄을 출력한다. 엔진은 그대로다.
- 실제 InkOS 비교: `book backup <ID> --list`는 일부러 작품 언어가 아니라 환경 언어를 따른다(`commands/book.ts:312-314` 주석). `env -i`(LANG 없음)로 test-6에서 실행했다:
```
== runtime/locale 없음
test-6-murim-나루-객주의-짐표-사환 还没有备份。用 inkos book backup test-6-murim-나루-객주의-짐표-사환 创建一份。
== runtime/locale = ko
test-6-murim-나루-객주의-짐표-사환의 백업이 없습니다. 생성 명령: inkos book backup test-6-murim-나루-객주의-짐표-사환
```
  환경 언어를 쓰는 곳: `book backup`·`book restore`, `doctor`, `config` 모델 목록(`resolveCliLanguage()` 인자 없음).
  `write next`, `revise`, `status` 같은 작품 명령은 작품 언어(`book.language`)를 먼저 따르므로 기록이 없어도 한국어다.
- 시험: 브리지 프로젝트 기록 14 → 19.
  - 기록 생성, 틀린 값은 exit 2이고 아무것도 쓰지 않음.
  - `doctor`의 locale 줄, job이 `INKOS_LOCALE=ko`를 받음.
  - 셸의 `INKOS_LOCALE=en`이 먼저, 기록이 없으면 넣지 않음.
  - 설치 스크립트 57 → 58(setup이 `ko`를 기록).

## 시험 수

프록시 변수 제거, shim 경유: core 757 / studio 307 / cli 101 = 1,165 통과. 브리지 38/38, 브리지 프로젝트 기록 19/19(새 파일), Drive 51/51, novel-brief 27/27, 설치 스크립트 58/58(보완 뒤).
