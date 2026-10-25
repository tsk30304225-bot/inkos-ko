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
- 작품 폴더 보관 방식(세션 간 원고 이어가기): 미정.
- 대상 장르·유형: 한국 라이트 무협, 판타지, 현대판타지, 드라마 대본, 설명형 영상 대본. (2026-10-25 사용자 결정)
- 드라마 대본 기본 형식(미니시리즈/세로형 숏드라마): 미정.
- 설명 영상 대본의 출력 형식: 미정. AI 비디오 스튜디오의 입력 스키마를 받아 맞춘다.

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
