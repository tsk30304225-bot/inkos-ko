# 7단계 검증 — 보관 마무리와 장편 외 감사 확인

2026-10-25, 브랜치 `claude/eeum-n0rsol`. 시험 작품 `test-7-script`·`test-7-explainer`(프로젝트 `test-7/`, git 무시)는 밖으로 내보내지 않았다.

## 1. xz 전환 (`tools/novel-drive.py`)

- `pack`: 기본 `.tar.xz`. 이름이 `.tar.gz`/`.tgz`이거나 `--gz`면 gzip. Python에 `lzma`가 없으면 경고를 내고 gzip(`.tar.gz`)으로 만든다. 이름의 확장자는 실제 형식에 맞춘다.
- `unpack`: 형식을 내용으로 알아본다(`r:*`). `lzma`가 없는데 xz 압축본이면 "`tar -xJf`를 쓰라"는 메시지와 함께 멈춘다.
- OAuth `push`는 바꾸지 않았다(계속 gzip, "선택, 앱이 쓰지 않음").
- 시험 `tools/tests/test_novel_drive.py` 31 → 38: 기본 xz(매직 바이트 `FD 37 7A 58 5A 00`), xz 복원, `.tar.gz` 이름은 gzip, `--gz`, `lzma` 없는 실행(가져오기를 막은 Python)에서 경고와 gzip·gz 복원·xz 복원 실패 메시지.

실제 압축본으로 확인(6단계에 만든 gz 압축본과 새 xz 압축본):
```
$ unpack (6단계에 만든 gz 압축본)
unpacked 46 files into r-gz
$ pack test-6 --resume (기본 xz)
packed /home/user/inkos-ko/test-6 -> test-6-murim_xz_3화.tar.xz (38628 bytes)
$ unpack (xz)
unpacked 46 files into r-xz
gz 복원 == xz 복원 (diff 없음)
```
같은 3화 작품: gzip 85,280바이트 → xz 38,628바이트.

## 2. 회차별 원고 업로드 지침과 Drive 파일 이름

RUNTIME "원고 보관 지침", 브리지 AGENTS.md, CLAUDE.md에 같은 문장:

> 실제 작품: 대화형은 질문을 기다리기 전에 재개용 압축본 전체를, 일괄은 회차마다 원고 `.md`를 Drive 'Inkos ko'에 올리고, 일괄이 끝나거나 멈출 때(경고·실패) 압축본을 올린다. 시험 작품(`test-`)은 올리지 않는다.

파일 이름(올린 시각, UTC):
- 압축본 `<작품ID>_<YYYYMMDD-HHMM>_<마지막 회차>화.tar.xz`(gz면 `.tar.gz`), 조각 `<압축본 이름>.part<N>of<M>`, 목록 `<압축본 이름>.parts.json`.
- 원고 `<작품ID>_<회차 네 자리>화_<YYYYMMDD-HHMM>.md`(내용은 `chapters/<회차 네 자리>_<제목>.md` 그대로, 다시 올리면 새 파일).
- 받기: 가장 늦은 압축본을 복원하고, 그 뒤 회차의 원고만 있으면 상태가 없다는 것을 사용자에게 알리고 묻는다.
일괄 예시 문구는 "N개 화 써줘", "다섯 화 써줘"로 바꿨다. RUNTIME의 환경별 절에서 OAuth `push` 기준으로 남아 있던 문장 4곳과 "저장소 루트 AGENTS.md"(파일 없음)를 고쳤다.

## 3. 대본·설명 영상 감사에 붙는 스킬 (4단계 남은 위험 3)

경로: 두 작품 모두 `create`에는 감사 단계가 없다. 검수는 대화형(`interact --work …`)의 `workspace__review_work_artifact` → `artifact-method` 작업자(`harness/tools/artifact-methods.ts`)이고, 프로필의 필수+권장 스킬을 붙인다.
대본 프로필(`script`)은 권장 스킬이 없고, 설명 영상 프로필은 자체 스킬만 있다.

수정 전(검수 요청 프롬프트의 스킬 목록, 이 요청은 확인용이라 `fail`로 닫음):
```
# r-20261025-222505-024e8b34 (대본 검수)
165:### inkos-script-writing — inkos-script-writing
167:# 한국어 드라마 대본 집필
184:#### Reference: references/korean-drama-format.md:0-1434
253:#### Reference: references/episode-scene-craft.md:0-683
# r-20261025-222658-48010aa5 (설명 영상 검수)
165:### inkos-ko-explainer-script — inkos-ko-explainer-script
167:# 한국어 설명형 영상 대본
209:#### Reference: references/scene-table.md:0-839
247:#### Reference: references/review-questions.md:0-688
249:# 설명 영상 검수 질문
```
대본 검수에는 한국어 검수 기준(검수 기준표, "등급을 낮추지 않는다")이 없었다. 설명 영상 검수에는 한국어 검수 질문 10개가 있었지만 등급·인용 규칙이 없었다.

수정:
- `skills/korean-review-skills.ts`: ko 작품의 검수·수정 작업자에 `artifact-method`를 더하고, 자체 검수 기준이 없는 `script` 프로필에는 한국어 review 스킬(`inkos-story-review`)을 붙인다.
  스킬은 원본 `resolveProfileSkillActivations`와 같은 방식(같은 id면 뒤의 한국어판)으로 고른다 — 처음에 `find`로 원본(영어판)을 골라 시험이 실패했고, 고쳤다. `agents/base.ts`는 1줄만 바뀜.
- 설명 영상은 장편 기준표를 붙이지 않고(형식이 다름), 한국어 설명 영상 스킬의 "검수" 절에 "등급을 낮추지 않는다"와 "인용은 해당 문장만(줄 범위)" 두 줄을 더했다.
- zh/en, 다른 작업자(writer 등)는 그대로. 시험 `korean-skills.test.ts` "gives Korean review criteria to ko script and explainer artifact reviews"(ko/en/zh × 작업자).

수정 후(브리지로 다시 검수):
```
# r-20261025-223144-3b605110 (대본 검수, 수정 후)
165:### inkos-script-writing — inkos-script-writing
167:# 한국어 드라마 대본 집필
184:#### Reference: references/korean-drama-format.md:0-1434
253:#### Reference: references/episode-scene-craft.md:0-683
281:### inkos-story-review — inkos-story-review
283:# 한국어 원고 검수
289:- 인용은 해당 문장만: …
291:- 해결되지 않은 문제의 등급을 낮추지 않는다. …
302:#### Reference: references/review-matrix.md:0-1773
304:# 검수 기준표
# r-20261025-223202-f2d19711 (설명 영상 검수, 수정 후)
165:### inkos-ko-explainer-script — inkos-ko-explainer-script
167:# 한국어 설명형 영상 대본
208:해결되지 않은 문제의 등급을 낮추지 않는다. …
209:인용은 해당 문장만: …
211:#### Reference: references/scene-table.md:0-839
249:#### Reference: references/review-questions.md:0-688
251:# 설명 영상 검수 질문
```

검수 결과(reviewer 서브에이전트, 작성은 조정 세션):
- 대본 「나루터 첫 짐표」(1화, 1분): 높음 1(손님은 12번 상자를 요청했는데 고친 뒤 21번을 실음 — 고친 장부가 화면에 없음), 보통 1(짐표를 뗀 순간이 없음), 낮음 1(하게체·해라체 섞임), 관찰 2(1분에 씬 4개는 길 수 있음).
- 설명 영상 「짐표는 왜 두 번 읽을까」(쇼츠 52초): 높음 3(출처 칸 `없음`인 사실 주장), 보통 3(`확인 필요` 장면과 검증 안 된 전제), 낮음 1, 관찰 2.
  설명 영상 스킬의 1번 질문(출처 없는 사실 주장)이 그대로 쓰였다. 시험 작품이라 고치지 않았다.

## 4. 남은 영어 출력(목록만)

- `script create` 진행 문구: `Writing script creation spec...`, `Writing script draft...`, `Script "<id>" completed.`(원본 `pipeline/script-storyboard-runner.ts`, `agent/agent-tools.ts`, 모든 언어에서 영어). 설명 영상(`explainer create`)은 한국어.

## 5. 브리지 요청

14건: delivered 12, failed 2(수정 전 프롬프트 확인용 검수 요청을 일부러 `fail`). 작성 2건(대본·설명 영상)은 조정 세션이 writer로, 검수 2건은 reviewer 서브에이전트가 답했다.
대화형 조정 요청 8건은 조정 세션이 답했다(검수 도구 호출, 끝내기). `r-20261025-223144-3b605110`은 조정 세션이 실수로 claim했고 reviewer가 `--force`로 답했다.
대화형 job: 확인용 2개 exit 1(검수 실패로 `blocked` 종료, 의도), 수정 후 2개 exit 0.

## 6. 환경 시험 절차서

`korean-port/ENV_TEST.md`: 설치(`setup-cloud.sh --project test-env`), doctor, `lzma` 확인, 시험 작품 `test-env-<환경>` 1화와 대화형 질문, 압축·복원·조각, 시험 실행, 보고 양식.

## 7. 시험

`pnpm -r --no-bail test`(프록시 변수 제거): core 757 · studio 307 · cli 101 = 1,165 통과, 실패 0(6단계 1,164 + 1).
브리지 33/33, Drive 38/38, novel-brief 27/27.
