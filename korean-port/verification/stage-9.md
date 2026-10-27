# 9단계 검증 — 라이트 무협 문체 스킬 편입 (프리셋 B)

2026-10-27, 브랜치 `claude/eeum-n0rsol`. 기준: 감독 설계안 `light-murim-style-design.md`와 9단계 지시서. 원작 금지 목록(파일 5)은 받지 않았고 쓰지 않았다.
저장소·시험·보고에 원작 고유명사를 쓰지 않았다. 시험 작품 `test-9-…`은 지어낸 이름만 쓰고 밖으로 내보내지 않는다.

## 0. 먼저 확인한 것

1. writer 2단계(상태 정산)도 `this.name = "writer"`로 같은 `submitStructured` → `prepareWorkerMessages(…, "writer")`를 거친다(`agents/writer.ts:316`, `agents/base.ts:55-81`).
   지난 정산 요청 프롬프트(`r-20261025-215933-…`)에도 `inkos-long-writing` 스킬 블록이 붙어 있었다.
   정산 호출에는 `writer.ts:314`가 붙이는 고정 문자열 `## Settlement baseline`이 있다. 원본을 고치지 않고 이 표식이 있는 writer 호출에는 문체 스킬을 붙이지 않는다(시험으로 확인).
2. continuity-auditor 프롬프트에는 `book_rules.md` 본문도 `style_guide.md`도 들어가지 않는다(고치지 않음).
   - test-6 3화 감사 요청(`r-20261025-215715-…`)의 user 메시지 출처는 `governed-context`와 원고 두 개다.
   - governed-context의 증거 93개는 현재 상태 54, hook 9+5, story_frame 절 8, 인물 8, 계획 노드 4, 기억 2, memo·focus·author_intent 각 1이다.
   - `book_rules.md`의 긴 줄 38개 가운데 감사 프롬프트에 그대로 있는 것은 1줄뿐이다(작가 의도에 같은 문장이 있어서). `agents/continuity.ts`에는 book_rules·style_guide·prohibitions를 읽는 코드가 없다.
   - 그래서 `book_rules`의 금지는 감사가 직접 보지 못한다. 이 스킬의 치명 등급 "작품 `book_rules`의 금지 위반"은 감사가 아는 범위(작가 의도, story_frame)에서만 걸린다.

## 1. 스킬 파일 정리

`packages/core/skills-ko/inkos-ko-light-murim/`: `SKILL.md`, `references/combat-patterns.md`, `references/scene-patterns.md`, `references/examples.md`.
분석 파일 1~4의 코드 블록을 스크립트로 옮기고 정리했다(각 바꿈은 원문이 정확히 한 번 있을 때만 적용되게 확인).

| 파일 | 정리 전(코드 블록) | 정리 후 |
|---|---|---|
| SKILL.md | 27,015 B | 29,923 B |
| combat-patterns.md | 25,539 B | 25,385 B |
| scene-patterns.md | 20,777 B | 20,530 B |
| examples.md | 22,303 B | 18,431 B |
| 합계 | 95,634 B | 94,269 B |

- 지운 것: 파일 1 머리말 전체(분석 범위, 근거 코드 표, 표기 규칙, 요약), 각 파일 앞뒤 안내 문장, `근거: E…` 줄과 줄 안의 `근거: E…`, `(대략, E…)` → `(대략)`, 회차 번호, `§`, `## 파일 N — ` 접두어.
  예문 파일 맺음말의 "확인하지 못한 것"도 지웠다.
- 옮긴 것(지시와 다름, 판단): 예문 파일 맺음말의 "규칙끼리 충돌하는 곳" 표와 "엔진 기본 규칙과 부딪히는 장치" 목록은 규칙이라 지우지 않고 SKILL.md `## 다른 규칙과의 관계` 아래 `###` 두 절로 옮겼다.
- 뜻을 지키려고 남긴 표시: 지운 T2 근거 줄에 있던 "복귀 지점은 미관찰"을 `[공통 / 복귀 지점은 추정]`으로 남겼다. SKILL "전투 패턴 고르기" 표의 근거 칸에 있던 관찰 범위(장시간 농락 미관찰 등)는 요약 칸 괄호로 옮겼다.
  C10의 근거 줄은 E 코드만 빼고 `관찰 범위:`로 남겼다(C2를 대체 카드로 쓸 수 있다는 규칙 때문).
- "참고작의 ○○(구체 묘사)" 12곳은 "참고작 고유 재료 대신 작품 고유 재료로 바꾼다"로 일반화했다. 원래 방향(작품 주인공의 습관 등)은 괄호로 남겼다. 지운 구체 묘사 목록은 커밋하지 않고 사용자에게 따로 건넸다.
  일반 문장인 장면 "흔한 실패" 표의 "참고작의 특정 비유, 동작, 버튼 행동, 호칭을 그대로 씀"은 그대로 두었다.
- 엔진에 맞춤: 등급 표에 엔진 값 칸(통과 → 기록하지 않음, 경미 → `observation`, 중대·치명 → `issue`), "reviser에게 넘긴다"류 → "issue로 보고한다(수정은 사용자가 revise를 부를 때)".
  치명 기준과 금지 11번의 "파일 5" → "작품 `book_rules`의 금지". 설계안 2-6에 따라 "장치 자체를 이유로 issue를 만들지 않는다"와 수정 규칙 8(spot-fix·polish에서 장치를 바꾸지 않음)을 더했다.
- 절 제목: 설계안 템플릿과 지시 1-5대로. combat `## 흔한 실패 (카드 공통)` → `## 흔한 실패`. examples는 파일 1~3 절 이름과 같게(`## C1 일격 압살`, `## 일상` …). 두 흔한 실패는 `## 흔한 실패 (전투 카드 공통)`, `## 흔한 실패 (장면)`.
- SKILL.md에는 참고 문서 경로를 백틱·링크로 적지 않았다(파일 이름만). 시험으로 막는다.
- 예문은 그대로 썼다(사용자 확인, §C5 포함).

## 2. 활성화

- 새 파일 `packages/core/src/skills/korean-genre-skills.ts`, `agents/base.ts` 2줄(+import 1줄), `korean-genre-references.ts`의 `readBookGenre` export.
- 켜지는 조건: 작품 language `ko`, `resolveKoreanGenre`가 light-martial, `works/<ID>/source/story/korean_style_preset`(1.8 구조는 `books/<ID>/story/…`) 내용이 `light-murim-comic`. 묶음 ko 스킬 폴더의 이 스킬만 쓴다.
- 작업자별 첨부는 코드가 정한다. 검색으로 이 스킬 조각이 섞이지 않는다(이 스킬은 검색 대상 활성 스킬이 아니고, 같은 ID가 이미 있으면 빼고 다시 넣는다).

| 작업자 | SKILL.md | combat | scene | examples |
|---|---|---|---|---|
| planner | 전체 + 프리셋 지시 2줄(memo에 `장면 유형:`, 전투 회차는 `전투 패턴: C? → C?`) | 고르기 표, 조합 예시 | 유형 목록 | — |
| writer 본문 | 전체(아래 상한) | 전체 | 전체 | 전체 |
| writer 정산(`## Settlement baseline`) | — | — | — | — |
| continuity-auditor | 금지, 검수 판정 기준, 다른 규칙과의 관계 | 흔한 실패 | 흔한 실패 | — |
| reviser | 전체 | 전체 | 전체 | — |
| 그 밖(architect, settler, state-validator, composer 등) | — | — | — | — |

- writer 상한: 네 파일 전체는 94KB라 늘 넘는다. 넘으면 writer는 memo의 전투 카드(없으면 고르기 표)와 장면 유형(+유형 목록), 공통 예문(서술 목소리·리듬·개그 문법·온도 전환·금지)과 고른 카드·장면의 예문만 받는다.
  SKILL.md에서는 다른 작업자용 부분(검수 판정 기준, 장면·전투 고르기 요약, "엔진 기본 규칙과 부딪히는 장치")을 뺀다.
  상한은 지시의 45KB로는 맞지 않아 사용자 결정으로 50KB → 60KB(2026-10-27).

단위 시험에서 잰 바이트(스킬 블록, 참고 절 머리줄 포함):

| 경우 | 바이트 |
|---|---|
| planner | 41,104 |
| writer 일상(장면 1, 카드 없음) | 39,966 |
| writer 전투(장면 2, 카드 2) | 47,563 |
| writer 가장 무거운 memo(장면 3, 카드 3) | 58,037 |
| continuity-auditor | 21,787 |
| reviser | 82,630 |

## 3. 충돌 문장, 인터뷰

- 우리 ko 파일만 고쳤다(원본 `skills/`와 장르 문서는 그대로):
  - long-writing SKILL.md 군중 반응 줄, korean-prose.md 7행(같은 어미)·47행(군중)에 "작품에 장르 문체 스킬이 켜져 있고 그 스킬의 '의도된 장치' 조건을 충족하면 그 기준을 따른다."
  - deslop SKILL.md "정당한 목소리 선택" 줄 뒤에 "장르 문체 스킬이 정한 장치는 목소리 선택으로 본다."
- `novel-brief.py interview <brief>`는 장르 답이 라이트 무협일 때만 `문체 1) 기본 라이트 무협 2) 경쾌한 코믹 라이트 무협`을 더 묻는다(처음 7문항은 그대로).
- 브리프에서 작품 파일로: `book create --brief`가 브리프를 `story/brief.md`로 옮기므로(`pipeline/runner.ts:474`), 설계 직후 실행하는 `interview --work`가 그 파일의 문체 답을 보고 `story/korean_style_preset`을 쓴다("정해짐: 문체 프리셋: …" 출력). 끄려면 파일을 지운다.

## 4. 브리지 시험 (시험 작품 `test-9-light-솔바람관-막내`, 밖으로 내보내지 않음)

브리프(장르 1, 문체 2) → `book create`(요청 4건) → `interview --work`가 프리셋을 씀 → 1화(전투), 2화(일상). writer 역할과 reviewer 역할을 다른 서브에이전트가 맡았다. reviewer에게는 심은 장치·결함을 알리지 않았다.

| 요청 | 도구 | 프롬프트 | 스킬 블록 | 프리셋 전 | 붙은 참고 절 |
|---|---|---|---|---|---|
| 1화 memo | submit_chapter_memo | 101,414 | 34,399 | 67,015 | combat 고르기 표·조합 예시, scene 유형 목록 |
| 1화 본문 | submit_chapter_draft | 120,746 | 41,601 | 79,145 | combat C1·C7, scene 유형 목록·일상·분노, examples 공통 5절·C1·C7·일상·분노 |
| 1화 정산 | submit_runtime_state_delta | 90,924 | 0 | 90,924 | — |
| 1화 감사 | submit_chapter_review | 104,288 | 15,084 | 89,204 | combat·scene 흔한 실패 |
| 1화 상태 검증 | submit_state_validation | 69,644 | 0 | 69,644 | — |
| 2화 memo | submit_chapter_memo | 119,529 | 34,399 | 85,130 | 같음 |
| 2화 본문 | submit_chapter_draft | 125,192 | 33,304 | 91,888 | combat 고르기 표, scene 유형 목록·일상, examples 공통 5절·일상 |
| 2화 정산 | submit_runtime_state_delta | 110,041 | 0 | 110,041 | — |
| 2화 감사 | submit_chapter_review | 117,156 | 15,084 | 102,072 | combat·scene 흔한 실패 |
| 2화 상태 검증 | submit_state_validation | 77,599 | 0 | 77,599 | — |

("프리셋 전" = 프롬프트 − 스킬 블록. 프리셋이 더하는 것은 이 블록뿐이다.)

- memo: 1화 `장면 유형: 일상 → 분노`, `전투 패턴: C1 → C7` / 2화 `장면 유형: 일상`(전투 줄 없음). writer 본문 프롬프트에 그 카드·장면만 붙었다.
- 1화 "새끼줄 너머" 2,904자, 2화 "멀건 죽과 삼백 냥" 2,862자. 두 회차 모두 상태 반영(재정산 요구 없음).
- 감사(엔진 저장 결과, 원문 일부):
  - 1화 1건 `issue` `anger-scene-gag-leak`: "하랑이 피를 흘린 뒤의 분노 장면에서 '사내가 뒷걸음질 치는 꼴이 꼭 장날 놓친 돼지 같았다'는 서술자의 비꼼·개그 비유다. … 스킬 금지 8(분노 장면의 개그)을 어겨 … 장치의 위치 오류이므로 중대 등급이다." — 일부러 넣은 결함 그 문장이다.
    심은 장치(장터 일제 정적 → 다음 문장 하랑 한 사람으로 좁힘, 발소리 `저벅` 1·2·3회)는 올라오지 않았다. 감사 요약: "군중 일제 반응 … 각각 바로 하랑 한 사람으로 좁혀진다. … 저벅 1→2→3 발소리 … 정당한 장치다."
  - 2화 3건(심은 결함 없음): `issue` `injury-used-as-gag`(연무 속말 "깨진 건 이마가 아니라 두부였는데"가 하랑의 실제 부상을 개그로 씀), `observation` `continuity-public-violence`(1화와 어긋나는 회상 한 줄), `observation` `repeated-quip-formula`(같은 문형 1회 과용).
    writer가 실제로 잘못 쓴 문장들이다. 심은 장치(피해자 속말 합창 3줄, 밥상 앞 네 사람의 일제 시선 → 방철)는 올라오지 않았다.
- 한계: 감사도 writer도 같은 계열 모델(서브에이전트)이 답했다. 이 시험은 감사 프롬프트에 판정 기준이 들어가 그 기준으로 장치와 결함을 가를 수 있음을 보인 것이다. 다른 모델이 같은 판정을 하는지는 확인하지 않았다.

## 5. 시험 수

프록시 변수 제거, shim 경유: core 765(757 + 새 8) / studio 307 / cli 101 = 1,173 통과(원본 1,165 그대로 통과). 브리지 38/38, 프로젝트 기록 19/19, Drive 51/51, novel-brief 31/31(+4), 설치 스크립트 58/58.
