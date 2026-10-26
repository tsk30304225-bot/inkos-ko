# 7-b 검증 — 설치 안전성

2026-10-26, 브랜치 `claude/eeum-n0rsol`. 엔진·Studio는 바꾸지 않았다. 원본 `package.json`도 그대로다(`packageManager` 없음).

배경(Grok·Codex 환경 시험, e99aa31):
- Grok: `setup-cloud.sh`의 `cat > ~/.local/bin/inkos`가 링크를 따라가 다른 클론의 `packages/cli/dist/index.js`를 82바이트 런처로 덮어씀(복구됨). 예전 설치의 브리지가 4568에 떠 있었는데 doctor는 "bridge: up"만 보고함.
- Codex: 미리 깔린 pnpm 11.25.0 → `ERR_PNPM_LOCKFILE_CONFIG_MISMATCH`. 9.15.9를 PATH 앞에 두자 node 24.19.0에서 전부 통과.

## 0. 링크를 따라 쓰지 않음

`tools/setup-cloud.sh`, `tools/inkos-agent-bridge/install.sh`: `~/.local/bin/inkos`, `~/.bashrc`, 작품 프로젝트의 `AGENTS.md`·`CLAUDE.md`·`GROK.md`·`.claude/agents/*`·`.gitignore`를
같은 폴더의 임시 파일에 쓰고 `os.replace`(rename)로 바꿔 넣는다. `inkos-agent` 링크도 임시 링크를 만들어 rename한다. rename은 경로 자체를 바꾸므로 링크가 가리키던 파일은 건드리지 않는다.

시험 `tools/tests/test_setup_scripts.py`(새 파일, 44/44)는 임시 HOME에서 돌고, 대상 자리에 다른 파일을 가리키는 링크를 두고 실행한 뒤 링크 대상의 바이트를 비교한다.
옛 스크립트(7-a)로 같은 시험을 돌리면 `link target bytes unchanged`가 FAIL — Grok 사고가 재현된다.

## 1. 이미 있는 설치 → exit 3, `--replace`, 되돌리기

바꾸기 전에 `inkos`, `inkos-agent`, `~/.bashrc`의 `# inkos-ko setup` 블록을 모두 확인한다. 하나라도 다른 설치의 것이면(링크이거나 내용이 다른 `inkos`, 이 브리지가 아닌 `inkos-agent`,
링크인 `~/.bashrc`, 다른 프로젝트를 가리키는 블록) 목록을 출력하고 exit 3. 같은 설치로 다시 돌리면 exit 0이고 `~/.bashrc` 블록은 1개 그대로다.

```
before: 2f48c1333f32e892            (다른 클론 dist/index.js의 sha256 앞 16자)
$ sh tools/setup-cloud.sh --project P --no-build
existing installation found (this setup: /home/user/inkos-ko, project …/demo/project):
  …/home/.local/bin/inkos -> …/other/packages/cli/dist/index.js
  …/home/.local/bin/inkos-agent -> …/other/inkos-agent
nothing was changed. Rerun with --replace to back these up and replace them.
rc=3
$ … --replace
[setup] backed up to …/home/.local/bin/.inkos-ko-backup/20261026-010741 (undo: sh …/.inkos-ko-backup/20261026-010741/restore.sh)
[setup] project: …/demo/project
after: 2f48c1333f32e892             (그대로)
~/.local/bin:  inkos (74바이트 파일, 런처)   inkos-agent -> /home/user/inkos-ko/tools/inkos-agent-bridge/inkos-agent
백업 폴더:     README  inkos -> …/other/…/index.js  inkos-agent -> …/other/inkos-agent  restore.sh
$ sh restore.sh
rc=0
~/.local/bin:  inkos -> …/other/packages/cli/dist/index.js   inkos-agent -> …/other/inkos-agent
```

- 백업은 `cp -P`(링크는 링크 그대로). `restore.sh`는 각 항목을 지우고 백업을 되돌려 놓으며, 원래 없던 항목(`inkos`, `~/.bashrc`)은 지운다.
  이 데모에서 이 마지막 경우가 빠져 있던 것을 발견해 고치고 시험을 추가했다(43 → 44).
- `setup-cloud.sh --replace`가 부르는 `install.sh --replace`는 같은 백업 폴더(`INKOS_KO_BACKUP_DIR`)를 쓴다. `install.sh`만 따로 쓸 때는 자기 백업 폴더와 `restore.sh`를 만든다.
- 시험이 확인하는 것: `inkos-agent`만 다른 설치일 때 `inkos`도 만들지 않음, 다른 클론의 블록이 있는 `~/.bashrc`는 바이트 그대로, 링크인 `~/.bashrc`를 `--replace`하면 원래 줄을 유지한 파일이 되고
  링크 대상은 그대로, 복원 뒤에도 세 대상의 바이트 그대로, `install.sh`의 프로젝트 파일 링크(`AGENTS.md`, `.gitignore`)도 같은 방식.

## 2. 다른 설치의 브리지

`/health`에 `"state"`(runtime 폴더)와 `"root"`를 넣었다. 포트의 브리지가 보고하는 `state`가 이 설치의 runtime과 다르거나 없으면(1.2.0 이전 브리지) 다른 설치로 본다.
`doctor`는 경고(rc 1), `start`·`job start`는 exit 3(작업 폴더도 만들지 않음). `stop`은 자기 runtime의 pid 파일만 보므로 남의 브리지를 끄지 않는다.

실제 4568 브리지에 다른 runtime으로 붙여 본 출력:
```
$ INKOS_AGENT_STATE=<다른 runtime> inkos-agent doctor
bridge       : up at http://127.0.0.1:4568/v1, but NOT this installation's
WARNING      : port 4568 is served by another bridge (pid 1843, runtime /home/user/inkos-ko/tools/inkos-agent-bridge/runtime); this installation's runtime is …/other-state. Stop that bridge (its own `inkos-agent stop`) or set INKOS_AGENT_PORT to a free port
rc=1
$ … start
error: port 4568 is served by another bridge (pid 1843, …)
rc=3
$ … job start -- status
error: port 4568 is served by another bridge (pid 1843, …)
rc=3
```
브리지 시험 33 → 38(위 다섯 가지).

## 4. pnpm 9.15.9 고정

설치된 pnpm이 9.15.9면 그대로, 아니면 `corepack pnpm@9.15.9`(동작 확인 후), 안 되면 `npx -y pnpm@9.15.9`. 고른 것을 `[setup] pnpm: <버전> via '<명령>' (installed pnpm: <버전>)`으로 출력한다.
시험은 PATH 앞에 가짜 `pnpm`(11.0.0 보고)·`corepack`·`npx`를 두고 호출 기록을 본다:
- 11.0.0 + corepack 동작 → `pnpm: 9.15.9 via 'corepack pnpm@9.15.9' (installed pnpm: 11.0.0)`, `corepack pnpm@9.15.9 install --frozen-lockfile`·`-r build`, 설치된 pnpm은 `--version`만.
- 11.0.0 + corepack 실패 → `npx -y pnpm@9.15.9`로 install·build.
- 9.15.9 설치 → `pnpm` 그대로, corepack·npx 호출 없음.

이 컨테이너의 pnpm은 10.28.0이다(이번 세션에 실제 빌드는 다시 하지 않았다).

## 3·5. 문서

- `ENV_TEST.md`: 1절 앞 "기존 설치 확인"(`ls -l ~/.local/bin/inkos*`, `~/.bashrc` 블록, 4568 포트, `/health`). 둘 다 있으면 멈추고 보고, `--replace`와 `restore.sh`.
  1절: node 24는 "Codex에서 확인(v24.19.0)", `.gitignore` 3줄(`*`, `runtime/`, `inkos.pre-agent.json`), `[setup] pnpm:` 줄, `~/.bashrc` 2줄과 되돌리기. 6절 기준선 갱신, 설치 스크립트 시험 추가.
- `RUNTIME.md` 설치 절: pnpm 고정, node 24, 기존 설치·exit 3·`--replace`·되돌리기, 링크 안전 쓰기, 다른 브리지.
- 브리지 `AGENTS.md` Environment notes: 한 컴퓨터에 한 설치, exit 3, 다른 브리지는 보고만.

## 시험

프록시 변수 제거: core 757 / studio 307 / cli 101 = 1,165 통과. 브리지 38/38, Drive 38/38, novel-brief 27/27, 설치 스크립트 44/44.
