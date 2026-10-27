/**
 * Korean (ko) text for the pipeline's progress and warning logs.
 *
 * Upstream log calls carry only `{ zh, en }`, so a ko work printed the English
 * line. The zh text of each call is fixed, so it is the lookup key here: the
 * call sites stay unchanged and zh/en output is untouched. A message that is
 * not listed keeps the English fallback.
 */
type KoreanRule = readonly [RegExp, (match: RegExpMatchArray) => string];

const RULES: ReadonlyArray<KoreanRule> = [
  // book create / import
  [/^生成基础设定$/, () => "기초 설정 생성"],
  [/^保存书籍配置$/, () => "작품 설정 저장"],
  [/^写入基础设定文件$/, () => "기초 설정 파일 쓰기"],
  [/^初始化控制文档$/, () => "제어 문서 준비"],
  [/^创建初始快照$/, () => "초기 스냅샷 만들기"],
  [/^导入同人正典$/, () => "동인 원작 설정 가져오기"],
  [/^生成同人基础设定$/, () => "동인 기초 설정 생성"],
  [/^导入正传正典参照$/, () => "본편 설정 가져오기"],
  [/^生成番外基础设定$/, () => "외전 기초 설정 생성"],
  [/^提取参考作品风格指纹$/, () => "참고 작품 문체 특징 추출"],
  // audit / revise
  [/^审计第(\d+)章$/, (m) => `${m[1]}화 감사`],
  [/^加载第(\d+)章修订上下文$/, (m) => `${m[1]}화 수정 맥락 불러오기`],
  [/^修订第(\d+)章$/, (m) => `${m[1]}화 수정`],
  [/^落盘第(\d+)章修订结果$/, (m) => `${m[1]}화 수정 결과 저장`],
  [/^更新第(\d+)章索引与快照$/, (m) => `${m[1]}화 색인과 스냅샷 갱신`],
  // write next
  [/^准备章节输入$/, () => "회차 입력 준비"],
  [/^撰写章节草稿$/, () => "회차 초고 쓰기"],
  [/^生成章节审查观察$/, () => "회차 검수 의견 모으기"],
  [/^落盘最终章节$/, () => "최종 회차 저장"],
  [/^生成最终真相文件$/, () => "최종 상태 파일 다시 만들기"],
  [/^校验真相文件变更$/, () => "상태 파일 변경 검증"],
  [/^根据已编辑正文同步真相文件与索引$/, () => "편집한 본문으로 상태 파일과 색인 맞추기"],
  // writer phases
  [/^阶段 1：创作正文（第(\d+)章）$/, (m) => `1단계: ${m[1]}화 본문 쓰기`],
  [/^阶段 2：状态结算（第(\d+)章，(\d+)字）$/, (m) => `2단계: ${m[1]}화 상태 정산 (${m[2]}자)`],
  [/^阶段 2：把第(\d+)章事实投影到运行时状态$/, (m) => `2단계: ${m[1]}화 사실을 상태에 반영`],
  // state validation
  [/^状态校验：第(\d+)章发现 (\d+) 条观察$/, (m) => `상태 검증: ${m[1]}화 의견 ${m[2]}건`],
  [/^状态投影需要对账，正在仅重算第(\d+)章结算层$/, (m) => `상태 반영을 다시 맞춰야 해서 ${m[1]}화 정산만 다시 계산합니다`],
  [/^状态校验重试后，第(\d+)章仍有 (\d+) 条观察$/, (m) => `상태 검증을 다시 해도 ${m[1]}화 의견 ${m[2]}건이 남았습니다`],
];

export const KOREAN_STAGE_PREFIX = "단계: ";

export function koreanLogMessage(message: { readonly zh: string }): string | undefined {
  for (const [pattern, render] of RULES) {
    const match = message.zh.match(pattern);
    if (match) return render(match);
  }
  return undefined;
}

/** The same message with its ko text filled in when the table knows it. */
export function withKoreanLogMessage<T extends { readonly zh: string; readonly en: string; readonly ko?: string }>(
  message: T,
): T & { readonly ko?: string } {
  if (message.ko !== undefined) return message;
  const ko = koreanLogMessage(message);
  return ko === undefined ? message : { ...message, ko };
}
