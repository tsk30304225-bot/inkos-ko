# 실행 환경 안내 (RUNTIME)

이 포크는 모델 API를 쓰지 않는다. InkOS의 모델 호출은 `tools/inkos-agent-bridge`(127.0.0.1:4568)로 가고, **에이전트 세션이 직접 답한다**.
세 실행 환경(Claude Code 클라우드, Codex 클라우드, Grok봇)은 같은 설치 스크립트와 같은 규칙(`tools/inkos-agent-bridge/AGENTS.md`)을 쓴다.

## 공통: 설치 한 번

```sh
sh tools/setup-cloud.sh            # 기본 작품 프로젝트: <저장소>/novel
```

스크립트가 하는 일:

1. Node 22.16 이상·python3 확인(node 24는 Codex에서 확인(v24.19.0)), lockfile의 pnpm 9.15.9로 `install --frozen-lockfile && -r build`.
   `tools/pnpm-pin/pnpm`(shim)을 이 두 명령에만 PATH 앞에 둔다. shim은 PATH에서 자기 자신을 뺀 실제 `pnpm`이 9.15.9면 그것을,
   아니면 `corepack pnpm@9.15.9`, 안 되면 `npx -y pnpm@9.15.9`를 쓴다. 쓴 경로를 출력한다(`package.json`은 고치지 않는다).
   패키지 스크립트 안의 `pnpm` 호출(`packages/cli`의 `prebuild`/`pretypecheck` → `pnpm run prepare:workspace-core` → `pnpm --filter @actalk/inkos-core build`,
   `pretest` → `pnpm run build`)도 PATH에서 shim을 다시 찾으므로 9.15.9로 돈다. 다른 pnpm이 만든 `node_modules`는 확인 질문 없이 다시 설치한다(`--config.confirm-modules-purge=false`).
   shim은 `~/.local/bin`이나 `~/.bashrc`에 넣지 않는다. 셸에 예전 `INKOS_PNPM_PIN_CMD`가 남아 있으면 shim은 버전을 다시 확인하지 않고 그 명령을 쓴다(직접 둘 일은 없다. 이상하면 `unset INKOS_PNPM_PIN_CMD`).
2. `~/.local/bin/inkos` 실행기 생성(빌드 결과 `packages/cli/dist/index.js`에는 실행 권한이 없어서 래퍼를 둔다)
3. 작품 프로젝트가 없으면 `inkos init --lang ko`(OAuth 비밀값을 넣고 `--pull`을 주면 최신 보관본을 복원 — 위 원고 보관 지침의 사용자 확인을 먼저 받을 것)
4. 브리지 설치(`install.sh --project … --locale ko`: 작품 프로젝트 경로와 CLI 언어를 git 무시 위치 `tools/inkos-agent-bridge/runtime/project`·`runtime/locale`에 기록. 셸에 `INKOS_LOCALE`이 없으면 브리지가 job에 `ko`를 넣는다), `~/.bashrc`에 `PATH`·`INKOS_BIN`·`INKOS_LOCALE=ko`·`INKOS_AGENT_PROJECT` 추가, `inkos-agent doctor`

이미 있는 설치: 바꾸기 전에 `~/.local/bin/inkos`, `~/.local/bin/inkos-agent`, `~/.bashrc`의 `# inkos-ko setup` 블록을 모두 확인한다.
하나라도 다른 설치의 것이면 무엇이 어디를 가리키는지 출력하고 **exit 3**으로 멈춘다(아무것도 바꾸지 않음). `--replace`를 주면
셋을 링크 그대로 `~/.local/bin/.inkos-ko-backup/<UTC 시각>/`에 복사하고(`README`, `restore.sh`) 바꾼다. 되돌리기는 `sh <백업 폴더>/restore.sh`.
백업 폴더는 restore 뒤에도 남는다. restore 뒤에는 지워도 된다.
파일은 링크를 따라 쓰지 않는다(임시 파일에 쓰고 이름 바꾸기, 권한 유지). `~/.bashrc`에 덧붙이는 것은 2줄(`# inkos-ko setup`과 `export …`)이고, 지우면 되돌아간다.
`~/.bashrc`가 링크(dotfiles 관리 도구 등)이면 고치지 않고 그 2줄을 출력하며, 백업·되돌리기 대상에서도 빠진다.
브리지(`/health`)는 자기 runtime 폴더(`state`)를 알려 준다. 포트의 브리지가 이 설치의 것이 아니면 `doctor`는 경고, `start`·`job start`는 exit 3.

시험 명령(저장소 루트에서, shim을 PATH 앞에 두고):

```sh
env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy PATH="$PWD/tools/pnpm-pin:$PATH" pnpm -r --no-bail test
```

API 키나 외부 모델 주소는 설정하지 않는다. `doctor`가 `modelOverrides … bypasses the bridge`를 보고하면 실제 API로 나가는 설정이 있다는 뜻이므로 사용자에게 먼저 묻는다.

작품 프로젝트가 저장소 안(`novel/`)에 있으면 스크립트가 `novel/.gitignore`에 `*`를 넣어 코드 저장소에 원고가 커밋되지 않게 한다. 원고 보관은 아래 원고 보관 지침을 따른다.

## 공통: 작업 순서 (에이전트용)

```sh
inkos-agent start
JOB=$(inkos-agent job start -- book create --title "제목" --genre light-martial --lang ko)
inkos-agent wait --job $JOB --timeout 90     # 브리지 1.2: 항상 exit 0, 첫 줄 EVENT: request(답하기) / job-finished(끝) / timeout(다시 wait)
```

- 장르 기준이 있는 값: `light-martial`(라이트 무협), `fantasy`(판타지), `modern-fantasy`(현대판타지). 한국어 이름(무협, 현대판타지 등)도 알아본다.
- 대본: `inkos script create …`(기본 세로형 숏드라마), 설명 영상: `inkos explainer create …`(기본 롱폼 8~15분, ko 프로젝트 전용).
- 작품별 피로어 목록(선택): `works/<작품>/source/story/korean_fatigue_words.md`에 한 줄에 하나. 검수 때 빈도가 관찰로 붙는다.

### 원고 수정(`revise`) 지침

- 상태(현재 상태·복선·회차 요약·스냅샷)는 가장 최근 회차가 가진다. 최신이 아닌 회차를 `revise`하면 원고와 회차 색인만 저장되고 상태는 되감기지 않는다.
  ko 작품에서는 이때 CLI가 "상태 파일에는 수정 전 사실이 남을 수 있습니다" 경고를 낸다.
- 그래서 최신이 아닌 회차는 사실을 바꾸지 않는 `spot-fix`(문장·말투·단어)만 한다.
- 사실이 바뀌는 수정이 꼭 필요하면 그 회차를 고치는 대신, 다음 회차를 `write next <작품> --context "<바로잡을 내용>"`으로 쓰며 넘기고,
  무엇을 바꿨는지 작가에게 알린다. 엔진 상태를 손으로 되감거나 상태 파일을 고치지 않는다.
- `--brief`(수정 지시)에는 줄 번호 대신 고칠 문장을 인용문으로 적는다. 엔진의 줄 번호는 제목 2줄을 빼고 세므로 파일 줄 번호와 2만큼 다르다.

### 작가 선택: 대화형(기본)과 일괄
- 대화형이 기본이다. 작가가 정할 것은 에이전트가 정하지 않는다. 선택지를 보여주고 답을 받은 뒤 진행한다.
- 질문 형식(휴대폰에서 번호만 답할 수 있게). 질문 원문은 `tools/novel-brief.py`가 만든다:
  ```
  [선택 1] 서술 시점
    1) 3인칭 주인공 제한 (추천: 장르 관행, 정보 통제 쉬움)
    2) 1인칭 주인공
    3) 3인칭 다중 시점
   기타) 직접 입력
  ```
- 대기 전 보관(필수): 질문하고 답을 기다리기 전에 `pack --resume`으로 아래 원고 보관 지침을 수행한다(클라우드 VM은 쉬는 동안 회수될 수 있고,
  Codex는 질문이 곧 작업 종료일 수 있다). 시험 작품은 VM 안에만 둔다.
- 순서:
  1. 책 만들기 전 인터뷰: `python3 tools/novel-brief.py interview <brief.md>` → 비었거나 "미정"인 항목만 묻는다(장르, 서술 시점, 주인공 장치,
     톤·수위, 회차 수·회당 분량, 금지 사항, 결말 방향). 답은 `--answer N=번호` 또는 `--answer N=기타:글`로 브리프에 적는다.
     다 정해지면 `inkos book create --title "…" --genre … --brief <brief.md>`. 회귀·빙의·헌터 등은 고를 수 있는 장치일 뿐 강제하지 않는다.
  2. 설계 직후: `novel-brief.py interview --work works/<ID>` → 설계가 "미정(작가 선택)"으로 남긴 항목 가운데 브리프나 지시 기록에 답이 없는 것만 묻는다.
     답은 `--answer`로 `works/<ID>/source/story/author_directions.md`의 "설계 후 작가 선택"에 기록된다.
  3. 매 회차 전: `novel-brief.py next works/<ID>` → 다음 화 브리핑(직전 화 요약, 열린 복선, 권 지도상 다음 박자, 정해진 작가 선택,
     전개 선택지 — "계획대로 진행"과 "직접 지시" 포함). 답은 `novel-brief.py direct works/<ID> --choice K -o <파일>`(또는 `--text "작가의 말"`)로
     `--context` 원문을 만들고, `inkos write next <ID> --context-file <파일>`로 넘긴다. `direct`는 같은 원문을 `author_directions.md`의 "N화" 항목에 그대로 덧붙인다.
- "N화 써줘"의 해석: 회차 수를 말하면("다섯 화 써줘", "5개 화 써줘", "5화 더 써줘", "3화 연달아 써줘") 일괄로 쓰고 질문은 생략한다. 회차 번호만 말하면("3화 써줘") 그 한 회차만 평소대로 브리핑 질문을 하고 대화형으로 쓴다. 그 번호가 다음 회차가 아니면 쓰지 않고 "다음은 N화"라고 알려 확인을 받는다.
- 일괄: 회차별 질문을 생략하고 계획대로 쓴다. 회차마다 `direct works/<ID> --plan -o <파일>` → `write next <ID> --count 1 --context-file <파일>`.
  - 멈추는 조건: 상태 미반영 경고(`경고: N화 원고는 저장됐지만 상태(…)는 반영되지 않았습니다.`) 또는 작업 실패. 그 회차에서 멈추고 보고한다.
  - 감사가 지적한 문제는 끝에 모아 보고한다. 끝나면 회차별 분량·감사 의견 수·상태 반영 여부를 표로 보고하고, 다음에 정할 선택지(`next`)를 붙인다.
  - 일괄 중에도 미정인 작가 선택은 확정하지 않는다. 임시로 정했다면 "가정"으로 표시해 보고한다.
- 질문은 한 번만: 브리프와 지시 기록에 있는 항목은 정해진 것으로 보고 다시 묻지 않는다(`novel-brief.py`가 거른다).
- 브리핑 근거는 작품 파일(상태·복선·권 지도)에서만 뽑는다. 에이전트 기억으로 채우지 않고, 파일에 없는 칸은 "없음"으로 둔다.

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
- 보조: 사용자에게 파일로 건넨다(아래 "파일로 건네고 다음 세션에서 받기") — 사용자가 원할 때, 또는 Drive 업로드가 실패했을 때.
- 쓴 경로와 파일 이름(원본 크기·sha256 포함)을 사용자에게 보고한다. 어느 경로도 안 되면 실패 사실과 이유를 보고에 적는다.
- 세션 시작: 받은 압축본을 unpack하기 전에 파일 이름, 마지막 회차, sha256을 사용자에게 보여주고 확인받는다.
- 한 작품을 두 환경에서 동시에 작업하지 않는다.

### 작업 시작과 끝 (작업 공간이 남지 않을 때)
Codex는 작업이 끝나면 `/workspace`가 남지 않는다고 가정한다. Grok과 Claude Code 클라우드도 VM이 회수되면 같다. 실제 작품은 작업을 시작할 때마다 이 순서로 한다.

```sh
git clone -b claude/eeum-n0rsol https://github.com/tsk30304225-bot/inkos-ko && cd inkos-ko
sh tools/setup-cloud.sh                       # 빈 novel/ 프로젝트가 생긴다
export PATH="$HOME/.local/bin:$PATH" INKOS_BIN=$HOME/.local/bin/inkos INKOS_LOCALE=ko INKOS_AGENT_PROJECT=$PWD/novel   # 7-f부터 프로젝트·inkos는 없어도 찾는다
# Drive 'Inkos ko'에서 그 작품의 가장 늦은 압축본을 받는다(조각이면 join). 이름·마지막 회차·sha256을 사용자에게 보여 주고 확인받는다.
python3 tools/novel-drive.py unpack <압축본> novel --force   # 방금 만든 빈 프로젝트라서 --force
tools/inkos-agent-bridge/inkos-agent run -- status <작품ID>   # 마지막 회차가 압축본 이름과 맞는지 확인
```

- `novel/`에 원고가 있으면(작품 폴더 `works/<ID>/`, 회차 원고 `source/chapters/*.md`, 1.8 구조 `books/*/chapters/*.md`) 도구가 `--force`를 거부하고 exit 3으로 끝난다(아무것도 바꾸지 않음).
  이때는 멈추고 사용자에게 묻는다. 사용자가 덮으라고 하면 `--overwrite-work`를 쓴다. 이 옵션은 먼저 대상 폴더 전체를 `<폴더 이름>.before-unpack-<UTC>.tar.xz`로 압축해 두고, 그 경로와 둔 곳의 이유를 출력한 뒤 덮는다.
  백업 위치: 대상이 git 작업 트리 안이면(기본 배치 `<저장소>/novel`) `~/.inkos-ko-backup/unpack/`(저장소 밖이라 커밋될 수 없다), git 밖이면 대상 폴더 옆.
  백업에는 원고가 들어 있으니 커밋하거나 올리지 않는다. 압축본에 없는 파일은 지우지 않는다.
- 압축본 뒤 회차의 원고 `.md`가 Drive에 있으면 위 "받기"대로 사용자에게 묻는다. 그다음 이어 쓴다(올리는 때는 위와 같다).
- 작업을 끝낼 때: 마지막으로 올린 압축본 뒤에 바뀐 것이 있으면 압축본을 올린다.
- 같은 VM에서 다시 시작해 작품 폴더가 남아 있으면 clone·setup·unpack을 건너뛰고 `status`부터 한다.
- 2026-10-26 확인: 이 순서(새 `inkos init` 프로젝트에 `unpack --force`)로 푼 작품의 `status`가 원본과 같다(경로 줄 제외, test-6 `--resume` 압축본).

### 시험 작품 (`test-`)
1. 개발·실행 시험에서 검증용으로 만든 작품이다. 새로 만드는 시험 작품의 ID는 `test-`로 시작한다(예: `test-6-murim`).
   작품 ID는 제목에서 만들어지므로 제목을 `test-…`로 시작한다. 이 규칙 전에 만든 시험 작품(청운객잔·철쭉골·잿빛 탑·환승역)도 시험 작품이다.
2. 시험 작품은 밖으로 내보내지 않는다: 사용자에게 파일로 보내지 않고, Drive에 올리지 않고, 커밋하지 않는다.
   `pack --resume`은 같은 VM 안에서 재개를 검증할 때만 쓴다.
3. 예외: 사용자가 요청한 경우, 또는 감독이 보관 경로 자체를 시험하라고 지시한 경우에만 내보낸다.
4. 증거는 짧게: 보고와 VERIFICATION에는 원고를 몇 줄 이하로 인용하고 분량·크기·sha256으로 남긴다. 원고 전문은 붙이지 않는다.
   VERIFICATION이 너무 커지면 단계별 파일로 나눈다(`korean-port/verification/stage-N.md`).

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

"Inkos ko" 폴더 ID: `1FYkA9t5AiI3u31cL0uM8dSFjgf5LxnEU`. 각 실행 환경(Claude Code·Codex 클라우드, Grok봇)에는 각자 Google Drive 연결이 있다(2026-10-25 사용자 결정).
`pack`(옵션 없음)은 작품 프로젝트 전체(설정·원고·상태·스냅샷·작업 기록)를 묶는 전체 압축본이다. 보관 지침은 `--resume`을 쓴다. 어느 쪽이든 `.env`·브리지 `runtime/`·`.inkos-drive-base`는 넣지 않는다.
받은 압축본은 `python3 tools/novel-drive.py unpack <압축본> <작품 폴더>`로 푼다. 기존 프로젝트가 있으면 `--force`가 필요하고, `--force`는 방금 `init`만 한 빈 프로젝트에서만 통한다.
원고가 있으면 exit 3으로 멈춘다. 사용자에게 묻고, 덮기로 하면 `--overwrite-work`(자동 백업: git 작업 트리 안이면 `~/.inkos-ko-backup/unpack/`, 밖이면 대상 옆)를 쓴다. OAuth `pull`도 같다.

### 압축본 구성과 재개용 묶음(`pack --resume`)

5-a 1차 작품(설계 + 2화)의 전체 압축본 752,334바이트 구성(파일별 zlib 압축 크기 합, 2026-10-25 측정):

| 항목 | 압축 후 | 원래 크기 | 무엇인가 | 이어 쓰기에 필요한가 |
| --- | --- | --- | --- | --- |
| `.inkos/harness.sqlite` | 606,701 | 2,076,672 | 실행 기록(`creative_episodes` 4행, `creative_episode_events` 211행) | 아니오. 기록일 뿐 다시 만들어진다 |
| `works/<id>/revisions/` | 136,662 | 405,184 | 모든 파일의 판 73개(현재 판 포함) | 지난 판은 아니오. 현재 판은 `source/`와 같은 내용 |
| `works/<id>/source/story/` | 60,416 | 212,423 | 설계·상태·스냅샷·`memory.db` | 예(`memory.db`는 다시 만들어지는 검색 색인이라 제외 가능) |
| `works/<id>/source/chapters/` | 19,013 | 58,132 | 원고, 회차 색인 | 예 |
| `works/<id>/work.json` | 5,915 | 55,588 | 작업 목록(판 기록 포함) | 예 |
| 브리지 문서(`AGENTS.md` 등 5개) | 6,622 | 12,562 | 브리지 설치가 다시 쓰는 문서 | 아니오 |

`pack --resume`은 이어 쓰기에 필요한 것만 묶는다: `inkos.json`·`.node-version`·`.nvmrc`, 작품마다 `work.json`과 `source/` 전체
(`book.json`, `chapters/`, `story/`의 설계·상태 파일, 가장 최근 스냅샷 2개).
스냅샷을 2개 두는 이유는, 가장 최근 회차를 수정하거나 다시 쓸 때 그 앞 회차의 스냅샷을 기준으로 상태를 되돌리기 때문이다(`runner.ts` revise, `write rewrite`).
빠지는 것: `.inkos/`(실행 기록), `revisions/`(지난 판), `story/memory.db`(다시 만들어지는 검색 색인), 더 오래된 스냅샷, 브리지 문서, 그리고 원래 `pack`처럼 `runtime/` 폴더.
`unpack`은 각 파일의 현재 판 스냅샷을 `source/`의 같은 파일에서 다시 만든다(체크섬이 같을 때만).

```
python3 tools/novel-drive.py pack <작품 폴더> <작품ID>_<YYYYMMDD-HHMM>_<마지막 회차>화 --resume   # .tar.xz (lzma가 없으면 .tar.gz)
```

같은 작품(2화)의 `--resume` 압축본: 47,685바이트(base64 63,580자). 빈 폴더에 풀면 `inkos status` 출력이 원래 프로젝트와 같다(경로만 다름).
현재 판 59개 중 43개가 다시 만들어지고, 16개(스냅샷 0, `memory.db`, `story/runtime/` 회차 기록)는 의도적으로 빠진다.
압축본이 하는 일의 한계:
- 지난 판(되돌리기용 기록)과 그 16개 현재 판은 읽을 수 없다(`ARTIFACT_SNAPSHOT_UNAVAILABLE`).
- 가장 최근 2개보다 앞 회차의 수정·다시 쓰기는 기준 스냅샷이 없어 실패한다. 그런 작업이 필요하면 전체 압축본을 쓴다.
- 다음 회차를 쓸 때 빠진 원본 파일(스냅샷 0, 지난 `runtime/`)은 작업 목록에서 제거됨으로 표시된다. 원래 `pack`도 `runtime/`을 넣지 않으므로 같은 동작이다.

Drive 연결 도구(`create_file`)는 파일 내용을 base64 문자열로 호출 안에 직접 넣는다. 크기 한계는 Drive가 아니라 에이전트가 한 번의 호출에 쓸 수 있는 글자 수다.
2026-10-25 이 세션에서 base64 15,240자(11,430바이트)는 올라갔고 Drive가 돌려준 크기가 일치했다.

#### 회차마다 커지는 양 (2026-10-25 측정, 조사만 — 바꾸지 않음)

같은 작품(철쭉골)의 `--resume` 압축본: 2화 49,008바이트 → 3화 84,636바이트(+35,628) → 4화 118,446바이트(+33,810). 파일별 zlib 크기 합으로 나누면(+32,127):

| 늘어난 것 | 2화 → 3화(파일별 zlib) | 이유 |
| --- | --- | --- |
| `chapters/index.json` | 8,574 → 18,195 | 회차 감사 관찰의 `sourceRefs` 인용문. 3화 관찰 10개가 37,424바이트(인용 하나가 8KB인 관찰 2개). 1·2화는 13~15KB |
| 최신 스냅샷 교체(`snapshots/1` 빠지고 `3` 들어옴) | 9,933 → 20,533 | 상태가 회차마다 쌓인다(`current_state.json` 2화 15,565 → 3화 25,424바이트 원래 크기) |
| `story/state/*.json`, 상태 md | +3,333, +3,033 | 같은 이유 |
| 원고 1화분 | +3,832 | 3화 본문 |
| `work.json` | +1,707 | 작업 목록 |

- gzip은 32KB 창 안에서만 중복을 줄인다. 가장 최근 스냅샷은 현재 상태와 내용이 같고, 상태는 md와 json으로 두 번 저장되는데, 창 밖이라 거의 줄지 않는다.
  같은 내용을 xz(LZMA)로 묶으면 2화 32,944 → 3화 43,200바이트(+10,256)다.
- 줄일 수 있는 방법(측정값, 3화 기준, 적용하지 않음):
  1. xz로 압축: 84,636 → 43,200(−49%). `unpack`도 함께 바꿔야 한다.
  2. 가장 최근 스냅샷(현재 상태와 같은 내용)을 빼고 `unpack`에서 현재 상태로 다시 만들기: gzip 84,636 → 72,269.
  3. reviewer 지침에 "인용은 해당 문장만" 추가: `index.json` 증가분 대부분이 긴 인용이다(엔진 변경 없음).
  4. `chapters/.versions/`(수정 전 원고 판) 빼기: −662바이트로 효과가 거의 없다.
- 추정(측정 아님): 지금 방식(gzip)으로는 회차당 30KB 안팎씩 늘 수 있어 10화 무렵 300KB 안팎이 된다. 보관 기본 경로인 파일 건네기에는 문제가 없고, Drive 조각(12,000바이트)으로는 25조각을 넘는다.

#### 6단계 조사와 지침안 (2026-10-25 측정)

7단계에서 적용함: 2(xz, `pack` 기본값)와 3(회차별 원고 업로드 — 대화형은 질문 대기 전 압축본 전체 유지, 일괄만 원고 `.md`). 위 "원고 보관 지침"이 현재 규칙이다.

1. 감사 인용(3안, 채택·적용됨): 근거(`sourceRefs`)는 줄 범위로 제출되고 엔진이 그 범위의 본문 전체를 인용으로 저장한다(`models/observation.ts` `resolveObservationSources`).
   그래서 규칙은 "문제를 보여 주는 줄만 범위로 고른다"로 적었다. 같은 3화 기준 `index.json` 원래 크기 72,250 → 26,280바이트(−64%).
   test-6 3화(범위 1줄씩) 인용 9개 합 1,592바이트, 철쭉골 3화 37개 합 28,291바이트. 다만 압축본 전체(gzip)는 85,280바이트로 철쭉골 3화(84,636)와 비슷했다 —
   이 작품은 상태가 더 커서(사실 76행, 스냅샷 134KB) 줄어든 몫을 상쇄했다. 회차가 쌓일수록 상태·스냅샷 증가가 압축본 크기를 정한다.
2. xz(1안, 조사만): 같은 압축본을 xz로 묶으면 철쭉골 2·3·4화 32,944·43,200·51,460바이트(gzip의 44~67%), test-6 3화 38,080바이트. 압축 0.1~0.3초.
   바꾸려면 `pack`의 `w:gz`·`unpack`의 `r:gz`를 형식 자동 인식(`r:*`)으로 바꾸고 이름을 `.tar.xz`로 해야 한다. 위험: 환경의 Python에 `lzma` 모듈이 없으면 실패,
   스크립트 없이 풀 때 `xz` 실행 파일 필요. 이 VM에는 둘 다 있다. Codex·Grok 환경은 확인하지 않았다.
3. 회차 완료 때 무엇을 올릴지(지침안, 코드 아님): 실제 작품의 원고 `.md`는 회차마다 따로 올리고(회당 약 9.5KB, 연결 도구 한 번),
   재개용 압축본은 세션이 끝날 때만 올린다. 측정한 증가량(gzip 회차당 약 34.7KB, xz 약 9.3KB)으로 추정한 조각 수(12,000바이트 기준):

   | 회차 | gzip 압축본 | 조각 | xz 압축본(참고) | 조각 |
   | --- | --- | --- | --- | --- |
   | 4화 | 118,446(측정) | 10 | 51,460(측정) | 5 |
   | 10화 | 약 327,000 | 28 | 약 107,000 | 9 |
   | 20화 | 약 674,000 | 57 | 약 200,000 | 17 |
   | 30화 | 약 1,021,000 | 86 | 약 292,000 | 25 |

   한 세션에 9·10화 두 회차를 쓰면: 지금 방식(회차마다 압축본) 29+29 = 58번 올림, 지침안(원고 2번 + 끝에 압축본 1번) 2+29 = 31번.
   한계: 대화형은 질문하고 기다리기 전마다 압축본 보관이 필수이므로(위 "작가 선택"), 회차마다 기다리는 대화형에서는 줄지 않고 일괄 모드에서만 준다.
   세션이 압축본을 올리기 전에 끊기면 마지막 압축본 뒤 회차는 원고만 남고 상태는 없다(그 회차는 원고를 보며 다시 써야 한다).

## 선택: OAuth 직접 동기화 (`novel-drive.py push`/`pull`) — 선택, 앱이 쓰지 않음

Drive 연결 대신, 실행 환경의 비밀값으로 스크립트가 Drive API를 직접 부르는 방법이다. 선택 사항이며 기본 지침은 위의 Drive 연결이다.

```sh
python3 tools/novel-drive.py push novel          # 묶어서 올림(같은 작품의 최신 10개만 남기고 이전 것은 휴지통)
python3 tools/novel-drive.py pull novel          # 최신 보관본 복원 — 위 지침대로 먼저 사용자에게 확인
python3 tools/novel-drive.py list                # 보관본 목록
```

덮어쓰기 방지(2026-10-25 감독 지시): `pull`은 복원한 보관본 이름을 작품 폴더의 `.inkos-drive-base`에 기록한다.
`push`는 Drive에 있는 같은 작품의 최신 보관본이 그 기록과 다르면(다른 세션이 그 사이에 올림) 거부하고 exit 3을 낸다.
Drive에 이미 보관본이 있는데 이 사본이 Drive에서 복원된 것이 아니어도 거부한다.
**`novel-drive.py push`가 exit 3(덮어쓰기 방지 거부)을 내면 `--force`를 쓰지 말고 멈춰서 사용자에게 보고한다.**
작품 구분은 폴더 이름이 아니라 보관본 이름의 작품 키(`inkos-novel-<키>-<날짜-시각>.tar.gz`)로 한다.
OAuth 방식은 `drive.file` 범위라 도구가 만든 폴더(`init-folder`)만 쓸 수 있고, 위의 "Inkos ko" 폴더와는 별개다.

### OAuth를 쓸 때 처음 한 번: 인증 준비 (사용자가 직접)

비밀값은 대화창에 붙여 넣지 않는다. 각 실행 환경의 **비밀값(Secrets)/환경 변수 설정**에 넣는다.

1. Google Cloud Console에서 프로젝트를 만들고 **Google Drive API**를 사용 설정한다.
2. OAuth 동의 화면을 만든다(외부, 본인 계정을 테스트 사용자로). 범위는 `https://www.googleapis.com/auth/drive.file`(이 도구가 만든 파일만 볼 수 있는 좁은 범위).
   - 동의 화면이 "테스트" 상태면 Google 정책상 refresh token이 7일 뒤 만료된다. 계속 쓰려면 "프로덕션으로 게시"로 바꾼다(`drive.file`은 민감하지 않은 범위라 개인 용도면 심사 없이 경고 화면만 뜬다).
3. OAuth 클라이언트 ID(유형: 데스크톱 앱)를 만들어 client ID와 client secret을 받는다.
4. [OAuth 2.0 Playground](https://developers.google.com/oauthplayground)에서 톱니바퀴 → "Use your own OAuth credentials"에 3의 값을 넣고,
   범위 `https://www.googleapis.com/auth/drive.file`을 승인한 뒤 "Exchange authorization code for tokens"로 **refresh token**을 받는다.
5. 실행 환경의 비밀값에 세 개를 넣는다: `INKOS_GDRIVE_CLIENT_ID`, `INKOS_GDRIVE_CLIENT_SECRET`, `INKOS_GDRIVE_REFRESH_TOKEN`.
6. 새 세션에서 `python3 tools/novel-drive.py init-folder`를 실행하면 Drive에 `inkos-novels` 폴더를 만들고 ID를 출력한다.
   그 값을 `INKOS_GDRIVE_FOLDER_ID` 비밀값으로 추가한다. (`drive.file` 범위에서는 도구가 만든 폴더만 보이므로 Drive 화면에서 만든 폴더는 쓸 수 없다.)

Drive API 주소는 `oauth2.googleapis.com`, `www.googleapis.com`이다. 네트워크가 제한된 환경이면 이 두 호스트를 허용 목록에 넣는다
(2026-10-25 Claude Code 클라우드에서 두 호스트 접속 확인: 인증 없이 401/404 응답 = 연결은 됨).

## Claude Code 클라우드

- 환경 설정의 **Setup script**에 `sh tools/setup-cloud.sh`를 넣는다. 원고 보관은 이 세션의 Google Drive 연결(커넥터)로 한다. OAuth 동기화를 쓸 때만 `INKOS_GDRIVE_*` 비밀값을 넣는다.
- 집필·검수는 `.claude/agents`의 `inkos-writer`·`inkos-reviewer` 서브에이전트를 쓴다(검수는 집필한 서브에이전트와 다른 서브에이전트가 맡는다).
- `inkos-agent wait`는 일반 Bash 호출(`--timeout 90`)로 반복한다. 작업 자체는 `job start`로 이미 백그라운드에서 돈다.
- 세션이 오래 쉬면 컨테이너가 회수되어 진행 중인 작업과 브리지 요청이 사라진다(6단계에서 실제로 겪음). 그래서 원고 보관 지침대로 질문 대기 전·회차 끝에 Drive 연결 도구로 올린다.
- 작품 폴더를 `<저장소>/novel`에 두면 Claude 앱에서 원고 파일을 열어 볼 수 있다.

## Codex 클라우드

- Codex는 **Codex 클라우드**(같은 작업 안에서 작업 공간 유지)에서 확인했다. ChatGPT의 '워크 모드'는 메시지 사이에 작업 위치가 바뀌거나 사라져 지원하지 않는다(2026-10-26 확인).
- 기본 경로(사용자의 실행 방식, 2026-10-26): 저장소를 연결하지 않는다. 작업은 git 저장소가 없는 빈 `/workspace`에서 시작하고, 작업 단계에 인터넷이 열려 있다.
  작업 안에서 `git clone -b claude/eeum-n0rsol https://github.com/tsk30304225-bot/inkos-ko && cd inkos-ko` → `sh tools/setup-cloud.sh`를 실행한다. 1차 환경 시험이 이 방식으로 통과했다.
- 작업이 끝나면 `/workspace`가 남지 않는다. 실제 작품은 원고 보관 지침의 "작업 시작과 끝" 순서(Drive에서 압축본 받기 → `unpack` → `status`)로 시작하고, 끝낼 때 압축본을 올린다.
- 첫 지시 예: "https://github.com/tsk30304225-bot/inkos-ko 의 `claude/eeum-n0rsol` 브랜치를 clone하고 `sh tools/setup-cloud.sh`를 실행한 뒤 `novel/AGENTS.md`를 읽고 따라라."
  (`install.sh`가 작품 프로젝트에 `AGENTS.md`(브리지 지침)를 복사한다. 저장소 루트에는 `AGENTS.md`가 없다.)
- Drive 보관은 Codex 환경의 Google Drive 연결 도구로 한다(원고 보관 지침). OAuth `push`를 쓸 때만 `oauth2.googleapis.com`, `www.googleapis.com` 접속이 필요하다.
- `tools/inkos-agent-bridge/setup/codex-cloud-setup.sh`(환경의 **Setup script**)는 저장소를 연결한 Codex 환경용이다. 확인하지 않았다.
- 서브에이전트가 없으면 집필과 검수를 별도 패스로 나눈다. 검수 요청은 집필 때의 기억이 아니라 요청 프롬프트의 원고를 다시 읽고 답한다.
- 결과가 PR/브랜치로 남는 것은 코드 변경뿐이다. 원고는 원고 보관 지침대로 Drive 연결 도구로 남긴다.

## Grok봇

- Grok이 같은 컴퓨터에서 셸과 백그라운드 프로세스를 쓸 수 있어야 한다(채팅만 되는 Grok은 InkOS를 돌릴 수 없다).
- 첫 지시: "tools/inkos-agent-bridge/GROK.md와 AGENTS.md를 읽고 따라라. 먼저 `sh tools/setup-cloud.sh`를 실행해라."
- 서브에이전트가 셸을 못 쓰면 메인이 대신 `claim`/`reply`한다. 검수는 새 패스에서 원고를 다시 읽고 답한다.
- 로컬 컴퓨터라면 원고가 남아 있으므로 Drive 보관은 백업 용도다(원고 보관 지침대로 Grok의 Drive 연결 도구로).

## 알려진 제약

- 세션이 끝나면 작업이 멈춘다. 무인 백그라운드 집필기는 없다.
- 토큰 사용량은 0으로 보고된다(브리지가 에이전트의 토큰을 잴 수 없음).
- 클라우드 샌드박스에서는 `inkos-agent`가 InkOS 작업의 프록시 변수를 지운다(127.0.0.1에 닿기 위해). InkOS의 외부 기능(웹 검색, 원격 표지 API)은 그때 프록시 없이 동작한다.
