import { describe, expect, it } from "vitest";
import {
  formatKoreanEarlierRevisionNotice,
  formatKoreanReviseFailure,
  formatKoreanReviseResultLines,
  formatKoreanReviseStart,
  formatKoreanStreamingProgress,
} from "../korean-cli-text.js";

describe("Korean CLI text", () => {
  it("prints revise progress and results in Korean", () => {
    expect(formatKoreanReviseStart("book", 1, "spot-fix")).toBe('"book" 1화 수정 중 [모드: spot-fix]...');
    expect(formatKoreanReviseStart("book", undefined, "polish")).toBe('"book" 최신 회차 수정 중 [모드: polish]...');
    expect(formatKoreanReviseResultLines({ chapterNumber: 1, changed: true, wordCount: 2898, observations: [1, 2] }))
      .toEqual(["  1화 수정 완료", "  분량: 2898자", "  검수 의견: 2건"]);
    expect(formatKoreanReviseResultLines({ chapterNumber: 2, changed: false, wordCount: 2880, observations: [] })[0])
      .toBe("  2화: 적용할 변경 없음");
    expect(formatKoreanReviseFailure(new Error("x"))).toBe("수정 실패: Error: x");
  });

  it("warns only when a changed chapter is not the latest one", () => {
    expect(formatKoreanEarlierRevisionNotice(3, 3, true)).toEqual([]);
    expect(formatKoreanEarlierRevisionNotice(1, 3, false)).toEqual([]);
    const lines = formatKoreanEarlierRevisionNotice(1, 3, true);
    expect(lines[0]).toBe("  경고: 1화는 최신 회차(3화)가 아니어서 원고와 회차 색인만 저장했습니다.");
    expect(lines.join("\n")).toContain("수정 전 사실이 남을 수 있습니다");
    expect(lines.join("\n")).toContain("write next --context");
  });

  it("prints streaming progress without the CJK count", () => {
    expect(formatKoreanStreamingProgress(12_400, 3150)).toBe("응답 받는 중 12초, 3150자");
  });
});
