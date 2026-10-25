# 0단계 조사 결과 (SURVEY)

기준: 원본 `Narcooo/inkos` master `53adac4e`(이 저장소 `53adac4`), 조사일 2026-10-25, 브랜치 `claude/eeum-n0rsol`.
코드 수정 없음. 각 표의 "기존 패치"는 `korean-port/reference/inkos-2.0.0-korean.patch`(90파일, +1180/−469, 이 master에 `git apply --check` 통과)를 뜻한다.

## 1. 원본 기준선

환경: Node v22.22.0, pnpm 10.28.0(계획서는 9.15.9 — 저장소에 `packageManager` 지정이 없고 10.28로 `--frozen-lockfile` 설치가 그대로 통과했다.
pnpm 10은 esbuild·msw·protobufjs의 build script를 건너뛰었지만 빌드·테스트에 영향이 없었다).

| 단계 | 명령 | 결과 |
|---|---|---|
| 설치 | `pnpm install --frozen-lockfile` | 통과 (1,010 패키지) |
| 빌드 | `pnpm -r build` | 통과 (core, studio, cli) |
| 테스트 (클라우드 기본 환경) | `pnpm -r test` | core **13 실패** / 701, 첫 실패에서 중단되어 studio·cli 미실행 |
| 테스트 (프록시 변수 제거) | `env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy pnpm -r --no-bail test` | **전부 통과**: core 124파일 701, studio 47파일 304, cli 24파일 88 = **1,093 통과 / 0 실패** |

13개 실패의 원인은 전부 클라우드 샌드박스의 외부 프록시다: 테스트가 `127.0.0.1`에 띄운 가짜 모델 서버로 가는 요청이
`HTTPS_PROXY`를 타고 나가 `403 request blocked: no rule allows host "127.0.0.1"`로 막힌다(코드 결함 아님).
→ **이 포크의 "원본 테스트 통과" 기준은 프록시 변수를 뺀 위 명령으로 잰다.** 브리지(`inkos-agent`)도 같은 이유로 InkOS 실행 시 프록시를 제거한다.
테스트는 인터넷이 필요 없다.

브리지 자체 시험: `python3 -I tools/inkos-agent-bridge/tests/test_bridge.py` → 28/28 통과.

## 2. 스킬 덮어쓰기 우선순위 (코드 + 실험으로 확인)

코드: `packages/core/src/skills/builtin-loader.ts` `loadAvailableAgentSkills()`가 `[...builtin, ...configured]` 순서로 합치고,
`skills/registry.ts` `dedupeSkills()`가 같은 ID를 **나중 것이 이기게**(last-write-wins) 정리한다.
`configured` 순서는 `skills/external-loader.ts` `configuredSkillDirs()`:

| 순서(낮음→높음) | 위치 | source |
|---|---|---|
| 1 | 패키지 내장 `packages/core/skills/` | builtin |
| 2 | `$INKOS_SKILL_DIRS` (여러 개면 적힌 순서) | external |
| 3 | `~/.openclaw/skills` | user |
| 4 | `~/.agents/skills` | user |
| 5 | `<project>/.agents/skills` | project |
| 6 | `<project>/skills` | project |

실험(빌드된 core에 같은 ID `inkos-long-writing`을 위치마다 만들어 `getSkill()` 결과 확인, 2026-10-25):

```
builtin only                       -> builtin  | 长篇小说的场景构造…
env only                           -> external | override from env
env + ~/.agents                    -> user     | override from home/.agents/skills
env + home + proj(.agents+skills)  -> project  | override from proj/skills
(proj/skills 삭제 후)               -> project  | override from proj/.agents/skills
```

주의할 점:
- `INKOS_SKILL_DIRS`는 이름과 달리 **사용자·프로젝트 스킬보다 우선순위가 낮다.** 한국어 스킬을 환경 변수로 주입하면
  사용자가 `~/.agents/skills`에 둔 같은 ID가 이긴다.
- 스킬은 **프로젝트 단위**로 로드된다(`projectRoot`만 받음). 작품(book) 언어는 로더에 전달되지 않는다.
  한 프로젝트에 zh/en/ko 작품이 섞이면 "프로젝트 폴더에 복사" 방식으로는 작품별 선택이 안 된다.
- 같은 ID 하나만 남으므로, 한국어판이 원본을 덮으면 그 프로젝트의 영어·중국어 작품도 한국어 스킬을 받는다.

### 한국어 스킬 연결 방식 (2단계 방침 제안)

| 안 | 방식 | 장점 | 단점 |
|---|---|---|---|
| A | `inkos init --lang ko`가 `skills-ko/`를 `<project>/.agents/skills/`에 복사 | 원본 코드 수정 0, 사용자가 보고 고칠 수 있음 | 프로젝트 단위(혼합 프로젝트 불가), 포크 업데이트 시 복사본이 낡음 |
| B | 로더가 작품 언어를 받아 `ko`일 때 `packages/core/skills-ko/`를 builtin 바로 위에 끼움 | 작품별 선택, 업데이트 자동 반영 | `loadAvailableAgentSkills` 호출 지점 15곳에 언어 전달 필요(아래), 원본 수정 큼 |
| C | B의 축소판: `loadAvailableAgentSkills`에 선택적 `language` 인자 추가, 프로젝트 `inkos.json`의 `language`가 `ko`면 `skills-ko` 삽입 | 수정이 로더 1곳 + 설정 읽기, 사용자 스킬이 여전히 이김 | 프로젝트 단위(A와 같음) |

**권장: C로 시작.** 이유: 원본 수정이 가장 작고(새 파일 `skills/korean-skill-root.ts` + 로더 몇 줄), 사용자·프로젝트 스킬
덮어쓰기 규칙을 그대로 유지하며, 실제 사용(한국어 전용 프로젝트)에 맞는다. 혼합 프로젝트가 필요해지면 B로 넓힌다.
`loadAvailableAgentSkills` 호출 지점(테스트 제외): core `agents/base.ts:134`, `agents/style-guide.ts:20`,
`agents/import-context.ts:39`, `pipeline/runner.ts:439`, `pipeline/short-fiction-runner.ts:1071`,
`play/play-image.ts:223`, `harness/tools/artifact-methods.ts:195`, `harness/tools/short-production.ts:37`,
`agent/agent-session.ts:834`, cli `utils.ts:37`, `commands/short-fiction.ts:90`, `commands/translate.ts:69`,
studio `api/server.ts:196,934,1138,3979,6473`. C안은 로더 내부에서 `projectRoot/inkos.json`을 읽으므로 이 호출 지점을 바꾸지 않는다.

### references가 프롬프트에 들어가는 방식 (장르 references 설계에 중요)

`agent/skill-tool.ts` `hydrateActivatedSkillGuidance()`:
1. SKILL.md 본문에 `` `references/….md` `` 또는 `](references/….md)` 형태로 **직접 링크된 파일은 항상 전부** 들어간다(`loadLinkedSkillResources`).
2. 링크되지 않은 references는 작업 문장(user 메시지)으로 SQLite FTS5 검색해 상위 4조각만 들어간다(`retrieveSkillResources`, limit 4).

한국어 위험: 검색 토크나이저(`retrieval/local-search.ts` `tokenizeSearchText`)는 `Intl.Segmenter` 단어 단위라
한국어 어절을 조사째 한 토큰으로 본다("무협의" ≠ "무협"). 중국어용 한자 bigram 보정은 있지만 한글 보정은 없다.
→ 한국어 references를 검색에 맡기면 잘 안 걸린다. **장르 references는 검색이 아니라 결정론적으로 넣어야 한다.**

## 3. 작업 프로필과 장르

### 프로필 구조
- 정의: `harness/builtin-profiles.ts` `PROFILE_INPUTS`(9개: workspace-default, longform-novel, short-fiction, script,
  storyboard, interactive-film, interactive-world, translation, visual-asset). 스키마: `harness/contracts.ts` `WorkProfileSchema`.
- 프로젝트별 추가·교체: `<project>/.inkos/profiles/*.json`을 `registry.replace()`로 읽는다(`createBuiltInWorkProfileRegistry`).
  즉 코드 수정 없이도 프로필을 넣을 수 있다. 단 `.inkos/`는 `.gitignore` 대상이라 포크에 실으려면 builtin에 넣는 편이 맞다.
- 프로필 → 능력(capability): `capabilityIds`. 능력의 도구는 `harness/production-capabilities.ts`가 등록한다.
- `script` 프로필: `capabilityIds: [workspace, script, adaptation, visual]`, `requiredSkillIds: [inkos-script-writing]`,
  `artifactKinds: [script-spec, script]`. 도구는 `script_create` 하나(`agent/agent-tools.ts:1852` `createScriptCreationTool`
  → `pipeline/script-storyboard-runner.ts` `runScriptCreation`). `targetFormat`은 자유 문자열이며 내장 값은
  `vertical_short_drama`, `screenplay`, `audio_drama`, `interactive_script`, `general_script`(`agents/script-storyboard.ts:494`).
  `createScriptCreationTool`의 `language` 타입이 `"zh" | "en"`이다.
- **CLI에 대본 명령이 없다.** `packages/cli/src/commands/`에 script 명령이 없고, 대본은 에이전트 대화(`inkos interact`/`agent`)나
  Studio의 `script_create` 도구로만 만든다. 브리지 원칙("명시적 CLI 동작 우선")과 충돌하므로 2-2단계에서
  `inkos script create` 같은 얇은 CLI 명령을 새 파일로 추가하는 것을 검토한다.

### `explainer-script` 프로필을 넣으려면 고칠 곳
1. `harness/builtin-profiles.ts` `PROFILE_INPUTS`에 항목 추가(새 capability id 또는 `script` 재사용, `requiredSkillIds: [inkos-ko-explainer-script]`).
2. 산출물 형식을 검사하려면 `contracts.ts` `artifactSchemas` enum에 새 값 추가 + `harness/artifact-validation.ts`에 검사기.
3. 도구: `script` capability를 재사용하면 `script_create`가 쓰는 `runScriptCreation`의 프롬프트가 드라마용이다.
   설명 영상은 장면 표(초·내레이션·화면·레퍼런스·출처)라 **새 capability + 새 runner(새 파일)**가 깔끔하다.
   등록: `production-capabilities.ts` `registerToolCapability(...)`, `CONFIRMED_CAPABILITY_BINDINGS`, `proposalActionForProfile`.
4. `interaction/action-envelope.ts`의 `RequestedIntent`/payload 스키마에 새 intent 추가(대화 경로를 쓸 경우).
5. 스킬 `packages/core/skills/inkos-ko-explainer-script/` 또는 `skills-ko/`.

### 장르 값
- `models/book.ts` `GenreSchema = z.string().min(1)` — **자유 문자열이고 장르 목록·장르 프로필이 없다.**
  쓰이는 곳은 프롬프트 문자열 삽입뿐(`agents/architect.ts:69,136`, `agents/writer-prompts.ts:19,28` 등).
- CLI 기본값은 `xuanhuan`(`cli/src/commands/book.ts`), 플랫폼 기본값 `tomato`.
- 스킬 선택에 쓰는 장치는 없지만, 같은 모양의 선례가 있다: `skills/activations.ts` `WORK_CREATION_SKILLS`가
  `work.metadata.creationKind`(fanfic 등) → 필수 스킬 ID를 결정론적으로 붙인다.
- **장르 값 제안(2-1단계 확정 전 사용자 확인 불필요한 기술 결정):** `light-martial`, `fantasy`, `modern-fantasy`.
  영문 소문자 ID로 두는 이유: 파일 이름·스킬 ID와 맞추기 쉽고, 한국어 표시는 UI에서 붙인다.
  연결은 `activations.ts`와 같은 방식의 새 파일 `skills/korean-genre-references.ts`가 `language === "ko"`이고
  장르가 위 셋 중 하나일 때 `inkos-long-writing`(한국어판) 활성화에 해당 `references/genres/<장르>.md`를
  링크 리소스로 더하는 방식. 검색(FTS)에 맡기지 않는다(위 한국어 토크나이저 위험).

## 4. 언어 분기 전수 조사 — 종합

계획서의 검색식 `rg -n 'language (===|!==) "(zh|en)"|isEn\b|isZh\b|"zh" \| "en"'`(테스트 제외)은 **558줄 / 76파일**에 걸린다.
상세 표는 부록 A~C(구문 단위로 묶어 core agents 127행, core 나머지 91행, cli·studio 83행).

**검색식이 놓치는 분기가 많다.** `resolvedLanguage === "en"`, `lang === "en"`, 공백 없는 `language==="en"`, 작은따옴표 `'en'`,
`countingMode === "en_words"`, `locale === "en"`, `t("nav.connected") === "已连接"` 같은 형태가 빠진다.
넓힌 검색식 `rg -c "[=!]==\s*[\"'](en|zh)[\"']"`은 **305줄 / 67파일**(부록 D). 1단계는 이 넓힌 목록과
"ko를 넣으면 타입 오류가 나는 곳"을 함께 기준으로 삼는다.

### 처리 방침 (1단계에 적용)

| 분류 | 방침 | 이유 |
|---|---|---|
| PROMPT (모델에게만 보이는 지시문) | **영어 경로 공유** + 한국어 출력 지시 1곳 주입 | 한국어로 번역해도 품질 이득이 불확실하고 원본 파일 수정이 커진다. 단 "Respond in English." 같은 **출력 언어 지시는 반드시 ko 분기**. |
| COUNT (분량 단위) | **별도 분기** `ko_chars` | 영어 경로(`en_words`, `[A-Za-z0-9]+`만 셈)를 타면 한국어 원고 분량이 0에 가깝게 계산된다. |
| PARSE (회차 제목·태그 파싱) | **별도 분기** | `제N화`/`N화`를 인식해야 한다. |
| FORMAT (저장 파일에 남는 제목·표·라벨) | **별도 분기** (한국어 문구) | 한국어 작품 폴더에 영어/중국어 표제가 저장되면 안 된다. |
| UI (오류·진행 문구, 화면) | **별도 분기** (4단계에서 일괄, 1단계는 저장 파일에 들어가는 것만) | |
| TYPE (`"zh" \| "en"` 유니온·zod enum) | `ko` 추가 | 공용 타입 `WritingLanguage = "zh" \| "en" \| "ko"`를 새 파일에 두고 재사용. |

구조 권고: 흩어진 삼항식을 직접 고치지 말고, 새 파일(`utils/korean-language.ts` 등)에 용도별 도우미를 둔다 —
`promptLanguage(lang)`(ko→en), `countingModeFor(lang)`(ko→ko_chars), `chapterLabel(lang, n)`(ko→제N화), `outputLanguageDirective(lang)`.
원본 파일에서는 해당 삼항식을 도우미 호출로만 바꾼다(zh/en 결과는 그대로).

### 가장 위험한 곳 (세 조사 종합, 표본 직접 확인한 것은 ✔)

1. **분량 계산** ✔ `agents/writer.ts:258` `resolvedLanguage === "en" ? "en_words" : "zh_chars"` — 원본은 ko→zh_chars, 기존 패치는 `!== "zh"`로 ko→en_words(한국어 거의 0). `ko_chars` 분기 필수.
2. **ko가 중국어로 접힘** — `harness/production-capabilities.ts:188`, `harness/tools/short-production.ts:34`, `harness/artifact-validation.ts:66,75`(`=== "en" ? "en" : "zh"`), studio `BookCreate.tsx:204`, `server.ts:2934/2942/2955`, cli `localize`·TUI `getTuiCopy` 등. 타입만 넓히면 컴파일 오류 없이 중국어가 나온다.
3. **출력 언어 지시** ✔ `agents/state-validator.ts:42-44`는 패치 후에도 ko에 "Respond in English." 메인 에이전트(`harness/system-prompt.ts`)는 패치의 한국어 지시 주입(`agents/base.ts` `prepareWorkerMessages`) 밖에 있다.
4. **회차 표기 혼재** — 패치의 utils는 `제N화`, `agents/short-fiction.ts:171,658`·`agents/import-context.ts`는 `Chapter N`.
5. **단편 분량** ✔ 패치의 `!== "zh"`로 ko 단편 생성이 영어 단어 상수 650(`SHORT_FICTION_EN_DEFAULT_WORDS_PER_CHAPTER`)을 ko_chars로 써서 장당 650자, 수정 경로(`short-fiction-runner.ts:729`)는 미변경이라 1000자 — 생성과 수정 목표가 다르다.
6. **패치가 zh/en 기본값을 바꾼다** ✔ (원칙 1 위반 → 1단계에서 되돌림): `cli/commands/agent.ts`·`interact.ts` `config.language ?? "ko"`, `init.ts`·`short-fiction.ts` `--lang` 기본 `ko`, `studio.ts` 새 프로젝트 `ko`, `localization.ts` `resolveCliLanguage` 최종 기본 `ko`, `project-bootstrap.ts`, `tui/setup.ts` autoInit `ko`, `book.ts` `--platform` 기본 `tomato` 삭제, `export.ts` `book.language ?? "ko"`와 zh 분량 표시 변경, `init.ts` 안내문 재작성. 패치의 `korean-cli.test.ts`도 "새 프로젝트 기본값 = ko"를 고정한다.
7. **Studio의 한국어 경로가 실제로 닿지 않음** — 헤더 `한국어` 버튼을 눌러도 `PUT /api/v1/project`(`server.ts:4125`)가 zh/en만 저장, 인라인 `tr()` 312곳 중 ko 인자 0, `isZh = t("nav.connected") === "已连接"` 추측식은 ko에서 영어, ImportManager 언어 select에 ko 없음. TUI(`tui/i18n.ts`, `effects.ts`, `setup.ts`)는 패치 미변경.
8. **회차 분할 오탐** — 패치의 한국어 제목 정규식은 `#`·`제`·구분자가 모두 선택이라 "3장의 편지…" 같은 본문 줄도 경계로 자를 수 있고, 프롤로그·에필로그·외전 미지원.
9. **작품 ID 규칙 변경이 zh/en에도 적용** — 패치의 NFC + `\p{L}\p{N}` 규칙은 악센트·키릴 제목의 기존 ID 계산을 바꾼다. 한글 범위만 더하는 쪽이 보수적. `memory-retrieval`의 권 anchor slug는 한글 제목이 모두 `volume-summary`로 겹친다.
10. **언어 정보 손실** — `agent/agent-session.ts:1329`가 ko를 `"en"`으로 저장, `languageFromLengthSpec` 등 분량 단위에서 언어를 역추정하는 곳.
11. **내보내기** — `translation/export.ts`의 EPUB `lang`에 언어 이름("Korean")이 들어감(BCP 47 아님). `DEFAULT_CHAPTER_LENGTH_KO`가 `index.ts`에서 export되지 않음.
12. **스키마 호환** — `book.json`·runtime manifest의 zod enum에 `ko`/`ko_chars`를 넣으면, 패치 없는 원본 InkOS가 한국어 작품 폴더를 열 때 parse 실패한다(포크 전용 작품이 되는 것은 감수할 차이로 기록).

## 5. 1단계 전에 사용자에게 확인할 것

- **회당 분량 기준(미정)**: 공백 포함/제외, 기본 목표 글자 수, 플랫폼별 프리셋. 현재 패치 값은 `ko_chars`(메타데이터 제거 → NFC → 공백 제거 → 코드 포인트 수) 3,000자.
  참고: 공백 제외 3,000자는 대략 공백 포함 3,600~3,800자다(어절 평균 길이로 추정한 값, 실측 아님).
- Studio 첫 실행 화면에 ko 카드를 맨 앞에 두는 등 **zh/en 사용자에게도 보이는 화면 변경**을 허용할지(원칙 1과 충돌). 허용하지 않으면 ko 카드를 맨 뒤에 추가만 한다.

## 6. 원본 수정 범위 (원본 업데이트를 받을 때의 충돌 범위, 2026-10-25 측정)

측정: `git diff --numstat 53adac4 HEAD -- packages`(원본 master 기준, 작업 트리 기준 커밋 `(stage 4-1 fix)`). 앞선 보고의 "분기 몇 줄씩"은 틀린 표현이었다
(감독 지적). 실제로는 아래와 같고, 대부분은 1단계에서 그대로 적용한 기존 패치의 몫이다.

| 구분 | 파일 수 | 줄 |
| --- | --- | --- |
| 원본 파일 수정(충돌 가능) — 대상 밖 정리 전 | 87 | +801 / −482 |
| 원본 파일 수정(충돌 가능) — **현재** | **79** | **+773 / −450** |
| 새 파일(충돌 없음: `korean-*.ts`, `skills-ko/`, 한국어 테스트 등) | 43 | +2,785 |

현재 원본 파일 수정의 영역별 분포:

| 영역 | 파일 | 줄 |
| --- | --- | --- |
| `core/src/agents` | 17 | +199 / −161 |
| `core/src/utils` | 9 | +62 / −28 |
| `cli/src/commands` | 7 | +63 / −20 |
| `core/src/pipeline` | 6 | +84 / −51 |
| `core/src/harness` | 6 | +24 / −10 |
| `core/src/models` | 4 | +4 / −4 |
| `core/src/interaction` | 4 | +11 / −11 |
| `studio/src/pages` | 3 | +47 / −15 |
| `studio/src/api` | 3 | +29 / −17 |
| `core/src/state` | 3 | +35 / −18 |
| `core/src/agent` | 2 | +33 / −32 |
| `studio/src/shared` | 1 | +1 / −1 |
| `studio/src/lib` | 1 | +7 / −3 |
| `studio/src/hooks` | 1 | +9 / −3 |
| `studio/src/App.tsx` | 1 | +5 / −0 |
| `core/src/skills` | 1 | +7 / −3 |
| `core/src/references` | 1 | +1 / −1 |
| `core/src/prompts` | 1 | +35 / −31 |
| `core/src/llm` | 1 | +3 / −3 |
| `core/src/index.ts` | 1 | +10 / −1 |
| `core/src/forecast` | 1 | +2 / −1 |
| `core/package.json` | 1 | +2 / −1 |
| `cli/src/tui` | 1 | +22 / −20 |
| `cli/src/project-bootstrap.ts` | 1 | +2 / −2 |
| `cli/src/program.ts` | 1 | +3 / −0 |
| `cli/src/localization.ts` | 1 | +73 / −13 |

수정이 큰 파일: `cli/src/localization.ts`(+73/−13, ko 문구), `core/src/pipeline/runner.ts`(+41/−13), `core/src/prompts/short-fiction.ts`(+35/−31),
`core/src/agent/agent-tools.ts`(+31/−30), `core/src/agents/script-storyboard.ts`(+31/−27), `core/src/agents/writer.ts`(+30/−23),
`studio/src/pages/BookCreate.tsx`(+29/−7), `core/src/agents/architect.ts`(+27/−24). 줄 수의 대부분은 `"zh" | "en"` 유니온에 `"ko"`를 더하거나
`=== "en"`을 `!== "zh"`로 바꾼 한 줄 변경이라 충돌은 넓게 흩어지지만 각각은 작다. 원본 업데이트를 받을 때는 이 79개 파일을 대조한다.

### 대상 밖 변경 정리

대상 기능(장편·단편·대본·설명 영상·내보내기) 밖인 **인터랙티브 플레이, 인터랙티브 필름, 서사 예측**의 패치 변경을 원본으로 되돌렸다.

| 파일 | 처리 |
| --- | --- |
| `core/src/play/play-agents.ts`, `play-runner.ts`, `play-store.ts` | 원본으로 되돌림 |
| `core/src/agent/film-authoring-tools.ts` | 원본으로 되돌림 |
| `core/src/forecast/agent.ts`, `prompts.ts`, `schema.ts` | 원본으로 되돌림 |
| `studio/src/components/chat/NarrativeForecastPreview.tsx` | 원본으로 되돌림 |
| `core/src/forecast/context-builder.ts` | 1줄만 남김: 책 언어를 넘길 때 `upstreamLanguage()` |

이 기능들에 ko가 넘어가는 지점 4곳(`agent-tools.ts` 플레이 세계 생성, `production-capabilities.ts` 필름 도구, `studio/src/api/server.ts` 필름 구조 도구,
`forecast/context-builder.ts`)은 `utils/korean-language.ts`의 `upstreamLanguage()`(ko→en)로 명시적으로 바꿔 넘긴다. 동작은 기존 패치의
`!== "zh"`와 같다(ko 작품의 플레이·필름·예측은 영어 경로). 한국어 플레이 세계는 `language: "en"`으로 저장된다. 한국어화가 필요해지면 그때 별도 단계로 다룬다.

되돌리지 않은 것과 이유:
- Studio 화면 일부(`App.tsx`, `pages/*`, `hooks/use-i18n.ts`, `lib/app-language.ts`, `api/book-create.ts`): 사용자 결정(화면 한국어·영어 선택)에 해당하고,
  ko 작품 생성 경로(`BookCreate.tsx`, `server.ts`)가 쓰고 있다.
- 단편(`prompts/short-fiction.ts`, `agents/short-fiction.ts`, `pipeline/short-fiction-runner.ts`): 계획서 2단계 스킬 우선순위(`inkos-short-writing`)에 들어 있다.
- `interaction/*`, `state/*`, `utils/*`: 장편 저장·내보내기 경로라 대상 안이다.

## 부록 A. core agents·prompts·harness·forecast


범위: `packages/core/src/{agents,prompts,harness,forecast}`의 테스트 제외 .ts 파일 중
`rg -n 'language (===|!==) "(zh|en)"|isEn\b|isZh\b|"zh" \| "en"'`에 걸린 193줄. 한 구문에 속한 인접 줄은 한 행으로 묶었다. composer.ts의 순수 타입 유니온 11곳은 한 행으로 묶었다.
전제: 모든 worker 에이전트(BaseAgent·runWorkerAgent)는 `prepareWorkerMessages`(agents/base.ts)를 거친다. 기존 패치는 여기서 ko 작성 지시(`applyProjectLanguagePolicy`, 한국어 작성 + ko_chars 계수 지시)를 주입한다. 그래서 모델에게만 보이는 영어 지시문은 SHARE_EN으로 판정했다. harness 메인 에이전트(system-prompt.ts)는 이 주입 경로 밖에 있다.
"기존 패치" 열의 `!==zh`는 `language === "en"`을 `language !== "zh"`로 바꿔 ko가 en 경로로 가게 했다는 뜻이다.

| 파일:줄 | 현재 동작 | 분류 | ko 방침 | 기존 패치 |
|---|---|---|---|---|
| agents/settler-prompts.ts:7 | settler 시스템 프롬프트의 language 파라미터 타입 | TYPE | KO_BRANCH: 유니온에 ko 추가 | ko 추가 |
| agents/settler-prompts.ts:9-12 | 전체 인물 추적 지시를 zh/en 중에서 선택 | PROMPT | SHARE_EN: 모델 전용 지시. 한국어 출력은 정책 주입으로 처리 | !==zh |
| agents/settler-prompts.ts:14-16 | settler 시스템 프롬프트 zh/en | PROMPT | SHARE_EN | !==zh |
| agents/settler-prompts.ts:26 | settler user 프롬프트 params 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/settler-prompts.ts:28-35 | isEnglish로 user 프롬프트 제목과 첫 줄 선택(第N章「」 vs Chapter N) | PROMPT | SHARE_EN | !==zh |
| agents/planner.ts:61-63 | 지시가 없을 때의 기본 taskGoal(续写第N章 vs Continue chapter N) | PROMPT | SHARE_EN | !==zh |
| agents/planner.ts:124 | planChapterMemo 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/planner-prompts.ts:4-6 | 플래너 memo 시스템 프롬프트 zh/en(+타입) | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/planner-prompts.ts:19 | 플래너 user 메시지 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/planner-prompts.ts:25-33 | memo 요청 user 메시지(第N章 memo 请求 / 宿主字数遥测) | PROMPT | SHARE_EN: 단위는 lengthBudget.unit 값을 그대로 쓴다. ko에서 '자'가 넘어오는지 확인 필요 | !==zh |
| agents/fanfic-canon-importer.ts:20 | importFromText의 language 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/fanfic-canon-importer.ts:23-27 | 동인 정사 컴파일 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/fanfic-canon-importer.ts:30-32 | user 메시지의 원작 소재 라벨 | PROMPT | SHARE_EN | !==zh |
| agents/fanfic-canon-importer.ts:45-47 | 저장되는 fanfic_canon.md의 제목(同人正典/来源/素材/同人模式/正典内容) | FORMAT | KO_BRANCH: "동인 정사/출처/소재/동인 모드/정사 내용". 49줄의 전각 괄호（）도 ko에서는 일반 괄호로 | !==zh(영어 제목이 저장됨) |
| agents/fanfic-canon-importer.ts:65 | prepareSourceText 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/fanfic-canon-importer.ts:79-81 | 청크 컴파일 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/fanfic-canon-importer.ts:86-87 | 청크 user 라벨(原作/片段) | PROMPT | SHARE_EN | !==zh |
| agents/fanfic-canon-importer.ts:103-108 | 압축 자료 패키지 머리말(모델 입력) | PROMPT | SHARE_EN | !==zh |
| agents/writer.ts:88-89 | localize(): 로그 메시지 zh/en 선택 | UI | SHARE_EN: 영어 로그 허용. 장기적으로는 messages에 ko 키 추가 | !==zh |
| agents/writer.ts:92,96 | logInfo/logWarn 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/writer.ts:275 | settle 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/writer.ts:367 | saveChapter language를 renderChapterDocument·state 렌더러로 전달 | TYPE | KO_BRANCH: ko 추가. 하위 렌더러(utils)에서 "# 제N화: 제목"과 한국어 state 라벨 필요 | ko 추가(utils 쪽에 제N화) |
| agents/writer.ts:460 | buildUserPrompt params 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/writer.ts:475-477 | 사용자 방향 블록 제목 | PROMPT | SHARE_EN | !==zh |
| agents/writer.ts:484-497 | writer user 프롬프트(请续写第N章 vs Write chapter N) | PROMPT | SHARE_EN | !==zh |
| agents/writer.ts:513-516 | 회차별 사용자 지시 블록 | PROMPT | SHARE_EN | !==zh |
| agents/writer.ts:531-536 | settler 통제 입력 블록 | PROMPT | SHARE_EN | !==zh |
| agents/writer.ts:551-556 | 길이 요구 블록: zh는 "字·공백 제외 문자", en은 "words" | COUNT | KO_BRANCH: "목표 N자(공백 제외, ko_chars)" | !==zh(ko에 "words"가 노출되어 정책 주입과 모순) |
| agents/writer.ts:631,666 | runtime state 아티팩트 빌더 language 타입(state md 렌더) | TYPE | KO_BRANCH: ko 추가. 하위 state 렌더러에 ko 라벨 | ko 추가 |
| agents/composer.ts:62,76,166,338,369,594,742,783,848,920,945 | 각종 요청 인터페이스·헬퍼의 language 타입 | TYPE | KO_BRANCH: ko 추가(공용 타입으로 통일 권장) | ko 추가 |
| agents/composer.ts:429-431 | 아웃라인·역할 카드 선택 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/composer.ts:457-459 | 참고자료 선택 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/composer.ts:511-517 | semanticCandidateLabel(role cards/角色卡 등) | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/composer.ts:863-864 | 참조 훅의 role/promise 라벨(备忘引用伏笔/（未写明）) | PROMPT | SHARE_EN | !==zh |
| agents/composer.ts:874-880 | 참조 훅 컨텍스트 reason/excerpt | PROMPT | SHARE_EN: 컨텍스트 트레이스에 영어로 남는 것은 허용 | !==zh |
| agents/architect.ts:132 | foundation 프로토콜 params 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/architect.ts:135-137 | 작품 메타데이터 블록(平台/题材/每章字数) | PROMPT | SHARE_EN: "Chapter length"에 단위가 없으니 ko는 '자' 명시 권장(낮음) | !==zh |
| agents/architect.ts:138-140 | foundation 생성 프로토콜 | PROMPT | SHARE_EN | !==zh |
| agents/architect.ts:145 | writeFoundationFiles 언어를 createInitialRuntimeState로 전달(초기 state 파일) | TYPE | KO_BRANCH: ko 추가. 초기 state 렌더러 ko 처리 | ko 추가 |
| agents/architect.ts:265 | generateFoundationInStages 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/architect.ts:276-279 | 도구 label/description(提交基础框架) | UI | SHARE_EN | !==zh |
| agents/architect.ts:288-290 | 세부 단계 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/architect.ts:298-301 | 도구 label/description(提交基础详情) | UI | SHARE_EN | !==zh |
| agents/architect.ts:347-352 | 이전 검토 피드백 블록 | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/state-validator.ts:35 | validate의 language 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/state-validator.ts:42-44 | 응답 언어 지시 "Respond in English." vs "用中文回答。" | PROMPT | KO_BRANCH: "한국어로 답하라." en을 공유하면 영어 응답을 명시적으로 강제하게 된다 | !==zh(ko에 "Respond in English."가 남음, 위험) |
| agents/state-validator.ts:78 | 도구 label(提交状态对账) | UI | SHARE_EN | !==zh |
| agents/short-fiction.ts:88-90 | 저장되는 판매 패키지 md 제목(简介/卖点/封面提示词) | FORMAT | KO_BRANCH: "## 소개/## 셀링 포인트/## 표지 프롬프트" | !==zh(영어 제목이 저장됨) |
| agents/short-fiction.ts:171 | 아웃라인의 회차별 계획 제목 "## 第N章" vs "## Chapter N"(저장) | FORMAT | KO_BRANCH: "## 제N화" | !==zh(Chapter N) |
| agents/short-fiction.ts:638 | 초고 md의 오프닝 훅 제목(开篇钩子) | FORMAT | KO_BRANCH: "## 오프닝 훅"(또는 "## 도입 장면") | !==zh |
| agents/short-fiction.ts:658 | 단편 회차 제목 "第N章 제목" vs "Chapter N: 제목" | FORMAT | KO_BRANCH: "제N화 제목". utils renderChapterDocument·chapter-splitter의 제N화와 일치시켜야 함 | !==zh(Chapter N이 되어 utils의 제N화와 불일치) |
| agents/writer-prompts.ts:12 | languageOverride 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/writer-prompts.ts:17-35 | writer 시스템 프롬프트 섹션 묶음(本书规则/文风指南 라벨 포함) | PROMPT | SHARE_EN | !==zh |
| agents/writer-prompts.ts:39-40 | 권위 순서 계약 | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/writer-prompts.ts:47-48 | 길이 계약 "N words" vs "N 字" | COUNT | KO_BRANCH: "목표 N자(공백 제외)" | !==zh(words) |
| agents/writer-prompts.ts:53-56 | 서술 인칭 계약 | PROMPT | SHARE_EN | !==zh |
| agents/writer-prompts.ts:60-67 | 주인공 권위 블록과 구분자(、/；) | PROMPT | SHARE_EN: ", " / "; " 구분자는 한국어에도 무난 | !==zh |
| agents/reviser.ts:40 | reviseChapter options 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/reviser.ts:52(57-70) | isEnglish로 관찰 목록, 길이 계약 unit "words", user 프롬프트(修订第N章) 선택 | COUNT | KO_BRANCH: lengthBlock의 unit만 "공백 제외 글자(ko_chars)"로. 나머지는 en 공유 | !==zh(ko_chars 수치에 unit:"words"가 붙음) |
| agents/reviser.ts:167-177 | 수정 프로토콜 시스템 프롬프트(+타입) | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/semantic-context-compiler.ts:10 | 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/semantic-context-compiler.ts:40-42 | 청크 컴파일 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/semantic-context-compiler.ts:47-48 | 의도·청크 라벨 | PROMPT | SHARE_EN | !==zh |
| agents/semantic-context-compiler.ts:65-67 | 예산 재압축 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/semantic-context-compiler.ts:71 | Token 예산 라벨 | PROMPT | SHARE_EN | !==zh |
| agents/continuity.ts:34 | audit options 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/continuity.ts:39-41(84-85) | 감사 시스템 프롬프트·도구 라벨(isEnglish) | PROMPT | SHARE_EN | !==zh |
| agents/style-guide.ts:13 | 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/style-guide.ts:29-31 | 문체 가이드 컴파일 시스템 프롬프트. 결과는 style_guide.md로 저장 | PROMPT | SHARE_EN: 산출물 언어는 정책 주입으로 한국어 | !==zh |
| agents/style-guide.ts:35-37 | 출처 라벨(来源/参考文本) | PROMPT | SHARE_EN | !==zh |
| agents/import-context.ts:16-20 | renderCompleteImportSource 회차 라벨 "第N章" vs "Chapter N:"(foundation 원천이 되는 모델 입력) | FORMAT | KO_BRANCH: "제N화 제목". foundation 문서로 Chapter 표기가 옮겨 가는 것을 방지 | 유니온 ko + !==zh |
| agents/import-context.ts:29 | compileImportSource 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/import-context.ts:52-54 | 임포트 컴파일 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/import-context.ts:63 | 컴파일된 청크 제목(编译源片段) | PROMPT | SHARE_EN | !==zh |
| agents/import-context.ts:65-67 | 장 목록 "- 第N章：" vs "- Chapter N:" | FORMAT | KO_BRANCH: "- 제N화: 제목" | !==zh |
| agents/import-context.ts:70-72 | 문서 제목과 장 목록 제목 | PROMPT | SHARE_EN | !==zh |
| agents/script-storyboard.ts:17,30,44 | Script/Storyboard/InteractiveFilm 입력 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/script-storyboard.ts:54 | recoverProductionMarkdown 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| agents/script-storyboard.ts:60-72 | 출력 복구 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| agents/script-storyboard.ts:77,80 | 필수 제목·출력 조각 라벨 | PROMPT | SHARE_EN | !==zh |
| agents/script-storyboard.ts:107 | 대본 필수 제목 "## Characters/## Script" vs "## 人物/## 剧本正文"(복구 검증에 쓰이고 script.md에 저장) | PARSE | KO_BRANCH: "## 등장인물/## 대본". 309·324 프롬프트와 반드시 함께 변경. 영어 제목을 유지하기로 한다면 세 곳 모두 SHARE_EN | !==zh(영어 제목) |
| agents/script-storyboard.ts:171-172 | productionBrief의 en 플래그(작가 요청·제작 개요 제목) | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/script-storyboard.ts:308-309 | 대본 시스템 프롬프트(정확한 제목 계약 포함) | PROMPT | KO_BRANCH: 107의 제목 결정에 따름. 나머지 문장은 en 공유 가능 | 유니온 ko + !==zh |
| agents/script-storyboard.ts:323-324 | 대본 user 프롬프트(renderScriptSpec와 제목 템플릿) | PROMPT | SHARE_EN: 제목 템플릿은 107과 연동 | 유니온 ko + !==zh |
| agents/script-storyboard.ts:361-362 | 스토리보드 시스템 프롬프트 | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/script-storyboard.ts:374-378 | 스토리보드 user 프롬프트·최대 샷 규칙 | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/script-storyboard.ts:415-416 | 인터랙티브 영화 시스템 프롬프트 | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/script-storyboard.ts:430-431 | 인터랙티브 영화 user 프롬프트 | PROMPT | SHARE_EN | 유니온 ko + !==zh |
| agents/script-storyboard.ts:492-497 | formatScriptTarget 납품 형식 라벨(저장되는 *-spec.md) | FORMAT | KO_BRANCH: "세로형 숏드라마/시나리오/오디오 드라마…". render*Spec의 ko 분기와 함께 | 유니온 ko + !==zh(호출부 render*Spec 183/222/259는 미수정이라 ko는 zh) |
| agents/script-storyboard.ts:527-529 | summarizeSourceForSpec 원문 요약 "about N characters"(spec 저장) | FORMAT | KO_BRANCH: "원문 약 N자 제공" | 유니온 ko + !==zh |
| prompts/short-fiction.ts:3 | ShortFictionLanguage 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| prompts/short-fiction.ts:35-37 | 아웃라인 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:43 | 창작 방향 제목 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:47-50 | 목표: "about N words per chapter" vs "每章约 N 字" | COUNT | KO_BRANCH: "회차당 약 N자(공백 제외)" | !==zh(words) |
| prompts/short-fiction.ts:51 | 참고자료 제목 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:55-57 | 단편 writer 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:64-66 | 과제: "about N words each" vs "每章约 N 字" | COUNT | KO_BRANCH: "회차당 약 N자" | !==zh(words) |
| prompts/short-fiction.ts:70-71 | 회차 최대·최소 길이 "words" vs "非空白字符(含标点)" | COUNT | KO_BRANCH: "공백 제외 N자(문장부호 포함)" | !==zh(words) |
| prompts/short-fiction.ts:73,76,78 | 방향·계획·이전 회차 제목 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:82-84 | 초고 검토 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:89-92 | 검토 user 제목들 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:96 | 검토 대상 원고 제목 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:101-103 | 패키지 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| prompts/short-fiction.ts:108-111 | 패키지 user 제목들 | PROMPT | SHARE_EN | !==zh |
| harness/production-capabilities.ts:188 | 환경 언어를 en/zh로 정규화(ko는 zh)해 제안 도구와 모든 생산 도구에 전달 | OTHER | KO_BRANCH: ko를 그대로 전달. 지금은 ko 작품 전체가 중국어 경로로 간다 | ko 분기 추가 |
| harness/artifact-validation.ts:66 | 판매 패키지 md 렌더 언어(ko는 zh라 중국어 제목이 저장됨) | FORMAT | KO_BRANCH: ko 전달 + 렌더러에 ko 제목 | ko 분기 추가(렌더러는 ko를 영어로 처리) |
| harness/artifact-validation.ts:75 | 단편 초고 charCount 계수 모드(ko는 zh_chars) | COUNT | KO_BRANCH: ko_chars(NFC). zh_chars도 공백 제외 길이라 수치는 거의 같다 | ko 분기 추가 |
| harness/tools/longform-production.ts:18 | 도구 옵션 language 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가(132줄 activeWork 정규화도 ko 분기) |
| harness/tools/short-production.ts:32-34 | Work 언어를 en/zh로 정규화(ko는 zh)해 단편 파이프라인 전체에 전달 | OTHER | KO_BRANCH: ko 그대로 전달 | ko 분기 추가 |
| harness/system-prompt.ts:15 | isZh 정의(=== "zh"라 ko는 자동으로 en 경로) | OTHER | SHARE_EN | 미수정 |
| harness/system-prompt.ts:17-31 | 현재 작품·확인된 동작·재개 문구 | PROMPT | SHARE_EN | 미수정 |
| harness/system-prompt.ts:34 | 메인 harness 에이전트 base 프롬프트 | PROMPT | KO_BRANCH(최소): "사용자에게 한국어로 응답" 한 줄 추가. worker 정책 주입 경로 밖이다 | 미수정 |
| harness/system-prompt.ts:102,109 | appendSkillGuidance에 isZh 전달 | OTHER | SHARE_EN | 미수정 |
| harness/system-prompt.ts:113 | 강제 스킬 라벨(强制/forced) | PROMPT | SHARE_EN | 미수정 |
| harness/system-prompt.ts:130 | 강제 스킬 섹션 제목 | PROMPT | SHARE_EN | 미수정 |
| harness/system-prompt.ts:134-135 | 의도별 스킬 카탈로그 제목·설명 | PROMPT | SHARE_EN | 미수정 |
| harness/system-prompt.ts:142 | 사용 불가 스킬 안내 | PROMPT | SHARE_EN | 미수정 |
| forecast/context-builder.ts:29 | ForecastContext language 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| forecast/context-builder.ts:172 | 예측 컨텍스트 md 섹션 제목(=== "zh"라 ko는 en). 모델 입력 | PROMPT | SHARE_EN | 미수정(자동 en) |
| forecast/context-builder.ts:195 | readBookConfig 반환 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| forecast/prompts.ts:4 | ForecastLanguage 타입 | TYPE | KO_BRANCH: ko 추가 | ko 추가(schema.ts enum도) |
| forecast/prompts.ts:15 | 예측 시스템 프롬프트 | PROMPT | SHARE_EN | !==zh |
| forecast/prompts.ts:22 | 예측 user 프롬프트 | PROMPT | SHARE_EN | !==zh |
| forecast/prompts.ts:51 | 검증 실패 수리 프롬프트 | PROMPT | SHARE_EN | !==zh |
| forecast/render.ts:8 | 저장되는 예측 비교 md(=== "zh"라 ko는 영어 제목·표·안내문) | FORMAT | KO_BRANCH: 한국어 제목, "기준 회차: N화" 등 | 미수정(ko는 영어로 저장) |
| forecast/render.ts:51 | 저장되는 선택 분기 계획 md | FORMAT | KO_BRANCH: 한국어 제목·경고·푸터 | 미수정(ko는 영어로 저장) |
| forecast/agent.ts:44 | 도구 label(提交剧情推演) | UI | SHARE_EN | !==zh |

### 핵심 위험

1. **harness/production-capabilities.ts:188, harness/tools/short-production.ts:34, harness/artifact-validation.ts:66/75**: `=== "en" ? "en" : "zh"`라서 ko가 아무 표시 없이 zh로 접힌다. ko 작품의 생산 도구 전체, 단편 파이프라인, 판매 패키지 저장, 계수가 중국어 경로를 탄다. 기존 패치는 ko 분기를 넣었다.
2. **글자 수 계수 (rg 패턴 밖: agents/writer.ts:258 `resolvedLanguage === "en" ? "en_words" : "zh_chars"`)**: 기존 패치는 이를 `!== "zh"`로 바꿔 ko를 en_words로 보낸다. en_words 정규식은 `[A-Za-z0-9]+`만 세므로 한국어 원고의 wordCount가 거의 0이 된다. 반드시 ko_chars로 분기해야 한다.
3. **길이 단위 프롬프트 (writer.ts:551-556, writer-prompts.ts:47-48, reviser.ts:52의 unit:"words", prompts/short-fiction.ts:47-50/64-66/70-71)**: en 경로를 공유하면 ko에 "N words"를 지시한다. 패치가 주입하는 ko_chars 정책과 모순되고, 영어 단어 기준으로 분량이 어긋난다. "N자(공백 제외)"로 바꾸는 ko 분기가 필요하다.
4. **state-validator.ts:42-44**: 패치 후에도 ko에 "Respond in English."가 명시적으로 남는다. 주입되는 한국어 정책과 직접 충돌하므로 "한국어로 답하라."로 분기해야 한다.
5. **회차 표기 불일치 (agents/short-fiction.ts:171/658, import-context.ts:16-20/65-67)**: 패치는 ko를 "Chapter N"으로 보낸다. 같은 패치의 utils(renderChapterDocument·chapter-splitter)는 "제N화"를 쓴다. 저장되는 단편 원고와 아웃라인에 영어 회차 표기가 섞이므로 "제N화"로 통일해야 한다.
6. **저장 파일의 영어·중국어 제목 (fanfic-canon-importer.ts:45-47, short-fiction.ts:88-90/638, forecast/render.ts:8/51, script-storyboard.ts:492-529)**: ko 책 폴더에 영어 제목(패치 적용 시) 또는 중국어 제목(미수정 시)이 저장된다. forecast/render.ts는 패치가 건드리지 않았다.
7. **harness/system-prompt.ts**: 메인 에이전트는 prepareWorkerMessages의 ko 정책 주입을 거치지 않는다. 패치도 이 파일을 수정하지 않았다. 사용자에게 한국어로 응답하라는 지시를 최소한으로 추가해야 한다.
8. **script-storyboard.ts:107/309/324의 대본 제목 계약과 render*Spec(183/222/259, rg 패턴 밖)**: 제목은 세 곳을 함께 결정해야 한다. 더 급한 쪽은 render*Spec이다. `(input.language ?? "zh") === "en"`이라 ko가 zh로 가고, 패치도 수정하지 않았다. 그래서 script-spec.md 같은 spec 파일이 중국어로 저장된다.
9. **rg 패턴 밖에서 ko가 zh로 가는 곳 (패치 미수정)**: 공백 없는 `language==="en"` 또는 `resolvedLang === "en"` 형태다. prompts/short-fiction.ts:45/68/69/93/95/112, agents/short-fiction.ts:64/259/609(unit "non-whitespace-characters"), architect.ts:320/327, writer.ts:320-321, harness/parent-canon.ts:33. 이곳들에서는 ko에 중국어 지시문이나 라벨이 들어간다. 2차 스윕 때 `===\s*["']en["']` 전체를 검사해야 한다.
10. **구조 권고**: 흩어진 `!== "zh"` 치환은 이번처럼 누락이 생긴다. 공용 `WritingLanguage = "zh" | "en" | "ko"` 타입을 두고, 용도별 헬퍼로 분리할 것을 권한다. 예: `promptLang(ko→en)`, `countingMode(ko→ko_chars)`, `chapterLabel(ko→제N화)`.

## 부록 B. core 나머지 (agent·play·pipeline·state·utils 등)


범위: `rg -n 'language (===|!==) "(zh|en)"|isEn\b|isZh\b|"zh" \| "en"'` 일치 132줄(21개 파일) + 지정 파일(length-metrics, chapter-splitter, book-id, models/*, export). 정규식에 안 걸리지만 같은 성격인 분기(작은따옴표 `'en'`, `resolvedLanguage`, `countingMode === "en_words"`, `!== "en"`, zod enum)는 **†** 표시로 추가했다.
기호: **ko→zh** = 이분 분기에서 ko가 중국어 쪽으로 빠짐, **ko→en** = 영어 쪽으로 빠짐.
기존 패치 = `korean-port/reference/inkos-2.0.0-korean.patch`.

| 파일:줄 | 현재 동작 | 분류 | ko 방침 | 기존 패치 |
|---|---|---|---|---|
| utils/governed-context.ts:5 | `language?: "zh"\|"en"` 매개변수 | TYPE | KO_BRANCH: 유니온에 ko 추가 | ko 타입 추가 |
| utils/governed-context.ts:15,42-78 † | `resolvedLanguage === "en"`으로 근거 블록 제목 7종(伏笔/摘要/正典 등) 선택. **ko→zh** | PROMPT | SHARE_EN: 모델용 섹션 제목일 뿐이며 파서 키가 아님 | `!== "zh"`로 변경 |
| utils/narrative-control.ts:12-21 | `isEn`으로 메모 블록 제목 Goal/目标, Thread Refs/关联线索. **ko→zh** | PROMPT | SHARE_EN: 모델용 제목 | `!== "zh"`로 변경 |
| utils/narrative-control.ts:34 | `_language` 미사용 인자 | TYPE | N/A(타입만 확장) | ko 타입 추가 |
| utils/narrative-control.ts:41-45 | 근거 제목/라벨 Evidence·reason·detail ↔ 证据·原因·细节. **ko→zh** | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| utils/length-metrics.ts:3 | `LengthLanguage = "zh"\|"en"` | TYPE | KO_BRANCH: ko 추가 | ko 추가 |
| utils/length-metrics.ts:8-12 | 기본 분량 en 2000단어, 그 밖 3000. **ko→zh**(값은 3000으로 같지만 단위는 zh_chars) | COUNT | KO_BRANCH: `DEFAULT_CHAPTER_LENGTH_KO`(공백 제외 ko_chars 기준), 수치는 플랫폼 관행 확인 후 결정 | `DEFAULT_CHAPTER_LENGTH_KO = 3000` 추가 |
| utils/length-metrics.ts:15-27 † | zh_chars = 메타데이터 제거 뒤 `\s` 제거 후 UTF-16 `.length` | COUNT | KO_BRANCH: ko_chars = NFC 후 공백 제외, 코드 포인트(`Array.from`) 개수 | `ko_chars` 분기 추가(NFC, `\s` 제거, Array.from) |
| utils/length-metrics.ts:29-33 | `resolveLengthCountingMode`: en→en_words, 그 밖→zh_chars. **ko→zh** | COUNT | KO_BRANCH: ko→`ko_chars` | ko→ko_chars 추가 |
| utils/length-metrics.ts:35-40 † | `formatLengthCount`: en_words가 아니면 `N字`. **ko→zh** | FORMAT | KO_BRANCH: `N자` | `N자` 분기 추가 |
| index.ts:434 † | `DEFAULT_CHAPTER_LENGTH_ZH/EN`만 공개 export | TYPE | KO_BRANCH: KO 상수도 export | 미변경(KO 상수는 export하지 않음) |
| utils/governed-working-set.ts:8 | language 타입. renderHooksProjection에 그대로 전달 | TYPE | KO_BRANCH: ko 추가 | ko 타입 추가 |
| state/state-projections.ts:9-22 | `story/pending_hooks.md` 제목·열 이름 `# Pending Hooks` ↔ `# 伏笔池`. **ko→zh** | FORMAT | KO_BRANCH 권장: JSON이 원본이고 이 md를 읽는 파서가 없으므로 `# 복선 목록`과 한국어 열 이름을 써도 안전(최소한 SHARE_EN) | `!== "zh"`로 변경(ko는 영어 표) |
| state/state-projections.ts:47-58 | `chapter_summaries.md` 제목·열 이름. **ko→zh** | FORMAT | KO_BRANCH 권장(`# 회차 요약`, `회차/제목/등장인물…`) | `!== "zh"`로 변경 |
| state/state-projections.ts:80-92 | `current_state.md` 제목·라벨·열 이름. **ko→zh** | FORMAT | KO_BRANCH 권장(`# 현재 상태`, `현재 회차`) | `!== "zh"`로 변경 |
| state/manager.ts:59-68 | 기본 author_intent·current_focus 템플릿. 분기가 `=== "zh" ? 中 : EN`이라 **ko→en** | FORMAT | KO_BRANCH: 한국어 템플릿 | ko 분기 추가(목적·맥락·기준·경계 4요소 템플릿) |
| state/manager.ts:78,124 | 타입. `resolveControlDocumentLanguage`는 BookConfigSchema.language를 반환 | TYPE | KO_BRANCH: models/book enum과 함께 확장 | ko 타입 추가 |
| state/runtime-state-store.ts:27,68,97,114 | manifest.language 기록, projection 렌더링에 전달 | TYPE | KO_BRANCH: RuntimeStateLanguageSchema와 함께 확장 | ko 타입 추가(+runtime-state enum) |
| play/play-runner.ts:34,49,444,528 | 옵션·인자 타입 | TYPE | KO_BRANCH: ko 추가 | ko 타입 추가 |
| play/play-runner.ts:159 | 개막 action.intent 문장. 이 문장은 `projections/state.md`에 저장됨. **ko→zh** | PROMPT/FORMAT | SHARE_EN 가능, 한국어 문장 권장 | `!== "zh"`로 변경 |
| play/play-runner.ts:184-186 | PlayOpeningSeedError 메시지(사용자 노출). **ko→zh** | UI | KO_BRANCH 권장(한국어 오류문) | `!== "zh"`로 변경(영어) |
| play/play-runner.ts:531-551 | 회차 재생성 제약 프롬프트. **ko→zh** | PROMPT | SHARE_EN + 출력 언어 한국어 지시 | `!== "zh"`로 변경 |
| play/play-runner.ts:553-567 | 세계 맥락 라벨(premise/contract/visual). **ko→zh** | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| play/play-runner.ts:594-599 | 엔티티 라벨 status/状态, 구분자 `; `/`；`. **ko→zh** | PROMPT | SHARE_EN(구분자도 ASCII로) | `!== "zh"`로 변경 |
| play/play-agents.ts:17,30 | 입력 타입 | TYPE | KO_BRANCH | ko 타입 추가 |
| play/play-agents.ts:314-327 | 개막 상태 추출 시스템 프롬프트. **ko→zh**. 영어판에는 출력 언어 지시가 없음 | PROMPT | KO_BRANCH: 영어 프롬프트 + "사람이 읽는 label/summary는 한국어" 한 줄 | `!== "zh"`로 변경(지시 없음. play는 bookId가 없어 inkos.json이 ko일 때만 정책 주입) |
| play/play-agents.ts:330-352 | 개막 user 프롬프트 라벨 | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| play/play-agents.ts:355-385 | 턴 시스템 프롬프트와 choiceRule. **ko→zh** | PROMPT | KO_BRANCH: sceneText·suggestedActions를 한국어로 쓰라는 지시 추가 | `!== "zh"`로 변경(지시 없음) |
| play/play-agents.ts:388-410 | 턴 user 프롬프트 라벨 | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| play/play-store.ts:39 † | PlayWorld `z.enum(["zh","en"])` | TYPE | KO_BRANCH | ko 추가 |
| pipeline/short-fiction-runner.ts:67 | 최소 분량 비율의 기준값: en 650(단어), 그 밖 1000(字). **ko→zh** | COUNT | KO_BRANCH: `SHORT_FICTION_KO_DEFAULT_CHARS_PER_CHAPTER`(ko_chars) 신설 | **`!== "zh"`로 변경해 ko가 650을 쓰는데 ko_chars로 셈. 1화 650자로 지나치게 짧음(버그)** |
| pipeline/short-fiction-runner.ts:324-326 | 장당 기본 분량: en 650, 그 밖 1000. **ko→zh** | COUNT | KO_BRANCH(위와 같은 상수) | **`!== "zh"`로 변경, ko=650자(버그)** |
| pipeline/short-fiction-runner.ts:422 † | 진행 메시지 `language==='en'`. **ko→zh** | UI | KO_BRANCH(한국어) 또는 SHARE_EN | 미변경, ko에 중국어 노출 |
| pipeline/short-fiction-runner.ts:514 | `reviews/draft-warning.md` 본문. **ko→zh** | FORMAT | KO_BRANCH(`# 검토 불가` 등) | `!== "zh"`로 변경(영어) |
| pipeline/short-fiction-runner.ts:538 † | 포장 요청 라벨 `language==="en"`. **ko→zh** | PROMPT | SHARE_EN | 미변경, ko에 중국어 라벨 |
| pipeline/short-fiction-runner.ts:554 | `reviews/package-warning.md`. **ko→zh** | FORMAT | KO_BRANCH | `!== "zh"`로 변경(영어) |
| pipeline/short-fiction-runner.ts:642 | `work.language === "en" ? "en" : "zh"`로 ko를 zh로 접음 | OTHER | KO_BRANCH: ko 보존 | ko 보존으로 변경 |
| pipeline/short-fiction-runner.ts:729 † | 수정 단계 기본 분량 `language==="en"` 650/1000. **ko→zh** | COUNT | KO_BRANCH(KO 상수) | **미변경: 수정 단계 1000, 생성 단계 650으로 서로 다름** |
| pipeline/short-fiction-runner.ts:785-797 | 검토 보고서 md(`# 成稿审查`, `## 审稿观察`, `证据：`). **ko→zh** | FORMAT | KO_BRANCH(`# 원고 검토`, `## 검토 관찰`, `근거:`) | `!== "zh"`로 변경(영어) |
| pipeline/short-fiction-runner.ts:1490 | 표지 이미지 지시문. **ko→zh** | PROMPT | SHARE_EN(+printedTitle 한글 그대로 렌더링 명시 권장) | `!== "zh"`로 변경 |
| pipeline/short-production-state.ts:28 † | target.language enum | TYPE | KO_BRANCH | ko 추가 |
| pipeline/runner.ts:86-100 | 번외편 기초 맥락(영어판 제목에 "番外"가 들어 있음). **ko→zh** | PROMPT | SHARE_EN("番外" 제거 권장) | `!== "zh"`로 변경 |
| pipeline/runner.ts:253-255 | `localize`로 로그·진행 메시지 {zh,en} 선택. **ko→zh** | UI | KO_BRANCH: `{zh,en,ko?}`로 확장하고 ko가 없으면 en | `!== "zh"`로 변경(ko는 영어 로그) |
| pipeline/runner.ts:272-274 † | `languageFromLengthSpec`: en_words가 아니면 zh. **ko_chars→zh** | OTHER | KO_BRANCH: ko_chars→ko | ko_chars→ko 추가 |
| pipeline/runner.ts:831 † | 감사용 기본 brief `book.language==='en'`. **ko→zh** | PROMPT | KO_BRANCH(`기존 제N화 검토`) 또는 SHARE_EN | 미변경, 중국어가 프롬프트에 섞임 |
| pipeline/runner.ts:910-912 † | 수정 의도 기본문 `language==='en'`. **ko→zh** | PROMPT | 위와 같음 | 미변경 |
| pipeline/runner.ts:919 | preRevision 요약 "User-directed revision". 관찰 기록으로 남음. **ko→zh** | UI/FORMAT | KO_BRANCH(`사용자 지정 수정`) 또는 SHARE_EN | `!== "zh"`로 변경 |
| pipeline/runner.ts:944-946 † | 이전 telemetry가 en_words면 en, 아니면 book.language | COUNT | N/A(ko 책이면 book.language=ko로 동작) | 미변경 |
| pipeline/runner.ts:1089-1091 | 하위 회차에 기록되는 재검토 알림(`第N章已重写`). **ko→zh** | FORMAT/PROMPT | KO_BRANCH(`제N화가 변경되었습니다…`) | `!== "zh"`로 변경(영어) |
| pipeline/runner.ts:1522 † | resync 사실 재구성 의도 `pipelineLang==='en'`. **ko→zh** | PROMPT | KO_BRANCH 또는 SHARE_EN | 미변경 |
| pipeline/runner.ts:1762-1764 † | 가져오기 회차 재구성 의도 `resolvedLanguage==='en'`. **ko→zh** | PROMPT | KO_BRANCH 또는 SHARE_EN | 미변경 |
| pipeline/runner.ts:1973-2030 | 가져오기 재생용 current_state.md·pending_hooks.md 씨앗 표. **ko→zh** | FORMAT | KO_BRANCH(state-projections와 같은 한국어 표) | `!== "zh"`로 변경(영어) |
| pipeline/chapter-review.ts:39 | auditor 옵션 타입 | TYPE | KO_BRANCH | ko 추가 |
| pipeline/chapter-review.ts:59 † | auditor 언어를 countingMode로 추정(en_words가 아니면 zh). **ko_chars→zh** | OTHER | KO_BRANCH: ko_chars→ko | ko_chars→ko 추가 |
| pipeline/chapter-review.ts:65-75 † | 검토 불가 요약 `isEnglish`(en_words). **ko→zh** | UI/FORMAT | KO_BRANCH | **미변경: ko에 `审稿暂不可用` 노출** |
| pipeline/chapter-state-recovery.ts:138-150 | 상태 정산 피드백(모델용). **ko→zh** | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| pipeline/chapter-state-recovery.ts:161-163 | unresolved 관찰 요약(기록·노출). **ko→zh** | UI/FORMAT | KO_BRANCH 권장 | `!== "zh"`로 변경(영어) |
| pipeline/script-storyboard-runner.ts:39,57,77,446 | 옵션 타입. 446은 work manifest에 language 저장 | TYPE | KO_BRANCH | ko 추가 |
| pipeline/script-storyboard-runner.ts:519-521 | "Additional requirements:"/补充要求. **ko→zh** | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| references/reference-context.ts:11 | 선택 task 타입 | TYPE | KO_BRANCH | ko 추가 |
| interaction/session-transcript-restore.ts:462 | 복원된 사용자 메시지의 "Attachments:"/附件. **ko→zh** | UI | KO_BRANCH(`첨부 파일:`) | `!== "zh"`로 변경(그런데 저장 시 ko→"en"이라 ko 값이 들어오지 않음) |
| interaction/session-transcript-schema.ts:82 † | userInput.language enum | TYPE | KO_BRANCH | ko 추가 |
| interaction/action-envelope.ts:39,59,71,147,166,180,196 † | 7개 payload의 `z.enum(["zh","en"])` | TYPE | KO_BRANCH | ko 추가 |
| interaction/export-artifact.ts:113-116 † | 내보낼 회차 제목 언어 `'en'`, 그 밖 zh → **ko 책이 `# 第N章`으로 내보내짐** | FORMAT | KO_BRANCH: `제N화` | ko 분기 추가(book.language 또는 heading.language가 ko일 때) |
| interaction/export-artifact.ts:131 | EPUB `lang`: en 또는 `zh-CN` → **ko→zh-CN** | FORMAT | KO_BRANCH: `ko`(필요하면 ko-KR) | ko 분기 추가(`"ko"`) |
| translation/export.ts:35 † | EPUB lang = `manifest.targetLanguage`(사람이 읽는 이름, 예: "Korean") | FORMAT | KO_BRANCH: BCP 47 태그(`ko`)로 변환 | 미변경 |
| llm/long-form-completion.ts:10,76-79 | 이어쓰기 지시(모델용). **ko→zh** | PROMPT | SHARE_EN(이미 쓴 문서 언어를 그대로 이어감) | `!== "zh"`로 변경 + 타입 |
| agent/agent-session.ts:359-385 | 첨부 파일 블록(모델용, language는 세션 UI 문자열). **ko→zh** | PROMPT | SHARE_EN | `!== "zh"`로 변경 |
| agent/agent-session.ts:1329 | transcript 표시용 userInput.language를 en/zh로 접음. **ko→zh** | TYPE/UI | KO_BRANCH: "ko"를 그대로 저장 | `!== "zh" ? "en"`(ko를 en으로 저장. 스키마는 ko 허용) |
| agent/film-authoring-tools.ts:236 | `FilmAuthoringLanguage` 유니온 | TYPE | KO_BRANCH | ko 추가 |
| agent/film-authoring-tools.ts:239,244 † | 노드 생성·수정 시스템 프롬프트 `language === 'en'`. **ko→zh** | PROMPT | SHARE_EN + 한국어 출력 지시 | **미변경: ko의 골격은 영어 프롬프트, 노드는 중국어 프롬프트** |
| agent/film-authoring-tools.ts:391-394 | 구조(골격) 시스템·user 프롬프트. **ko→zh** | PROMPT | SHARE_EN + 한국어 출력 지시 | `!== "zh"`로 변경 |
| agent/agent-tools.ts:95,485,634,1698,1857,1948,2046,2212,2389,2422,2521,2975 | 옵션·인자의 `"zh"\|"en"` 유니온 12곳 | TYPE | KO_BRANCH | 모두 ko 추가(TypeBox `Literal("ko")` 9곳 포함) |
| agent/agent-tools.ts:104 † | `deriveBookIdFromTitle`가 빈 문자열이면 예외 | OTHER | KO_BRANCH(book-id 수정에 따름) | book-id 쪽에서 수정 |
| agent/agent-tools.ts:115 | 기본 분량 `defaultChapterLength(en? en : zh)`. **ko→zh** | COUNT | KO_BRANCH: ko 전달 | ko→ko(3000), 알 수 없는 값→en |
| agent/agent-tools.ts:1729 | 활성 Work 언어를 `en? en : zh`로 접음 → **ko 단편이 중국어로 생성** | OTHER | KO_BRANCH: ko 보존 | ko 보존으로 변경 |
| agent/agent-tools.ts:2283-2285 | 기본 개막 sceneText(`你进入「…」`). transcript에 저장되고 사용자에게 보임. **ko→zh** | FORMAT | KO_BRANCH(`「제목」에 들어섰다.` 등) | `!== "zh"`로 변경(ko는 영어 "You enter …") |
| agent/agent-tools.ts:2325,2539,2663,2750 | 도구 오류 메시지. **ko→zh** | UI | SHARE_EN 가능, 한국어 권장 | `!== "zh"`로 변경 |
| agent/agent-tools.ts:2543,2589-2611 | `isZh = (world.language) !== "en"` → **ko→zh**: play 그래프에 `玩家`·`已更新` 라벨과 결과문 저장 | FORMAT/UI | KO_BRANCH(`플레이어`·`갱신됨`·`설정을 갱신했습니다`) | **미변경: ko 세계 그래프에 중국어가 영구 저장됨** |
| agent/agent-tools.ts:2754,2783-2812 | play_revise의 `isZh !== "en"` 오류·결과문. **ko→zh** | UI | KO_BRANCH 또는 SHARE_EN | **미변경** |
| agent/agent-tools.ts:2996 | resync 요약 `zh = language !== "en"`. **ko→zh** | UI | KO_BRANCH(`제N화 본문은 그대로…`) 또는 SHARE_EN | **미변경** |
| models/book.ts:32 † | BookConfigSchema `z.enum(["zh","en"])`. ko 책은 parse 실패 | TYPE | KO_BRANCH | ko 추가 |
| models/project.ts:106 † | ProjectConfig language enum, 기본값 zh | TYPE | KO_BRANCH(기본값 zh 유지) | ko 추가 |
| models/runtime-state.ts:3 † | RuntimeStateLanguageSchema | TYPE | KO_BRANCH | ko 추가 |
| models/length-governance.ts:3 † | `LengthCountingModeSchema = zh_chars\|en_words` | TYPE/COUNT | KO_BRANCH: `ko_chars` 추가 | `ko_chars` 추가 |
| utils/chapter-splitter.ts:6-34 † | `readChapterHeading`: `第N章/回`, `Chapter N`만 인식 → **`제1화` 원고를 가져오면 회차가 0개** | PARSE | KO_BRANCH: `^#{0,6}\s*제\s*\d+\s*화` 등을 줄 머리로만, 엄격하게 인식 | 한국어 정규식 추가(`제` 생략 가능, `화`/`장`, 숫자 뒤 구분자 생략 가능. 오탐 위험) |
| utils/chapter-splitter.ts:100-110 † | 제목 없는 회차의 대체 제목: Chapter N / 第N回 / 第N章 → **ko→`第N章`** | FORMAT | KO_BRANCH: `제N화` | `제N화` 분기 추가(`N장` 원문도 `제N화`로 바뀜) |
| utils/chapter-document.ts:4-25 † | 회차 파일 제목 `# Chapter N: t` / `# 第N章 t` → **ko 회차 파일 첫 줄이 `第N章`** | FORMAT | KO_BRANCH: `# 제N화 제목` | `# 제N화: 제목` 분기 + 타입 3곳 |
| utils/book-id.ts:3-10 † | ID 허용 문자 `[a-z0-9一-鿿]`만 → **한글 제목이 빈 ID가 되어 책 생성 실패** | OTHER | KO_BRANCH: NFC 정규화 + Hangul(`가-힣`) 허용, 또는 `\p{L}\p{N}` | NFC + `[^\p{L}\p{N}]`로 변경(모든 문자 체계에 적용) |
| utils/memory-retrieval.ts:268-274 † | 권 요약 anchor slug도 `[a-z0-9一-鿿]`만 → 한글 제목이 모두 `volume-summary`로 겹침 | OTHER | KO_BRANCH: 한글 허용(book-id와 같은 규칙) | 미변경 |
| agents/writer.ts:695 †(참고) | 회차 파일 이름 sanitize는 한글을 보존(NFC 정규화 없음) | OTHER | N/A(파일 조회는 번호 접두로 함) | 미변경 |

총 **91행**(정규식 일치 132줄을 묶은 것 + † 보조 항목).

### 분량·분할·ID·내보내기

**분량(COUNT)**
- 현재: `resolveLengthCountingMode`는 en→`en_words`(`[A-Za-z0-9]+('…)?` 단어 수), 나머지→`zh_chars`. 둘 다 `stripMarkdownMetadata`(front matter, 코드 펜스, `#` 제목줄, `---`/`...` 제거)를 거친다. zh_chars는 `\s` 제거 후 UTF-16 `.length`라서 이모지·보충 평면 문자를 2개로 센다. 기본 분량은 zh 3000字, en 2000 words. 단편은 장당 zh 1000字, en 650 words(agents/short-fiction.ts:25-26). ko는 upstream에서 zh_chars와 3000字로 처리되고 표기도 `N字`로 나온다.
- 패치: `ko_chars` = 메타데이터 제거 → NFC → `\s+` 제거 → `Array.from().length`(코드 포인트 수). 한글·라틴·숫자·문장부호·이모지를 모두 1로 센다. 다만 ZWJ로 이어진 이모지와 결합 문자는 여러 개로 센다. `DEFAULT_CHAPTER_LENGTH_KO = 3000`, 표기는 `N자`. 정책문(KOREAN_WRITING_POLICY)도 같은 정의를 모델에 알려 준다.
- **계획서의 "회차당 공백 제외 3,000자"는 장편 기본값(ko_chars 3000)으로 확인됨.** 다만 단편 경로는 다르다. 패치의 `!== "zh"` 때문에 ko 단편 생성은 `SHORT_FICTION_EN_DEFAULT_WORDS_PER_CHAPTER = 650`을 ko_chars로 적용해 **장당 650자**가 된다(short-fiction-runner.ts:67, 324). 수정 경로(729)는 미변경이라 1000이다. ko 단편 상수를 따로 정의해야 한다.
- 참고: 공백 제외 3,000자는 공백 포함으로 약 3,600~3,800자다. 한국 웹소설 연재의 통상 회차 분량(대체로 공백 포함 5천 자 안팎으로 알려짐)보다 짧을 수 있으므로 기본값을 확정하기 전에 확인이 필요하다(추정이며 검증하지 않음).

**분할(PARSE)**
- 현재: `readChapterHeading`과 `splitChapters`는 `第N章/回`(한자 숫자 포함)와 `Chapter N/로마 숫자`만 인식한다. 한국어 원고를 가져오면 `[]`가 되어 분할에 실패한다. `chapterDocumentBody`도 이 함수로 본문 앞의 중복 제목을 걷어낸다.
- 패치: 한국어 정규식 `^#{0,6}\s*(?:제\s*)?(\d+)\s*[화장](?:[:：.]|\s+)?\s*(.*)$`을 중국어보다 먼저 검사한다. `#`과 `제`, 숫자 뒤 구분자가 모두 선택이라 "3장의 편지를 받았다", "2화면" 같은 **본문 줄도 회차 제목으로 오인**할 수 있다. 아라비아 숫자만 받고 `프롤로그/에필로그/외전`은 지원하지 않는다. 대체 제목은 장·화 구분 없이 `제N화`다.

**ID**
- 현재 `deriveBookIdFromTitle`은 라틴 소문자·숫자·CJK 한자만 남긴다. 한글 제목은 빈 문자열이 되어 `buildAgentBookConfig`가 예외를 던진다. fanfic/imitation의 targetWorkId도 비게 된다.
- 패치는 NFC + `[^\p{L}\p{N}]`로 바꿔 한글을 보존한다(`달빛-아래-첫-약속`). 이 변경은 zh/en에도 적용되어, 악센트 문자나 키릴 문자가 들어간 제목은 예전과 다른 ID가 나온다. 저장된 ID와 다시 계산한 ID가 어긋날 수 있다. `isSafeBookId`는 이미 블랙리스트 방식이라 한글을 허용한다. memory-retrieval의 권 anchor slug는 미변경이다.

**내보내기**
- 현재 export-artifact는 회차 제목을 en 또는 zh(`第N章`)로, EPUB `lang`을 `en`/`zh-CN`으로 정한다. ko 책은 중국어 제목에 `zh-CN` 태그로 나간다. `totalWords`는 index의 wordCount 합이다(단위는 책의 countingMode).
- 패치: 회차 제목 `# 제N화: 제목`, EPUB `lang: "ko"`. CLI export 로그는 `N개 회차…(N자)`(CLI 범위). translation/export.ts는 사람이 읽는 언어 이름을 EPUB lang에 넣는 문제가 여전하다.

### 핵심 위험

- **ko→zh로 새는 분기 중 패치가 놓친 곳**: 정규식이 큰따옴표만 잡아서 작은따옴표 `language==='en'`, `!== "en"`, `isEnglish` 분기를 놓쳤다. runner.ts 831/910/1522/1762(모델 프롬프트에 중국어 의도문), chapter-review.ts:65-75(`审稿暂不可用`), short-fiction-runner.ts:422/538, film-authoring-tools.ts:239/244, agent-tools.ts 2543/2754/2996의 `isZh`/`zh` 분기가 그렇다. 특히 2589-2611은 play 그래프에 `玩家`/`已更新`을 **영구 저장**한다.
- **단편 분량 버그**: 패치 이후 ko 단편 생성의 기본값은 650(영어 단어용 상수)을 ko_chars로 세서 장당 650자다. 수정 경로는 1000이라 생성과 수정의 목표가 다르다. ko 전용 상수가 필요하다.
- **`!== "zh"`로 모두 바꾼 방식은 ko→en 고정**이다. 사용자에게 보이는 파일(state-projections의 story/*.md, import seed, reviews/*.md, 기본 개막 sceneText, 하위 회차 알림, 오류·로그)이 한국어 책에서 영어로 나온다. 계획대로 ko를 명시적인 제3언어로 다루려면 FORMAT/UI 항목은 KO_BRANCH가 필요하다.
- **출력 언어 보장이 약함**: SHARE_EN 프롬프트(play, film, long-form)에는 출력 언어 지시가 없다. 패치는 `agents/base.ts prepareWorkerMessages`에서 inkos.json/book.json이 ko일 때만 정책을 주입한다. play 세계(bookId 없음)나 프로젝트는 zh/en인데 Work만 ko인 경우에는 영어로 출력될 수 있다.
- **분할 정규식 오탐**: 패치의 한국어 제목 정규식은 `#`과 `제`가 선택이고 숫자 뒤 구분자도 선택이라 "3장의…" 같은 본문 첫머리를 회차 경계로 자른다. chapterDocumentBody가 본문 첫 줄을 제목으로 보고 지울 위험도 있다. 줄 머리 `제N화`·`N화` + 경계를 요구하는 엄격한 규칙과 오탐 테스트가 필요하다.
- **ID 규칙 변경의 부작용**: 패치의 `\p{L}\p{N}`은 zh/en 책에도 적용되어, 기존 비ASCII 라틴·키릴 제목의 ID 계산 결과가 바뀐다(다시 계산해 조회하는 fanfic/imitation targetWorkId가 어긋날 수 있음). 한글 범위만 추가하는 편이 보수적이다. memory-retrieval의 anchor slug는 한글 제목이 모두 `volume-summary`로 겹친다.
- **스키마 호환성**: `ko_chars`/`"ko"`를 zod enum에 추가하면 패치가 없는 이전 버전이나 studio가 book.json·runtime manifest·lengthTelemetry를 읽다가 parse에 실패한다. 프로젝트 기본값은 zh로 유지되므로 ko 프로젝트에서 language를 빠뜨리면 중국어로 동작한다.
- **언어 정보 손실 지점**: agent-session.ts:1329는 ko를 `"en"`으로 저장한다(스키마는 ko를 허용하는데도). `languageFromLengthSpec`/chapter-review처럼 countingMode에서 언어를 거꾸로 추정하는 곳이 남아 있다. 이런 곳이 늘어날수록 새는 곳이 생기므로 언어를 직접 전달하도록 바꿔야 한다.
- **내보내기 태그**: translation/export.ts가 EPUB lang에 "Korean" 같은 이름을 넣는다. `DEFAULT_CHAPTER_LENGTH_KO`가 index.ts에서 export되지 않아 CLI/studio가 하드코딩할 위험이 있다.
- **기본 분량 수치**: 공백 제외 3,000자가 한국 연재 관행(공백 포함 기준)과 맞는지 확인이 필요하다. formatLengthCount의 `N자`가 공백 제외 기준이라는 점을 UI에 표시하지 않으면 사용자가 공백 포함으로 오해할 수 있다.

## 부록 C. cli·studio


- 대상: `packages/cli/src`, `packages/studio/src`의 비테스트 .ts/.tsx
- 검색식: `rg -n 'language (===|!==) "(zh|en)"|isEn\b|isZh\b|"zh" \| "en"'` → 233건 / 29파일
- 보조 확인: 검색식에 안 걸리지만 같은 문제를 가진 곳(`locale === "en"`, `getAppLanguage() === "en"`, `tr()`, `resolveCliLanguage` 등)은 `(+)` 표시로 추가함
- 패치 기준: `korean-port/reference/inkos-2.0.0-korean.patch` (4684줄). "미변경" = 그 파일/줄을 패치가 건드리지 않음
- 기호: **[ko→zh]** = `=== "en" ? en : zh` / `!== "en"` 꼴이라 ko가 **중국어**를 받음. **[ko→en]** = `isZh ? zh : en` / `=== "zh"` 꼴이라 ko가 **영어**를 받음
- 저장소 파일은 수정하지 않음

### 1. 분기 목록

### 1.1 CLI (`packages/cli/src`)

| 파일:줄 | 현재 동작 | 분류 | ko 방침 | 기존 패치 |
|---|---|---|---|---|
| commands/short-fiction.ts:85 | `--chars` 파싱 fallback: en이면 650단어, 아니면 1000자. CliLanguage 확장 시 ko는 zh 값(1000자) 사용 [ko→zh] | CONFIG | KO_BRANCH: ko 전용 기본값 상수(ko_chars 기준) 명시. 값이 1000자로 같더라도 명시 분기 | 85줄 미변경. 단 56줄 `--lang` 기본값 `"zh"`→`"ko"` (**기본값 변경**), `parseShortFictionLanguage`→`parseWritingLanguage` |
| commands/import.ts:98 | 장 가져오기 시작 메시지 `language === "en" ? en : zh` [ko→zh] | UI | KO_BRANCH: localization.ts로 옮겨 ko 문구 추가 | 미변경 (패치 적용 후 ko 책은 중국어 출력) |
| localization.ts:3 | `CliLanguage = "zh" \| "en"` | TYPE | KO_BRANCH: `"ko"` 추가 | `"ko"` 추가 |
| localization.ts:20 | `localize()`: `language === "en" ? en : zh`. 함수 55개가 모두 이 경로를 씀 [ko→zh] | UI | KO_BRANCH: ko 문구 필수(또는 ko→en 폴백을 명시). 폴백이 zh가 되면 안 됨 | `ko?:` 선택 필드, `ko ? (ko ?? en)`; ko 문구 57개 추가(사실상 전체) |
| (+) localization.ts:23-53 `normalizeCliLanguageTag`/`resolveCliLanguage` | 명시값 → `INKOS_LOCALE` → `LC_ALL/LC_MESSAGES/LANG` → 기본 `"zh"`. `ko` 태그는 인식하지 못함 | CONFIG | KO_BRANCH: `ko*` 태그 인식 추가. 최종 기본값 `"zh"`는 유지 | `ko` 인식 추가 + **최종 기본값 `"zh"`→`"ko"`** (**기본값 변경**: LANG=C/fr 등 사용자와 인자 없는 호출 `book.ts:312,353`, `doctor.ts:116`, `config.ts:308`가 한국어로 바뀜) |
| (+) localization.ts:421 `formatChapterSyncChange` | `countingMode: "zh_chars" \| "en_words"` | TYPE | KO_BRANCH: `"ko_chars"` 추가 | `ko_chars` 추가 |
| progress-text.ts:64-75 | `formatImportCompletionLines`: 5줄 모두 `=== "en"` [ko→zh]. 이 파일을 import하는 곳이 없음(죽은 코드) | UI | KO_BRANCH(우선순위 낮음) 또는 삭제 후보. 되살아날 때 ko가 중국어를 받음 | 미변경 |
| project-bootstrap.ts:6 | 옵션 타입 `language?: "zh" \| "en"` | TYPE | KO_BRANCH: `"ko"` 추가 | `"ko"` 추가 |
| project-bootstrap.ts:62 | `buildProjectConfig(…, language: "zh" \| "en")` | TYPE | KO_BRANCH | `"ko"` 추가. **126줄 `options.language ?? "zh"`→`?? "ko"`** (**기본값 변경**) |
| tui/slash-autocomplete.ts:21 | 슬래시 힌트 `language === "en" ? en : zh` [ko→zh]. 또 `SLASH_COMMANDS = buildSlashCommands("zh")`가 고정이라 dashboard.tsx:185는 언어와 상관없이 항상 zh | UI | KO_BRANCH: variant에 `ko` 추가 + dashboard가 locale을 따라가게 함 | 미변경 |
| tui/agent-input.ts:57 | `config.language === "en" ? "en" : "zh"` → ko 프로젝트가 zh가 됨 [ko→zh] | CONFIG | KO_BRANCH: ko 보존 | `ko ? ko : en ? en : zh` |
| tui/agent-input.ts:61 | `/use` 응답 문구 | UI | KO_BRANCH: ko 문구 | `language !== "zh"`로 바꿈 → ko는 **영어** [ko→en], ko 문구 없음 |
| tui/agent-input.ts:207, 240, 396 | `language: "zh" \| "en"` 파라미터(240은 기본값 `"zh"`) | TYPE | KO_BRANCH: 타입 확장, 기본값 `"zh"` 유지 | `"ko"` 추가, 기본값 `"zh"` 유지 |
| tui/agent-input.ts:212, 214, 226-228 | `/works`, `/work` 출력 라벨(`Profile/Artifacts/Recent episodes`) | UI | KO_BRANCH | ko 문구 추가(`ko ? … : !== "zh" ? en : zh`) |
| tui/agent-input.ts:248, 258, 281-282 | `/confirm`, `/cancel` 로컬 응답 | UI | KO_BRANCH | ko 문구 추가 |
| tui/agent-input.ts:288, 295, 302, 311 | `/new`, `/short`, `/cover`, `/play`에 본문이 없을 때 모델에 보내는 기본 사용자 메시지 | PROMPT | KO_BRANCH: 한국어 지시문 | ko 문구 추가 |
| tui/agent-input.ts:320 | `/write` userMessage `Write the next chapter` / `写下一章` (intent는 `write_next`로 명시) | PROMPT | KO_BRANCH | `다음 회차를 집필해 주세요` 추가 |
| tui/agent-input.ts:397 | `formatProposedAction` 확인 카드 | UI | KO_BRANCH | ko 카드 추가 |
| (+) tui/i18n.ts:3, 166-206 | `TuiLocale = "zh-CN" \| "en"`. `normalizeLocale("ko")`이 undefined라 env를 보고, 결국 `"zh-CN"`으로 감. `getTuiCopy`: `locale === "en" ? EN : ZH_CN` [ko→zh] | UI/CONFIG | KO_BRANCH: `"ko"` locale + `KO: TuiCopy` 추가. 최종 기본값 zh-CN 유지 | **미변경** → ko 프로젝트 TUI 크롬(라벨·composer·help)이 중국어 |
| (+) tui/effects.ts:280, 383, 449, 463 | 의도 배지·help 섹션·테마 라벨 `locale === "en"` [ko→zh] | UI | KO_BRANCH | 미변경 |
| (+) tui/setup.ts:78, 144 | LLM 설정 마법사 문구 `locale === "en"` [ko→zh] | UI | KO_BRANCH | 미변경. 단 **270줄 autoInit `language: "zh"`→`"ko"`** (**기본값 변경**) |
| (+) commands/init.ts:10, 17 | `--lang` 기본값 `"zh"`. `opts.lang === "en" ? "en" : "zh"`라 ko가 zh가 됨 [ko→zh] | CONFIG | KO_BRANCH: ko 허용. 기본값 zh 유지 | **기본값 `"ko"`**. 출력 블록을 통째로 다시 씀: zh/en에서도 `Global LLM config detected`/set-global 안내/`English project? …` 힌트가 사라지고 zh 예시에 `--lang zh`가 붙음 (**zh/en 출력 변경**) |

### 1.2 Studio (`packages/studio/src`)

| 파일:줄 | 현재 동작 | 분류 | ko 방침 | 기존 패치 |
|---|---|---|---|---|
| shared/contracts.ts:39 | `BookDetail.language: "zh" \| "en" \| null` | TYPE | KO_BRANCH | `"ko"` 추가 |
| hooks/use-i18n.ts:3 | `type Lang = "zh" \| "en"` | TYPE | KO_BRANCH | `"ko"` 추가 |
| hooks/use-i18n.ts:377 | `data?.language === "en" ? "en" : "zh"`. `t(key) = strings[key][lang]` [ko→zh] | CONFIG/UI | KO_BRANCH: ko 판별 + ko 테이블. 폴백은 en | `normalizeAppLanguage` + `koreanStrings[key] ?? strings[key].en`. ko 테이블은 315키 중 305키를 덮음(누락 10: `analytics.*Tokens`, `analytics.observations`, `book.review` 등). 지금 키에 없는 키 30개가 남아 있음(Record<string,string>이라 타입 검사가 못 잡음). `translateStudioString` export |
| lib/app-language.ts:3 (+ `tr()` 17줄) | `AppLanguage = "zh" \| "en"`, `tr(zh,en)`: `current === "en" ? en : zh` [ko→zh]. 29파일 312곳에서 호출 | TYPE/UI | KO_BRANCH: `tr(zh,en,ko?)`, ko→(ko ?? en) | `tr(zh, en, ko?)` + `normalizeAppLanguage`. 하지만 **기존 312개 `tr()` 호출 중 ko 인자를 넣은 곳은 0개** → 인라인 문구는 모두 영어 |
| (+) lib/error-copy.ts:19 | `getAppLanguage() === "en"`이면 원문 영어, 아니면 중국어로 치환 [ko→zh] | UI | KO_BRANCH: ko 치환표(또는 영어 원문 유지) | 미변경 → ko는 중국어 오류 문구를 받음 |
| (+) lib/truth-display.ts:54 | foundation 파일 라벨: `=== "en" ? EN : zh` [ko→zh] | UI | KO_BRANCH: ko 라벨 | 미변경 |
| (+) App.tsx:72, 199-220 | `setAppLanguage(currentLang)`, 헤더 `中/EN` 버튼 → `PUT /project` | UI/CONFIG | KO_BRANCH | `한국어` 버튼 추가(zh/en 사용자에게도 보임). 그런데 서버 PUT 화이트리스트(server.ts:4125)를 안 고쳐서 **버튼이 아무 일도 하지 않음** |
| pages/LanguageSelector.tsx:3-7 | 첫 실행 언어 선택 카드 zh/en | TYPE/UI | KO_BRANCH: ko 카드 추가 | 타입 확장 + ko 카드를 **맨 앞에** 추가, 하단 문구를 3개 언어로 바꿈(zh/en 첫 화면도 달라짐) |
| pages/TranslationManager.tsx:132 | `isZh = t("nav.connected") === "已连接"` (번역 문자열로 언어를 추측) [ko→en] | OTHER | KO_BRANCH: `useI18n().lang`으로 직접 판별 | 미변경 |
| pages/TranslationManager.tsx:133, 143-144 | 언어 프리셋 목록, 원문 기본값 `自动识别/Auto detect`, 번역 목표 기본값 `中文（简体）/English` [ko→en] | CONFIG | KO_BRANCH: ko 프리셋(한국어 표기) + ko 프로젝트의 기본 목표 언어(예: `한국어`) | 미변경 |
| pages/TranslationManager.tsx:188, 213, 234, 259, 345 | 업로드/생성/실행/내보내기 상태 문구, 프리셋 필터 [ko→en] | UI | KO_BRANCH | 미변경 |
| pages/Dashboard.tsx:269 | `book.language === "en"`이면 `EN` 배지. ko 책은 배지 없음 | UI | KO_BRANCH(선택): `KO` 배지 | 미변경 |
| pages/BookCreate.tsx:31 | 페이로드 `language: "zh" \| "en"` | TYPE | KO_BRANCH | `"ko"` 추가 |
| pages/BookCreate.tsx:69 | `PAGE_COPY: Record<"zh"\|"en", …>` | UI | KO_BRANCH | ko 카피 추가 |
| pages/BookCreate.tsx:110-111 | 회차 기본 분량: en이면 2000, 아니면 3000. ko는 암묵적으로 zh 값을 탐 [ko→zh] | CONFIG | KO_BRANCH: ko 기본값 명시 | 타입만 확장(ko는 그대로 3000) |
| pages/BookCreate.tsx:114-115 | 플랫폼 목록 `en ? EN : ZH` [ko→zh] | CONFIG | KO_BRANCH | ko → `[{other, "기타 / 직접 설정"}]` |
| pages/BookCreate.tsx:118, 145 | `defaultBookCreateForm`, `buildBookCreatePayload` 타입 | TYPE | KO_BRANCH | `"ko"` 추가 |
| pages/BookCreate.tsx:149 | 폼 미완성 오류 `language === "zh" ? zh : en` [ko→en] | UI | KO_BRANCH | 미변경 |
| pages/BookCreate.tsx:204 | `projectLang = project?.language === "en" ? "en" : "zh"` [ko→zh] | CONFIG | KO_BRANCH (**필수**) | **미변경** → ko 프로젝트에서도 PAGE_COPY.zh, 중국 플랫폼 목록이 나오고 **페이로드 language가 "zh"로 감**. 패치의 ko 카피/플랫폼 코드는 화면에서 닿지 않음(테스트만 통과) |
| pages/ImportManager.tsx:311, 366 | 동인/모방 언어 select(`zh`, `en` 옵션). 초기값은 `useI18n().lang` | TYPE/UI | KO_BRANCH: `<option value="ko">한국어</option>` | 캐스트만 확장, **ko 옵션이 없음** → state는 "ko"인데 화면에는 첫 옵션(중국어)이 보이고, 사용자가 다른 값을 고르면 ko로 되돌릴 수 없음 |
| pages/BookDetail.tsx:139, 162, 185, 241 | 재작성/수정/동기화/설정 재정비 `window.prompt` 안내 `=== "en"` [ko→zh] | UI | KO_BRANCH | 미변경 |
| pages/BookDetail.tsx:253 | `Foundation revised.` 완료 문구 [ko→zh] | UI | KO_BRANCH | 미변경 |
| pages/BookDetail.tsx:296 | EN 배지 | UI | KO_BRANCH(선택) | 미변경 |
| pages/BookDetail.tsx:523 | 동기화 버튼 tooltip [ko→zh] | UI | KO_BRANCH | 미변경 |
| pages/ProjectSettings.tsx:91 | `isZh = t("nav.connected") === "已连接"` [ko→en] | OTHER | KO_BRANCH: lang 직접 판별 | 미변경 |
| pages/ProjectSettings.tsx:168-291 | Agent Skills 섹션(가져오기/삭제/오류) 라벨 [ko→en] | UI | KO_BRANCH | 미변경 |
| pages/ProjectSettings.tsx:399-448 | 리서치 검색 제공자·API Key 환경변수 라벨 [ko→en] | UI | SHARE_EN (개발자용 설정, 자주 안 봄) | 미변경 |
| pages/ChatPage.tsx:336 | `isZh = t("nav.connected") === "已连接"` → 아래 모든 행의 기준 [ko→en] | OTHER | KO_BRANCH: `lang` 기반 3분기 | 미변경 |
| pages/ChatPage.tsx:185-263 | Skill 선택 팝오버(제목/가져오기/로딩/없음/오류) | UI | KO_BRANCH | 미변경 |
| pages/ChatPage.tsx:463-468 | 모델 선택 placeholder `选择模型/Select model` | UI | KO_BRANCH | 미변경 |
| pages/ChatPage.tsx:647 | 첨부 크기 초과 안내 | UI | KO_BRANCH | 미변경 |
| pages/ChatPage.tsx:747 | 제안 거절 시 에이전트에 보내는 메시지 `取消这次操作…/Cancel this action…` [ko→en] | PROMPT | KO_BRANCH: 한국어 지시(대화 기록에 남음) | 미변경 |
| pages/ChatPage.tsx:762, 776 | 서사 예측 지시 언어 인자 `isZh ? "zh" : "en"` → ko는 "en" | PROMPT | KO_BRANCH: `"ko"` 전달 | 미변경(받는 함수만 ko 타입 허용) |
| pages/ChatPage.tsx:831-840 | 빈 대화 안내(short/play/기본) | UI | KO_BRANCH | 미변경 |
| pages/ChatPage.tsx:858-898 | 새 작품 세션 / 플레이 방식 선택(点着玩/自由玩) | UI | KO_BRANCH | 미변경 |
| pages/ChatPage.tsx:1008-1290 | 생각 중, 재시도, 첨부/Skill 제거, 입력 placeholder, 정지, 모델 로딩, 모델 설정, 세계 보기, 자동 삽화 설정·오류, 하위 컴포넌트에 `isZh` 전달(1025, 1039, 1075, 1290) | UI | KO_BRANCH | 미변경 |
| components/chat/QuickActions.tsx:11, 55, 59 | 빠른 실행 칩 라벨 `labelZh/labelEn` [ko→en] | UI | KO_BRANCH: `labelKo` | 미변경 |
| components/chat/QuickActions.tsx:60 | 칩을 누르면 보내는 명령 `写下一章/write next`, `审计/audit`, `导出全书/export book`, `扫描市场趋势…` [ko→en] | PROMPT | KO_BRANCH: `commandKo` (write_next 말고는 모델이 의도를 추론하므로 언어 일관성이 중요) | 미변경 |
| components/chat/NarrativeForecastPreview.tsx:79-81, 88-90 | `select_narrative_branch`/`get_narrative_forecast` 호출 지시 `=== "zh" ? zh : en` [ko→en] | PROMPT | KO_BRANCH: ko 지시문(도구 이름은 그대로) | 타입만 `"ko"` 확장 → ko는 영어 지시 |
| components/chat/NarrativeForecastPreview.tsx:249 | `zh = forecast.language === "zh"` → 카드 라벨 [ko→en] | UI | KO_BRANCH | 미변경 |
| components/chat/BookSidebar.tsx:186, 207-209, 223 | `isZh` 추측(t 비교), 작성·감사·수정 진행 문구 | UI/OTHER | KO_BRANCH | 미변경 |
| components/sidebar/ChaptersSection.tsx:16-48 | `章节/Chapters`, `暂无章节`, 제목 없는 장 `第N章/Chapter N` [ko→en] | UI | KO_BRANCH: `N화` | 미변경 |
| components/chat/PlayHud.tsx:323-644 (29건) | 플레이 HUD 제목·턴·모드·빈 상태·세계 시간·주변/소지품/상태 섹션·뒤로·aria [ko→en] | UI | KO_BRANCH (플레이의 주 화면) | 미변경 |
| components/chat/PlayChoicePanel.tsx:4, 10 | `推进中…/等待场景给出选项…` | UI | KO_BRANCH | 미변경 |
| components/chat/play-hud/HoldingSlot.tsx:7-31 | `KIND_LABEL_ZH/EN`, `新/NEW` | UI | KO_BRANCH: `KIND_LABEL_KO` | 미변경 |
| components/chat/play-hud/HoldingInspect.tsx:8-89 | 종류/사다리 라벨, 뒤로, 방금 얻음, 속성, 연결, `第N幕 取得` | UI | KO_BRANCH: `LADDER_LABEL_KO` 등 | 미변경 |
| components/chat/play-hud/RelationWeb.tsx:37, 45 | SVG aria-label `关系网/Relations` | UI | SHARE_EN (aria 전용) | 미변경 |
| api/book-create.ts:27 | `StudioBookConfigDraft.language: "zh" \| "en"` | TYPE | KO_BRANCH | `"ko"` 추가 |
| api/book-create.ts:48 | 회차 분량 기본값 `defaultChapterLength(en ? en : zh)` [ko→zh] | CONFIG | KO_BRANCH | ko 분기 추가 |
| api/book-create.ts:51 | `language: en ? en : zh` → ko가 **zh로 저장됨** [ko→zh] | CONFIG | KO_BRANCH (필수) | ko 보존. 그리고 id 생성에 `.normalize("NFC")` + 한글 범위 추가(zh/en 결과는 사실상 같음) |
| api/server.ts:178-184 | `StudioLanguage`, `normalizeStudioLanguage` (ko→zh), `pick(lang, zh, en)`: `=== "en"`. 서버 문구 73곳이 사용 | TYPE/UI | KO_BRANCH: `pick(lang, zh, en, ko?)` | 타입/normalize에 ko 추가. `pick`은 `!== "zh" ? en : zh` → ko는 **영어**(73곳 모두) |
| api/server.ts:2934, 2942, 2955 | `/books/create`: actionPayload·도구 파라미터에 `language`는 `en\|zh`일 때만 넣음, 도구 language는 `en ? en : zh` → ko 책의 foundation 생성이 **zh로 돎** [ko→zh] | CONFIG/PROMPT | KO_BRANCH (필수) | **미변경** (bookConfig는 ko인데 도구에는 language가 없거나 zh) |
| api/server.ts:3091 | 영감 카드: `book.language === "en" ? "en" : "zh"` | CONFIG | KO_BRANCH | `normalizeStudioLanguage(book.language ?? 프로젝트 language)`로 바꿈 (**zh/en 동작 변경**: language가 없는 책을 en 프로젝트에서 열면 zh였던 것이 en이 됨) |
| api/server.ts:3103-3116 | 영감 카드 system/user 프롬프트 `language === "en"` [ko→zh] | PROMPT | KO_BRANCH: ko 프롬프트(또는 en 템플릿 + ko 출력 지시) | **미변경** → 3091이 ko를 넘겨도 프롬프트는 중국어 |
| api/server.ts:4125 | `PUT /project`: `language === "zh" \|\| === "en"`일 때만 저장 | CONFIG | KO_BRANCH (필수) | **미변경** → App 헤더 `한국어` 버튼이 아무 일도 하지 않음 |
| api/server.ts:4804-4805 | 에이전트 surface 언어(config/book) en→en, 그 외 zh [ko→zh]. `runAgentSession`, `resolveToolLabel`, `formatAgentActionFailure`, `pick`에 전달됨 | CONFIG | KO_BRANCH | ko 보존(`normalizeStudioLanguage` 및 3분기) |
| api/server.ts:5530 | `POST /project/language` 바디 타입 | TYPE | KO_BRANCH | `"ko"` 추가 + 지원하지 않는 값은 400 (예전에는 아무 문자열이나 저장. zh/en 정상 경로는 영향 없음) |
| api/server.ts:5820 | 책 설정 PUT의 language 캐스트 | TYPE | KO_BRANCH(검증도 추가 권장) | 캐스트만 확장(검증 없음) |
| api/server.ts:5918 | `/style/analyze` 바디 타입 | TYPE | KO_BRANCH | `"ko"` 추가 |
| api/server.ts:5930 | 스타일 가이드 언어 기본값 `config.language === "en" ? "en" : "zh"` [ko→zh] | CONFIG/PROMPT | KO_BRANCH | **미변경** → ko 프로젝트에서 스타일 가이드가 중국어 |
| api/server.ts:6094, 6160, 6232 | 동인/파생/모방 책의 language 캐스트 | TYPE | KO_BRANCH | `"ko"` 추가 |

행 수: CLI 22행 + Studio 61행 = **83행**. 검색식 233건은 모두 위 행 중 하나에 들어가며, `(+)` 행은 검색식 밖에서 추가한 것.

### 2. UI 언어 구조

### CLI (일반 명령)
- `localization.ts`의 `resolveCliLanguage(explicit?, env)` 우선순위: ① 명시값(보통 `book.language`나 `opts.lang ?? config.language`) → ② `INKOS_LOCALE` → ③ `LC_ALL ?? LC_MESSAGES ?? LANG` → ④ 기본 `"zh"`. 태그는 `startsWith("en"/"zh")`로만 판별.
- 문구 테이블: 함수 하나가 메시지 하나를 맡음(`formatXxx(language, …)` 41개 export, `localize(language, {zh, en})` 55회). 폴백은 **zh**(`=== "en" ? en : zh`).
- 이 체계를 거치지 않는 인라인 분기도 있음: `commands/import.ts:98`, `progress-text.ts`, `commands/init.ts`, `commands/export.ts`(언제나 영어), fanfic 오류(`formatFanficCanonMissingError`, 영·중 한 줄 병기).
- ko를 추가하는 최소 방법(zh/en 불변):
  1. `CliLanguage`에 `"ko"` 추가, `normalizeCliLanguageTag`에 `ko*` 인식 추가. **기본값 `"zh"`는 유지.**
  2. `localize(language, {zh, en, ko})`. ko는 필수 필드로 두는 편이 안전함(빠뜨리면 타입 오류). 선택 필드로 하더라도 폴백은 en이어야 하며 zh는 안 됨.
  3. `import.ts:98`, `progress-text.ts` 같은 인라인 `=== "en"` 분기를 localization.ts로 옮기거나 3분기로 바꿈.

### TUI
- `tui/i18n.ts`: `TuiLocale = "zh-CN" | "en"`. `resolveTuiLocale(env, projectLanguage)`: `INKOS_TUI_LOCALE ?? INKOS_LOCALE` → `inkos.json`의 language(`detectProjectLanguage`) → `LC_ALL/LC_MESSAGES/LANG` → `"zh-CN"`.
- 테이블은 `TuiCopy` 인터페이스(labels/composer/notes/roles/activity/depthLabels, 일부 값은 함수)를 따르는 `ZH_CN`, `EN` 객체 2개. `getTuiCopy`: `locale === "en" ? EN : ZH_CN`, 폴백 zh.
- 이 테이블 밖의 TUI 문구도 있음: `effects.ts`(배지/help/테마), `setup.ts`(설정 마법사), `agent-input.ts`(CliLanguage 사용, `config.language`로 직접 판별), `slash-autocomplete.ts`(대시보드는 zh 고정).
- 최소 방법: `TuiLocale`에 `"ko"` 추가 → `KO: TuiCopy` 작성(인터페이스가 있어서 빠진 키를 타입 검사가 잡아 줌) → `normalizeLocale`에 `ko` 인식 → `getTuiCopy`를 `switch`로 → `effects.ts`/`setup.ts`의 `locale === "en"` 분기에 ko 추가 → 슬래시 힌트에 ko variant를 넣고 dashboard가 locale을 따르게 함. **패치는 이 작업을 전혀 하지 않음.**

### Studio
- 서버: `GET /api/v1/project`가 `inkos.json`의 `language`(스키마 기본 `"zh"`)와 `languageExplicit`를 돌려줌. `languageExplicit`가 false면 첫 실행 `LanguageSelector` → `POST /project/language`. 헤더 토글은 `PUT /project`(zh/en 화이트리스트).
- 클라이언트:
  - `useI18n()`이 `/project`를 읽어 `lang`을 정함(`=== "en" ? en : zh`). `strings` 테이블은 `{key: {zh, en}}` 315개, `as const`이고 `StringKey` 타입으로 키 검사.
  - `App.tsx`가 렌더할 때마다 `setAppLanguage(lang)`으로 모듈 싱글턴을 맞추고, hook을 못 쓰는 코드(`tr(zh, en)`, `error-copy`, `truth-display`)가 그 값을 읽음.
  - 일부 컴포넌트는 `isZh = t("nav.connected") === "已连接"`로 언어를 **추측**함(ChatPage, ProjectSettings, TranslationManager, BookSidebar). 그래서 ko 테이블이 생기면 자동으로 영어 쪽으로 감.
  - 페이지별 테이블도 따로 있음(BookCreate `PAGE_COPY`, QuickActions `labelZh/labelEn`, play-hud `KIND_LABEL_*`, TranslationManager `LANGUAGE_PRESETS_*`).
- 폴백: 전부 **zh**(`=== "en" ? en : zh`). 다만 `isZh` 추측 경로와 `=== "zh"` 경로는 ko에게 **en**을 줌.
- 최소 방법(zh/en 불변):
  1. 서버에서 `PUT /project`·`POST /project/language` 화이트리스트에 ko 추가, `normalizeStudioLanguage`·`pick`을 3분기로.
  2. 클라이언트에 `normalizeAppLanguage` 하나를 만들어 `useI18n`·`BookCreate:204`·`book-create.ts` 등 모든 판별부가 공유.
  3. `strings`를 `{zh, en, ko?}`로 확장하거나 별도 `koreanStrings: Partial<Record<StringKey, string>>` + en 폴백. `Record<string,string>`은 오래된 키를 못 잡으니 쓰지 않음.
  4. `tr(zh, en, ko?)`: ko→(ko ?? en).
  5. `isZh` 추측을 `lang` 기반 3분기 헬퍼(`pickLang(lang, {zh, en, ko})`)로 교체.
  6. 모델에 보내는 문구(PROMPT 행)는 ko 문구를 필수로 둠.

### 3. 핵심 위험

1. **`=== "en" ? en : zh` 꼴은 타입만 넓히면 ko가 조용히 중국어를 받음.** CLI `localize`, TUI `getTuiCopy`/effects/setup, Studio `useI18n`·`tr`·`error-copy`·`truth-display`·`BookDetail`·`server.ts:3103-3116`·`5930`이 모두 이 꼴. 컴파일 오류가 나지 않아 놓치기 쉬움.
2. **패치가 TUI i18n을 건드리지 않음**: `tui/i18n.ts`·`effects.ts`·`setup.ts` 미변경. ko 프로젝트에서 TUI 크롬은 중국어(또는 LANG에 따라 영어)이고, `agent-input.ts`가 돌려주는 메시지만 한국어라서 한 화면에 두 언어가 섞임.
3. **Studio 작품 생성 경로가 ko를 잃음**: `BookCreate.tsx:204`가 미변경이라 페이로드 language가 "zh"로 감. `server.ts:2934/2942/2955`도 미변경이라 foundation 도구가 zh로 돎. 패치의 ko PAGE_COPY/플랫폼 코드는 화면에서 닿지 않고 단위 테스트만 통과함.
4. **헤더 `한국어` 버튼이 아무 일도 하지 않음**: `PUT /api/v1/project`(server.ts:4125) 화이트리스트가 zh/en 그대로라 저장되지 않음. `POST /project/language`(첫 실행 선택)만 ko를 받음.
5. **언어 추측 해킹(`t("nav.connected") === "已连接"`)**: ko 테이블이 생기면 ChatPage·PlayHud·ProjectSettings·TranslationManager·QuickActions 등 수십 곳이 모두 영어가 됨. ChatPage 762/776은 서사 예측 지시 언어로 `"en"`을 넘김.
6. **모델로 가는 문구(PROMPT)가 영어나 중국어로 남음**: QuickActions 명령, ChatPage 747 거절 메시지, NarrativeForecast 지시는 영어. server.ts 3103-3116 영감 카드와 5930 스타일 가이드는 중국어. 한국어 출력 정책(core `applyProjectLanguagePolicy`)이 붙더라도 대화 기록과 의도 추론의 언어 일관성이 깨짐.
7. **Studio 인라인 `tr()` 312곳에 ko가 0개, server `pick()` 73곳은 ko→영어**: 한국어 UI라고 해도 실제로는 대부분 영어. `koreanStrings`는 `Record<string,string>`이라 누락 10키와 오래된 키 30개를 타입 검사가 잡지 못함.
8. **ImportManager의 언어 select에 ko 옵션이 없음**: state는 "ko"인데 화면에는 "中文"이 보임. 사용자가 한 번 바꾸면 ko로 돌아갈 수 없음.
9. **패치가 zh/en 사용자 기본값을 바꿈**(아래 4절). 모든 사용자의 CLI 기본 언어·플랫폼과 init/export 출력이 달라져 "zh/en 동작 불변" 규칙을 어김. 회귀 테스트(`korean-cli.test.ts`)도 "새 프로젝트 기본값 = ko"를 고정해 버림.
10. **`CliLanguage`와 `ShortFictionLanguage`·core 타입을 함께 넓히지 않으면** `parseWritingLanguage`가 받은 ko가 core에서 zh 기본 프롬프트로 떨어질 수 있음(`ShortFictionLanguage = "zh"` 기본 파라미터들). 패치는 core 타입은 넓혔지만 기본값 `"zh"` 경로가 많음.

### 4. 패치가 zh/en 동작을 바꾸는 기본값·출력 변경 (cli/studio)

| # | 위치(패치 hunk) | 변경 | zh/en 영향 |
|---|---|---|---|
| 1 | cli/commands/agent.ts:57 | `config.language ?? "zh"` → `?? "ko"` | 스키마 기본값이 `"zh"`(core project.ts:106, 패치도 유지)라 보통은 도달하지 않음. 그래도 기본값이 갈라짐 → 되돌려야 함 |
| 2 | cli/commands/interact.ts:96 | `config.language ?? "zh"` → `?? "ko"` | 1과 같음 |
| 3 | cli/commands/book.ts:36-37, 69 | `--genre` 기본값 `"xuanhuan"`, `--platform` 기본값 `"tomato"` 제거. 장르는 `(opts.lang ?? config.language) === "ko" ? "other" : "xuanhuan"`, 플랫폼은 `opts.platform ?? "other"` | **zh/en 사용자가 `--platform` 없이 만들면 tomato가 아니라 other가 됨**. 장르는 zh/en 모두 xuanhuan 유지. `--lang` 검증 추가(잘못된 값이 이제 오류) |
| 4 | cli/commands/init.ts:10-33 | `--lang` 기본값 `"zh"` → `"ko"`, 출력 블록 재작성 | **인자 없는 `inkos init`가 ko 프로젝트를 만듦**. zh/en 출력에서 "Global LLM config detected"/set-global 안내/"English project?" 힌트 제거, zh 예시에 `--lang zh` 추가 |
| 5 | cli/commands/short-fiction.ts:56 | `--lang` 기본값 `"zh"` → `"ko"` | **인자 없는 `inkos short`가 한국어 단편을 생성** |
| 6 | cli/commands/studio.ts:53 | `ensureProjectDirectoryInitialized(…, {language: "zh"})` → `"ko"` | **Studio가 새로 초기화하는 프로젝트가 ko** |
| 7 | cli/localization.ts:56 `resolveCliLanguage` | 최종 기본값 `"zh"` → `"ko"` (+ `ko*` 인식) | LANG=C/POSIX/fr 등이고 INKOS_LOCALE이 없는 사용자의 CLI 메시지가 한국어가 됨(`book.ts:312,353`, `doctor.ts:116`, `config.ts:308`처럼 인자 없이 호출하는 곳). ko_KR 인식 자체는 추가일 뿐이라 괜찮음 |
| 8 | cli/project-bootstrap.ts:126 | `options.language ?? "zh"` → `?? "ko"` | 언어 옵션 없이 부트스트랩하는 모든 경로가 ko 프로젝트를 만듦 |
| 9 | cli/tui/setup.ts:270 `autoInit` | `language: "zh"` → `"ko"` | **TUI 자동 초기화 프로젝트가 ko** |
| 10 | cli/commands/export.ts:32-36 | `book.language ?? "ko"`, 길이를 `formatLengthCount`로 표시 | zh 책의 내보내기 출력이 `(N words)`에서 zh_chars 단위 표기로 바뀜(영어 문장 + 중국어 단위 등). language가 없는 책은 한국어 출력 |
| 11 | studio/api/server.ts:3091 | `book.language === "en" ? "en" : "zh"` → `normalizeStudioLanguage(book.language ?? 프로젝트 language)` | language가 없는 책을 en 프로젝트에서 열면 영감 카드가 zh에서 en으로 바뀜 |
| 12 | studio/api/server.ts:5531 | `POST /project/language`에 지원 언어 검증 추가(400) | 정상 zh/en에는 영향 없음. 예전에는 임의 값을 저장했음(경미) |
| 13 | studio/App.tsx:200, pages/LanguageSelector.tsx:25-35, 80 | 헤더에 `한국어` 버튼, 첫 실행 카드 맨 앞에 ko 카드, 하단 문구 3개 언어 | zh/en 사용자에게 보이는 UI가 바뀜(추가성 변경이지만 첫 화면 구성과 문구가 다름) |
| 14 | studio/api/book-create.ts:39-41 | id 생성에 `normalize("NFC")` + 한글 범위 | zh/en 제목은 사실상 같은 id(NFD 라틴 악센트는 원래도 `-`로 바뀜). 경미 |

규칙(zh/en 불변)에 맞추려면 #1-#10은 되돌림: 기본값 `"zh"` 유지, `--platform` 기본값 `"tomato"`·`--genre` 기본값 `"xuanhuan"` 유지, init/export의 zh/en 출력 원문 유지, ko 문구는 ko일 때만 추가. #11은 ko일 때만 새 로직을 타게 바꿈. #13은 제품 판단 필요.

## 부록 D. 넓힌 검색식 파일별 건수

`rg -c "[=!]==\s*[\"'](en|zh)[\"']" packages/{core,cli,studio}/src` (테스트 제외) — 305줄 / 67파일

| 파일 | 건수 |
|---|---|
| `packages/core/src/prompts/short-fiction.ts` | 30 |
| `packages/core/src/agents/architect.ts` | 18 |
| `packages/core/src/agents/script-storyboard.ts` | 17 |
| `packages/cli/src/tui/agent-input.ts` | 17 |
| `packages/studio/src/api/server.ts` | 16 |
| `packages/core/src/pipeline/short-fiction-runner.ts` | 13 |
| `packages/core/src/agents/writer.ts` | 11 |
| `packages/core/src/pipeline/runner.ts` | 10 |
| `packages/core/src/agent/agent-tools.ts` | 10 |
| `packages/core/src/agents/writer-prompts.ts` | 8 |
| `packages/core/src/agents/short-fiction.ts` | 8 |
| `packages/core/src/agents/fanfic-canon-importer.ts` | 8 |
| `packages/studio/src/pages/BookDetail.tsx` | 7 |
| `packages/core/src/utils/governed-context.ts` | 7 |
| `packages/core/src/state/state-projections.ts` | 7 |
| `packages/core/src/agents/composer.ts` | 7 |
| `packages/core/src/agents/import-context.ts` | 6 |
| `packages/studio/src/pages/BookCreate.tsx` | 5 |
| `packages/core/src/play/play-runner.ts` | 5 |
| `packages/core/src/play/play-agents.ts` | 5 |
| `packages/core/src/agents/semantic-context-compiler.ts` | 5 |
| `packages/cli/src/progress-text.ts` | 5 |
| `packages/studio/src/pages/LanguageSelector.tsx` | 4 |
| `packages/core/src/utils/narrative-control.ts` | 4 |
| `packages/core/src/agent/film-authoring-tools.ts` | 4 |
| `packages/cli/src/tui/effects.ts` | 4 |
| `packages/studio/src/components/chat/NarrativeForecastPreview.tsx` | 3 |
| `packages/core/src/pipeline/chapter-state-recovery.ts` | 3 |
| `packages/core/src/forecast/prompts.ts` | 3 |
| `packages/core/src/agents/settler-prompts.ts` | 3 |
| `packages/studio/src/api/book-create.ts` | 2 |
| `packages/studio/src/App.tsx` | 2 |
| `packages/core/src/utils/length-metrics.ts` | 2 |
| `packages/core/src/state/manager.ts` | 2 |
| `packages/core/src/interaction/export-artifact.ts` | 2 |
| `packages/core/src/harness/artifact-validation.ts` | 2 |
| `packages/core/src/forecast/render.ts` | 2 |
| `packages/core/src/agents/style-guide.ts` | 2 |
| `packages/core/src/agents/state-validator.ts` | 2 |
| `packages/core/src/agents/reviser.ts` | 2 |
| `packages/core/src/agents/planner-prompts.ts` | 2 |
| `packages/core/src/agent/agent-session.ts` | 2 |
| `packages/cli/src/tui/setup.ts` | 2 |
| `packages/cli/src/commands/short-fiction.ts` | 2 |
| `packages/cli/src/commands/init.ts` | 2 |
| `packages/studio/src/pages/Dashboard.tsx` | 1 |
| `packages/studio/src/lib/truth-display.ts` | 1 |
| `packages/studio/src/lib/error-copy.ts` | 1 |
| `packages/studio/src/lib/app-language.ts` | 1 |
| `packages/studio/src/hooks/use-i18n.ts` | 1 |
| `packages/core/src/utils/chapter-document.ts` | 1 |
| `packages/core/src/pipeline/script-storyboard-runner.ts` | 1 |
| `packages/core/src/llm/long-form-completion.ts` | 1 |
| `packages/core/src/interaction/session-transcript-restore.ts` | 1 |
| `packages/core/src/harness/tools/short-production.ts` | 1 |
| `packages/core/src/harness/tools/longform-production.ts` | 1 |
| `packages/core/src/harness/system-prompt.ts` | 1 |
| `packages/core/src/harness/production-capabilities.ts` | 1 |
| `packages/core/src/harness/parent-canon.ts` | 1 |
| `packages/core/src/forecast/context-builder.ts` | 1 |
| `packages/core/src/forecast/agent.ts` | 1 |
| `packages/core/src/agents/planner.ts` | 1 |
| `packages/core/src/agents/continuity.ts` | 1 |
| `packages/cli/src/tui/slash-autocomplete.ts` | 1 |
| `packages/cli/src/tui/i18n.ts` | 1 |
| `packages/cli/src/localization.ts` | 1 |
| `packages/cli/src/commands/import.ts` | 1 |
