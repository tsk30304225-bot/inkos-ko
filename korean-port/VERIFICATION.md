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

## 2026-10-25 — 5-a 보완 후 재실행 (라이트 무협 2화, 새 작품)

5-a 보완(`ab694b9` 상태 검증 기준·상태 미적용 경고, `ce1a9c5` 한글 앵커, `42352b9` `pack --resume`) 뒤 같은 세션에서 새 프로젝트 `novel-5a2/`(git 무시)로 다시 실행했다.
새 writer·reviewer 서브에이전트(1차와 다른 인스턴스). reviewer는 갱신된 `inkos-reviewer.md`와 한국어 스킬을 읽었다. API 키 없음.

```
inkos-agent job start -- book create --title "철쭉골 대장간 막내" --genre light-martial --lang ko --target-chapters 30 --chapter-words 3000
→ j-20261025-154008-f38606d5 exit=0  "작품을 생성했습니다: 철쭉골-대장간-막내"
inkos-agent job start -- write next 철쭉골-대장간-막내 --count 1
→ j-20261025-154732-01f21412 exit=0  1화 "금 간 칼날" 분량: 2897자, 검수 의견: 7건
→ j-20261025-155937-6959dbd5 exit=0  2화 "굴대 하나" 분량: 2880자, 검수 의견: 6건
```

설계: 인물 `roles/major` 7명(모루·편재옥·단석·여울·육현보·마척·설하람), `roles/minor` 3명(설경원·홍 좌수·주담), 복선 8개(H01~H08).
설계 요청 프롬프트의 장르 문서는 `references/genres/light-martial.md` 하나. `narrativePerson`은 설계에서 미정으로 남았고, 이 시험의 회차만 3인칭 제한(모루)으로 썼다.

### 확인 1 — 1화 뒤 상태가 1화 기준으로 채워짐

1화 상태 검증: 첫 검증 `reconciliationRequired: true`. 지적 2건은 둘 다 본문과의 실제 충돌이었다:
풀무숨을 "편재옥이 붙인 이름"으로 적음(본문은 "사부님은 그걸 풀무숨이라 불렀다"), "새벽부터"(본문에 그 시각 표시 없음).
재정산 → 재검증 `false`. 시작 회차 0은 "엔진의 정규화 규칙이지 충돌이 아니다"로 판정해 재정산 사유로 삼지 않았다.

```
$ cat story/state/manifest.json
{ "schemaVersion": 2, "language": "ko", "lastAppliedChapter": 1, "projectionVersion": 1 }
$ chapter_summaries.md
| 1 | 금 간 칼날 | 모루, 편재옥, 단석, 여울, 육현보 | 모루가 한 달 동안 몰래 친 철쭉쇠 칼날을 개울가에서 … 금이 간다. 금계상단 마차가 마을로 들어온다. …
$ current_state.md → "> 현재 회차: 1", 사실 행 30개
$ hooks: H02 progressing 0 1 / H06 progressing 0 1 / hook open 1 1 / 나머지 6개 deferred 0 0
$ snapshots: 0 1
```

### 확인 2 — 2화가 1화에만 있는 사실을 이어받음

- 2화 정산 요청(r-20261025-160234-441013d9)의 기준 상태가 1화 상태다: 프롬프트에 `"chapter":1,"currentState"`, 1화 사실 행("흉년에 마을에 돈을 꿔 준 곳" 등)이 들어 있다. 2화 기획 요청에는 현재 상태 사실 28개, 1화 회차 요약(Evidence "Relevant episodic memory"), 복선 9개가 들어갔다.
- 사례 1. 1화 상태 `| 편재옥 | 모루에게 내린 지시 | 내일 육현보가 오면 모루는 뒤뜰에서 장작을 패라 | 1 | 1 |`
  → 2화 3·9행 "도끼가 장작 한가운데에 박혔다가 멈췄다." / "뒤뜰과 대장간 앞마당 사이에는 어깨 높이의 흙담 하나뿐이었다. 사부님이 왜 하필 뒤뜰로 보냈는지, 모루는 이제야 알 것 같았다." 2화 정산에서 이 지시는 수행됨으로 만료됐다.
- 사례 2. 1화 상태 `| 모루의 첫 칼날 | 금이 간 원인에 대한 말 | … 모루는 사부를 따라 물통 물로 …`
  → 2화 117·119행 "모루는 굴대를 물통 앞까지 들고 갔다가, 멈췄다." / "어제 그 칼날은 물통 물에 넣었다. 그리고 금이 갔다." (굴대를 물 대신 재에 식힘)
- 2화 감사도 1화 상태 사실과 회차 요약으로 대조해 모순 없음(`CH1-CONTINUITY`). 2화 상태 검증은 첫 판정에서 `false`.
- 2화 뒤: `lastAppliedChapter: 2`, 회차 요약 1·2화 두 줄, `hook` resolved(1→2), `hook-2` open, 스냅샷 0·1·2.

### 확인 3 — 설계 절이 모두 프롬프트에 들어감

이야기 틀 제목 9개(새 작품은 제목 포함 9절)가 1화 기획 요청에 모두 들어갔고, 1화 맥락 파일에 서로 다른 출처 9개로 기록됐다:

```
9 story_frame sources
  story/outline/story_frame.md#철쭉골-대장간-막내-이야기-틀
  story/outline/story_frame.md#설정-상태
  story/outline/story_frame.md#전제
  story/outline/story_frame.md#중심-갈등
  story/outline/story_frame.md#동기-요약-상세는-인물-카드
  story/outline/story_frame.md#세계-규칙
  story/outline/story_frame.md#시점과-정보-공개
  story/outline/story_frame.md#톤
  story/outline/story_frame.md#종착-상태-관찰-가능
```
1차 작품의 이야기 틀도 수정 후 다시 재면 `story_frame.md 8 sections -> 8 distinct anchors`(수정 전 `-> 1`).

### 확인 4 — `pack --resume` 압축본을 빈 폴더에 풀어 `inkos status` 비교

```
$ python3 tools/novel-drive.py pack novel-5a2 철쭉골-대장간-막내_20261025-1608_2화.tar.gz --resume
packed novel-5a2 -> …/철쭉골-대장간-막내_20261025-1608_2화.tar.gz (48501 bytes)
$ python3 tools/novel-drive.py unpack 철쭉골-대장간-막내_20261025-1608_2화.tar.gz <빈 폴더>/novel
unpacked 46 files into <빈 폴더>/novel
$ diff <(원본 inkos status) <(복원본 inkos status)        # --json도 같은 결과
< InkOS Project: /home/user/inkos-ko/novel-5a2
> InkOS Project: …/resume-empty-5a2/novel
```
복원본 출력: `회차: 2 / 30`, `분량: 5777자 (회당 평균 2889자, 공백 제외)`, `검수 의견: 13건 (2개 회차)`, `상태 마지막 반영: 2화`. 경로 말고 다른 줄은 없다. `write next`는 실행하지 않았다.

### 확인 5 — Drive 연결로 "Inkos ko"에 올림

압축본 48,501바이트(base64 64,668자)는 연결 도구 한 번의 호출에 그대로 넣기에는 길어서(호출 안에 base64를 직접 써야 한다), 같은 압축본을 12,126바이트씩 4조각으로 나눠 바이너리로 올렸다.

| Drive 파일 | Drive 크기 | 로컬 크기 |
| --- | --- | --- |
| `철쭉골-대장간-막내_20261025-1608_2화.tar.gz.part1of4` | 12126 | 12126 |
| `….part2of4` | 12126 | 12126 |
| `….part3of4` | 12126 | 12126 |
| `….part4of4` | 12123 | 12123 |

로컬에서 4조각을 이으면 원본과 같다(sha256 `4cff0f1d76b8d14e08156f4dd6fe9c74f80c87c2caf311ee1a67150219495450`).
받을 때: 4조각을 받아 `cat ….part1of4 ….part2of4 ….part3of4 ….part4of4 > 철쭉골-대장간-막내_20261025-1608_2화.tar.gz` 후 `unpack`.
Drive 쪽 바이트 대조는 하지 못했다(연결 도구가 체크섬을 주지 않고, 내려받은 내용도 호출 결과로만 돌아온다). 크기만 일치를 확인했다.

### 감사·검증과 "한국어 문장 점검"

- 1화 감사 요청에는 블록이 없다(검사기 결과 `[]`). 2화 감사 요청에는 블록이 들어갔다: `ending-repetition` 서술 문장 4개가 연달아 `~었다`로 끝납니다. (줄 25, 29, 35).
  reviewer는 대사 줄이 사이에 끊어 주어 리듬을 해치지 않는다고 보고 관찰로 남기지 않았다.
- 감사 결과
  - 1화(7건): PLAN-BEAT-PREEMPTED(중간, 4화에 둔 첫 질문을 91행에서 먼저 함), KO-HONORIFIC-REGISTER(경미, 141행 "버리시더군" 하오체 이탈), MEMO-SHOW-NOT-SUMMARY(경미),
    WORLD-RULE-WATER-CONTINUITY·MEMO-SCENES-AND-BOUNDS·HOOK-MOVEMENT·COUNT-AND-VOICE-CONSISTENT(관찰).
  - 2화(6건): SENTENCE-SELF-CONTRADICTION(경미, 85행 "치수만 재 주었다" 뒤 지시가 이어짐), CH1-CONTINUITY·HOOK-MOVEMENT·PULMU-COST-CARRYOVER·WATER-INFERENCE-CONTINUITY·VOICE-AND-REGISTER(관찰).
- 상태 검증: 1화 true → 재정산 → false, 2화 false. 1차와 달리 시작 회차 0을 모순으로 판정한 일은 없다.

### 브리지 요청 (16건 모두 delivered, failed 0, 버려짐 0)

| 요청 | 도구 | 답한 쪽 |
| --- | --- | --- |
| r-20261025-154009-6a89e729 | submit_foundation_outline | writer |
| r-20261025-154345-dbf6e5f3 | submit_foundation_details | writer |
| r-20261025-154538-fc786138 | submit_foundation_cast_index | writer |
| r-20261025-154558-b20a730f | submit_foundation_cast_documents | writer |
| r-20261025-154733-21376a40 | submit_chapter_memo (1화) | writer |
| r-20261025-154851-58d1be8f | submit_chapter_draft (1화) | writer |
| r-20261025-155054-01e7978a | submit_runtime_state_delta (1화) | writer |
| r-20261025-155206-2083a5a1 | submit_chapter_review (1화) | reviewer |
| r-20261025-155458-f93f31e3 | submit_state_validation (1화) | reviewer |
| r-20261025-155635-173714b5 | submit_runtime_state_delta (1화 재정산) | writer |
| r-20261025-155741-38cd778b | submit_state_validation (1화 재검증) | reviewer |
| r-20261025-155938-9aee8ef5 | submit_chapter_memo (2화) | writer |
| r-20261025-160051-19a27a8d | submit_chapter_draft (2화) | writer |
| r-20261025-160234-441013d9 | submit_runtime_state_delta (2화) | writer |
| r-20261025-160355-3a7f2164 | submit_chapter_review (2화) | reviewer |
| r-20261025-160623-7624a53c | submit_state_validation (2화) | reviewer |

CLI·로그(job 3개)의 중국어 줄: 0. 영어 출력 목록은 1차와 같다(`Stage: …`, `(2880 words)`).
분량: 엔진 기록 1화 2897·2화 2880 = 파일 재계산 2897·2880(장면 구분 `***` 포함). 둘 다 2,591~3,409 안.

## 2026-10-25 — 5-b단계

### 1·2. 보관 지침과 파일 건네기

- 지침 갱신(`599dd1a`): `pack --resume`, 보관 경로 순서(파일 건네기 → Drive 조각(작을 때만, 10화 이상이면 쓰지 않음) → OAuth `push`(선택)), 조각 복원 절차.
  `novel-drive.py split`(조각 + `<압축본>.parts.json`: 이름·크기·sha256)과 `join`(조각마다·전체 크기와 sha256 대조, 다르면 멈춤). Drive 시험 31/31.
- 파일 건네기 시험: 이 세션의 파일 보내기 도구로 `철쭉골-대장간-막내_20261025-1608_2화.tar.gz`(48,501바이트, sha256 `4cff0f1d…5450`)를 첨부로 보냄 →
  도구 결과 `1 file delivered to user`. 사용자 확인: 휴대폰에서 받아짐("잘받아짐").
- 다음 세션에서 받기: 사용자가 대화에 첨부한 파일은 `/root/.claude/uploads/<세션ID>/<접두어>-<파일명>`에 놓인다(이 세션의 kickoff zip이 `/root/.claude/uploads/8d4cf92a-…/3b153c82-inkos-ko-kickoff.zip`으로 들어온 것으로 확인).
  sha256을 맞춘 뒤 `unpack`. 압축본은 공개 포크에 커밋하지 않았다.

### 3. revise 시험 (`novel-5a2`, 철쭉골 대장간 막내)

엔진 동작(코드 `pipeline/runner.ts` `reviseDraft`): `--brief`가 있으면 사용자 지시 수정으로 보고 수정 전 감사를 건너뛴다. 수정 → 정산 → 상태 검증 → 수정 후 감사.
가장 최근 회차가 아니면 원고 파일과 회차 색인만 저장하고 상태(현재 상태·복선·요약·스냅샷)는 다시 쓰지 않는다("Only the latest chapter owns current truth"). 뒤 회차에는 `upstream-revision` 관찰이 붙는다.
브리프의 줄 번호는 파일 줄(제목 2줄 포함)이라 엔진 번호보다 2 크다 — writer가 인용문으로 실제 줄을 찾았다. 다음부터는 브리프에 줄 번호 대신 인용문을 쓴다.

| 수정 | 모드·근거 | 적용 | 재감사 | 상태 재정산 / `lastAppliedChapter` | 스냅샷 | 원고 diff |
| --- | --- | --- | --- | --- | --- | --- |
| 1화 하오체 이탈 | spot-fix(지시) | 적용(바뀐 줄 1개) | 예(관찰 7 + `state-projection-review`) | 정산·검증은 돌았지만(`false`) 저장 안 됨 / 2 그대로 | 변화 없음 | 143행 `버리시더군` → `버리시더구려` |
| 1화 4화 박자 선취(중간) | spot-fix: 문제가 대사 한 줄에 한정되고, 1화는 최근 회차가 아니라 상태가 다시 정산되지 않으므로 사실을 바꾸는 rewrite·rework는 2화 상태와 어긋남 | 적용(1줄) | 예(관찰 8 + 1) | 저장 안 됨 / 2 그대로 | 변화 없음 | 93행 `왜 안 되는데요? 장림문 검도 고쳐 주시잖아요. 칼을 고치는 건 되고 치는 건 왜 안 되는데요?` → `왜 안 되는데요? 왜 사람 벨 쇠는 안 치시는데요?` |
| 2화 85행(파일 87행) | spot-fix(지시) | 적용(1줄, `만`→`를`: 단순 삭제는 "치수 재 주었다"로 어색해 조사로 바꿈) | 예(관찰 7 + 1) | 재정산 저장됨, 검증 `false` / 2 | `snapshots/2`의 4개 파일만 바뀜(`chapter_summaries.md`, `current_state.md`, `state/chapter_summaries.json`, `state/current_state.json`) | 87행 `치수만 재 주었다` → `치수를 재 주었다` |

- 다른 부분: 세 번 모두 원고의 다른 줄은 바이트 단위로 같다(diff 1줄). 1화 수정 때 2화 파일과 상태·스냅샷은 그대로, 2화 수정 때 1화 파일 그대로.
  2화 수정 후 상태 변화는 `단석 | 2화 행적` 행과 2화 요약의 사건 문구뿐. 복선(H01~H08, `hook` resolved, `hook-2` open)은 바뀌지 않았다.
- 부작용(고치지 않음, 등급 그대로): 1화 두 번째 수정 뒤 저장된 상태가 원고와 어긋난다. `current_state.md` 45행 `편재옥 | 원칙`과 H02 notes(`pending_hooks.md`, `state/hooks.json`),
  `snapshots/1`·`2`에 지운 대사 "칼을 고치는 건 되고 치는 건 왜 안 되느냐는 모루의 물음"이 남았다. 2화 재정산도 이 1화 사실은 고칠 수 없다(2화 본문에 근거가 없음).
  reviewer가 `state-fact-stale-wording`(보통)으로 남겼다. 그대로 두면 이후 기획이 "4화의 질문은 이미 나왔다"고 읽을 수 있다. 엔진이 의도한 동작(앞 회차 수정은 현재 상태를 되감지 않음)의 결과다.
- 남은 원고 문제(감사, 이번 수정 범위 밖, 등급 그대로): 1화 `그렇겠지요`(하오체 이탈, 경미), `벼려 보고`(단어 선택, 경미~보통), 39행 모호한 문장(경미), 2화 11행 `드리지요`(하오체 이탈, 경미).
- CLI 출력: `Chapter 1 revised` / `Words: 2898` / `Review observations: 8` — ko 작품인데 영어(4단계 목록에 추가).

### 4. 재개 후 이어 쓰기 (빈 폴더에 `--resume` 복원 → 3화)

```
$ python3 tools/novel-drive.py pack novel-5a2 철쭉골-대장간-막내_20261025-1657_2화.tar.gz --resume
packed novel-5a2 -> …/철쭉골-대장간-막내_20261025-1657_2화.tar.gz (49008 bytes)   sha256 8ba63c88cecacea6e186d4b0dcd10935c64b940d30b603c7fe6c20295f977d2d
$ ls -A novel-5a2-resumed        → .gitignore (git 무시용 한 줄만)
$ python3 tools/novel-drive.py unpack 철쭉골-대장간-막내_20261025-1657_2화.tar.gz novel-5a2-resumed
unpacked 49 files into /home/user/inkos-ko/novel-5a2-resumed
$ inkos status   → 회차: 2 / 30, 분량: 5760자, 검수 의견: 17건, 상태 마지막 반영: 2화
$ inkos-agent job start -- write next 철쭉골-대장간-막내 --count 1      (INKOS_AGENT_PROJECT=novel-5a2-resumed)
→ j-20261025-165815-d03833d2 exit=0  3화: 장날의 낫 / 분량: 2940자 / 검수 의견: 10건
```

복원 뒤 원래 `novel-5a2`는 쓰지 않았다(한 작품 한 곳). 3화 뒤: `lastAppliedChapter: 3`, 회차 요약 1·2·3화, 스냅샷 `1 2 3`(복원본에는 최근 2개만 들어왔고 3이 새로 생김),
H08 deferred → progressing(최근 진전 3), 나머지 복선 그대로. 분량 2,940(파일 재계산 같음, 범위 안).
3화 정산의 기준 상태는 2화(사실 46행), 3화 기획 요청에는 1·2화 상태 사실 46행과 1·2화 회차 요약이 들어갔다.

1·2화 상태에서 이어받은 사례(저장된 2화 뒤 상태 행 → 3화 본문):
- `| 모루 | 몸 | 풀무숨을 오래 써서 손가락이 떨리고 손바닥 가운데가 화끈거림. 여울이 감아 준 헝겊을 감고 있음. 모루는 오늘 하루 망치를 잡지 못할 …`
  → 3행 "사흘 만에 헝겊을 풀었다." / 5행 "손가락은 더 까딱거리지 않았다. 다만 손바닥 가운데를 엄지로 누르면 아직 시큰했다." / 129행 "물집 잡힌 손바닥에 그것을 펴 바르고 헝겊을 감았다. 사흘 전과 같은 손이었다."
- `| 편가 낙관 | 모양 | 둥근 테 안에 '편' 자 하나. 호미 목에 찍힘 | 1 | 1 |` → 43행 "슴베 쪽 목을 뒤집었다. 둥근 테 안에 '편' 자 하나. 사부님의 낙관이었다. 진짜였다."

3화 감사: 막는 문제 없음. `state-fact-stale-wording`(보통, 1화 수정 뒤 남은 상태 문구) 그대로, 경미 5건(낫 판매 수 공백, 앞선 질문, 싸움 횟수, 중복 박자, 1화 문구 반복).
"한국어 문장 점검" 블록에 `cross-chapter-repetition` 3건 → reviewer가 2건(69·141행)은 경미로 남기고, 41행 낙관 묘사는 진품 확인 장면이라 의도된 반복으로 보고 뺐다.
reviewer 보고: 감사 요청에 `inkos-story-review` 스킬 블록이 없었다. 저장한 감사 프롬프트를 다시 세어 보면 5-a 1차·재실행 1·2화와 5-b 판타지 1화 감사에도 모두 `inkos-long-writing` 하나뿐이다(회차 파이프라인의 원본 동작). 한국어 검수 기준(`review-matrix.md`)은 회차 감사에 들어가지 않고, 한국어 문장 기준은 long-writing의 `korean-prose.md`로 들어간다. 상태 검증 `false`. CLI·로그 중국어 줄 0.

### 5. 다른 장르 (각 `book create` + 1화)

| 장르 | 작품 | 설계 프롬프트 장르 문서 | 1화 | 분량(엔진 = 파일 재계산) | 1화 상태 | 복선 |
| --- | --- | --- | --- | --- | --- | --- |
| fantasy | 잿빛 탑의 견습 필사공(`novel-fantasy/`) | `references/genres/fantasy.md` 하나(설계 요청 4건 모두) | 빈 칸 | 2,932 | `lastAppliedChapter 1`, 요약 1행, 현재 상태 21행, 스냅샷 0·1 | H01 deferred→open(최근 진전 1), 새 후보 `hook` open, H02~H06 그대로 |
| modern-fantasy | 환승역 균열 신고 접수처(`novel-mfantasy/`) | `references/genres/modern-fantasy.md` 하나 | 유출물 1 | 2,976 | `lastAppliedChapter 1`, 요약 1행, 현재 상태 21행, 스냅샷 0·1 | H01 deferred→open(최근 진전 1), 새 후보 `hook` open, H02~H06 그대로 |

```
fantasy:        j-20261025-171126-bc205396 book create exit=0 / j-20261025-171812-1790ac76 write next exit=0  "1화: 빈 칸 / 분량: 2932자"
modern-fantasy: j-20261025-172402-842ccd53 book create exit=0 / j-20261025-172921-6f38a93c write next exit=0  "1화: 유출물 1 / 분량: 2976자"
```

- 인물 폴더: 둘 다 `roles/major`·`roles/minor`. 판타지 주요 5·보조 2(도하·가비·솔매·길명로·비연 / 차운·은로), 현대판타지 주요 5·보조 2(공나연·허봉수·민태건·양선희·채도윤 / 문옥례·공재연). 이름은 앞 작품들과 겹치지 않는다.
- 감사 요청의 장르 문서: 판타지 1화 감사에 `fantasy.md`(검수 질문 6개), 현대판타지 1화 감사에 `modern-fantasy.md`. 각각 다른 장르 문서는 0건.
- 1화 상태 검증: 두 작품 모두 첫 검증 `true`(본문과의 실제 충돌 — 판타지 "두 손이 굳어"(본문은 "그 손"), 현대판타지 "두 사람이 신고"(본문은 한 사람)) → 재정산 → 재검증 `false` → 저장.
- 감사 요약: 판타지 — canon-copy-role-drift(주의, 본문은 도하가 부본을 베꼈다고 하고 이야기 틀·memo는 정본), 주어 모호 1곳(경미), 관찰 4.
  현대판타지 — memo-resistance-not-staged(주의, 안전선 규칙이 장면에서 압력이 되지 않음), 경미 2, 관찰 3.
  "한국어 문장 점검" 블록: 판타지 `ending-repetition` 5건, 현대판타지 3건 → reviewer가 모두 의도된 리듬·대구로 보고 관찰에서 뺐고 이유를 요약에 적음.
- 브리지 요청(5-b 전체, 16:38~): 42건 모두 delivered, 실패 0, 버려짐 0. CLI·로그(5-b job 7개)의 중국어 줄 0.

### 6. 4단계 대상 — ko 작품에 남은 영어 출력 (목록만, 고치지 않음)

| 출력 | 나오는 곳 |
| --- | --- |
| `INFO [inkos] Stage: generating foundation / saving book config / writing foundation files / initializing control documents / creating initial snapshot` | `book create` 진행 로그 |
| `INFO [inkos] Stage: preparing chapter inputs / writing chapter draft / collecting chapter review observations / validating truth file updates / rebuilding final truth files / persisting final chapter` | `write next` 진행 로그 |
| `INFO [writer] Phase 1: creative writing for chapter N`, `Phase 2: state settlement for chapter N (N words)`, `Phase 2: projecting chapter N facts into runtime state` | `write next`·`revise`(ko에 `words` 단위) |
| `INFO [inkos] streaming Ns, N chars (N CJK)` | 모델 응답 대기 |
| `WARN [inkos] State validation: N observation(s) for chapter N`, `State projection needs reconciliation; recalculating settlement for chapter N`, `State validation retry still reports N observation(s) for chapter N` | 상태 검증 |
| `Revising "<id>" chapter N [mode: spot-fix]...`, `Stage: loading revision context / revising chapter N / persisting revision / updating chapter index and snapshots`, `Chapter N revised`, `Words: N`, `Review observations: N` | `revise` 출력(결과 줄까지 영어) |

코드에만 있는 것(출력 미확인): 알림 제목 `${book.title} 第${chapterNumber}章`(`pipeline/runner.ts`, 알림 채널 설정 시), `chapter-review.ts`의 검토 불가 요약(SURVEY 부록 B).

## 2026-10-25 — 4단계 (화면 한국어 + 5-b 보완)

### 1. ko 회차 감사에 한국어 review 스킬

원인: 대화형 경로(`agent-session.ts`)는 auditor·reviser에 프로필의 권장 스킬(`recommendedSkillIds` = `inkos-story-review`)을 붙이지만,
CLI `write next`의 회차 파이프라인은 작업자 스킬을 넘기지 않아 `prepareWorkerMessages`가 필수 스킬(`inkos-long-writing`)만 붙였다.
CLI `revise`는 원래부터 모든 언어에서 권장 스킬을 붙인다(`resolveCliProfileSkills(..., { includeRecommended: true })`) — en 복사본의 수정 뒤 감사에도 239행에 있었다.
수정: `skills/korean-review-skills.ts` — ko 작품의 `continuity-auditor`·`reviser`에만 권장 스킬을 더한다(`agents/base.ts` 3줄). zh/en, 다른 작업자(writer·state-validator)는 그대로.
시험: `korean-skills.test.ts` "adds the Korean review skill to ko chapter audits and revisions only"(ko/en/zh × 작업자 4종). 수정을 빼면 `ko continuity-auditor: expected false to be true`로 실패.

브리지 확인(`novel-5a2-resumed`, `write next` 4화, job `j-20261025-180100-7526f584`): 감사 요청 `r-20261025-180939-74c05bf4` 프롬프트
```
161:### inkos-long-writing — inkos-long-writing
383:## 상태 검증의 판정 기준
461:### inkos-story-review — inkos-story-review
463:# 한국어 원고 검수
466:- 해결되지 않은 문제의 등급을 낮추지 않는다. 이번 수정 범위 밖이라는 이유로 실제 문제를 `info`로 내리지 말고, …
481:#### Reference: references/review-matrix.md:0-1773
483:# 검수 기준표
532:## 상태 검증
```
같은 job의 상태 검증 요청은 `inkos-long-writing`(판정 기준 294행)만 — 검증 작업자에는 붙이지 않는다(의도).
4화 "줄인 칼" 3,004자, 감사 의견 7건(보통 1: 1화 수정 뒤 남은 상태 문구, 경미 4, 관찰 2), 상태 검증 1차 `true`(본문에 없는 "아침"·화자 추론) → 재정산 → `false` → 저장.
`lastAppliedChapter 4`, 스냅샷 1~4. 4화 정산에서 `편재옥 | 원칙` 행과 H02 notes가 1화 현재 본문에 맞게 다시 쓰였다(5-b의 낡은 상태 문구가 다음 회차에서 바로잡힘).

### 2. 앞 회차 수정 경고와 지침

- ko CLI `revise`: 바뀐 회차가 최신 회차보다 앞이면 경고 3줄(`korean-cli-text.ts` `formatKoreanEarlierRevisionNotice`). `--json` 출력은 그대로.
- 지침: `RUNTIME.md` "원고 수정(`revise`) 지침", 브리지 `AGENTS.md` "Revision in Korean projects" — 앞 회차는 사실을 바꾸지 않는 spot-fix만,
  사실이 바뀌면 다음 회차 `write next --context`로 넘기고 작가에게 알림, 상태 되감기·손 편집 금지, `--brief`에는 줄 번호 대신 인용문.

브리지 확인(작품 복사본 `scratchpad/rev-ko` — 시험 작품의 남은 원고 문제는 그대로 두기로 했으므로 원본은 건드리지 않음, job `j-20261025-181747-98ce7860`):
```
$ inkos revise 철쭉골-대장간-막내 2 --mode spot-fix --brief "하오체 이탈 한 곳만 고친다: \"반은 먼저 드리지요.\"의 '드리지요'를 …"
"철쭉골-대장간-막내" 2화 수정 중 [모드: spot-fix]...
INFO  [inkos] 단계: 2화 수정 맥락 불러오기
INFO  [inkos] 단계: 2화 수정
INFO  [writer] 2단계: 2화 사실을 상태에 반영
INFO  [writer] 2단계: 2화 사실을 상태에 반영
INFO  [inkos] 단계: 2화 수정 결과 저장
INFO  [inkos] 단계: 2화 색인과 스냅샷 갱신
  2화 수정 완료
  분량: 2880자
  검수 의견: 3건
  경고: 2화는 최신 회차(4화)가 아니어서 원고와 회차 색인만 저장했습니다.
        상태 파일(현재 상태·복선·회차 요약·스냅샷)에는 수정 전 사실이 남을 수 있습니다.
        사실이 바뀌는 수정이었다면 다음 회차를 쓸 때 `write next --context`로 바로잡을 내용을 넘기세요.
```
원고 diff는 파일 13행(엔진 11행) 한 줄 `드리지요` → `드리겠소`. `story/` 전체가 원본과 같고 `lastAppliedChapter 4` 그대로(경고 내용과 일치).
수정 요청(384행)·수정 뒤 감사(459행)·상태 검증 프롬프트 모두 `inkos-story-review` 포함(CLI `revise`의 원래 동작).

### 3. CLI 문구 한국어화 (ko 작품에서만)

- 파이프라인 진행·경고 로그: `utils/korean-log-messages.ts` — 호출부의 zh 문구를 열쇠로 ko 문구를 찾는다(호출부 30곳은 그대로, `runner.ts` `logStage`·`logInfo`·`logWarn`과 `writer.ts` `localize`만 수정).
  시험 `korean-log-messages.test.ts`가 네 파일의 모든 `logStage`/`logInfo`/`logWarn` 호출을 읽어 빠진 문구가 없는지 확인한다.
- `(N words)` → `N자`, `Stage:` → `단계:`, writer `Phase 1/2` → `1단계/2단계`, 상태 검증 경고 3종.
- `revise` 출력 전체(`Revising…`, `Chapter N revised`, `Words:`, `Review observations:`, `Revise failed:`) → `korean-cli-text.ts`.
- 응답 대기 `streaming Ns, N chars (N CJK)` → `응답 받는 중 N초, N자`(한글은 CJK 수에 들어가지 않아 그 숫자는 뺐다). 프로젝트 `inkos.json`의 language로 고른다.
- 알림 제목 `${title} 第N章` → ko는 `${title} N화`(`runner.ts`, 알림 채널이 있을 때만; 알림 채널이 없어 실제 출력은 확인하지 못함).
- `write next`의 의견 목록 머리말: ko `검수 의견:`이 바로 위 `검수 의견: N건`과 겹쳐 `의견 목록:`으로 바꿈.

전후(ko, 같은 작품):
```
변경 전(5-b, 3화·revise)                           변경 후(4단계, 4화·revise)
INFO  [inkos] Stage: preparing chapter inputs       INFO  [inkos] 단계: 회차 입력 준비
INFO  [inkos] streaming 30s, 0 chars (0 CJK)       INFO  [inkos] 응답 받는 중 30초, 0자
INFO  [writer] Phase 1: creative writing for chapter 3   INFO  [writer] 1단계: 4화 본문 쓰기
INFO  [writer] Phase 2: state settlement for chapter 3 (2940 words)   INFO  [writer] 2단계: 4화 상태 정산 (3004자)
INFO  [writer] Phase 2: projecting chapter 3 facts into runtime state INFO  [writer] 2단계: 4화 사실을 상태에 반영
INFO  [inkos] Stage: collecting chapter review observations   INFO  [inkos] 단계: 회차 검수 의견 모으기
INFO  [inkos] Stage: persisting final chapter      INFO  [inkos] 단계: 최종 회차 저장
INFO  [inkos] Stage: rebuilding final truth files  INFO  [inkos] 단계: 최종 상태 파일 다시 만들기
INFO  [inkos] Stage: validating truth file updates INFO  [inkos] 단계: 상태 파일 변경 검증
WARN  [inkos] State validation: 1 observation(s) for chapter 3   WARN  [inkos] 상태 검증: 4화 의견 1건
(5-a) State projection needs reconciliation; …     WARN  [inkos] 상태 반영을 다시 맞춰야 해서 4화 정산만 다시 계산합니다
(5-a) State validation retry still reports …       WARN  [inkos] 상태 검증을 다시 해도 4화 의견 1건이 남았습니다
Revising "철쭉골-대장간-막내" chapter 1 [mode: spot-fix]...   "철쭉골-대장간-막내" 2화 수정 중 [모드: spot-fix]...
INFO  [inkos] Stage: loading revision context for chapter 1   INFO  [inkos] 단계: 2화 수정 맥락 불러오기
  Chapter 1 revised / Words: 2898 / Review observations: 8   2화 수정 완료 / 분량: 2880자 / 검수 의견: 3건
```
4화 job 로그 전체에서 영어 진행 문구 0줄, 한자 줄 0.

en(변경 후, 작품 복사본의 `inkos.json`·`work.json`·`book.json` language를 en으로 바꾼 `scratchpad/rev-en`, job `j-20261025-182618-474d9fdc`):
```
Revising "잿빛-탑의-견습-필사공" chapter 1 [mode: spot-fix]...
INFO  [inkos] Stage: loading revision context for chapter 1
INFO  [inkos] Stage: revising chapter 1
INFO  [writer] Phase 2: projecting chapter 1 facts into runtime state
INFO  [inkos] streaming 30s, 0 chars (0 CJK)
INFO  [inkos] Stage: persisting revision for chapter 1
INFO  [inkos] Stage: updating chapter index and snapshots for chapter 1
  Chapter 1 revised
  Words: 0
  Review observations: 7
```
변경 전 영어 문구(5-b의 ko 작품이 냈던 줄)와 같다. `Words: 0`은 en 단어 수로 한국어 본문을 세서 생긴 시험용 복사본의 값이다. zh 출력은 단위 시험으로만 확인(`korean-log-messages.test.ts` "leaves zh and en output unchanged", 원본 시험 전체 통과).

### 4. 압축본 크기 조사

`RUNTIME.md` "회차마다 커지는 양": 2화 49,008 → 3화 84,636 → 4화 118,446바이트. 증가의 큰 몫은 감사 관찰의 긴 인용문(`chapters/index.json`)과 최신 스냅샷 교체이고,
gzip 32KB 창 때문에 중복이 줄지 않는다(xz면 3화 43,200). 줄이는 방법 4가지를 측정만 하고 적용하지 않았다.

### 5. 브리지 요청

4화 7건(기획·초고·정산 2·감사·검증 2) + ko revise 7건(범위·교체·정산 2·검증 2·감사) + en revise 5건(범위·교체·정산·검증·감사) = 19건, 모두 delivered.
writer와 reviewer는 서로 다른 서브에이전트(수정 범위·교체 4건은 조정 세션이 직접 답함). 임시 복사본 `rev-ko`·`rev-en`은 시험 뒤 지웠다.
4화 뒤 `--resume` 압축본: `철쭉골-대장간-막내_20261025-1817_4화.tar.gz` 118,446바이트, sha256 `1f946149d0680c7839b27f153f514edb03382632ff378bfe7e18dd6d95650cfd`(사용자에게 파일로 건넴).

## 2026-10-25 — 6단계

VERIFICATION이 커져서(47KB) 6단계부터 단계별 파일로 나눈다: [`verification/stage-6.md`](verification/stage-6.md).
