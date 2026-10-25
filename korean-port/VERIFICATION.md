# 검증 기록 (VERIFICATION)

작품 폴더(`works/` 등)와 브리지 요청 기록(`tools/inkos-agent-bridge/runtime/`)은 git에 남지 않으므로, 클라우드 세션이 끝나기 전에 확인한 결과를 여기에 옮겨 적는다.

## 2026-10-25 — 2-1단계: `book create` 설계 프롬프트의 장르 references

환경: Claude Code 클라우드, 브랜치 `claude/eeum-n0rsol`, Node v22.22.0. API 키 없음. 브리지 `tools/inkos-agent-bridge`(1.1.0)로만 실행.

준비:

```
inkos init ko-novel --lang ko                      # inkos.json "language": "ko"
sh tools/inkos-agent-bridge/install.sh --project <ko-novel>
INKOS_BIN=<wrapper: exec node packages/cli/dist/index.js "$@">   # dist/index.js에 실행 권한이 없어 래퍼 사용(4-1단계 설치 스크립트에서 처리할 것)
inkos-agent doctor
  inkos binary : …/bin/inkos (2.0.0)
  project      : …/ko-novel (ok)
  bridge       : up at http://127.0.0.1:4568/v1
  proxy env    : HTTPS_PROXY, https_proxy (stripped for inkos jobs)
  (modelOverrides 경고 없음)
```

장르마다 `inkos-agent job start -- book create --title <제목> --genre <장르> --lang ko --target-chapters 30`을 실행하고,
첫 architect 요청(`tools=submit_foundation_outline`)의 `prompt.md`를 확인했다. 확인이 목적이라 답하지 않고 `inkos-agent fail`로 끝냈다
(작업은 exit=1, "draft Work … preserved"로 종료 — 의도한 결과).

| 장르 | 요청 ID | 프롬프트에 들어간 장르 문서 | 다른 장르 문서 | 요청 상태 |
| --- | --- | --- | --- | --- |
| `light-martial` | r-20261025-102523-934a9476 | `references/genres/light-martial.md:0-2069` (`# 장르 기준: 한국 라이트 무협 (light-martial)`) | 없음 | failed(의도) |
| `fantasy` | r-20261025-102727-16ad5f02 | `references/genres/fantasy.md:0-1756` (`# 장르 기준: 판타지 (fantasy)`) | 없음 | failed(의도) |
| `modern-fantasy` | r-20261025-102731-ed27925f | `references/genres/modern-fantasy.md:0-1649` (`# 장르 기준: 현대판타지 (modern-fantasy)`) | 없음 | failed(의도) |

세 프롬프트 모두 공통으로 확인한 것:

- `## Korean writing language (ko)`와 `## 소설 설정의 항목별 작성 계약`(언어 정책 주입)
- `### inkos-long-writing` 아래 `# 한국어 장편 집필 방법`(한국어 스킬)과 링크된 references 5개: `foundation-design.md`, `reader-contract-and-progression.md`,
  `scene-dialogue-and-length-budget.md`, `korean-prose.md`, `state-projection.md`
- `Genre: <장르>` 작품 메타데이터

같은 실행에서 발견해 고친 것: architect의 외부 지시 제목이 ko 작품에도 `## 外部指令`(중국어)로 나왔다(원본은 en에도 중국어). ko에만 `## 외부 지시` 분기를 추가했고,
fantasy·modern-fantasy 실행에서 `## 외부 지시`로 나오는 것을 확인했다.

필터가 실제로 필요한지도 확인했다: 같은 질의("무협 판타지 현대판타지 마법 내공 게이트 등급 회차를 써라")로 `retrieveSkillResources`를 직접 호출하면
`genres/modern-fantasy.md`, `genres/fantasy.md`, `genres/light-martial.md`, `state-projection.md`가 모두 검색된다. 장르 문서를 고르는 코드
(`packages/core/src/skills/korean-genre-references.ts`)가 선택된 장르 외의 문서를 걸러낸다.
