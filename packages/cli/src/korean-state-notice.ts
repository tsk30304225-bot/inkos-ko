import { readFile } from "node:fs/promises";
import { join } from "node:path";

// A chapter whose state validation stayed unresolved is saved, but InkOS keeps
// the previous runtime state (pipeline/chapter-truth-validation.ts). The only
// persisted trace is one of these observation codes on the chapter.
const STATE_NOT_APPLIED_CODES = new Set(["state-reconciliation", "state-validation", "state-validation-unavailable"]);

interface ChapterObservations {
  readonly number: number;
  readonly observations: ReadonlyArray<{ readonly code: string }>;
}

export function isStateNotApplied(observations: ChapterObservations["observations"]): boolean {
  return observations.some((observation) => STATE_NOT_APPLIED_CODES.has(observation.code));
}

export function formatKoreanWriteStateNotice(chapterNumber: number, observations: ChapterObservations["observations"]): string[] {
  if (!isStateNotApplied(observations)) return [];
  return [
    `  경고: ${chapterNumber}화 원고는 저장됐지만 상태(현재 상태·복선·회차 요약)는 반영되지 않았습니다.`,
    "        상태 검증이 재정산 뒤에도 해결되지 않아 이전 상태를 유지했습니다. 다음 회차는 이 회차의 사실 없이 이어집니다.",
  ];
}

export async function readLastAppliedChapter(bookDir: string): Promise<number | undefined> {
  try {
    const manifest = JSON.parse(await readFile(join(bookDir, "story", "state", "manifest.json"), "utf8")) as { lastAppliedChapter?: unknown };
    return typeof manifest.lastAppliedChapter === "number" ? manifest.lastAppliedChapter : undefined;
  } catch {
    return undefined;
  }
}

export function koreanStateNotAppliedChapters(index: ReadonlyArray<ChapterObservations>): number[] {
  return index.filter((chapter) => isStateNotApplied(chapter.observations)).map((chapter) => chapter.number);
}

export function formatKoreanStatusStateLines(index: ReadonlyArray<ChapterObservations>, lastAppliedChapter: number | undefined): string[] {
  if (index.length === 0) return [];
  const lines = [`    상태 마지막 반영: ${lastAppliedChapter === undefined ? "알 수 없음" : `${lastAppliedChapter}화`}`];
  const missing = koreanStateNotAppliedChapters(index);
  if (missing.length > 0) {
    lines.push(`    경고: 상태가 반영되지 않은 회차 — ${missing.map((number) => `${number}화`).join(", ")}. 원고는 있지만 그 회차의 현재 상태·복선·회차 요약은 빠져 있습니다.`);
  }
  return lines;
}
