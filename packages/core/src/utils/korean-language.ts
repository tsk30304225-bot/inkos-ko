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

/** Length-unit phrase for prompts, e.g. "3000자(공백 제외)". */
export function koreanLengthPhrase(count: number): string {
  return `${count}자(공백 제외)`;
}
