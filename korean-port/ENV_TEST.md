# 실행 환경 시험 절차서 (Codex 클라우드 · Grok)

이 문서는 Codex 클라우드와 Grok봇이 그대로 따라 하는 시험 절차다. 사용자가 이 파일을 그 환경에 넘긴다.
목적은 한국어판이 그 환경에서 설치·실행·질문·보관까지 되는지 확인하는 것이다. 코드는 고치지 않는다.

지킬 것:
- API 키와 외부 모델 주소를 쓰지 않는다. 모델 호출은 브리지(`tools/inkos-agent-bridge`)로만 받고, 에이전트가 직접 답한다.
- 이 시험의 작품은 시험 작품이다. ID는 `test-env-<환경>`(예: `test-env-codex`, `test-env-grok`).
  시험 작품은 밖으로 내보내지 않는다(사용자에게 파일로 보내지 않음, Drive에 올리지 않음, 커밋하지 않음). 압축은 같은 환경 안의 복원 시험에만 쓴다.
- 브랜치: `claude/eeum-n0rsol`. 작품 폴더는 git 무시(`.gitignore`에 `*`) 상태로 둔다.
- 각 단계의 명령과 출력 원문(요약 말고)을 보고에 붙인다. 원고 본문은 몇 줄 이하로만 인용하고 분량·sha256으로 남긴다.

## 저장소 받기

Grok봇과 Codex 클라우드(기본: 저장소를 연결하지 않고 빈 `/workspace`에서 시작)는 작업 안에서 먼저 받는다.
저장소를 연결한 환경이면 이 단계를 건너뛰고 브랜치만 맞춘다(`git checkout claude/eeum-n0rsol`).

```sh
git clone -b claude/eeum-n0rsol https://github.com/tsk30304225-bot/inkos-ko && cd inkos-ko
```

## 0. 시작 기록

```sh
date -u; uname -a; git rev-parse --abbrev-ref HEAD; git log --oneline -1
```

## 기존 설치 확인 (1절 전에)

같은 컴퓨터에 이미 다른 설치(다른 클론의 `inkos`·`inkos-agent`, 떠 있는 브리지)가 있는지 먼저 본다.

```sh
ls -l ~/.local/bin/inkos* 2>&1
grep -n "inkos-ko setup" -A1 ~/.bashrc 2>&1
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep 4568 || echo "4568 포트 비어 있음"
curl -s --max-time 3 http://127.0.0.1:4568/health || echo "브리지 없음"
```

- `~/.local/bin/inkos*`가 있고 4568 포트도 쓰이고 있으면(둘 다) 멈추고 그 출력 원문을 보고한다. 사용자가 정할 일이다.
- 하나만 있으면 출력을 보고에 붙이고 1절로 간다. 다른 설치가 있으면 1절의 `setup-cloud.sh`가 무엇이 어디를 가리키는지 출력하고 **exit 3**으로 멈춘다(아무것도 바꾸지 않음). 그 출력도 그대로 보고한다.
- `/health`의 `"state"`는 그 브리지의 runtime 폴더다. 이 저장소의 `tools/inkos-agent-bridge/runtime`이 아니면 다른 설치의 브리지이고, `doctor`는 경고, `start`·`job start`는 exit 3으로 멈춘다.
  `"state"`가 없는 브리지(1.2.0 이전 설치)도 다른 설치로 본다.
- 사용자가 바꾸라고 하면 `sh tools/setup-cloud.sh --project test-env --replace`. 바꾸기 전에 `~/.local/bin/inkos`, `~/.local/bin/inkos-agent`, `~/.bashrc`(링크가 아닐 때)를 링크 그대로
  `~/.local/bin/.inkos-ko-backup/<UTC 시각>/`에 복사하고 `README`(무엇을 바꿨는지)와 `restore.sh`를 남긴다.
  되돌리기: `sh ~/.local/bin/.inkos-ko-backup/<UTC 시각>/restore.sh`(원래 없던 것은 지운다). 백업 폴더는 restore 뒤 지워도 된다. 다른 클론의 브리지는 그 클론에서 `inkos-agent stop`으로 끈다.
- 설치 스크립트는 링크를 따라 쓰지 않는다. 임시 파일에 쓰고 이름을 바꿔 넣으므로 링크 자체가 바뀌고, 링크가 가리키던 파일은 그대로다.

## 1. 설치

```sh
sh tools/setup-cloud.sh --project test-env      # 작품 프로젝트 폴더: <저장소>/test-env
```

- Codex 클라우드도 작업 안에서 위 명령으로 설치한다. `tools/inkos-agent-bridge/setup/codex-cloud-setup.sh`(Setup script)는 저장소를 연결한 Codex 환경용이고 확인하지 않았다.
- 확인: `node -v`(22.16 이상. node 24는 Codex에서 확인(v24.19.0)), `inkos --version`, `ls test-env/AGENTS.md`,
  `cat test-env/.gitignore`(3줄: `*`, `runtime/`, `inkos.pre-agent.json`), `git status --short`에 `test-env`가 없어야 한다.
- pnpm은 lockfile의 9.15.9로 고정한다. setup은 `tools/pnpm-pin/pnpm`(shim)을 PATH 앞에 두고 install·build를 돌린다. 패키지 스크립트 안의 `pnpm` 호출도 shim을 탄다.
  설치된 pnpm이 다른 버전이면 `corepack pnpm@9.15.9`, 그것도 안 되면 `npx -y pnpm@9.15.9`로 실행한다. 다른 pnpm이 만든 `node_modules`는 확인 질문 없이 다시 설치한다.
  출력의 `[setup] pnpm: 9.15.9 via '…' (installed pnpm: …)` 줄을 보고에 붙인다.
- setup은 `~/.bashrc` 끝에 2줄을 덧붙인다: `# inkos-ko setup` 줄과 그다음 `export PATH=… INKOS_BIN=… INKOS_LOCALE=ko INKOS_AGENT_PROJECT=…` 줄.
  같은 설치로 다시 돌리면 그 2줄을 새로 바꿔 쓸 뿐 늘지 않는다. 파일 권한은 그대로 둔다. 되돌리기: 그 2줄을 지운다(`--replace`였다면 `restore.sh`가 원래 `~/.bashrc`를 되살린다).
  `~/.bashrc`가 링크(dotfiles 관리 도구 등)이면 고치지 않고 그 2줄을 출력한다(`a link, left unchanged`). 사용자가 직접 넣는다. 나머지 설치는 계속된다.
- 설치 중 인터넷이 막혀 실패하면 실패 출력과 막힌 주소를 그대로 보고하고 멈춘다.

## 2. doctor

```sh
export PATH="$HOME/.local/bin:$PATH" INKOS_BIN=$HOME/.local/bin/inkos INKOS_LOCALE=ko INKOS_AGENT_PROJECT=$PWD/test-env
# 명령마다 새 셸이 열리는 환경(Codex 등)에서는 이 export가 다음 명령에 이어지지 않는다. 7-f부터는 없어도 된다:
# inkos-agent가 setup이 기록한 tools/inkos-agent-bridge/runtime/project와 ~/.local/bin/inkos를 찾고,
# CLI 언어는 runtime/locale(ko)에서 넣는다(셸에 INKOS_LOCALE이 있으면 그것이 먼저).
tools/inkos-agent-bridge/inkos-agent doctor
tools/inkos-agent-bridge/inkos-agent start
```

- `modelOverrides … bypasses the bridge`가 나오면 멈추고 사용자에게 묻는다(실제 API로 나가는 설정).
- `bridge ready: http://127.0.0.1:4568/v1`이 나와야 한다.

## 3. lzma 확인

```sh
python3 -c "import lzma; print('lzma ok')"
command -v xz || echo "xz 실행 파일 없음"
```

- `lzma ok`가 아니면 그대로 보고한다. 그 환경의 압축본은 `.tar.gz`가 된다(5절에서 확인).

## 4. 시험 작품 1화와 대화형 질문 1개

`tools/inkos-agent-bridge/AGENTS.md`의 "Author choices"와 `korean-port/RUNTIME.md`의 "작가 선택"을 따른다. 이 시험에서는 에이전트가 작가 역할도 맡고, 실제 사용자에게는 묻지 않는다.

1. 인터뷰(질문 원문을 보고에 그대로 붙인다):
   ```sh
   mkdir -p test-env/briefs
   python3 tools/novel-brief.py interview test-env/briefs/brief.md
   python3 tools/novel-brief.py interview test-env/briefs/brief.md --answer 1=1 --answer 2=1 --answer 3=1 --answer 4=1 --answer 5=1 --answer 6=2 --answer 7=1
   ```
   답은 첫 명령이 출력한 질문 번호를 보고 정한다. 위 `--answer`는 질문이 7개일 때의 예시다(질문 수가 다르면 그 번호에 맞춘다).
   마지막 출력이 `물을 항목 없음`이어야 한다.
2. 작품 만들기(제목이 `test-env-…`로 시작해야 ID가 `test-env-…`가 된다):
   ```sh
   JOB=$(tools/inkos-agent-bridge/inkos-agent job start -- book create --title "test-env-<환경> 시험" --genre light-martial --target-chapters 30 --chapter-words 3000 --brief $PWD/test-env/briefs/brief.md --lang ko)
   tools/inkos-agent-bridge/inkos-agent wait --job $JOB --timeout 90      # EVENT: request → 답하기, job-finished → 끝
   ```
   요청에 답하는 법은 브리지 `AGENTS.md` 3절. 서브에이전트가 있으면 writer와 reviewer를 나누고, 없으면 별도 패스로 나눈다.
3. 설계 후 질문(대화형 질문 1개 이상):
   ```sh
   W=test-env/works/<만들어진 ID>
   python3 tools/novel-drive.py pack test-env /tmp/env-before-question --resume     # 질문 전 보관(같은 환경 안에서만)
   python3 tools/novel-brief.py interview --work $W                                 # 질문 원문을 보고에 붙인다
   python3 tools/novel-brief.py interview --work $W --answer 1=1                    # 고른 답을 보고에 적는다
   ```
   물을 항목이 없으면 그 출력을 그대로 붙이고 다음으로 간다.
4. 1화 브리핑과 1화:
   ```sh
   python3 tools/novel-brief.py next $W
   python3 tools/novel-brief.py direct $W --choice 1 -o test-env/ch1.txt
   JOB=$(tools/inkos-agent-bridge/inkos-agent job start -- write next <ID> --count 1 --context-file $PWD/test-env/ch1.txt)
   tools/inkos-agent-bridge/inkos-agent wait --job $JOB --timeout 90
   ```
5. 확인:
   ```sh
   tools/inkos-agent-bridge/inkos-agent run -- status <ID>
   cat $W/source/story/state/manifest.json                  # lastAppliedChapter: 1
   cat $W/source/story/author_directions.md                 # "## 1화" 항목 = test-env/ch1.txt
   # 프롬프트에 --context 원문이 들어갔는가: 첫 줄의 앞 20자(글자 단위)를 담은 요청 프롬프트를 센다
   python3 -c "import glob,sys; head=open(sys.argv[1],encoding='utf-8').read().splitlines()[0][:20]; hits=[p for p in glob.glob('tools/inkos-agent-bridge/runtime/requests/*/prompt.md') if head in open(p,encoding='utf-8').read()]; print(repr(head), len(hits)); print(*hits, sep='\n')" test-env/ch1.txt
   ```
   - 1화 출력에 `경고: 1화 원고는 저장됐지만 상태…`가 있으면 상태 미반영이다. 그대로 보고한다.
   - job 로그(`inkos-agent job log $JOB`)에 영어 진행 문구(`Stage:`)나 중국어 줄이 있으면 그 줄을 보고한다.

## 5. 압축과 복원

```sh
python3 tools/novel-drive.py pack test-env /tmp/test-env-<환경>_$(date -u +%Y%m%d-%H%M)_1화 --resume
ls -l /tmp/test-env-<환경>_*; sha256sum /tmp/test-env-<환경>_*
mkdir -p /tmp/env-restore && python3 tools/novel-drive.py unpack /tmp/test-env-<환경>_*_1화.tar.* /tmp/env-restore
INKOS_AGENT_PROJECT=/tmp/env-restore tools/inkos-agent-bridge/inkos-agent run -- status <ID>    # 원래 status와 같아야 한다(경로만 다름)
python3 tools/novel-drive.py split /tmp/test-env-<환경>_*_1화.tar.* /tmp/env-parts
python3 tools/novel-drive.py join /tmp/env-parts/*.parts.json -o /tmp/env-joined
cmp /tmp/env-joined /tmp/test-env-<환경>_*_1화.tar.* && echo "join 일치"
```

- 압축본 이름이 `.tar.xz`인지 `.tar.gz`인지 적는다(lzma가 없으면 경고와 함께 `.tar.gz`).
- Drive에는 올리지 않는다(시험 작품). Drive 연결 도구가 있는지만 적는다(도구 이름, 이 시험에서 쓰지 않음).

## 6. 시험 실행

```sh
env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy PATH="$PWD/tools/pnpm-pin:$PATH" pnpm -r --no-bail test 2>&1 | grep -E "Tests |FAIL"
python3 -I tools/inkos-agent-bridge/tests/test_bridge.py | tail -1
python3 -I tools/inkos-agent-bridge/tests/test_project_file.py | tail -1
python3 -I tools/tests/test_novel_drive.py | tail -1
python3 -I tools/tests/test_novel_brief.py | tail -1
python3 -I tools/tests/test_setup_scripts.py | tail -1
```

실패 기준: 기준선은 core 757 · studio 307 · cli 101 = 1,165 통과, 브리지 38/38, 브리지 프로젝트 기록 19/19, Drive 51/51, novel-brief 27/27, 설치 스크립트 58/58(Claude Code, 7-f 보완).
통과 수가 이보다 적거나 실패가 하나라도 있으면 실패다. 실패한 시험 이름과 출력 원문을 보고하고, 고치지 않는다.

## 7. 보고 양식

`korean-port/OPERATING_RULES.md`의 `[보고]` 양식을 쓰고, 머리말은 `[코덱스]` 또는 `[그록]`으로 한다.

```
[코덱스] [보고] 환경 시험 / 브랜치 claude/eeum-n0rsol / 커밋 <해시>
한 일: 설치, doctor, lzma, 시험 작품 1화, 대화형 질문, 압축·복원, 시험
증거:
- 0~1: node -v, inkos --version, `[setup] pnpm:` 줄, .gitignore 3줄, git status(작품 폴더 없음)
- 2: doctor 출력 원문, bridge ready
- 3: lzma ok / 없음, xz 실행 파일 유무
- 4: 인터뷰·설계 후 질문 원문과 고른 답, 1화 제목·분량·감사 의견 수, lastAppliedChapter, --context 원문이 들어간 프롬프트 줄, 영어·중국어 줄 유무
- 5: 압축본 이름·크기·sha256, 복원 뒤 status 비교, join 일치
- 기존 설치 확인: ls·포트·/health 출력 원문, setup의 exit 3 출력(있었다면)
- 6: 시험 수(core / studio / cli, 브리지, Drive, novel-brief, 설치 스크립트)
- 브리지 요청 수와 상태(delivered / failed / abandoned)
바뀐 파일: 없음(코드 변경 없음)
깨질 수 있는 것: (이 환경에서만 다르게 동작한 것)
확인하지 못한 것: (막힌 단계와 이유)
결정필요: (없으면 "없음")
```
