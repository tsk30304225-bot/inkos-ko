import { describe, expect, it } from "vitest";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readChapterHeading, splitChapters } from "../utils/chapter-splitter.js";
import { chapterDocumentBody, chapterDocumentHeading, renderChapterDocument } from "../utils/chapter-document.js";
import { deriveBookIdFromTitle } from "../utils/book-id.js";
import { countChapterLength, resolveLengthCountingMode } from "../utils/length-metrics.js";
import { chapterLabel, normalizeWritingLanguage, pickByLanguage, promptLanguage, upstreamLanguage } from "../utils/korean-language.js";
import { renderChapterSummariesProjection, renderCurrentStateProjection, renderHooksProjection } from "../state/state-projections.js";
import { formatShortFictionChapterHeading, shortFictionDefaultChapterLength } from "../agents/short-fiction.js";
import { unresolvedStateObservation } from "../pipeline/chapter-state-recovery.js";
import { StateManager } from "../state/manager.js";
import { writeExportArtifact } from "../interaction/export-artifact.js";

// The upstream rule, kept here to prove zh/en titles still derive the same IDs.
const upstreamBookId = (title: string) => title.trim().toLowerCase()
  .replace(/[^a-z0-9一-鿿]/gu, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "").slice(0, 30);

describe("Korean edition stage 1", () => {
  it("recognises Korean chapter headings without splitting ordinary prose", () => {
    for (const heading of ["제1화", "제 12 화 귀환", "제3장 그날", "# 제4화: 약속", "## 5화 밤", "6화", "7화. 출발", "8화: 끝"]) {
      expect(readChapterHeading(heading)?.language, heading).toBe("ko");
    }
    expect(readChapterHeading("# 제4화: 약속")).toEqual({ number: 4, title: "약속", language: "ko" });
    expect(readChapterHeading("7화. 출발")).toEqual({ number: 7, title: "출발", language: "ko" });
    for (const prose of ["3장의 편지가 도착했다.", "2장짜리 지도를 펼쳤다.", "3화째 되는 날이었다.", "제1화에서 그는 웃었다.", "2화 만에 끝났다.", "10장 넘게 썼다."]) {
      expect(readChapterHeading(prose), prose).toBeUndefined();
    }
    expect(splitChapters("제1화 시작\n3장의 편지가 도착했다.\n2화 만에 끝났다.\n제2화 귀환\n둘째")).toEqual([
      { title: "시작", content: "3장의 편지가 도착했다.\n2화 만에 끝났다." },
      { title: "귀환", content: "둘째" },
    ]);
    expect(splitChapters("제1화\n본문")).toEqual([{ title: "제1화", content: "본문" }]);
  });

  it("keeps Chinese and English heading parsing unchanged", () => {
    expect(readChapterHeading("第十二章 归来")).toEqual({ number: 12, title: "归来", language: "zh" });
    expect(readChapterHeading("Chapter IV: Return")).toEqual({ number: 4, title: "Return", language: "en" });
  });

  it("writes and strips one 제N화 chapter document heading", () => {
    expect(chapterDocumentHeading(3, "귀환", "ko")).toBe("# 제3화 귀환");
    expect(chapterDocumentHeading(3, "Return", "en")).toBe("# Chapter 3: Return");
    expect(chapterDocumentHeading(3, "归来", "zh")).toBe("# 第3章 归来");
    expect(chapterDocumentBody("# 제3화 귀환\n\n본문", 3, "귀환", "ko")).toBe("본문");
    expect(renderChapterDocument(3, "귀환", "# 제3화: 귀환\n\n본문", "ko")).toBe("# 제3화 귀환\n\n본문");
  });

  it("derives Hangul book IDs while zh/en titles keep the upstream ID", () => {
    expect(deriveBookIdFromTitle("화산의 검")).toBe("화산의-검");
    expect(deriveBookIdFromTitle("화산의 검".normalize("NFD"))).toBe("화산의-검");
    for (const title of ["My Novel: Part 1", "Café Ñoño", "Ведьмак", "我的小说 第一部", "Ｆｕｌｌ width"]) {
      expect(deriveBookIdFromTitle(title), title).toBe(upstreamBookId(title));
    }
  });

  it("counts Korean manuscripts in ko_chars, never English words", () => {
    const text = "그는 검을 뽑았다. 바람이 멈췄다.";
    expect(resolveLengthCountingMode("ko")).toBe("ko_chars");
    expect(countChapterLength(text, resolveLengthCountingMode("ko"))).toBe(15);
    expect(countChapterLength(text, "en_words")).toBe(0);
  });

  it("routes language helpers explicitly", () => {
    expect(promptLanguage("ko")).toBe("en");
    expect(promptLanguage("zh")).toBe("zh");
    expect(normalizeWritingLanguage("ko")).toBe("ko");
    expect(normalizeWritingLanguage("fr")).toBe("zh");
    expect(pickByLanguage("ko", { zh: "中", en: "en", ko: "한" })).toBe("한");
    expect(pickByLanguage("ko", { zh: "中", en: "en" })).toBe("en");
    expect(chapterLabel("ko", 2)).toBe("제2화");
    expect(upstreamLanguage("ko")).toBe("en");
    expect(upstreamLanguage("zh")).toBe("zh");
    expect(upstreamLanguage(undefined)).toBeUndefined();
  });

  it("renders Korean state projections and keeps zh/en headings", () => {
    const hooks = { hooks: [] };
    expect(renderHooksProjection(hooks, "ko")).toContain("# 복선 목록");
    expect(renderHooksProjection(hooks, "en")).toContain("# Pending Hooks");
    expect(renderHooksProjection(hooks, "zh")).toContain("# 伏笔池");
    expect(renderChapterSummariesProjection({ rows: [] }, "ko")).toContain("| 회차 | 제목 |");
    const current = renderCurrentStateProjection({ chapter: 2, facts: [] }, "ko");
    expect(current).toContain("# 현재 상태");
    expect(current).toContain("> 현재 회차: 2");
    expect(unresolvedStateObservation("ko").summary).toMatch(/[가-힣]/);
    expect(unresolvedStateObservation("en").summary).toBe("State reconciliation remains unresolved after recalculation.");
  });

  it("uses a Korean short-fiction default and heading", () => {
    expect(shortFictionDefaultChapterLength("ko")).toBe(1000);
    expect(shortFictionDefaultChapterLength("en")).toBe(650);
    expect(shortFictionDefaultChapterLength("zh")).toBe(1000);
    expect(formatShortFictionChapterHeading(1, "시작", "ko")).toBe("제1화 시작");
    expect(formatShortFictionChapterHeading(1, "Start", "en")).toBe("Chapter 1: Start");
  });

  it("exports a Korean book with 제N화 headings", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-export-"));
    try {
      const state = new StateManager(root), now = new Date().toISOString(), id = "달빛";
      await state.saveBookConfig(id, { id, title: "달빛", genre: "other", platform: "other", status: "active", targetChapters: 2, chapterWordCount: 3000, language: "ko", createdAt: now, updatedAt: now });
      const chapter = (number: number, title: string) => ({ number, title, wordCount: 4, provenance: "imported" as const, observations: [], createdAt: now, updatedAt: now });
      await state.saveChapterIndex(id, [chapter(1, "시작"), chapter(2, "귀환")]);
      await writeFile(join(state.bookDir(id), "chapters/0001_시작.md"), "# 제1화 시작\n\n첫 장면.\n");
      await writeFile(join(state.bookDir(id), "chapters/0002_귀환.md"), "둘째 장면.\n");
      const md = await writeExportArtifact(state, id, { format: "md" });
      const text = await readFile(md.outputPath, "utf8");
      expect(text).toContain("# 제1화 시작");
      expect(text).toContain("# 제2화 귀환");
      expect(text).not.toMatch(/第\d+章|Chapter \d/);
    } finally { await rm(root, { recursive: true, force: true }); }
  });
});
