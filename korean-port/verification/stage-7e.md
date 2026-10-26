# 7-e 검증 — 안쪽 pnpm 호출까지 9.15.9 고정

2026-10-26, 브랜치 `claude/eeum-n0rsol`. 감독 11:02 [지시] 7-e(Codex 재확인 실패 원인). 원본 `package.json`과 패키지 스크립트는 고치지 않았다. 엔진·Studio도 그대로다.

## 원인

- 7-b의 고정은 setup이 직접 부르는 바깥 명령만 9.15.9로 돌렸다. Codex에서도 `[setup] pnpm: 9.15.9 via 'corepack pnpm@9.15.9'`로 나왔다.
- 그런데 `packages/cli/package.json`의 스크립트가 `pnpm`을 다시 부른다:
  - `prebuild`, `pretypecheck`: `pnpm run prepare:workspace-core`
  - `prepare:workspace-core`: `pnpm --filter @actalk/inkos-core build`
  - `pretest`, `pretest:flows`: `pnpm run build`
- 이 안쪽 `pnpm`은 PATH에서 찾는다. corepack이나 npx로 띄운 pnpm은 자기 자신을 PATH에 넣지 않으므로, PATH의 pnpm 11이 돌았다.

### `prepare:workspace-core`가 하는 일

CLI를 빌드하거나 타입 검사하기 전에 core 패키지(`@actalk/inkos-core`)를 먼저 빌드해 `dist/`를 만든다. CLI는 workspace 링크로 core를 가져오고, 그 진입점이 `dist`를 가리키기 때문이다.
이 스크립트는 `pnpm install`을 부르지 않는다.

### 빌드 중에 install이 일어난 이유

pnpm 11 쪽 동작이다. 스크립트를 실행하기 전에 pnpm 11이 스스로 의존성 단계를 거친다.
- 작은 작업공간(패키지 a, b; b의 `prebuild` → `pnpm run prep` → `pnpm --filter a build`)에서 `npx -y pnpm@11`(11.28.8)로 `run build`만 실행했다.
  pnpm 11은 스크립트 전에 의존성 단계를 거쳤고, `node_modules` 상태 파일의 `packageManager`를 `pnpm@11.28.8`로 다시 썼다.
- 저장소의 `node_modules`처럼 다른 pnpm이 만든 것이면, 이 단계에서 "modules directories will be removed and reinstalled" 확인을 묻는다.
  TTY가 없으면 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`(Codex)가 나고, TTY가 있으면 yes로 넘어가 pnpm 11 트리로 다시 설치된다(Grok).
- 정확한 설정 이름(pnpm 11의 실행 전 의존성 확인)은 문서로 확인하지 않았다.

## 한 일

1. `tools/pnpm-pin/pnpm`(새 파일, 755, 추적됨).
   - PATH에서 자기 자신(표식 줄 `inkos-ko pnpm-pin shim`이 있는 파일, 복사본 포함)을 뺀 실제 `pnpm`이 9.15.9면 그것을 쓴다.
     아니면 `corepack pnpm@9.15.9`(`COREPACK_ENABLE_DOWNLOAD_PROMPT=0`), 그것도 안 되면 `npx -y pnpm@9.15.9`.
   - 고른 것을 `INKOS_PNPM_PIN_CMD`로 넘겨, 안쪽 호출은 다시 고르지 않고 같은 것을 쓴다.
   - 재귀 방지: 자기 자신은 후보에서 뺀다. 중첩이 20단을 넘으면 exit 70.
   - `INKOS_PNPM_PIN_SHOW=1`이면 고른 것만 출력한다.
2. `tools/setup-cloud.sh`
   - install과 build만 `PATH="$REPO/tools/pnpm-pin:$PATH"`로 실행한다. 전역 PATH, `~/.local/bin`, `~/.bashrc`에는 넣지 않는다.
   - `[setup] pnpm: <버전> via '<shim이 고른 것>' (installed pnpm: <버전>)`을 출력한다. 고른 것이 9.15.9를 보고하지 않으면 멈춘다.
   - install에 `--config.confirm-modules-purge=false`를 붙인다. 다른 pnpm이 만든 `node_modules`는 묻지 않고 다시 설치한다(지울 대상은 다시 만들 수 있는 `node_modules`뿐).
     이 VM에서 확인한 것: 옵션 없이는 확인 질문을 띄운 채 아무것도 설치하지 않고 rc 0으로 끝났다.
3. 문서
   - ENV_TEST 6절과 RUNTIME 시험 명령: `PATH="$PWD/tools/pnpm-pin:$PATH" pnpm -r --no-bail test`.
   - RUNTIME 설치 1번과 ENV_TEST 1절에 shim과 안쪽 호출을 적었다. PLAN 기본 사실 한 줄.

## 시험

`tools/tests/test_setup_scripts.py` 50 → 56. 가짜 pnpm 11을 PATH 앞에 둔다. 이 pnpm은 `--version`에만 답하고, 다른 호출은 기록을 남기고 실패한다.
corepack/npx 뒤의 가짜 pnpm 9.15.9는 실제 스크립트처럼 안쪽 호출을 PATH로 한다(`-r build` → `run prepare:workspace-core` → `--filter @actalk/inkos-core build`, `-r --no-bail test` → `run build`).
- corepack 경로: install(`--config.confirm-modules-purge=false`), build, 안쪽 호출 두 개, 문서의 시험 명령과 그 안쪽 `run build`가 모두 `corepack pnpm@9.15.9`로 돈다.
  pnpm 11은 `--version` 말고는 한 번도 불리지 않는다.
- corepack이 안 될 때: 모두 `npx -y pnpm@9.15.9`로 돈다. 9.15.9가 설치돼 있을 때: 그 경로를 그대로 쓰고 corepack·npx는 부르지 않는다.
- `~/.local/bin`에는 `inkos`, `inkos-agent`만 있다. `~/.bashrc`에 pnpm-pin이 없다.
- shim 복사본이 PATH에 있어도 건너뛴다(재귀 없음). 중첩 21단에서 exit 70.
- 옛 setup(7-d)으로 같은 시험을 돌리면 5개가 FAIL이다. 호출 기록에 `pnpm11 run prepare:workspace-core`가 남는데, Codex 실패와 같은 자리다.

### 이 VM에서 실제로

설치된 pnpm은 10.28.0(`/opt/node22/bin/pnpm`)이다. 이 VM의 `node_modules`도 그동안 pnpm 10.28.0이 만든 것이었다(`.modules.yaml`의 `packageManager: pnpm@10.28.0`).
그래서 7-e 전의 기준선 시험(1,165)은 pnpm 10 트리 위에서 돈 것이다. overrides 대상(`@mariozechner/pi-ai`, `pi-agent-core`)은 그때도 lockfile과 같은 0.67.1이었다.
- shim으로 다시 설치: `PATH=tools/pnpm-pin:… pnpm install --frozen-lockfile --config.confirm-modules-purge=false` → "Done in 11.3s using pnpm v9.15.9", `packageManager: pnpm@9.15.9`, pi-ai 0.67.1.
- 설치된 pnpm 10.28.0 앞에 기록용 래퍼를 두고(PATH = shim, 래퍼, 나머지) 실행했다.
  - `pnpm --filter @actalk/inkos-cli build`: rc 0.
  - 문서의 시험 명령: core 757 / studio 307 / cli 101 통과.
  - 시험 로그에 안쪽 호출이 보인다: `packages/cli pretest$ pnpm run build` → `prebuild` → `pnpm run prepare:workspace-core` → `pnpm --filter @actalk/inkos-core build`.
  - 래퍼 기록: `installed-pnpm --version` 2번뿐(shim이 바깥 호출에서 버전을 본 것). 안쪽 호출은 한 번도 설치된 pnpm에 닿지 않았다.

시험 수(pnpm 9.15.9 트리, 프록시 변수 제거): core 757 / studio 307 / cli 101 = 1,165 통과. 브리지 38/38, Drive 51/51, novel-brief 27/27, 설치 스크립트 56/56.
