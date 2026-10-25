const UNSAFE_BOOK_ID_RE = /[\u0000-\u001f\u007f/\\:*?"'`{}<>|]/u;

// Upstream keeps ASCII letters/digits and CJK ideographs; the Korean edition adds Hangul syllables only,
// so IDs derived from zh/en titles stay identical. Decomposed Hangul (e.g. macOS NFD input) is composed first.
export function deriveBookIdFromTitle(title: string): string {
  return composeHangul(title)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff\uac00-\ud7a3]/gu, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 30);
}

export function composeHangul(value: string): string {
  return value.replace(/[\u1100-\u11ff\u3130-\u318f]+/gu, (run) => run.normalize("NFC"));
}

export function isSafeBookId(bookId: unknown): bookId is string {
  return (
    typeof bookId === "string"
    && bookId.length > 0
    && bookId.length <= 120
    && bookId.trim() === bookId
    && bookId !== "."
    && bookId !== ".."
    && !bookId.includes("..")
    && !UNSAFE_BOOK_ID_RE.test(bookId)
  );
}

export function assertSafeBookId(bookId: string, label = "bookId"): string {
  if (!isSafeBookId(bookId)) {
    throw new Error(`Invalid ${label}: ${JSON.stringify(bookId)}`);
  }
  return bookId;
}
