import { KOREAN_SETTING_POLICY, KOREAN_LIGHT_MARTIAL_POLICY } from "./korean-setting-policy.js";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { LLMMessage } from "../llm/provider.js";

export const KOREAN_WRITING_POLICY = `## Korean writing language (ko)
The configured writing language for this operation is Korean. Write original narrative, chapter titles, character descriptions, planning prose, state summaries and review explanations in natural Korean. This is not a request to translate an existing English story unless translation was actually requested. Preserve Korean names, honorifics, dialogue register and the author's genre/style constraints consistently. Do not default Korean characters or settings to foreign names or places without author direction.
Reuse the required protocol exactly: keep JSON property names, enum values, tool names, identifiers, file paths, parser headings and === SECTION === / === CHAPTER_CONTENT === tags unchanged. Put Korean human-readable content inside that existing contract. Earlier English/Chinese wording is a technical template, not an instruction to write English/Chinese prose. An explicit author-selected language for this task and explicit translation target language take precedence over this default; never translate source quotations or canonical proper names merely to satisfy this policy.
For ko_chars, measure the manuscript in NFC-normalized Unicode characters excluding whitespace and Markdown metadata, counting Korean, Latin letters, numbers and punctuation. Do not substitute English word counts or Chinese-only character counts. Meet the supplied target and hard/soft length limits in this unit. Never invent observations, pass reviews, or alter authority/confirmation gates to satisfy a language or length instruction.`;

/** Book/work preference wins over the project; no global language mutation. */
export async function resolveConfiguredWritingLanguage(projectRoot?: string, bookId?: string): Promise<string | undefined> {
  if (!projectRoot) return undefined;
  const candidates: string[] = [];
  if (bookId && /^[\p{L}\p{N}][\p{L}\p{N}._-]*$/u.test(bookId) && !bookId.includes("..")) {
    candidates.push(join(projectRoot, "books", bookId, "book.json"),
      join(projectRoot, "works", bookId, "source", "book.json"),
      join(projectRoot, "works", bookId, "work.json"));
  }
  candidates.push(join(projectRoot, "inkos.json"));
  for (const filename of candidates) {
    try {
      const value = JSON.parse(await readFile(filename, "utf8")) as { language?: string };
      if (value.language === "ko" || value.language === "en" || value.language === "zh") return value.language;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  return undefined;
}

export async function applyProjectLanguagePolicy(messages: ReadonlyArray<LLMMessage>, projectRoot?: string, bookId?: string): Promise<ReadonlyArray<LLMMessage>> {
  if (await resolveConfiguredWritingLanguage(projectRoot, bookId) !== "ko") return messages;
  let genre: string | undefined;
  if (projectRoot && bookId && /^[\p{L}\p{N}][\p{L}\p{N}._-]*$/u.test(bookId) && !bookId.includes("..")) {
    for (const filename of [join(projectRoot,"books",bookId,"book.json"), join(projectRoot,"works",bookId,"source","book.json"), join(projectRoot,"works",bookId,"work.json")]) {
      try { const value = JSON.parse(await readFile(filename,"utf8")) as {genre?: string};
        if (value.genre) { genre=value.genre; break; }
      } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    }
  }
  const martial = genre && /^(?:korean-martial|무협|한국무협|한국-무협|wuxia|martial-arts)$/iu.test(genre);
  return [...messages, { role: "system", content: [KOREAN_WRITING_POLICY, KOREAN_SETTING_POLICY,
    ...(martial ? [KOREAN_LIGHT_MARTIAL_POLICY] : [])].join("\n\n") }];
}
