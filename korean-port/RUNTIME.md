# 실행 환경 안내 (RUNTIME)

이 포크는 모델 API를 쓰지 않는다. InkOS의 모델 호출은 `tools/inkos-agent-bridge`(127.0.0.1:4568)로 가고, **에이전트 세션이 직접 답한다**.
세 실행 환경(Claude Code 클라우드, Codex 클라우드, Grok봇)은 같은 설치 스크립트와 같은 규칙(`tools/inkos-agent-bridge/AGENTS.md`)을 쓴다.

## 공통: 설치 한 번

```sh
sh tools/setup-cloud.sh            # 기본 작품 프로젝트: <저장소>/novel
```

스크립트가 하는 일:

1. Node 22.16 이상·python3 확인, pnpm이 없으면 설치, `pnpm install --frozen-lockfile && pnpm -r build`
2. `~/.local/bin/inkos` 실행기 생성(빌드 결과 `packages/cli/dist/index.js`에는 실행 권한이 없어서 래퍼를 둔다)
3. 작품 프로젝트가 없으면 `inkos init --lang ko`(OAuth 비밀값을 넣고 `--pull`을 주면 최신 보관본을 복원 — 위 원고 보관 지침의 사용자 확인을 먼저 받을 것)
4. 브리지 설치(`install.sh --project`), `~/.bashrc`에 `PATH`·`INKOS_BIN`·`INKOS_LOCALE=ko`·`INKOS_AGENT_PROJECT` 추가, `inkos-agent doctor`

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

## 원고 보관 지침 (모든 실행 환경)
- 작품 폴더와 원고는 공개 포크에 커밋하지 않는다.
- 회차 하나를 끝낼 때마다, 그리고 세션 끝에:
  python3 tools/novel-drive.py pack <작품 폴더> <작품ID>_<YYYYMMDD-HHMM>_<마지막 회차>화.tar.gz
  → 이 환경의 Google Drive 연결로 "Inkos ko" 폴더에 올리고, 올린 파일 이름을 사용자에게 보고한다.
- 압축본 업로드가 안 되면(크기 제한, 연결 오류 등): 회차 원고와 상태 파일만 텍스트로 올리거나, 사용자에게 파일로 넘긴다. 실패 사실을 보고에 적는다.
- 세션 시작: "Inkos ko"에서 그 작품의 가장 최근 압축본을 받아 unpack하기 전에, 파일 이름과 마지막 회차를 사용자에게 보여주고 확인받는다.
- 한 작품을 두 환경에서 동시에 작업하지 않는다.

"Inkos ko" 폴더 ID: `1FYkA9t5AiI3u31cL0uM8dSFjgf5LxnEU`. 각 실행 환경(Claude Code·Codex 클라우드, Grok봇)에는 각자 Google Drive 연결이 있다(2026-10-25 사용자 결정).
`pack`은 작품 프로젝트 전체(설정·원고·상태·스냅샷·작업 기록)를 tar.gz 하나로 묶고, `.env`·브리지 `runtime/`·`.inkos-drive-base`는 넣지 않는다.
받은 압축본은 `python3 tools/novel-drive.py unpack <압축본> <작품 폴더>`로 푼다(기존 프로젝트가 있으면 `--force`가 필요하다).

## 선택: OAuth 직접 동기화 (`novel-drive.py push`/`pull`)

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
- 세션이 오래 쉬면 컨테이너가 회수되어 진행 중인 작업과 브리지 요청이 사라진다. 그래서 원고 보관 지침대로 회차가 끝날 때마다 압축본을 Drive에 올린다.
- 작품 폴더를 `<저장소>/novel`에 두면 Claude 앱에서 원고 파일을 열어 볼 수 있다.

## Codex 클라우드

- 환경의 **Setup script**에 `tools/inkos-agent-bridge/setup/codex-cloud-setup.sh` 내용을 넣는다(설치는 setup 단계에서 인터넷으로, 작업 중에는 인터넷·모델 API 불필요).
  단, Drive 보관을 쓰려면 작업 중에도 `oauth2.googleapis.com`, `www.googleapis.com` 접속이 허용돼야 한다.
- Codex는 저장소 루트의 `AGENTS.md`를 읽는다. 작품 프로젝트에도 `install.sh`가 `AGENTS.md`를 복사한다. 첫 지시: "novel/AGENTS.md를 읽고 따라라."
- 서브에이전트가 없으면 집필과 검수를 별도 패스로 나눈다. 검수 요청은 집필 때의 기억이 아니라 요청 프롬프트의 원고를 다시 읽고 답한다.
- 결과가 PR/브랜치로 남는 것은 코드 변경뿐이다. 원고는 Drive `push`로 남긴다.

## Grok봇

- Grok이 같은 컴퓨터에서 셸과 백그라운드 프로세스를 쓸 수 있어야 한다(채팅만 되는 Grok은 InkOS를 돌릴 수 없다).
- 첫 지시: "tools/inkos-agent-bridge/GROK.md와 AGENTS.md를 읽고 따라라. 먼저 `sh tools/setup-cloud.sh`를 실행해라."
- 서브에이전트가 셸을 못 쓰면 메인이 대신 `claim`/`reply`한다. 검수는 새 패스에서 원고를 다시 읽고 답한다.
- 로컬 컴퓨터라면 원고가 남아 있으므로 Drive 보관은 백업 용도다(`push`만 주기적으로).

## 알려진 제약

- 세션이 끝나면 작업이 멈춘다. 무인 백그라운드 집필기는 없다.
- 토큰 사용량은 0으로 보고된다(브리지가 에이전트의 토큰을 잴 수 없음).
- 클라우드 샌드박스에서는 `inkos-agent`가 InkOS 작업의 프록시 변수를 지운다(127.0.0.1에 닿기 위해). InkOS의 외부 기능(웹 검색, 원격 표지 API)은 그때 프록시 없이 동작한다.
