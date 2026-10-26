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

(본문은 보고와 같음. 표는 아래 "크기")

## 2. 활성화

(브리지 시험 뒤 채움)
