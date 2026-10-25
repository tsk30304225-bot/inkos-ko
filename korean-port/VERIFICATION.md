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

## 2026-10-25 — 2-2단계: 드라마 대본 1회분, 설명 영상 대본 1편 (브리지 실제 생성)

같은 프로젝트(`inkos init --lang ko`), 같은 브리지. 요청은 세션(Claude Code)이 writer 역할로 직접 답했다. API 키 없음.

### 드라마 대본 (기본 형식 세로형 숏드라마)

```
inkos-agent job start -- script create --title "새벽 세 시의 배달" \
  --instruction "새벽 편의점 아르바이트생 서윤이 … 1화 끝에서 도시락 주인에 대한 첫 단서가 뒤집힌다." \
  --episodes 1 --episode-duration "2분"
→ 요청 r-20261025-120551-6d3f23b1 (delivered)
→ job j-20261025-120550-47657d49 exit=0
   Script "새벽-세-시의-배달" completed.
```

- 프롬프트 확인: `### inkos-script-writing` 아래 `# 한국어 드라마 대본 집필`, references `korean-drama-format.md`·`episode-scene-craft.md`,
  명세 `- 납품 형식: 세로형 숏드라마`(형식을 지정하지 않음 → ko 기본값), 출력 계약 `## 등장인물`/`## 장소`/`## 대본`.
- 저장 파일(`works/새벽-세-시의-배달/source/`): `script-spec.md`, `script.md`, `script-references.md`(등장인물 3명·장소 3곳 목록). work.json `profileId: script`, `language: ko`.
- 형식 검사(스크립트로 확인): 제목 `## 등장인물`·`## 장소`·`## 대본` 순서 일치, 씬 `S#1`~`S#5` 연속, 모든 씬 머리의 장소가 `## 장소` 목록에 있음, 본문 805자(공백 제외).

### 설명 영상 대본 (기본 길이 롱폼 8~15분)

원자료: `korean-port/PLAN.md` 사본(`sources/inkos-ko-plan.md`). 사실 주장은 이 문서에서만 가져와 출처 [1]~[3]으로 표시했다.

```
inkos-agent job start -- explainer create --title "AI 소설 도구는 한국어 분량을 어떻게 셀까" \
  --topic "InkOS 한국어판이 회차 분량을 공백 제외 글자 수로 세게 된 이유와 방식" \
  --audience "AI 집필 도구에 관심 있는 웹소설 작가" --source sources/inkos-ko-plan.md
→ 요청 r-20261025-120654-b7d29636 (delivered)
→ job j-20261025-120652-cdeee90b exit=0
   형식 검사: …/explainer-check.md — 통과, 장면 20개, 501초
```

- 프롬프트 확인: `### inkos-ko-explainer-script` 아래 `# 한국어 설명형 영상 대본`, references `scene-table.md`·`review-questions.md`, 명세 `목표 길이: 롱폼(기본) → 480~900초`.
- 저장 파일: `explainer-spec.md`, `explainer-script.md`, `explainer-check.md`, `explainer-check.json`, `source-material.md`. work.json `profileId: explainer-script`, `language: ko`, `status: active`.
- 형식 검사 결과(`explainer-check.md`): 통과 — 장면 20개, 합계 501초(목표 480~900초), 형식 문제 없음, 검수 참고 없음.
- 답을 쓰는 중에 발견해 고친 것: 첫 초안은 형식은 통과했지만 내레이션이 1초에 1.2~3자(공백 제외)로, 장면 길이에 비해 너무 적었다(무음 구간이 길어짐).
  검사기가 빠른 내레이션만 지적하고 있어 `narration-sparse` 관찰(1초에 3자 미만, 10초 이상 장면)을 추가했고, 초안에서 19개 장면이 걸리는 것을 확인했다.
  내레이션을 다시 쓰고 장면 길이를 내레이션 분량(약 1초 4자)에 맞춰 다시 계산한 뒤 제출했다(최종 1초 4.0~4.1자).

### 브리지 요청 목록(이번 세션 전체)

| 요청 | 상태 | 내용 |
| --- | --- | --- |
| r-20261025-102523-934a9476 | failed(의도) | 2-1 light-martial 프롬프트 확인 |
| r-20261025-102727-16ad5f02 | failed(의도) | 2-1 fantasy 프롬프트 확인 |
| r-20261025-102731-ed27925f | failed(의도) | 2-1 modern-fantasy 프롬프트 확인 |
| r-20261025-120551-6d3f23b1 | delivered | 2-2 드라마 1회분 |
| r-20261025-120654-b7d29636 | delivered | 2-2 설명 영상 대본 |
