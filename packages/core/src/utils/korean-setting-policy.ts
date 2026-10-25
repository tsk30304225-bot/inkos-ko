/** Craft guidance only: native schemas, output protocols and approval gates remain authoritative. */
export const KOREAN_SETTING_POLICY = `## 소설 설정의 항목별 작성 계약
설정의 작성·수정·검수에만 다음 계약을 적용한다. 소설 본문이나 매 회차 출력에 설정 설명서를 반복하지 않는다.
파일의 존재나 제목만으로 설정 완료로 판단하지 않는다. 각 의미 있는 설정 항목에는 다음 네 요소가 읽혀야 한다: 목적(어떤 서사적 선택에 쓰이는가), 맥락(누구의 관점에서 언제·어떤 원인/조건으로 성립하는가), 기준(장면이나 상태에서 무엇을 확인하면 준수/위반인가), 경계(적용 범위·예외 조건·허용하지 않는 확대해석). '적절히/일관되게/재미있게'만으로 기준을 대신하지 않는다.
기존 기술용 키·필드 타입·enum·태그·파서용 제목·SECTION 수는 그대로 둔다. 정수나 enum에 설명문을 넣거나 스키마에 purpose/context/criteria/boundary 키를 임의로 추가하지 않는다. 기존 산문 항목에 네 요소를 짧게 녹이고, 구조 데이터는 동일 항목의 읽기용 설명 또는 허용된 notes에 연결한다. prose-only 구간을 새 표로 바꾸거나 파일별 분량 예산을 늘려 채우지 않는다. 사소한 값마다 네 줄을 복제하기보다 동일 적용 범위를 공유하는 묶음을 한 번 정의하고 개별 차이만 명시한다.
저장 위치와 항목별 책임:
- author_intent: 독자에게 줄 경험·주제·핵심 약속·비중·금지·작가의 미정 선택. 작가 확정/제안/미정을 구별한다. 미정 취향을 에이전트가 확정 사실로 바꾸지 않는다.
- story_frame: 주제와 정서의 목적, 전면/배후 갈등의 인과 연결, 세계 법칙의 발동·대가·예외, 시점/정보 공개 범위, 확인 가능한 종착 상태. 시대·지역은 작가 지정 우선이며 한국어 집필이 한국 배경을 의미하지 않는다. 주인공의 전체 변화 곡선은 roles에만 두고 참조한다.
- volume_map: 권/막별 목표와 관찰 가능한 결과, 감정 곡선, 권말 되돌릴 수 없는 변화, 복선 약속과 회수 범위, 완급 조절 기준. 1.8의 권 단위 계약에서는 특정 회차 사건을 고정하지 않는다. 2.0에서 요청된 회차 방향은 해당 프로토콜과 작가 요청의 범위 안에서만 적는다. 계획을 이미 일어난 사건으로 쓰지 않는다.
- roles: 이름/역할/소속, 성격과 반전 디테일의 행동 근거, 과거의 현재 영향, 욕망/두려움/선택 기준, 시작→변화→대가, 현재 위치·몸 상태·보유 정보, 관계의 호칭/의무/갈등/변화 조건. 작가가 아는 비밀과 인물이 아는 사실을 분리한다. 성격 락을 성장 금지로 해석하지 않는다.
- book_rules: 주인공 personalityLock/behavioralConstraints, genreLock.primary/forbidden, narrativePerson, numericalSystemOverrides, eraConstraints, prohibitions, chapterTypesOverride, fatigueWordsOverride, additionalAuditDimensions, enableFullCastTracking, fanficMode/allowedDeviations 중 현재 버전이 실제 지원하는 필드만 사용한다. 각 금지는 이유·범위·예외 승인 조건을 명시하고 금지의 동의어를 바꿔 우회하지 않는다. narrativePerson은 작가의 명시 선택 없이는 확정하지 않는다. 원작 각색 범위와 새 정사를 구별한다.
- pending_hooks: ID는 추적 식별자, 시작/최근 전진 회차는 실제 증거, type은 단서 기능, status는 실제 단계, expectedPayoff는 관찰 가능한 회수 조건, payoffTiming은 계획 구간, dependsOn은 선행 조건, paysOffInArc는 예정 범위, coreHook는 중심 약속 여부, halfLife는 경고 기준, notes는 단서·출처·불확실성. 스키마가 제공하는 열/키만 쓴다. 계획한 단서를 이미 심거나 회수한 것으로 보고하지 않는다. 결말을 위해 불필요한 새 떡밥을 강제하지 않는다.
- current_state/자원 원장/기억/요약/관계/서브플롯/감정선: 실제 원고에서 확인된 시점·변화·원인·영향·증거와 다음 갱신 조건. 추측은 추측으로 표시한다. 능력·부상·부채·호칭 변화는 정산하며 편의로 초기화하지 않는다. 계획·검수 의견을 정사에 섞지 않는다.
- current_focus/chapter_memo: 이번 작업의 목표·입력 근거·성공 기준·금지/중단 조건·참조 항목. 현재 지시를 전 작품의 영구 규칙으로 승격하지 않는다.
- book.json: title/genre/platform/language/targetChapters/chapterWordCount 및 해당 버전의 min/maxChapterLength·writing 설정은 각각 독자 약속/분류/출력 조건/목표/분량/검토 동작을 제어한다. 목표 회차와 분량은 서사 성취의 증거가 아니다. ko 분량은 공백 제외 NFC 글자 수다. 엔진 관리 ID·시간·상태는 관측값이며 작가의 설정문으로 꾸미지 않는다.
검수할 때는 문제가 있는 파일과 항목, 빠진 요소, 충돌하는 원문 근거, 허용 범위 안의 수정안을 구체적으로 제시한다. 설명이 없으면 미기재로 보고하며 근거 없이 PASS나 수치 점수를 만들어 내지 않는다. 서로 충돌한 규칙은 조용히 덮어쓰지 말고 작가 명시 지시와 항목별 정본을 따라 충돌을 드러낸다.`;
