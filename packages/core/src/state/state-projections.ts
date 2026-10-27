import type {
  ChapterSummariesState,
  CurrentStateState,
  HooksState,
} from "../models/runtime-state.js";

export function renderHooksProjection(
  state: HooksState,
  language: "zh" | "en" | "ko" = "zh",
  options?: { readonly currentChapter?: number },
): string {
  void options;
  const title = language === "ko" ? "# 복선 목록" : language !== "zh" ? "# Pending Hooks" : "# 伏笔池";
  const headers = language === "ko"
    ? [
      "| hook_id | 시작 회차 | 유형 | 상태 | 최근 진전 회차 | 회수 예정 | 메모 |",
      "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    : language !== "zh"
    ? [
      "| hook_id | start_chapter | type | status | last_advanced_chapter | expected_payoff | notes |",
      "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    : [
      "| hook_id | 起始章节 | 类型 | 状态 | 最近推进 | 预期回收 | 备注 |",
      "| --- | --- | --- | --- | --- | --- | --- |",
    ];

  const rows = [...state.hooks]
    .sort((left, right) => (
      left.startChapter - right.startChapter
      || left.lastAdvancedChapter - right.lastAdvancedChapter
      || left.hookId.localeCompare(right.hookId)
    ))
    .map((hook) => `| ${
        [
          hook.hookId,
          hook.startChapter,
          hook.type,
          hook.status,
          hook.lastAdvancedChapter,
          hook.expectedPayoff,
          hook.notes,
        ].map(escapeTableCell).join(" | ")
      } |`);

  return [title, "", ...headers, ...rows, ""].join("\n");
}

export function renderChapterSummariesProjection(
  state: ChapterSummariesState,
  language: "zh" | "en" | "ko" = "zh",
): string {
  const title = language === "ko" ? "# 회차 요약" : language !== "zh" ? "# Chapter Summaries" : "# 章节摘要";
  const headers = language === "ko"
    ? [
      "| 회차 | 제목 | 등장인물 | 주요 사건 | 상태 변화 | 복선 변화 | 분위기 | 회차 유형 |",
      "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    : language !== "zh"
    ? [
      "| Chapter | Title | Characters | Key Events | State Changes | Hook Activity | Mood | Chapter Type |",
      "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    : [
      "| 章节 | 标题 | 出场人物 | 关键事件 | 状态变化 | 伏笔动态 | 情绪基调 | 章节类型 |",
      "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ];

  const rows = [...state.rows]
    .sort((left, right) => left.chapter - right.chapter)
    .map((summary) => `| ${
      [
        summary.chapter,
        summary.title,
        summary.characters,
        summary.events,
        summary.stateChanges,
        summary.hookActivity,
        summary.mood,
        summary.chapterType,
      ].map(escapeTableCell).join(" | ")
    } |`);

  return [title, "", ...headers, ...rows, ""].join("\n");
}

export function renderCurrentStateProjection(
  state: CurrentStateState,
  language: "zh" | "en" | "ko" = "zh",
): string {
  const title = language === "ko" ? "# 현재 상태" : language !== "zh" ? "# Current State" : "# 当前状态";
  const chapterLabel = language === "ko" ? "현재 회차" : language !== "zh" ? "Current chapter" : "当前章节";
  const headers = language === "ko"
    ? [
        "| 대상 | 관계·속성 | 현재 사실 | 적용 시작 회차 | 근거 회차 |",
        "| --- | --- | --- | --- | --- |",
      ]
    : language !== "zh"
    ? [
        "| Subject | Predicate | Object | Valid from | Source chapter |",
        "| --- | --- | --- | --- | --- |",
      ]
    : [
        "| 主体 | 关系 / 属性 | 当前事实 | 生效章节 | 来源章节 |",
        "| --- | --- | --- | --- | --- |",
      ];
  const facts = state.facts
    .filter((fact) => fact.validUntilChapter === null || fact.validUntilChapter >= state.chapter)
    .sort((left, right) => (
      left.subject.localeCompare(right.subject)
      || left.predicate.localeCompare(right.predicate)
      || left.object.localeCompare(right.object)
    ))
    .map((fact) => `| ${[
      fact.subject,
      fact.predicate,
      fact.object,
      fact.validFromChapter,
      fact.sourceChapter,
    ].map(escapeTableCell).join(" | ")} |`);

  return [
    title,
    "",
    `> ${chapterLabel}: ${state.chapter}`,
    "",
    ...headers,
    ...facts,
    "",
  ].join("\n");
}

function escapeTableCell(value: string | number): string {
  return String(value).replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>").trim();
}
