import { formatLengthCount } from "@actalk/inkos-core";

// Korean (ko) text for CLI lines that upstream prints in English for every
// language (revise output, streaming progress). zh/en keep the upstream text.

export function formatKoreanReviseStart(bookId: string, chapterNumber: number | undefined, mode: string): string {
  return `"${bookId}" ${chapterNumber ? `${chapterNumber}화` : "최신 회차"} 수정 중 [모드: ${mode}]...`;
}

export function formatKoreanReviseResultLines(result: {
  readonly chapterNumber: number;
  readonly changed: boolean;
  readonly wordCount: number;
  readonly observations: ReadonlyArray<unknown>;
}): string[] {
  return [
    result.changed ? `  ${result.chapterNumber}화 수정 완료` : `  ${result.chapterNumber}화: 적용할 변경 없음`,
    `  분량: ${formatLengthCount(result.wordCount, "ko_chars")}`,
    `  검수 의견: ${result.observations.length}건`,
  ];
}

/**
 * Revising a chapter that is not the latest saves only its file and index:
 * the runtime state belongs to the latest chapter and is not rewound
 * (pipeline/runner.ts reviseDraft). Facts removed from the earlier chapter can
 * therefore remain in the state files.
 */
export function formatKoreanEarlierRevisionNotice(chapterNumber: number, latestChapter: number, changed: boolean): string[] {
  if (!changed || chapterNumber >= latestChapter) return [];
  return [
    `  경고: ${chapterNumber}화는 최신 회차(${latestChapter}화)가 아니어서 원고와 회차 색인만 저장했습니다.`,
    "        상태 파일(현재 상태·복선·회차 요약·스냅샷)에는 수정 전 사실이 남을 수 있습니다.",
    "        사실이 바뀌는 수정이었다면 다음 회차를 쓸 때 `write next --context`로 바로잡을 내용을 넘기세요.",
  ];
}

export function formatKoreanReviseFailure(error: unknown): string {
  return `수정 실패: ${error}`;
}

export function formatKoreanStreamingProgress(elapsedMs: number, totalChars: number): string {
  return `응답 받는 중 ${Math.round(elapsedMs / 1000)}초, ${totalChars}자`;
}
