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

## 2026-10-25 — 5-a단계: 한국어 실제 생성 검증 1차 (라이트 무협 2화)

새 ko 프로젝트 `novel/`(git 무시), 브리지 1.2.0, API 키 없음. 역할 분리: 기획·집필·정산은 writer 서브에이전트(`inkos-writer.md`),
검수·상태 검증은 그 글을 쓰지 않은 reviewer 서브에이전트(`inkos-reviewer.md`). 메인 세션은 요청 배분과 확인만 했다.

```
inkos-agent job start -- book create --title "청운객잔 셋째 사환" --genre light-martial --lang ko --target-chapters 30 --chapter-words 3000
→ j-20261025-142222-dd96aebc exit=0  "작품을 생성했습니다: 청운객잔-셋째-사환 … 다음: inkos write next 청운객잔-셋째-사환"
inkos-agent job start -- write next 청운객잔-셋째-사환 --count 1
→ j-20261025-143317-784f0df1 exit=1  [ERROR] Failed to write chapter: Error: Unable to decode value as it does not match the expected schema
   (모델 호출 전. CLI가 write_chapters에 필수인 startChapterNumber를 넘기지 않음 — 모든 언어 공통 원본 결함. 커밋 0d1465d로 수정)
→ j-20261025-143729-ad9bb1cc exit=0  1화 "장날 밤" 분량: 2914자, 검수 의견 8건
→ j-20261025-145504-f0501fa6 exit=0  2화 "증인 없는 아침" 분량: 2866자, 검수 의견 7건
```

### 설계(book create)

- `book.json`: `language: "ko"`, genre `light-martial`, 30화, 회차당 3,000. 설계·인물·상태 파일 제목과 본문 모두 한국어.
- 인물 카드: `story/roles/major/`(곽대수·막삼·변유겸·윤다래·윤만석·진팔), `story/roles/minor/`(구만길·엄 영감·연청호·탁명옥·피오복). `主要角色`/`次要角色` 폴더 없음.
- 설계 요청 프롬프트의 장르 문서: `references/genres/light-martial.md` 하나(다른 장르 문서 0건). 1화 기획 프롬프트에서도 같은 결과.
- 스냅샷 0 생성. 복선 8개(deferred). `story_frame.md` 본문에 한자 1곳.

### 분량(`ko_chars`: NFC, 공백·제목 제외)

| 회차 | 제목 | 엔진 기록(index.json) | 파일 재계산 | 목표 범위 2,591~3,409 / 한계 2,182~3,818 |
| --- | --- | --- | --- | --- |
| 1 | 장날 밤 | 2914 | 2914 | 범위 안 |
| 2 | 증인 없는 아침 | 2866 | 2866 | 범위 안 |

### 상태 승계 (1화 → 2화)

- 1화: 정산 → 상태 검증 `reconciliationRequired: true`(6건) → 재정산 → 재검증 `true`(1건). 남은 1건은
  ledger-poison·truce-witness 메모의 "startChapter를 1로 둔다"와 표의 시작 회차 `0`이 어긋난다는 지적이었다.
  엔진 규칙 때문이다: `packages/core/src/state/state-reducer.ts:135` `startChapter: Math.min(existing.startChapter, incoming.startChapter)` —
  설계 때 0으로 등록된 복선은 무엇을 보내도 0이다. 재검증이 실패하면 `chapter-truth-validation.ts`가 기준 상태를 유지한다(`preserveCanonicalRuntimeState`).
- 결과: 1화 원고는 저장됐지만 1화 상태는 저장되지 않았다(`state/manifest.json` `lastAppliedChapter: 0`, `current_state.md` "현재 회차: 0" 빈 표,
  `chapter_summaries.md` 머리만, 복선 8개 모두 deferred 0/0). 1화 관찰에 `state-reconciliation`이 남았다.
- 2화 기획 프롬프트에는 1화 본문 전체가 "Previous chapter text required for chapter transition planning."으로 들어갔다. writer는 이 본문만을 근거로 계획했다.
- 2화 정산 프롬프트에는 1화 본문이 없다. 그래서 2화 본문이 다시 말한 1화 사실(빈 궤, 허리춤의 열쇠, 찻잔, 약탕 그릇, 두 냥 반, 종아리)만 상태에 들어갔고,
  1화에만 있는 사실(손님 수·방 배정, 매상, 엄 영감의 굽은 손, 피오복의 염창 소문)은 상태에서 빠졌다.
- 2화: 정산 → 검증 `true`(고칠 수 있는 4건 + 관찰 2건) → 재정산 → 재검증 `false`. 저장됨: `lastAppliedChapter: 2`, 회차 요약은 2화 한 줄,
  ledger-poison·truce-witness `progressing`(시작 0, 최근 진전 2), 나머지 6개 deferred.
- 본문 사이 모순(검수가 찾은 것): 2화 25행 막삼의 답 "마감하고 나서 위층에 올라간 사람은 주인어른과 큰형" — 1화에서 윤만석은 다툼 직후(영업 중)에,
  대수는 마감 정리 중에 올라갔다. 2화 정산 프롬프트에 1화 본문이 없어 상태 검증에서는 대조하지 못했고, 막삼의 진술로만 기록됐다.
  2화 안의 모순: 15행 "옆방 침상"으로 옮기는데 "계단참"에서 종아리가 꺾인다.

### 감사와 "한국어 문장 점검"

- 1화 감사 요청(r-20261025-144245-c3b603ef)에 블록이 들어갔다:
  ```
  ## 한국어 문장 점검 (host가 계산한 결정론적 관찰)
  - `ending-repetition` 서술 문장 6개가 연달아 `~었다`로 끝납니다. (줄 137, 139)
  ```
  reviewer는 발견 장면의 의도된 리듬(열쇠·뚜껑·빈 궤를 한 문장씩 확인)으로 판단해 관찰로 남기지 않았고, 그 판단을 요약에 적었다.
- 2화 감사 요청에는 블록이 없다. 검사기가 찾은 것이 없으면 블록을 넣지 않는다(`renderKoreanProseFindings`: `if (!findings.length) return ""`).
  저장된 2화 파일에 검사기를 직접 돌린 결과도 `[]`.
- 1화 첫 감사 응답은 도구 검증에서 거부됐다: `A scope violation requires distinct verified before/current sources and citations to both.`
  (`scope`는 수정 전후 비교에만 쓰는 분류). reviewer가 같은 지적을 `quality`로 다시 보냈고 등급(중간)은 유지했다.
- 감사 결과 요약
  - 1화(8건): memo-boundary-banshangbo(중간, 2화 박자인 반상보로 칼 막기를 1화가 먼저 씀), narrator-telling·duplicate-introduction·prose-ambiguity(경미),
    clue-vessel-record·hook-movement(관찰), governed-context-incomplete(unavailable), state-reconciliation.
  - 2화(7건): spatial-continuity·ledger-entry-stamp-logic·dialogue-attribution·narrator-recap(경미), stamp-count-record·hook-movement(관찰), governed-context-incomplete(unavailable).

### 근거 자료가 비어 들어간 것 (원인 확인)

- 이야기 틀: 모든 기획·집필·감사 프롬프트에 `# 청운객잔 셋째 사환 — 이야기 틀` 제목 한 줄만 들어갔다(파일은 6,210바이트, 절 8개).
  원인: `packages/core/src/agents/composer.ts:1018` `slugifyAnchor`가 `a-z0-9`와 한자(U+4E00–9FFF)만 남긴다. 한글 제목은 모두 `section`이 되고
  `dedupeBySource`가 첫 절만 남긴다. 측정: `story_frame.md 8 sections -> 1 distinct anchors`, `volume_map.md 4 sections -> 4`(제목에 숫자가 있어 우연히 구분됨).
  ko 전용 결함. 5-a 지시("4단계 수정 하지 말 것")에 따라 고치지 않았다.
- 작가 의도 `Create 청운객잔 셋째 사환` 한 줄, 현재 작업 초점은 빈 서식(book create 기본값).
- 복선 근거(Evidence)의 상세 줄에 hook id가 없다(`source`에만 있음). composer의 원본 동작이며 zh/en도 같다.

### 스냅샷과 브리지 요청

- 스냅샷: `story/snapshots/0`, `1`, `2`.
- 요청 19건 모두 delivered, failed 0, 버려짐 0.

| 요청 | 도구 | 답한 쪽 |
| --- | --- | --- |
| r-20261025-142223-4f24ad28 | submit_foundation_outline | writer |
| r-20261025-142541-b367e2c5 | submit_foundation_details | writer |
| r-20261025-142819-9bea38be | submit_foundation_cast_index | writer |
| r-20261025-142900-dbd28a55 | submit_foundation_cast_documents | writer |
| r-20261025-143731-e6186d18 | submit_chapter_memo (1화) | writer |
| r-20261025-143902-f5327536 | submit_chapter_draft (1화) | writer |
| r-20261025-144126-6795887b | submit_runtime_state_delta (1화) | writer |
| r-20261025-144245-c3b603ef | submit_chapter_review (1화, 도구 검증 거부) | reviewer |
| r-20261025-144645-93ac8ec5 | submit_chapter_review (1화 재제출) | reviewer |
| r-20261025-144755-f4867114 | submit_state_validation (1화) | reviewer |
| r-20261025-145043-01a61fd1 | submit_runtime_state_delta (1화 재정산) | writer |
| r-20261025-145211-d2a31239 | submit_state_validation (1화 재검증) | reviewer |
| r-20261025-145505-67496f11 | submit_chapter_memo (2화) | writer |
| r-20261025-145717-297bdddd | submit_chapter_draft (2화) | writer |
| r-20261025-145932-aa75e59b | submit_runtime_state_delta (2화) | writer |
| r-20261025-150134-78d708cb | submit_chapter_review (2화) | reviewer |
| r-20261025-150513-543c2234 | submit_state_validation (2화) | reviewer |
| r-20261025-150712-b4acb310 | submit_runtime_state_delta (2화 재정산) | writer |
| r-20261025-150829-83a07f5c | submit_state_validation (2화 재검증) | reviewer |

### CLI·로그의 중국어 문구 (목록만, 고치지 않음)

- 이번 실행의 CLI 출력과 job 로그 4개(book create, 실패한 write, 1화, 2화)에 중국어(한자) 줄 0개.
- 한국어가 아닌 출력(참고): `INFO [inkos] Stage: …`, `[writer] Phase 2: state settlement for chapter 1 (2914 words)`(ko에 `words` 단위),
  `streaming 30s, 0 chars (0 CJK)`, `State validation: N observation(s) …`(영어).
- 출력되지 않았지만 코드에 있는 중국어: 알림 제목 `${book.title} 第${chapterNumber}章`(`pipeline/runner.ts`, 알림 채널을 설정했을 때만), 상태 검증 경고의 zh 문구.

### 원고 보관 (Drive 연결)

- `python3 tools/novel-drive.py pack novel 청운객잔-셋째-사환_20261025-1510_2화.tar.gz` → 752,334바이트(`.inkos` 2MB가 대부분).
- 이 세션의 Google Drive 연결 도구(`create_file`)는 내용을 base64 문자열로 호출 안에 직접 넣는다. 752KB(base64 약 1MB)는 넣을 수 없어 올리지 못했다.
- 대신 원고 2화와 상태 파일(`current_state.md`, `chapter_summaries.md`, `pending_hooks.md`, `state/manifest.json`)만 묶은
  `청운객잔-셋째-사환_20261025-1510_2화_원고.tar.gz`(11,430바이트)를 바이너리(application/gzip)로 "Inkos ko" 폴더에 올렸다.
  Drive가 돌려준 크기 11,430 일치. 바이트 단위 대조(체크섬)는 연결 도구가 제공하지 않아 하지 못했다.
