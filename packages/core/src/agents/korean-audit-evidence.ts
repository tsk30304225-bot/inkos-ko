import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { chapterDocumentBody } from "../utils/chapter-document.js";
import { checkKoreanProse, renderKoreanProseFindings } from "../utils/korean-prose-check.js";

export const KOREAN_FATIGUE_WORDS_FILE = join("story", "korean_fatigue_words.md");
const PREVIOUS_CHAPTERS = 3;

/** One word or phrase per line; Markdown list markers and `#` comment lines are ignored. */
export function parseFatigueWords(text: string): string[] {
  return text.split(/\r?\n/u)
    .map((line) => line.replace(/^\s*[-*]\s*/u, "").trim())
    .filter((line) => line && !line.startsWith("#"));
}

async function readOptional(path: string): Promise<string | undefined> {
  try { return await readFile(path, "utf8"); }
  catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT" || code === "ENOTDIR") return undefined;
    throw error;
  }
}

async function previousChapters(bookDir: string, chapterNumber: number) {
  let files: string[];
  try { files = await readdir(join(bookDir, "chapters")); }
  catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT" || code === "ENOTDIR") return [];
    throw error;
  }
  const numbered = files.flatMap((file) => {
    const match = /^(\d{4})_.*\.md$/u.exec(file);
    const number = match ? Number(match[1]) : NaN;
    return number < chapterNumber && number >= chapterNumber - PREVIOUS_CHAPTERS ? [{ number, file }] : [];
  });
  return Promise.all(numbered.map(async ({ number, file }) => ({
    number,
    text: chapterDocumentBody(await readFile(join(bookDir, "chapters", file), "utf8"), number, "", "ko"),
  })));
}

/** Auditor system block with deterministic Korean prose observations, or "" when nothing was found. */
export async function koreanProseAuditBlock(bookDir: string | undefined, chapterNumber: number, chapterContent: string, sourceId: string): Promise<string> {
  const fatigue = bookDir ? await readOptional(join(bookDir, KOREAN_FATIGUE_WORDS_FILE)) : undefined;
  const findings = checkKoreanProse(chapterContent, {
    fatigueWords: fatigue ? parseFatigueWords(fatigue) : [],
    previousChapters: bookDir ? await previousChapters(bookDir, chapterNumber) : [],
  });
  return renderKoreanProseFindings(findings, sourceId);
}
