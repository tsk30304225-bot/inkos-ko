/**
 * Language helpers for the Korean (ko) edition.
 *
 * Upstream code branches on `language === "en" ? en : zh`. Widening the type
 * alone silently routes ko to whichever side the ternary defaults to, so call
 * sites use these helpers instead: zh/en results stay byte-identical, and ko
 * gets an explicit answer.
 */
export type WritingLanguage = "zh" | "en" | "ko";

/** Template language for model-facing instructions. ko reuses English templates; the Korean output policy is injected separately. */
export function promptLanguage(language: WritingLanguage | undefined): "zh" | "en" {
  return language === "en" || language === "ko" ? "en" : "zh";
}

/**
 * For subsystems outside the Korean edition's scope (interactive play,
 * interactive film, narrative forecast), which stay upstream zh/en code: ko
 * takes the English path, as the earlier patch's `!== "zh"` did.
 */
export function upstreamLanguage(language: WritingLanguage): "zh" | "en";
export function upstreamLanguage(language: WritingLanguage | undefined): "zh" | "en" | undefined;
export function upstreamLanguage(language: WritingLanguage | undefined): "zh" | "en" | undefined {
  return language === "ko" ? "en" : language;
}

/** Keep ko instead of folding it into zh; unknown values keep upstream's zh fallback. */
export function normalizeWritingLanguage(language: unknown): WritingLanguage {
  return language === "ko" ? "ko" : language === "en" ? "en" : "zh";
}

/** Choose user-visible text per language; ko falls back to English when no Korean text is given. */
export function pickByLanguage<T>(language: WritingLanguage | undefined, messages: { readonly zh: T; readonly en: T; readonly ko?: T }): T {
  if (language === "ko") return messages.ko ?? messages.en;
  return language === "en" ? messages.en : messages.zh;
}

/** Bare chapter label: 第N章 / Chapter N / 제N화. */
export function chapterLabel(language: WritingLanguage | undefined, chapterNumber: number): string {
  return pickByLanguage(language, {
    zh: `第${chapterNumber}章`,
    en: `Chapter ${chapterNumber}`,
    ko: `제${chapterNumber}화`,
  });
}

/**
 * Role-card folder under story/roles/. Upstream writes 主要角色/次要角色 for every
 * language; ko works use major/minor (every reader already accepts both).
 */
export function roleTierDirectory(language: WritingLanguage | undefined, tier: "major" | "minor"): string {
  if (language === "ko") return tier;
  return tier === "major" ? "主要角色" : "次要角色";
}

/** Folders a foundation revision clears; ko also clears older upstream-named folders. */
export function roleTierDirectories(language: WritingLanguage | undefined): string[] {
  return language === "ko" ? ["major", "minor", "主要角色", "次要角色"] : ["主要角色", "次要角色"];
}

/** Length-unit phrase for prompts, e.g. "3000자(공백 제외)". */
export function koreanLengthPhrase(count: number): string {
  return `${count}자(공백 제외)`;
}
