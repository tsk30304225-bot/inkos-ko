# 7-c 검증 — Codex 기본 경로와 작업 시작·끝 순서

2026-10-26, 브랜치 `claude/eeum-n0rsol`. 감독 [승인] 7-b 스레드의 "작은 보완 1~3"과 10:24 [지시 추가] 4~6을 묶은 단계.
코드 변경은 없다(`codex-cloud-setup.sh`는 머리 주석만). 엔진·Studio는 그대로다.

## 보완 1~3 (7-b 승인 스레드)

이미 `f0bfe09`(커밋 제목 `(stage 7-b)`)에 들어가 푸시됐다. 근거는 `stage-7b.md` "승인 후 보완".
1. 설치 스크립트 시험이 빌드 없이 돈다(임시 저장소 + 가짜 `dist/index.js`, `tools/`만 있는 복사본에서 50/50).
2. 링크인 `~/.bashrc`는 `--replace`여도 고치지 않고, 넣을 2줄을 출력한다.
3. `~/.bashrc`와 프로젝트 `.gitignore`의 권한을 유지한다.

## 4. Codex 문서 기본 경로

사용자의 Codex 실행 방식(10:24 [메모]): 저장소를 연결하지 않고 빈 `/workspace`에서 시작한다. 브랜치·Setup script 칸을 쓸 수 없고, 작업 단계 인터넷은 열려 있다.
- RUNTIME "Codex 클라우드": 기본은 작업 안에서 `git clone -b claude/eeum-n0rsol …` → `sh tools/setup-cloud.sh`. 첫 지시 예를 clone부터로 바꿨다.
- ENV_TEST "저장소 받기"와 1절: Codex도 작업 안에서 받는다.
- 브리지 AGENTS.md Environment notes: 같은 내용.
- `setup/codex-cloud-setup.sh`: 머리 주석과 문서에서 "저장소를 연결한 Codex 환경용, 확인하지 않음"으로 바꿨다.

## 5. 작업 공간이 남지 않는 환경의 작업 시작·끝

RUNTIME 원고 보관 지침에 "작업 시작과 끝" 절을 넣었다.
- 시작: clone → setup → Drive 'Inkos ko'의 가장 늦은 압축본(확인받기) → `unpack <압축본> novel --force` → `status` → 이어 쓰기.
- 끝: 압축본을 올린다.
- Grok과 Claude Code 클라우드도 VM이 회수되면 같은 순서를 따른다.

setup이 먼저 빈 `novel/`을 만들기 때문에 `unpack`은 `--force`가 필요하다. 지침에는 "방금 만든 빈 프로젝트에만"이라고 적었다.
같은 VM 안에서 시험 작품으로 이 순서를 확인했다(밖으로 내보내지 않음):
```
$ pack test-6 … --resume
packed test-6 -> …/test-6_resume.tar.xz (38628 bytes)
$ inkos init novel --lang ko      → .env .gitignore .node-version .nvmrc inkos.json radar/ works/
$ unpack … novel
novel-drive: …/novel already contains a project; pass --force to overwrite files from the archive   (rc=1)
$ unpack … novel --force
unpacked 46 files into …/novel
$ diff <(status test-6) <(status novel)   (경로 줄 제외)
status 같음 (경로 줄 제외, 10줄)
```

## 6. 백업 폴더

RUNTIME, ENV_TEST, 브리지 AGENTS에 한 줄씩 넣었다: "백업 폴더는 restore 뒤에도 남는다. restore 뒤에는 지워도 된다."

## 시험

프록시 변수 제거: core 757 / studio 307 / cli 101 = 1,165 통과. 브리지 38/38, Drive 38/38, novel-brief 27/27, 설치 스크립트 50/50.
`sh -n tools/inkos-agent-bridge/setup/codex-cloud-setup.sh` 통과.
