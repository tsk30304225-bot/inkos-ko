# InkOS 한국어판 포크 계획 (2.0 기준)

이 문서가 작업의 기준이다. 세션이 바뀌어도 여기서 이어간다. 단계를 끝낼 때마다
맨 아래 "진행 기록"에 날짜·커밋·검증 결과를 추가하고, 결정이 바뀌면 "결정 사항"을 고친다.

## 목표

InkOS 2.0(원본 `Narcooo/inkos` master, `53adac4e` 시점)을 한국어 소설·한국 웹소설에 맞게 고친
독립 포크를 만든다. **실행 환경은 API가 아니라 에이전트 세션이다: Claude Code(클라우드), Codex(클라우드),
Grok봇(서브에이전트 사용 가능).** 셋 다 휴대폰에서 시작·확인할 수 있어야 한다. 성공 기준은 하나다: **API 키 없이, Claude Code 세션이 모델 역할을 하여
`inkos book create`와 `inkos write next`로 한국어 장편을 실제로 써내고, 상태 파일·복선·스냅샷이
한국어로 일관되게 유지되는 것.** 대상 장르·작품 유형은 아래 "장르와 작품 유형 범위"를 따른다.

## 장르와 작품 유형 범위 (2026-10-25 사용자 지정)

| 구분 | 대상 | 2.0에서 얹을 곳 | 참고 예시(장르 감각용) |
|---|---|---|---|
| 장편 소설 | 한국 라이트 무협 | `longform-novel` 프로필 + 한국어 장르 스킬 | 화산귀환 |
| 장편 소설 | 판타지 | 같음 | — |
| 장편 소설 | 현대판타지 | 같음 | 용사가 돌아왔다 |
| 대본 | 드라마 대본 | 기존 `script` 프로필 + 한국어 `inkos-script-writing` | — |
| 대본 | 설명형 영상 대본 (사용자의 AI 비디오 스튜디오용) | **새 작업 프로필** `explainer-script` + 새 스킬 | — |

참고 예시는 "그 장르의 독자가 무엇을 기대하는가"를 잡기 위한 기준점이다. 스킬과 references에 그 작품의
이름·인물·설정·장면 순서·고유한 조합을 옮기지 않는다(원본 2.0 스킬의 "Do not reproduce source wording,
names, scene order, or signature combinations" 원칙을 그대로 지킨다). 작품에 대한 사실 설명이 필요하면
공개 자료로 확인한 것만 쓰고 출처를 남긴다.

## 출발점에 대해 알고 있는 사실 (2026-10-25 조사)

- 원본 2.0의 언어는 `zh`/`en`뿐이다. 중국어가 들어간 줄: core 970줄, cli 192줄, studio 1,261줄.
  core 쪽 상위 파일: `agents/script-storyboard.ts`(84), `llm/provider.ts`(72, 대부분 오류문),
  `pipeline/runner.ts`(59), `harness/system-prompt.ts`(32), `prompts/short-fiction.ts`(30),
  `forecast/render.ts`(29), `agents/architect.ts`(29), `agents/writer.ts`(20).
- 집필 방법론은 코드가 아니라 `packages/core/skills/*/SKILL.md`(영어 21개)와 `references/*.md`에 있다.
  핵심: `inkos-long-writing`(references 4개), `inkos-story-review`(review-matrix.md),
  `inkos-story-deslop`(semantic-cleanup.md), `inkos-short-writing`.
- 스킬은 같은 ID로 덮어쓸 수 있다. 탐색 위치(`packages/core/src/skills/external-loader.ts`):
  `$INKOS_SKILL_DIRS`, `~/.openclaw/skills`, `~/.agents/skills`, `<project>/.agents/skills`, `<project>/skills`.
  우선순위(나중 것이 이기는지)는 0단계에서 코드와 테스트로 확인한다.
- 2.0에는 1.8의 결정론적 검사기(post-write-validator, ai-tells, hook-ledger-validator,
  long-span-fatigue)가 없다. 검수는 점수·반려 없이 근거 있는 관찰만 남긴다(`skills/SKILL.md` Core contract).
  → 1.8에서 확인한 "80점 미달 반려 → 재생성", "수정 채택 기준(strict)" 같은 자동 관문은 2.0에 없다.
- `korean-port/reference/inkos-2.0.0-korean.patch`(이전 작업물, 4,684줄)가 이 master에 충돌 없이 적용된다.
  `ko` 언어, `ko_chars` 분량 단위, 한글 작품 ID, `제1화` 가져오기, EPUB `ko`, Studio 일부 한국어,
  공통 에이전트 경로의 한국어 지침 주입이 들어 있다. **단, 실제 한국어 원고 생성은 한 번도 시험되지 않았다.**
  알려진 약점: 여러 곳이 `language !== "zh"`로 바뀌어 한국어가 영어 경로를 탄다.
- Node 22.16 이상, pnpm 9.15.9. 빌드 `pnpm -r build`, 테스트 `pnpm -r test`.
- 라이선스 AGPL-3.0-only. 포크도 같은 라이선스와 저작권 고지를 유지한다.
- 원본 `.gitignore`가 `CLAUDE.md`, `docs/*`, `_*.md`, `books/`, `works/`, `inkos.json`, `.inkos/`를 무시한다.
  그래서 이 포크의 작업 문서는 `korean-port/`에 둔다. 루트 `CLAUDE.md`는 무시 대상이므로 처음 한 번 `git add -f CLAUDE.md`로
  추적을 시작한다(추적 중인 파일은 이후 정상 커밋됨). `tools/inkos-agent-bridge/CLAUDE.md`도 같다. 원본 `.gitignore`는 수정하지 않는다.
  시험용 작품 폴더는 커밋되지 않으므로, 클라우드 세션이 끝나기 전에 검증 결과를 `korean-port/VERIFICATION.md`에 옮겨 적는다.

## 1.8 시험에서 알게 된 것 (2026-10-25, Grok봇 실행)

- 브리지 방식 자체는 작동했다: 책 생성(요청 4건), 1화(9건), 수정 2회(각 9~14건)가 모두 전달됐고,
  엔진의 설계 반려(70→82점)와 수정 채택 기준이 실제로 돌았다.
- 환경: Node 20에는 `node:sqlite`가 없어 실패. Node를 두 번 겹쳐 설치했다가 npm이 깨져 빌드가
  `Class extends value undefined`로 멈춘 적이 있다 → 설치는 Node 하나만, 버전 확인 후 진행.
- 브리지 1.1의 역할 추측(role_guess)이 자주 틀렸다 → 1.2에서 제거, 시스템 프롬프트 첫머리를 보여준다.
- `wait`의 종료 코드 3(작업 끝)이 오류로 오해됐다 → 1.2에서 항상 0, 첫 줄 `EVENT:`로 구분.
- 응답 형식(태그·JSON 키)이 조금만 어긋나도 단계가 실패한다 → 1.2는 프롬프트가 말하는 태그가 답에 없으면 경고.
- 검수 담당(에이전트)이 범위 밖 문제를 `info`로 낮춘 일이 있었다. 엔진이 아니라 답한 쪽의 판단이었다.
  검수 지침과 한국어 review 스킬에 "해결되지 않은 문제의 등급을 낮추지 않는다"를 넣는다.
- 1.8 strict 수정 기준은 치명적 문제가 줄어도 막는 문제 수가 같으면 원고를 되돌렸다. 2.0에는 이 관문이 없으므로
  같은 상황의 처리를 5단계에서 확인한다.
- 인물 폴더가 `roles/主要角色`·`次要角色`로 저장된다(2.0도 같음: `agents/architect.ts:158`, `state/manager.ts:84`).
  읽는 쪽은 `major`·`minor`도 받는다.

## 지켜야 할 원칙

1. **영어·중국어 동작을 바꾸지 않는다.** 원본 테스트가 그대로 통과해야 한다. 한국어 분기는 명시적으로 추가한다
   (`!== "zh"` 같은 우회 금지 — `ko`를 별도 분기로 처리).
2. **한국어 코드는 가능한 한 새 파일에 모은다**(`korean-*.ts`, `skills-ko/`), 원본 파일 수정은 최소화한다.
   원본 업데이트를 나중에 받을 때 충돌을 줄이기 위해서다.
3. **방법론은 스킬로 바꾼다.** 코드 속 프롬프트를 번역하기보다, 같은 ID의 한국어 스킬과 references를 쓴다.
   영어 원문을 직역하지 말고 한국 소설 관행에 맞게 새로 쓴다.
4. **API 키를 쓰지 않는다.** 실제 생성 시험은 `tools/inkos-agent-bridge`(로컬 브리지, 세션이 직접 답함)로만 한다.
5. **검증은 실물로 한다.** "됐다"는 보고는 테스트 출력, 저장된 파일, 브리지 요청 기록으로 뒷받침한다.
6. **작은 커밋.** 단계마다 브랜치 `ko/<단계>`에서 작업하고, 테스트가 통과한 상태로만 main에 합친다.

## 단계

### 0단계 — 기준선과 조사 (코드 수정 없음)
- `pnpm install --frozen-lockfile && pnpm -r build && pnpm -r test` 실행, 통과·실패 수를 기록(원본 기준선).
- `rg -n 'language (===|!==) "(zh|en)"|isEn\b|isZh\b|"zh" \| "en"'`로 언어 분기 전수 목록을 만들어
  `korean-port/SURVEY.md`에 파일·줄·현재 동작·한국어 처리 방침(영어 경로 공유 / 별도 분기 / 무관)을 표로 정리.
- 스킬 덮어쓰기 우선순위를 코드와 짧은 실험으로 확인해 SURVEY.md에 적는다.
- 작업 프로필 추가 방법을 조사한다(`harness/builtin-profiles.ts`, `contracts.ts`, `capability-registry.ts`,
  `production-capabilities.ts`): `script` 프로필이 어떤 산출물·도구를 쓰는지, 새 프로필 `explainer-script`를
  넣으려면 어디를 고쳐야 하는지, 장르 값이 어디서 정해지고 스킬 references 선택에 쓸 수 있는지.
- 끝 조건: SURVEY.md 커밋, 기준선 테스트 수 기록.

### 1단계 — 기존 한국어 패치 적용과 정리
- `git apply korean-port/reference/inkos-2.0.0-korean.patch` 후 빌드·테스트.
- SURVEY.md 방침에 따라 `!== "zh"` 우회를 명시적 `ko` 분기로 바꾼다. 특히 분량 계산(`utils/length-metrics.ts`),
  장 분할(`utils/chapter-splitter.ts`), 작품 ID, 내보내기, 오류·진행 문구.
- **사용자 결정이 필요한 것**(시작 전에 물어볼 것): 회당 분량 기준 — 공백 포함/제외, 기본 목표 글자 수,
  플랫폼별 프리셋을 둘지. 결정 전에는 현재 패치 값(공백 제외 3,000자)을 유지한다.
- 끝 조건: 원본 테스트 전부 통과 + 한국어 단위 테스트(분량·ID·분할·EPUB) 통과.

### 2단계 — 한국어 스킬
- `packages/core/skills-ko/<같은 ID>/SKILL.md`와 references를 새로 쓴다. 우선순위:
  `inkos-long-writing`(+4 references), `inkos-story-review`(+review-matrix), `inkos-story-deslop`(+semantic-cleanup),
  `inkos-short-writing`. 나머지는 이후.
- 내용 기준: 한국어 문장 리듬, 호칭·존댓말 일관성, 대사 화법, 번역투(“~하는 것이었다”, 과도한 피동, 대명사 남용),
  한국 웹소설 연재 관행(회차 끝의 압력, 장르별 독자 약속). 장르 지침은 `korean-port/reference/`의
  `소설설정-항목별기준.md`, `현대한국-라이트무협-기준.md`를 반영하고, 현판·로판·무협·헌터·회귀/빙의 등은
  "선택 장치"로 다룬다(강제 금지). 웹 관행에 대한 사실 주장(플랫폼 규정 등)은 출처를 확인한 것만 쓴다.
- 언어가 `ko`인 작품에서만 한국어 스킬이 쓰이도록 연결한다(예: `inkos init --lang ko`가 프로젝트
  `.agents/skills/`에 복사, 또는 로더가 작품 언어로 선택). 0단계 조사로 방식을 정하고 이유를 SURVEY.md에 남긴다.
- 끝 조건: 영어 작품은 기존 스킬, 한국어 작품은 한국어 스킬이 로드됨을 테스트로 확인.

### 2-1단계 — 한국 장르 스킬 (장편)
- 장르별 references를 `skills-ko/inkos-long-writing/references/genres/`에 둔다(파일 하나에 장르 하나):
  - `light-martial.md` 한국 라이트 무협: `korean-port/reference/현대한국-라이트무협-기준.md`를 바탕으로 한다.
    문파·항렬·호칭, 무공의 대가와 상성, 개그와 진중함의 비율, 회귀·환생은 선택 장치.
  - `fantasy.md` 판타지: 세계 법칙(마법·신·종족)의 발동 조건과 대가, 지명·고유명사 일관성, 정보 공개 속도.
  - `modern-fantasy.md` 현대판타지: 귀환자·헌터·각성·게이트 등은 선택 장치. 현대 한국 사회(제도·언론·경제)와
    초능력의 충돌을 인과로 처리, 강함의 수치화(등급·레벨)를 쓸 때의 장부 관리.
- 작품의 장르 값으로 해당 references가 선택되게 한다(장르 값 이름은 0단계 조사 후 결정해 SURVEY.md에 기록).
- 각 장르 파일은 같은 틀을 쓴다: 독자 약속 → 주인공 설계 → 세계/세력 → 힘의 규칙과 대가 → 회차 리듬
  → 흔한 실패(뻔한 전개·고구마 과다·설명 덤프 등) → 검수 질문 목록. 검수 질문은 `inkos-story-review`
  한국어판이 장르별로 불러 쓴다.
- 끝 조건: 장르마다 `book create`의 설계 요청 프롬프트에 해당 장르 references가 실제로 들어가는지 확인
  (브리지 `inkos-agent show`로 확인 가능).

### 2-2단계 — 작품 유형: 드라마 대본, 설명형 영상 대본
- **드라마 대본**: 기존 `script` 프로필을 쓴다. `skills-ko/inkos-script-writing/`에 한국 드라마 대본 형식
  (씬 번호 `S#`, 장소·시간 표기, 지문은 보이고 들리는 것만, 대사 앞 인물명, `(E)`/`(F)`/`(N)` 같은 표기,
  회차 엔딩)을 쓴다. 미니시리즈형과 세로형 숏드라마 중 어느 형식을 기본으로 할지는 사용자에게 묻는다.
  사용자의 AI 비디오 스튜디오에 드라마 모드가 계획돼 있으므로(인물·장소 레퍼런스 고정 방식), 대본 끝에
  등장인물·장소 목록을 따로 내보내는 옵션을 둔다.
- **설명형 영상 대본**: 2.0에 없는 유형이므로 새 작업 프로필 `explainer-script`를 `builtin-profiles.ts`에
  추가하고 새 스킬 `inkos-ko-explainer-script`를 만든다. 산출물은 장면 단위 목록:
  장면 번호, 길이(초), 내레이션 원고, 화면 설명(이미지·자료·자막), 필요한 레퍼런스(화풍·인물·배경·목소리),
  출처 메모. 사용자의 AI 비디오 스튜디오와 소재 레이더(설명형 YouTube 소재 발굴)에 연결될 예정이다.
- **사용자에게 받아야 할 것**(이 단계 시작 전): AI 비디오 스튜디오가 입력으로 받는 대본·장면 형식(저장소의
  스키마 파일 경로 또는 예시 JSON), 설명 영상의 목표 길이(롱폼/쇼츠), 드라마 대본의 기본 형식.
  형식을 받기 전에는 위 장면 목록을 Markdown 표로 내고, 스키마가 정해지면 같은 내용을 JSON으로도 내보낸다.
- 설명 영상은 사실 정확성이 핵심이다. 대본의 사실 주장마다 출처 메모 칸을 두고, 출처 없는 주장은
  검수가 지적하게 한다(새 스킬의 review 질문에 포함).
- 끝 조건: 드라마 1회분, 설명 영상 대본 1편을 브리지로 실제 생성해 형식 검사(장면 번호·길이 합계·필수 칸)를
  통과시키고 결과를 VERIFICATION.md에 남긴다.

### 3단계 — 한국어 문장 점검(관찰용)
- 2.0 계약(점수·반려 없음)을 지키면서, 검수에 근거로 붙일 수 있는 결정론적 한국어 점검을 새 파일로 추가:
  같은 어미/문장 시작 반복, 번역투 표현 목록, 작품 규칙의 피로어 빈도, 회차 간 반복 구절.
  결과는 검수 증거(observation)로만 전달하고 원고를 자동 반려하지 않는다.
- 끝 조건: 점검 단위 테스트 + 검수 요청 프롬프트에 결과가 실제로 들어가는지 확인.

### 4단계 — 화면 한국어 (에이전트 실행 기준, 2026-10-25 범위 축소)
- 사용자는 본인 혼자 쓰고, 실행은 Codex·Grok봇·Claude Code가 한다. 화면은 **사람용 Studio가 아니라 에이전트가 읽는 CLI 출력**에 맞춘다.
- 화면 언어는 **한국어·영어 선택**(`ko`/`en`). zh 문구는 원본 그대로 두되 ko 화면에 섞이지 않게 한다.
- 우선: `packages/cli/src/localization.ts`, `progress-text.ts`, 오류 문구에 `ko`. `--json` 출력이 있는 명령은 그 형식을 유지·보강(에이전트가 파싱).
- 후순위(필요할 때만): TUI(`tui/i18n.ts`), Studio(`use-i18n.ts` 등). Studio 한국어화는 하지 않아도 된다.
- 끝 조건: `--lang ko` 프로젝트에서 `book create`·`write next`·`status`·`review`·`export`의 CLI 안내·오류에 중국어가 남지 않음(남은 곳은 목록화).

### 4-1단계 — 세 실행 환경 설치 경로
- 2.0 포크는 npm에 없으므로, 포크 소스를 받아 빌드·설치하는 스크립트 `tools/setup-cloud.sh`를 만든다:
  Node 22.16 이상 확인 → `pnpm install --frozen-lockfile && pnpm -r build` → `inkos` 실행 파일을 PATH에 연결
  (또는 `INKOS_BIN=packages/cli/dist/index.js`) → `tools/inkos-agent-bridge/install.sh --project <작품 폴더>`.
  API 키·외부 모델 주소를 설정하지 않는다.
- 환경별 안내를 `korean-port/RUNTIME.md`에 쓴다:
  - **Claude Code 클라우드**: 클라우드 환경의 setup script에 위 스크립트를 넣는 법, `.claude/agents`의
    집필/검수 서브에이전트 사용, 세션이 오래 쉬면 VM이 회수되어 진행 중인 작업이 사라진다는 점.
  - **Codex 클라우드**: 환경 Setup script에 위 스크립트를 넣는 법(설치는 setup 단계에서 인터넷으로,
    작업 중에는 인터넷·API 불필요), `AGENTS.md`를 읽는다는 점, 결과가 PR/브랜치로 남으므로 다음 작업 전에
    병합해야 상태 파일이 이어진다는 점. 서브에이전트가 없으면 집필과 검수를 별도 패스로 나눈다.
  - **Grok봇**: 같은 컴퓨터에서 셸과 백그라운드 프로세스를 쓸 수 있어야 한다는 전제, 첫 지시문, 서브에이전트가
    셸을 못 쓰면 메인이 대신 `reply`한다는 점(`tools/inkos-agent-bridge/GROK.md`).
- 세 환경 모두 공통으로 작품 폴더(`books/` 등)는 `.gitignore` 대상이다. 세션 간에 원고를 이어가려면
  작품 폴더를 별도 비공개 저장소로 두거나, 세션 끝에 내보내기(export)해서 보관하는 방법을 RUNTIME.md에서 정한다
  (사용자에게 확인).
- 끝 조건: 새 클라우드 세션에서 `tools/setup-cloud.sh` 한 번으로 `inkos-agent doctor`가 통과.

### 5단계 — 실제 생성 검증 (브리지)
- `tools/inkos-agent-bridge`로 API 없이 실행. `inkos-agent doctor`, `start` 후:
  `book create --lang ko`(장르는 2.0 프로필 기준) → `write next --count 2`.
  요청마다 서브에이전트(집필/검수 분리)가 한국어로 답한다.
- 확인: `book.json`의 `language: ko`, 설계·인물·상태 파일 한국어, 회차 분량이 `ko_chars` 기준 범위 안,
  상태 파일이 본문과 일치, 스냅샷 생성, 브리지 요청이 전부 delivered.
- 실행 환경별 시험: Claude Code 클라우드에서 위 전체 시험, Codex 클라우드와 Grok봇에서는 최소
  `book create` + 1화를 돌려 같은 기준으로 확인한다(브리지 요청 목록·작업 로그·저장 파일).
- 장르별 시험: 라이트 무협·판타지·현대판타지 각각 `book create` + 1화. 장르 references가 프롬프트에 들어갔는지,
  설계가 그 장르의 독자 약속을 담았는지 확인한다.
- 결과를 `korean-port/VERIFICATION.md`에 원본 출력(작업 로그, 요청 목록, index.json)과 함께 기록.

## 결정 사항
- 기준 버전: 2.0(master `53adac4e`). 이유: 한국어화 범위가 작고 스킬 덮어쓰기 구조가 있음. (2026-10-25 사용자 결정)
- 감수할 차이: 2.0에는 1.8의 자동 점수 관문이 없다. 필요하면 별도 단계로 논의한다.
- 회당 분량 기준: `ko_chars`(메타데이터 제거 → NFC → 공백 제외 → 코드 포인트 수), 기본 **3,000자**, 플랫폼별 프리셋 없음(플랫폼 공식 기준을 출처로 확인하지 못함), 작품별로 `--chapter-words`로 조정. (2026-10-25 사용자 "추천안대로")
- 화면 언어: 한국어·영어 선택. 화면 구성은 에이전트(Codex·Grok봇·Claude Code) 실행 기준, Studio 한국어화는 후순위. 사용자는 본인 1명. (2026-10-25 사용자 결정)
- 영어·중국어 동작 유지 원칙은 그대로 둔다(원본 업데이트를 받을 때 충돌을 줄이고 원본 테스트를 기준선으로 쓰기 위해). 기존 패치의 zh/en 기본값 변경은 되돌리고, 한국어는 `--lang ko`/`inkos.json`의 `language: "ko"`로 선택한다.
- 실행 환경: Claude Code(클라우드), Codex(클라우드), Grok봇. API 키 없이 브리지로만 실행. (2026-10-25 사용자 확인)
- 원고 보관: 각 실행 환경의 Google Drive 연결로 폴더 "Inkos ko"(ID `1FYkA9t5AiI3u31cL0uM8dSFjgf5LxnEU`)에 작품 압축본을 올리고 받는다. `novel-drive.py`의 OAuth 동기화는 선택. (2026-10-25 사용자 결정)
- 대상 장르·유형: 한국 라이트 무협, 판타지, 현대판타지, 드라마 대본, 설명형 영상 대본. (2026-10-25 사용자 결정)
- 드라마 대본 기본 형식: **세로형 숏드라마**(작품마다 바꿀 수 있음, 미니시리즈형도 지원). (2026-10-25 사용자 결정)
- 설명 영상 대본: 기본 길이 **롱폼(8~15분)**. 출력 형식은 스튜디오 스키마가 아직 없어 **장면 목록 Markdown 표**로 낸다. 스키마가 정해지면 같은 내용을 JSON으로도 내보낸다. (2026-10-25 사용자 결정)
- `ko` 작품의 인물 카드 저장 폴더: `roles/major`·`roles/minor`(영어·중국어 작품은 원본 그대로). 한글 폴더명은 읽는 쪽을 모두 고쳐야 하므로 쓰지 않음. (2026-10-25 감독 지시)
- Drive 덮어쓰기 방지: `pull` 때 복원한 보관본 이름을 작품 폴더에 기록하고, `push`는 Drive의 최신 보관본이 그 이름과 다르면
  거부한다(`--force`로만 진행). 두 세션이 같은 작품을 고치면 나중 것이 앞 것을 "최신"으로 덮어 보이게 되는 것을 막기 위해서. (2026-10-25 감독 지시)
- 개발 브랜치: Claude Code 클라우드 세션의 지정 브랜치 하나를 쓰고, 단계는 커밋 제목으로 구분한다(운영 규칙 v1.1). (2026-10-25 감독 결정)

## 진행 기록
- 2026-10-25: 계획 작성. 코드 변경 없음.
- 2026-10-25 (브랜치 `claude/eeum-n0rsol` — 클라우드 세션 지정 브랜치라 `ko/<단계>` 대신 사용): **0단계 완료.**
  - `f21cfe8` 킥오프 파일(CLAUDE.md, korean-port/, tools/inkos-agent-bridge/) 추가. 브리지 자체 시험 28/28 통과.
  - 기준선: 설치·빌드 통과. 클라우드 기본 환경의 `pnpm -r test`는 core 13개 실패(샌드박스 프록시가 127.0.0.1 요청을 403으로 막음, 코드 결함 아님).
    프록시 변수를 뺀 `pnpm -r --no-bail test`는 **core 701 / studio 304 / cli 88 = 1,093 전부 통과**. 이후 "원본 테스트 통과"는 이 명령으로 잰다.
  - `korean-port/SURVEY.md` 작성: 스킬 우선순위(실험 확인), 프로필·`explainer-script` 추가 지점, 장르 값, 언어 분기 전수(558줄/76파일 + 넓힌 검색 305줄/67파일), 기존 패치의 zh/en 기본값 변경 목록.
  - 다음: 1단계. 시작 전 사용자 확인 필요 — 회당 분량 기준, zh/en에도 보이는 Studio 화면 변경 허용 여부(SURVEY.md 5절).
- 2026-10-25 (`claude/eeum-n0rsol`): **1단계 완료.** 사용자 결정 반영(분량 공백 제외 3,000자·프리셋 없음, 화면 ko/en·에이전트 기준).
  - `c4a6684` 기존 패치를 그대로 적용(검토용 분리 커밋). 적용 직후 core 710 / studio 307 / cli 93 통과.
  - `ffba2a1` 패치가 바꾼 zh/en 기본값 복원: `init`/`short-fiction --lang` 기본 zh, `agent`·`interact`·`project-bootstrap`·TUI autoInit·Studio 새 프로젝트 zh,
    로캘 최종 기본 zh(`INKOS_LOCALE=ko` 또는 `LANG=ko_*`면 ko), `book create --platform` 기본 tomato(ko 작품은 other), `init`·`export`의 zh/en 출력 원본 그대로.
  - `e80db04` 명시적 ko 분기: 분량 계수(writer가 ko를 en_words로 세던 문제), 분량 지시 단위 ko_chars, 상태 검증 응답 언어, 메인 에이전트 한국어 응답 지시,
    회차 제목 엄격 인식("3장의 편지"·"2화 만에" 오탐 제거)과 `# 제N화 제목` 통일, 작품 ID는 원본 규칙 + 한글 음절만 추가(zh/en ID 불변),
    상태 파일(복선 목록·회차 요약·현재 상태) 한국어 표제, 단편 ko 기본 1,000자(패치는 650), ko가 중국어 프롬프트로 가던 곳(architect 인물 카드, runner 의도문 등).
  - 검증(프록시 변수 제거): **core 719 / studio 307 / cli 94 = 1,120 전부 통과**(원본 1,093 포함). 새 테스트 `packages/core/src/__tests__/korean-stage1.test.ts` 9개.
  - 남은 것(범위 밖이거나 후속 단계): Studio 화면·영감 카드(ko→중국어 프롬프트, 사용자 결정으로 후순위), TUI 문구, 플레이/인터랙티브 필름/예측(대상 장르 밖),
    대본 spec 파일 제목(2-2단계), 동인 정사 표제·단편 검토 보고서 표제(영어로 저장), 번역 EPUB `lang`(언어 이름이 들어감), 프롤로그·에필로그·외전 제목 인식.
  - 다음: 2단계(한국어 스킬). 권장 연결 방식은 SURVEY.md 2절 C안(프로젝트 `language: ko`면 로더가 `skills-ko/` 삽입).
- 2026-10-25 (`claude/eeum-n0rsol`): **2단계 완료.**
  - 연결 방식: SURVEY.md 2절 **C안** 채택. `packages/core/src/skills/korean-skill-root.ts` + `builtin-loader.ts` 몇 줄 — 프로젝트 `inkos.json`의 `language`가 `ko`면
    `packages/core/skills-ko/`를 내장 스킬 바로 위(사용자·프로젝트 스킬 아래)에 끼운다. 이유: 원본 수정 최소, 사용자·프로젝트 덮어쓰기 규칙 유지, 한국어 전용 프로젝트에 맞음.
    한계: 프로젝트 단위(zh/en 프로젝트 안의 ko 작품은 원본 스킬을 받음). `package.json` `files`에 `skills-ko` 추가.
  - 새로 쓴 스킬(같은 ID): `inkos-long-writing`(+references 5개: 원본 4개 대응 + 새 `korean-prose.md` 번역투·어미 반복·호칭/존댓말·대사·모바일 문단),
    `inkos-story-review`(+review-matrix, 한국어 문장·장르별 질문 절 추가), `inkos-story-deslop`(+semantic-cleanup), `inkos-short-writing`(+production-checklist).
    한국어 검색 토크나이저가 약하므로(SURVEY 2절) 장편 references는 모두 SKILL.md에 직접 링크해 항상 들어가게 했다. 프로토콜 값(hook 상태·회수 시점 enum, local/structural/unknown)은 원본 그대로.
  - 검증: `korean-skills.test.ts` 6개 — zh/en/미설정 프로젝트는 원본 스킬, ko 프로젝트는 한국어 스킬, ko에서도 프로젝트 스킬이 이김, 링크된 references 전부 로드,
    **실제 writer 메시지(`prepareWorkerMessages`)에 ko 프로젝트만 `# 한국어 장편 집필 방법`과 `# 한국어 문장 기준`이 들어가고 en 프로젝트는 원본이 들어감**.
    전체(프록시 변수 제거): core 725 / studio 307 / cli 94 통과.
  - 다음: 2-1단계(장르 references). 장르 값은 `light-martial`, `fantasy`, `modern-fantasy`(SURVEY 3절 제안).
- 2026-10-25 (`claude/eeum-n0rsol`): **2-1단계 완료.**
  - 장르 값 확정: `light-martial`, `fantasy`, `modern-fantasy`(한국어 이름·별칭도 인식: 무협·라이트무협·korean-martial, 판타지, 현대판타지·현판 등). 그 밖의 값은 장르 문서 없이 진행.
  - 문서: `packages/core/skills-ko/inkos-long-writing/references/genres/{light-martial,fantasy,modern-fantasy}.md` — 계획서의 공통 틀(독자 약속→주인공→세계/세력→힘의 규칙과 대가→회차 리듬→흔한 실패→검수 질문).
    특정 작품의 이름·설정은 넣지 않음. 라이트 무협은 `korean-port/reference/현대한국-라이트무협-기준.md` 바탕.
  - 연결: `packages/core/src/skills/korean-genre-references.ts` — 한국어 `inkos-long-writing`이 활성화되고 작품이 ko일 때, 작품 매니페스트 `metadata.genre`(없으면 book.json)로
    장르 문서를 결정론적으로 붙이고 다른 장르 문서는 검색 결과에서 걸러낸다. `agents/base.ts` `prepareWorkerMessages`에 2줄. 장르 문서는 링크하지 않음(항상 로드 방지).
    검수 질문은 같은 활성화로 auditor에도 들어간다(review-matrix "장르별 질문" 절이 이를 가리킴).
  - 패치의 `KOREAN_LIGHT_MARTIAL_POLICY` 별도 주입은 장르 문서와 중복이라 제거(패치 테스트를 그에 맞게 수정).
  - 같은 실행에서 고친 것: architect 외부 지시 제목이 ko에 `## 外部指令` → `## 외부 지시`(ko 분기만, en은 원본 그대로).
  - 검증: 브리지 실제 실행으로 장르마다 `book create` architect 요청 프롬프트에 **해당 장르 문서 하나만** 들어감을 확인 → `korean-port/VERIFICATION.md`.
    단위 테스트(`korean-skills.test.ts`)에 장르 매핑·장르별 단일 첨부·zh/en 미첨부 추가. 전체(프록시 변수 제거): core 728 / studio 307 / cli 94 통과.
  - 다음: 2-2단계(드라마 대본, 설명형 영상 대본). **시작 전 사용자 확인 필요**: 드라마 대본 기본 형식(미니시리즈/세로형 숏드라마), AI 비디오 스튜디오의 입력 스키마(또는 예시 JSON), 설명 영상 목표 길이(롱폼/쇼츠).
- 2026-10-25 (`claude/eeum-n0rsol`): **2-2단계 완료.** 사용자 결정: 드라마 기본 세로형 숏드라마, 설명 영상 기본 롱폼 8~15분, 스튜디오 스키마 없음 → Markdown 표.
  - 드라마: `script` 프로필에 ko 분기(`agents/korean-script.ts`) — 한국어 명세, 필수 제목 `## 등장인물`/`## 장소`/`## 대본`, ko 기본 형식 `vertical_short_drama`,
    `script-references.md`(등장인물·장소 목록, 영상 도구의 레퍼런스 고정용) 별도 저장. 한국어 `inkos-script-writing` 스킬(+`korean-drama-format.md` S#·장소(시간)·(E)/(F)/(N), `episode-scene-craft.md`).
  - 설명 영상: ko 프로젝트에만 등록되는 프로필 `explainer-script`(`harness/korean-profiles.ts` — zh/en 프로필 목록 불변), 스킬 `inkos-ko-explainer-script`
    (+`scene-table.md`, `review-questions.md` — 출처 없는 사실 주장은 항상 지적), 러너 `pipeline/korean-explainer-runner.ts`, 결정론적 형식 검사
    `utils/korean-explainer-check.ts`(제목·열·장면 번호·초·합계·빈 칸·출처 번호, 관찰: 확인 필요 출처·내레이션 과밀/과소·미사용 출처). 검사는 기록만 하고 반려하지 않는다.
  - CLI 새 명령: `inkos script create`, `inkos explainer create`(ko 프로젝트 전용). 기존 명령은 그대로.
  - 검증: 브리지로 드라마 1회분·설명 영상 1편 실제 생성, 형식 검사 통과 → `korean-port/VERIFICATION.md`. 테스트 `korean-scripts.test.ts` 9개.
  - 미뤄 둔 것: 설명 영상 JSON 내보내기(스튜디오 스키마가 정해지면), 설명 영상 검수(review) 동작은 스킬 질문만 있고 전용 검수 명령은 없음.
  - 다음: 3단계(한국어 문장 점검, 관찰용).
- 2026-10-25 (`claude/eeum-n0rsol`): **3단계 완료.**
  - `packages/core/src/utils/korean-prose-check.ts`: 서술 문장(대사 줄 제외)의 같은 어미 연속(끝 두 음절, 4문장 이상)·같은 문장 시작 연속(3문장 이상),
    번역투 후보(`~는 것이었다`, `되어지다`, `~에 의해`, `~에 있어서`, `~을 가지다`(have 직역), `~함에도 불구하고`, `~임에 틀림없다`, `가장 ~ 중 하나`, `그녀` 5회 이상),
    작품 피로어 빈도, 앞 3개 회차와 같은 5어절 구절. 결과는 `numberReviewSource`와 같은 줄 번호.
  - 계획과 다른 점: 2.0 `book_rules`에는 피로어 필드가 없다(1.8 `fatigueWordsOverride`). 그래서 작품별 목록 파일 `story/korean_fatigue_words.md`(한 줄에 하나)를 선택적으로 읽는다. 스키마는 바꾸지 않았다.
  - 연결: `agents/korean-audit-evidence.ts` + `agents/continuity.ts` 2줄 — ko 작품의 auditor 요청에 `## 한국어 문장 점검 (host가 계산한 결정론적 관찰)` 시스템 블록을 넣는다.
    "자동 실패 기준이 아니며, 읽기를 방해하는 것만 줄을 인용해 남기라"는 지시와 함께. 점수·반려 없음(2.0 계약 유지).
  - 검증: `korean-prose-check.test.ts` 7개 — 점검별 단위 테스트, 줄 번호 일치, **auditor 메시지에 ko만 블록이 들어가고 en은 들어가지 않음**(검수 호출 직전 메시지를 가로채 확인).
    전체(프록시 변수 제거): core 744 / studio 307 / cli 94 통과. 브리지 실물 확인은 5단계 `write next`에서 함께 한다.
  - 다음: 4단계(CLI 화면 한국어) → 4-1단계(설치 스크립트).
- 2026-10-25 (`claude/eeum-n0rsol`): **4-1단계(설치 경로) 완료, 일부는 다음 새 세션에서 확인 필요.**
  - `tools/setup-cloud.sh`: Node 22.16+·python3 확인 → pnpm 설치/빌드 → `~/.local/bin/inkos` 래퍼 → Drive 비밀값이 있으면 최신 보관본 복원, 없으면 `inkos init --lang ko`
    → 브리지 설치 → `~/.bashrc` 환경 변수 → `inkos-agent doctor`. 기본 작품 위치 `<저장소>/novel`(내부에 `.gitignore` `*`). API 키·외부 모델 설정 없음.
  - `tools/novel-drive.py`(표준 라이브러리만): `pack`/`unpack`/`push`/`pull`/`list`/`init-folder`. `.env`·`runtime/` 제외, 압축 해제 시 대상 밖 경로·링크 거부,
    기존 프로젝트 덮어쓰기는 `--force`일 때만, 같은 작품의 최신 N개(기본 10)만 남김. 오프라인 가짜 Drive 서버 시험 `tools/tests/test_novel_drive.py` 16/16 통과.
  - 이 세션에서 확인한 것: `setup-cloud.sh --no-build --no-pull`로 새 ko 프로젝트 생성·브리지 설치·`doctor` 통과(빌드 단계 명령은 0단계에서 같은 명령으로 확인),
    컨테이너에서 `www.googleapis.com`(401)·`oauth2.googleapis.com`(404) 접속 가능(인증 없이 연결만 확인). Codex setup 스크립트를 1.8 npm 설치에서 이 스크립트 호출로 교체.
  - **아직 확인 못 한 것**: 실제 Google 계정으로 `init-folder`/`push`/`pull`(사용자가 비밀값을 넣어야 함), 완전히 새 클라우드 세션에서 Setup script 한 번으로 `doctor` 통과.
  - `korean-port/RUNTIME.md`: 세 환경별 안내, Drive 인증 준비 절차(사용자용), 세션 끝 `push` 규칙. 브리지 `AGENTS.md`에도 `push` 규칙 추가.
  - 다음: 5단계(실제 생성 검증) + 4단계(CLI 문구, 5단계 실행 출력에서 중국어가 남는지 확인하며 함께 처리).
- 2026-10-25 (`claude/eeum-n0rsol`): **보고 채널과 운영 규칙 확인, 진행 멈춤.** 사용자 지시로 개발 상황을 Slack `#inkosgo`(C0CBSUEAQ4B)에 `[코드]` 머리말을 붙여 남긴다.
  채널의 운영 규칙 v1(단계 끝 `[보고]`, 승인 전 다음 단계 시작 금지, `ko/<단계>` 브랜치)과 0-a 지시(시작 패키지 v2 동기화)를 이때 처음 확인했다.
  그 전까지 단계별 승인 없이 4-1단계까지 진행했다는 점을 `[보고]`로 알렸다. 5단계 `book create`(작품 `매화검-막내의-장부`)는 설계 1단계(foundation outline)까지 답하고 멈춤.
  다음: 승인과 `[결정필요]` 답(v2 zip 업로드, 브랜치 방식, 1~4-1 검토, 5단계 재개 여부)을 기다린다.
- 2026-10-25 (`claude/eeum-n0rsol`): **0-a단계(동기화 묶음 v3) 완료.** 감독 검토: 0~3단계 승인, 4-1단계 조건부 승인, 4·5단계 보류.
  - 멈춘 5단계 `book create`(`매화검-막내의-장부`) 폐기: `inkos-agent job stop j-20261025-122756-7f57a17b`(state lost), 남은 요청 `r-20261025-123043-eec84205`는 fail로 닫음, 브리지 정지.
  - `inkos-ko-sync-v3.zip`(커밋 `dc66bb2`)에서 덮어씀: `CLAUDE.md`, `korean-port/OPERATING_RULES.md`(새 파일, v1.1), `tools/inkos-agent-bridge/**`(1.2.0). `setup/codex-cloud-setup.sh`는 묶음에 없어 유지.
  - `PLAN-additions-v3.md` 병합: "1.8 시험에서 알게 된 것" 절(원칙 절 앞), 결정 사항 3개(ko 인물 폴더 `major`/`minor`, Drive 덮어쓰기 방지, 개발 브랜치 방식). 다른 부분은 바꾸지 않음. 추가 파일은 저장소에 넣지 않고 삭제.
  - 시험: `python3 -I tools/inkos-agent-bridge/tests/test_bridge.py` → 33/33 passed, `test_long_wait.py` 2/2 PASS.
  - 남은 불일치: 새 `CLAUDE.md`는 "`ko/<stage>` 브랜치에서만 작업"이라고 쓰지만 운영 규칙 v1.1·결정 사항은 세션 지정 브랜치 하나를 허용한다. 우선순위(결정 사항 → 운영 규칙 → CLAUDE.md)대로 세션 브랜치를 쓴다.
  - 다음: 지시받은 이어서 할 일(4-1 fix: Drive 덮어쓰기 방지, SURVEY 원본 수정 범위 숫자·대상 밖 변경 정리, ko 인물 폴더) — 별도 커밋 `(stage 4-1 fix)`.
- 2026-10-25 (`claude/eeum-n0rsol`): **0-a 이어서 할 일(4-1 fix, 1단계 보완) 완료.** 커밋은 모두 `(stage 4-1 fix)`.
  - `289c01c` Drive 덮어쓰기 방지: `pull`이 `<작품>/.inkos-drive-base`에 복원한 보관본 이름·작품 키를 기록, `push`는 Drive 최신본이 그 기록과 다르거나
    기록이 없는데 Drive에 보관본이 있으면 exit 3으로 거부(`--force`로만 진행), 성공하면 기록 갱신. 작품 키는 보관본 이름에서 읽어 다른 폴더 이름으로 복원해도 같은 작품. 기록 파일은 묶지 않음.
    오프라인 가짜 Drive 시험 24/24.
  - `8b01e6f` 원본 수정 범위 숫자를 SURVEY.md 6절에 기록(87개 +801/−482 → 79개 +773/−450, 새 파일 43개 +2,785). 대상 밖인 플레이·인터랙티브 필름·예측의
    패치 변경 8개 파일을 원본으로 되돌리고, ko가 넘어가는 4곳은 `upstreamLanguage()`(ko→en)로 명시. 동작은 기존 패치와 같음.
  - 이번 커밋: ko 작품 인물 카드 폴더 `roles/major`·`roles/minor`(`utils/korean-language.ts` `roleTierDirectory`, `agents/architect.ts`, `state/manager.ts`).
    zh/en은 원본(`主要角色`/`次要角色`) 그대로. ko 설계 수정 때는 예전 중국어 폴더의 카드도 정리. 읽는 쪽은 원래 네 폴더를 모두 읽음. 테스트 `korean-role-folders.test.ts` 4개.
  - 검증(프록시 변수 제거): core 748 / studio 307 / cli 94 = 1,149 통과(원본 1,093 포함), 브리지 33/33, Drive 24/24. 원본 수정 현재 79개 +778/−454.
  - 감독 확인 필요: 브리지 `AGENTS.md`의 "InkOS writes role cards to roles/主要角色 … Do not rename them by hand"는 이제 ko 작품에는 맞지 않는다(감독 문서라 고치지 않음).
    1.8 교훈의 "한국어 review 스킬에 등급을 낮추지 않는다를 넣는다"는 아직 반영하지 않았다(지시 범위 밖).
- 2026-10-25 (`claude/eeum-n0rsol`): **5단계 준비 `(stage 5 prep)`.** 감독 승인: 0-a·4-1 보완. 결정필요 답변 4건과 원고 보관 지침(사용자 결정)을 한 커밋으로 반영.
  - 브리지 `AGENTS.md` 인물 폴더 문장: zh/en `roles/主要角色`·`次要角色`, ko `roles/major`·`roles/minor`, 손으로 옮기지 않음.
  - 한국어 review 스킬(`SKILL.md`, `review-matrix.md`): 해결되지 않은 문제의 등급을 수정 범위 밖이라는 이유로 낮추지 않는다.
  - `CLAUDE.md`: 세션 지정 브랜치 하나, 단계는 커밋 제목(운영 규칙 v1.1과 같게).
  - `novel-drive.py push` exit 3이면 `--force` 없이 멈추고 사용자에게 보고(`RUNTIME.md`, 브리지 `AGENTS.md`).
  - 원고 보관 지침(모든 실행 환경): 각 환경의 Drive 연결로 "Inkos ko"(`1FYkA9t5AiI3u31cL0uM8dSFjgf5LxnEU`)에 압축본을 올리고 받는다. OAuth 동기화는 선택. 결정 사항 교체.
    지침의 `pack <작품 폴더> <이름>.tar.gz`가 그대로 동작하도록 `pack`이 두 번째 인자로 압축본 이름을 받게 했고(시험 25/25),
    "unpack 전에 사용자 확인"에 맞춰 `setup-cloud.sh`의 자동 복원은 `--pull`을 줄 때만 한다(기본 끔).
  - 시험: 한국어 스킬 9/9, 브리지 33/33, Drive 25/25.
- 2026-10-25 (`claude/eeum-n0rsol`): **5-a단계 한국어 실제 생성 검증 1차 `(stage 5)`.** 라이트 무협 "청운객잔 셋째 사환"(`novel/`, git 무시) 설계 + 2화, 브리지 요청 19건 모두 delivered.
  역할 분리: writer 서브에이전트(설계·기획·집필·정산), reviewer 서브에이전트(감사·상태 검증). 증거와 원본 출력은 `VERIFICATION.md` 5-a 절.
  - `0d1465d` 원본 결함 수정: `inkos write next`가 `write_chapters`에 필수인 `startChapterNumber`를 넘기지 않아 모든 언어에서 모델 호출 전에 실패했다. 다음 회차 번호를 넘김(CLI 1줄).
  - 분량(ko_chars): 1화 2,914 / 2화 2,866 — 범위 안. 설계: `language: ko`, `roles/major`·`minor`, 장르 문서 `light-martial.md` 하나. 스냅샷 0·1·2.
  - 발견(고치지 않음, 등급 그대로): ① 한글 제목이 `slugifyAnchor`에서 모두 `section`이 되어 이야기 틀이 제목 한 줄만 프롬프트에 들어간다(ko 전용).
    ② 1화 상태가 저장되지 않았다: 재검증이 시작 회차 칸(엔진 규칙 `min(기존, 새 값)`으로 0 고정)과 메모의 불일치로 다시 실패 → 기준 상태 유지.
    2화 정산 프롬프트에 1화 본문이 없어 1화에만 있는 사실은 상태에서 빠졌다. ③ 2화의 "마감하고 나서 올라간 두 사람"이 1화의 시점과 다르다(원고 수정 필요).
  - 감사: 1화 요청에 "한국어 문장 점검" 블록(`ending-repetition`) 포함, reviewer가 의도된 리듬으로 판단해 관찰에서 뺌. 2화는 검사기 결과가 없어 블록 없음(설계대로).
  - CLI·로그의 중국어 문구: 0줄. 영어 출력(`Stage:`, `(2914 words)`)은 목록만.
  - Drive: 전체 압축본 752KB는 연결 도구(base64 직접 입력)로 올리지 못함. 원고+상태 압축본 `청운객잔-셋째-사환_20261025-1510_2화_원고.tar.gz`(11,430바이트)를 바이너리로 올림, 크기 일치.
  - 시험(프록시 변수 제거): core 748 / studio 307 / cli 94 = 1,149 통과, 브리지 33/33, Drive 25/25.
  - 사용자 확인 필요: 서술 시점을 시험 진행을 위해 3인칭 제한(막삼)으로 정했다(설계에서는 미정).
- 2026-10-25 (`claude/eeum-n0rsol`): **5-a 보완 후 재실행 `(stage 5-a fix)`.** 감독 판정: 5-a 미완(상태 승계 실패), `57e7695` 승인. 지시 A~D 수행.
  - `ab694b9` A: 재정산 실패 때 엔진 동작을 SURVEY 7절에 기록(재정산 1회, 미해결이면 원고 저장·상태 버림, 저장되는 흔적은 관찰 코드뿐).
    한국어 스킬 `state-projection.md`에 "상태 검증의 판정 기준"(본문과의 사실 충돌만 재정산 사유, 엔진 정규화 값은 모순 아님, 실제 사례), review-matrix에서 참조.
    브리지 `inkos-reviewer.md`·`AGENTS.md`에 같은 한 줄. ko `write next`·`status`에 상태 미적용 회차 경고(원본에는 표시가 없어 새 파일 `cli/src/korean-state-notice.ts`).
  - `ce1a9c5` B: `slugifyAnchor` 정규식에 한글 음절(가-힣) 추가, 테스트 2개(수정 전 실패 확인). SURVEY 8절 "원본 결함 수정" 목록(`0d1465d` 포함).
  - `42352b9` C: 전체 압축본 752KB 구성 측정(`.inkos/harness.sqlite` 실행 기록이 압축 후 607KB) → `RUNTIME.md`. `pack --resume`(설정·작업 목록·source/·최근 스냅샷 2개),
    `unpack`이 현재 판 스냅샷을 source/에서 다시 만듦. Drive 시험 28/28.
  - D 재실행(새 작품 "철쭉골 대장간 막내", `novel-5a2/`): 1화 뒤 `lastAppliedChapter 1`·회차 요약·현재 상태 30행·복선 이동 저장, 2화가 1화 상태의 사실을 이어받음(사례 2개),
    이야기 틀 9절 모두 프롬프트에, `--resume` 압축본(48,501바이트)을 빈 폴더에 풀어 `inkos status` 동일(경로만 다름), Drive에 4조각으로 올림(크기 일치).
    요청 16건 모두 delivered. 분량 1화 2,897 / 2화 2,880. 근거는 VERIFICATION.md "5-a 보완 후 재실행".
  - 시험(프록시 변수 제거): core 751 / studio 307 / cli 98 = 1,156 통과, 브리지 33/33, Drive 28/28.
- 2026-10-25 (`claude/eeum-n0rsol`): **5-b단계 `(stage 5-b)`.** 감독 승인: 5-a. 근거는 VERIFICATION.md "5-b단계".
  - `599dd1a` 보관 지침: `pack --resume`, 경로 순서(파일 건네기 → Drive 조각(작을 때, 10화 이상 금지) → OAuth 선택), `novel-drive.py split`/`join`(목록 파일의 크기·sha256 대조). Drive 시험 31/31.
  - 파일 건네기: 파일 보내기 도구로 `--resume` 압축본(48,501바이트)을 보냄 → 사용자가 휴대폰에서 받음. 다음 세션은 대화에 첨부 → `/root/.claude/uploads/<세션ID>/…`.
  - revise(`novel-5a2`): spot-fix 3번 모두 적용(각 1줄 diff), 재감사됨. 1화(최근 회차 아님)는 원고만 저장되고 상태·스냅샷은 그대로 — 지운 대사가 상태에 남는 부작용(보통) 발견.
    2화(최근 회차)는 재정산이 저장되고 `snapshots/2`만 바뀜. 1화 박자 선취는 spot-fix를 고름(대사 한 줄, 앞 회차라 상태가 재정산되지 않아 큰 수정은 어긋남).
  - 재개: 수정 뒤 `--resume`(49,008바이트)을 빈 폴더 `novel-5a2-resumed/`에 풀어 3화 "장날의 낫" 2,940자, `lastAppliedChapter 3`, 1·2화 상태 사례 2개 이어받음.
  - 장르: fantasy "잿빛 탑의 견습 필사공" 1화 2,932자, modern-fantasy "환승역 균열 신고 접수처" 1화 2,976자. 장르 문서 각 하나, 1화 상태 저장(둘 다 재정산 1회 후 통과).
  - 발견: 회차 감사 요청에는 `inkos-story-review` 스킬이 붙지 않는다(원본 동작, 한국어 검수 기준표가 회차 감사에 안 들어감). revise 출력이 영어(4단계 목록 갱신).
  - 시험(프록시 변수 제거): core 751 / studio 307 / cli 98 = 1,156 통과, 브리지 33/33, Drive 31/31. 요청 42건 모두 delivered.
