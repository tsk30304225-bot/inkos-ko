import { describe, expect, it } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  formatKoreanStatusStateLines,
  formatKoreanWriteStateNotice,
  isStateNotApplied,
  koreanStateNotAppliedChapters,
  readLastAppliedChapter,
} from "../korean-state-notice.js";

describe("Korean state-not-applied notice", () => {
  it("flags only the observation codes that mean the state was kept at the baseline", () => {
    for (const code of ["state-reconciliation", "state-validation", "state-validation-unavailable"]) {
      expect(isStateNotApplied([{ code }]), code).toBe(true);
    }
    expect(isStateNotApplied([{ code: "state-projection-review" }, { code: "narrator-telling" }])).toBe(false);
  });

  it("adds a write warning only for an unapplied chapter", () => {
    expect(formatKoreanWriteStateNotice(1, [{ code: "hook-movement" }])).toEqual([]);
    const lines = formatKoreanWriteStateNotice(1, [{ code: "state-reconciliation" }]);
    expect(lines[0]).toBe("  경고: 1화 원고는 저장됐지만 상태(현재 상태·복선·회차 요약)는 반영되지 않았습니다.");
  });

  it("lists unapplied chapters even when a later chapter moved the manifest forward", () => {
    const index = [
      { number: 1, observations: [{ code: "state-reconciliation" }] },
      { number: 2, observations: [{ code: "hook-movement" }] },
    ];
    expect(koreanStateNotAppliedChapters(index)).toEqual([1]);
    expect(formatKoreanStatusStateLines(index, 2)).toEqual([
      "    상태 마지막 반영: 2화",
      "    경고: 상태가 반영되지 않은 회차 — 1화. 원고는 있지만 그 회차의 현재 상태·복선·회차 요약은 빠져 있습니다.",
    ]);
    expect(formatKoreanStatusStateLines([index[1]!], 2)).toEqual(["    상태 마지막 반영: 2화"]);
    expect(formatKoreanStatusStateLines([], 0)).toEqual([]);
  });

  it("reads lastAppliedChapter from the runtime manifest", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-state-notice-"));
    try {
      expect(await readLastAppliedChapter(root)).toBeUndefined();
      await mkdir(join(root, "story", "state"), { recursive: true });
      await writeFile(join(root, "story", "state", "manifest.json"), JSON.stringify({ schemaVersion: 2, language: "ko", lastAppliedChapter: 1 }));
      expect(await readLastAppliedChapter(root)).toBe(1);
    } finally { await rm(root, { recursive: true, force: true }); }
  });
});
