# 7-d 검증 — `unpack --force` 범위 제한, `--overwrite-work`와 자동 백업

2026-10-26, 브랜치 `claude/eeum-n0rsol`. 감독 [승인] 7-b 보완·7-c 스레드의 [지시] 7-d. 바꾼 코드는 `tools/novel-drive.py`뿐이다. 엔진·Studio는 그대로다.

## 원고로 보는 것 (엔진 코드에서 확인)

- 2.0 작품 폴더: `works/<id>/`(`workDirectory`). 장편 회차 원고는 `works/<id>/source/chapters/NNNN_<제목>.md`(`agents/writer.ts`의 `join(bookDir, "chapters")`, bookDir = `works/<id>/source`).
- 대본·설명 영상은 회차 폴더가 없고 `source/script.md`, `source/explainer-script.md` 같은 파일이다(test-7에서 확인). 그래서 `works/*/work.json`도 원고로 센다.
- 1.8 구조: `books/<id>/chapters/*.md`(`korean-language-policy.ts`가 아직 읽는 경로).

`WORK_PATTERNS = works/*/work.json, works/*/source/chapters/*.md, books/*/chapters/*.md`. `inkos init`만 한 프로젝트는 `.env .gitignore .node-version .nvmrc inkos.json radar/ works/(빈 폴더)`이므로 하나도 걸리지 않는다.
이 기준은 지시의 "회차 원고가 하나라도"보다 넓다. 회차를 아직 쓰지 않은 작품(설계만 끝난 장편, 대본)도 막는다. "방금 init만 한 빈 프로젝트에서만 통한다"에 맞춘 것이다.

## 동작

- 대상에 `inkos.json`이 없으면 전과 같다(그냥 푼다).
- 대상에 `inkos.json`이 있고 원고가 없을 때: 옵션이 없으면 전과 같이 거부(rc 1)하고, `--force`면 푼다.
- 원고가 있을 때: `--force`여도 exit 3으로 거부하고 아무것도 바꾸지 않는다. 메시지에 걸린 경로(최대 5개)와 "Stop and ask the user", `--overwrite-work`를 적는다.
- `--overwrite-work`: 먼저 대상 전체를 `pack`(전체 압축)으로 `<dest>.before-unpack-<UTC>.tar.xz`에 쓴다(lzma가 없으면 `.tar.gz`). 기존 백업은 덮지 않는다.
  그 경로와 "커밋하거나 올리지 말 것"을 출력한 뒤 푼다.
  - 전체 압축이므로 `.env`, 브리지 `runtime/`, `.inkos-drive-base`는 백업에 들어가지 않는다(원고 아님).
  - 압축본에 없는 파일은 지우지 않는다(전과 같음).
- 압축본이 깨졌거나 lzma 없이 xz면, 백업이나 쓰기 전에 멈춘다.
- OAuth `pull`에도 같은 규칙과 `--overwrite-work`를 넣었다.

## 시험 (`tools/tests/test_novel_drive.py` 38 → 47)

- 빈 init 폴더에 `--force`: 성공하고 백업은 없다.
- 원고가 있는 폴더(1화를 로컬에서 고치고 2화를 추가)에 `--force`: exit 3, 메시지에 `0002_새_회차.md`와 `--overwrite-work`가 있고, 모든 파일의 바이트가 그대로이며 백업도 없다.
- 회차 없이 대본만 있는 작품, 1.8 구조 `books/*/chapters`: 둘 다 exit 3.
- `--overwrite-work`: 대상 옆에 백업이 하나 생기고 출력에 그 경로가 있다. 백업 안의 1화(고친 것)와 2화가 원래 바이트와 같고, 그 뒤 압축본으로 덮였다.
- 옛 `novel-drive.py`로 같은 시험을 돌리면 5개가 FAIL이다(원고가 있는 폴더에 `--force`가 "unpacked 2 files"로 통과함).

실제 `inkos init` 프로젝트와 test-6 `--resume` 압축본으로 한 데모(같은 VM 안에서만):
```
$ unpack … novel --force   (방금 init한 프로젝트)
unpacked 46 files into <tmp>/novel                                   rc=0
$ unpack … novel --force   (다시: 이제 원고가 있음)
novel-drive: <tmp>/novel already holds work (works/test-6-murim-…/work.json, …/source/chapters/0001_붉은_끈_백일곱_번.md, …0002…, …0003…); nothing was changed. --force only overwrites a freshly initialised project. Stop and ask the user: --overwrite-work first packs the whole of …/novel to novel.before-unpack-<UTC>.tar.xz beside it, then overwrites
rc=3      0001 sha256 앞 16자: d93baf7138a134a9 → d93baf7138a134a9
$ unpack … novel --overwrite-work
backed up <tmp>/novel (4 work files) to …/novel.before-unpack-20261026-013627.tar.xz before overwriting; it holds the manuscripts, so do not commit or upload it
unpacked 46 files into <tmp>/novel                                   rc=0
백업 40,808바이트, 안의 회차 원고 3개
```

## 문서

- RUNTIME "작업 시작과 끝": `--force`는 그대로 둔다. 원고가 있으면 도구가 거부(exit 3)하므로 멈추고 사용자에게 묻는다. 덮기로 하면 `--overwrite-work`(백업은 커밋·업로드 금지).
- RUNTIME 보관 절 끝의 unpack 설명과 브리지 AGENTS.md도 같은 내용으로 고쳤다.

## 남은 점

기본 배치(`<저장소>/novel`)에서는 백업이 저장소 루트(`<저장소>/novel.before-unpack-….tar.xz`)에 생긴다. 원본 `.gitignore`에 걸리지 않아 `git status`에 untracked로 보인다(`git check-ignore`로 확인).
보고의 결정필요에 올렸다.

## 보완: 백업 위치 (감독 [승인] 7-d의 결정필요 답 (b))

- 대상이 git 작업 트리 안이면(`git -C <dest> rev-parse --show-toplevel` 성공) 백업은 `~/.inkos-ko-backup/unpack/<dest 이름>.before-unpack-<UTC>.tar.xz`에 둔다.
  git 밖이거나 git이 없으면 전처럼 대상 폴더 옆에 둔다.
- 출력에 한 줄을 더 적는다: `backup location: outside the git work tree <top>, so it cannot be committed` 또는 `backup location: beside it (not in a git work tree)`.
- exit 3 메시지도 두 위치를 함께 적는다.
- 시험 47 → 51:
  - git 밖이면 위치 줄이 나온다.
  - `git init`한 저장소 안의 `novel/`(`.gitignore`는 `*` 등 3줄)에 `--overwrite-work`를 쓰면, 백업이 가짜 HOME의 `~/.inkos-ko-backup/unpack/`에 하나 생긴다.
    출력에 저장소 경로가 나오고, 저장소 안에는 백업이 없으며 `git status --porcelain`은 전후 모두 비어 있다. 백업에는 2화 원고가 들어 있다.
- 이 저장소 안에서 한 데모(작품 폴더 `novel-7d-demo/`, `.gitignore` `*`, 데모 뒤 삭제):
```
$ unpack … novel-7d-demo --overwrite-work
backed up novel-7d-demo (4 work files) to <tmp>/home/.inkos-ko-backup/unpack/novel-7d-demo.before-unpack-20261026-015922.tar.xz before overwriting; it holds the manuscripts, so do not commit or upload it
backup location: outside the git work tree /home/user/inkos-ko, so it cannot be committed
unpacked 46 files into novel-7d-demo                          rc=0
$ git status --porcelain
 M tools/novel-drive.py
 M tools/tests/test_novel_drive.py          (작업 중인 코드 변경만. 작품 폴더와 백업은 보이지 않음)
```
- 문서: RUNTIME "작업 시작과 끝"·보관 절, 브리지 AGENTS.md의 백업 위치.

## 시험 수

프록시 변수 제거: core 757 / studio 307 / cli 101 = 1,165 통과. 브리지 38/38, Drive 47/47(+9), novel-brief 27/27, 설치 스크립트 50/50.
