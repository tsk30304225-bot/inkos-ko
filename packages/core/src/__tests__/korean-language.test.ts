import { describe, expect, it } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { countChapterLength, buildLengthSpec, formatLengthCount, defaultChapterLength } from "../utils/length-metrics.js";
import { deriveBookIdFromTitle, isSafeBookId } from "../utils/book-id.js";
import { splitChapters } from "../utils/chapter-splitter.js";
import { StateManager } from "../state/manager.js";
import { BookConfigSchema } from "../models/book.js";
import { LengthCountingModeSchema } from "../models/length-governance.js";
import { applyProjectLanguagePolicy, resolveConfiguredWritingLanguage } from "../utils/korean-language-policy.js";

describe("Korean writing support", () => {
  it("applies setting contracts without duplicating genre guidance", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-setting-"));
    try {
      await writeFile(join(root,"inkos.json"), JSON.stringify({language:"ko"}));
      await mkdir(join(root,"books","무협"), {recursive:true});
      await writeFile(join(root,"books","무협","book.json"), JSON.stringify({language:"ko",genre:"korean-martial"}));
      const messages = [{role:"user" as const,content:"설정 검토"}];
      const general = (await applyProjectLanguagePolicy(messages,root)).at(-1)!.content;
      for (const axis of ["목적", "맥락", "기준", "경계"]) expect(general).toContain(axis);
      expect(general).toContain("정수나 enum에 설명문을 넣거나");
      expect(general).not.toContain("## 현대 한국 라이트 무협 편집 기준");
      // Light martial guidance now arrives as a Korean skill reference (korean-skills.test.ts).
      const martial = (await applyProjectLanguagePolicy(messages,root,"무협")).at(-1)!.content;
      expect(martial).toBe(general);
    } finally {await rm(root,{recursive:true,force:true});}
  });
  it("creates actionable Korean control documents and preserves an author's existing text", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-controls-"));
    try {
      const state = new StateManager(root), book = join(root,"books","시험");
      await state.ensureControlDocumentsAt(book,"ko");
      const author = join(book,"story","author_intent.md");
      const focus = await import("node:fs/promises").then(fs=>fs.readFile(join(book,"story","current_focus.md"),"utf8"));
      const initial = await import("node:fs/promises").then(fs=>fs.readFile(author,"utf8"));
      for (const axis of ["목적:","맥락:","기준:","경계:"]) {expect(initial).toContain(axis);expect(focus).toContain(axis);}
      expect(initial).toContain("미정");
      await writeFile(author,"작가가 직접 정한 원문");
      await state.ensureControlDocumentsAt(book,"ko");
      expect(await import("node:fs/promises").then(fs=>fs.readFile(author,"utf8"))).toBe("작가가 직접 정한 원문");
    } finally {await rm(root,{recursive:true,force:true});}
  });
  it("counts NFC characters, mixed scripts and emoji, excluding whitespace and metadata", () => {
    const text = "---\ntitle: ignored\n---\n# 제목\n가 나 A1🙂!\n```json\nignored\n```";
    expect(countChapterLength(text, "ko_chars")).toBe(6);
    expect(countChapterLength(text.normalize("NFD"), "ko_chars")).toBe(6);
  });
  it("imports Korean numbered chapter headings", () => {
    expect(splitChapters("# 제1화: 약속\n첫 본문\n# 2화 돌아온 밤\n둘째 본문")).toEqual([{title:"약속",content:"첫 본문"},{title:"돌아온 밤",content:"둘째 본문"}]);
  });
  it("uses native character length defaults and labels", () => {
    expect(defaultChapterLength("ko")).toBe(3000);
    expect(buildLengthSpec(3000, "ko").countingMode).toBe("ko_chars");
    expect(formatLengthCount(123, "ko_chars")).toBe("123자");
    expect(LengthCountingModeSchema.parse("ko_chars")).toBe("ko_chars");
  });
  it("preserves English words and Chinese character counting", () => {
    expect(countChapterLength("Don't stop 42.", "en_words")).toBe(3);
    expect(countChapterLength("你好 世界", "zh_chars")).toBe(4);
  });
  it("keeps Korean book identifiers and rejects traversal", () => {
    expect(deriveBookIdFromTitle(" 달빛 아래: 첫 약속! ".normalize("NFD"))).toBe("달빛-아래-첫-약속");
    expect(isSafeBookId("달빛-아래")).toBe(true);
    for (const id of ["../달빛", "책/원고", "책\\원고", ".."])
      expect(isSafeBookId(id)).toBe(false);
  });
  it("accepts Korean in the native book schema", () => {
    const now = new Date().toISOString();
    expect(BookConfigSchema.parse({ id: "달빛", title: "달빛", platform: "other", genre: "other", status: "active", targetChapters: 3, chapterWordCount: 3000, language: "ko", createdAt: now, updatedAt: now }).language).toBe("ko");
  });
  it("respects a Korean-named book's explicit language over the project", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-test-"));
    try {
      await writeFile(join(root, "inkos.json"), JSON.stringify({language:"ko"}));
      await mkdir(join(root, "books", "달빛"), {recursive:true});
      await writeFile(join(root, "books", "달빛", "book.json"), JSON.stringify({language:"en"}));
      expect(await resolveConfiguredWritingLanguage(root, "달빛")).toBe("en");
      const messages = [{role:"user" as const,content:"request"}];
      expect(await applyProjectLanguagePolicy(messages, root, "달빛")).toEqual(messages);
      const korean = await applyProjectLanguagePolicy(messages, root);
      expect(korean.at(-1)?.content).toContain("Korean");
      expect(korean.at(-1)?.content).toContain("JSON property names");
    } finally { await rm(root, {recursive:true,force:true}); }
  });
});
