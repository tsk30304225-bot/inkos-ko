import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { ActivatedSkillGuidance } from "../agent/skill-tool.js";
import type { WorkManifest } from "../harness/contracts.js";
import { koreanSkillsRoot } from "./korean-skill-root.js";

export const KOREAN_GENRE_IDS = ["light-martial", "fantasy", "modern-fantasy"] as const;
export type KoreanGenreId = typeof KOREAN_GENRE_IDS[number];

const GENRE_ALIASES: Readonly<Record<KoreanGenreId, ReadonlyArray<string>>> = {
  "light-martial": ["light-martial", "korean-martial", "martial", "martial-arts", "wuxia", "무협", "라이트무협", "한국무협", "신무협"],
  "fantasy": ["fantasy", "판타지", "정통판타지", "이세계판타지"],
  "modern-fantasy": ["modern-fantasy", "urban-fantasy", "현대판타지", "현판"],
};

const LONG_WRITING_SKILL_ID = "inkos-long-writing";
const GENRE_REFERENCE_DIR = "references/genres/";

/** Map a book's free-form genre value (English ID or common Korean name) to a Korean genre reference. */
export function resolveKoreanGenre(genre: unknown): KoreanGenreId | undefined {
  if (typeof genre !== "string") return undefined;
  const key = genre.normalize("NFC").trim().toLowerCase().replace(/[\s_]+/gu, "-");
  const compact = key.replace(/-/g, "");
  return KOREAN_GENRE_IDS.find((id) => GENRE_ALIASES[id].some((alias) => alias === key || alias.replace(/-/g, "") === compact));
}

export function koreanGenreReferencePath(genre: KoreanGenreId): string {
  return `${GENRE_REFERENCE_DIR}${genre}.md`;
}

/**
 * Deterministically attach the genre reference to the Korean long-writing
 * skill. Retrieval over Korean text is lexical and weak, so the selected genre
 * file is always added and other genres' files are dropped from retrieved
 * sections. Only applies when the activated skill is the bundled Korean one.
 */
export async function attachKoreanGenreReference(
  activations: ReadonlyArray<ActivatedSkillGuidance>,
  input: { readonly work: WorkManifest | null; readonly projectRoot?: string; readonly bookId?: string },
): Promise<ReadonlyArray<ActivatedSkillGuidance>> {
  const index = activations.findIndex(({ skill }) => skill.id === LONG_WRITING_SKILL_ID
    && skill.baseDir === join(koreanSkillsRoot(), LONG_WRITING_SKILL_ID));
  if (index < 0) return activations;
  if (input.work && input.work.language !== "ko") return activations;
  const genre = resolveKoreanGenre(input.work?.metadata.genre ?? await readBookGenre(input.projectRoot, input.bookId));
  const activation = activations[index]!;
  const others = activation.resources.filter((resource) => !resource.path.startsWith(GENRE_REFERENCE_DIR));
  let resources = others;
  if (genre) {
    const path = koreanGenreReferencePath(genre);
    const body = await readFile(join(activation.skill.baseDir!, path), "utf8");
    resources = [...others, { path, body, charStart: 0, charEnd: body.length }];
  }
  if (resources.length === activation.resources.length && resources.every((resource, i) => resource === activation.resources[i])) return activations;
  return activations.map((item, i) => i === index ? { ...item, resources } : item);
}

export async function readBookGenre(projectRoot?: string, bookId?: string): Promise<string | undefined> {
  if (!projectRoot || !bookId || !/^[\p{L}\p{N}][\p{L}\p{N}._-]*$/u.test(bookId) || bookId.includes("..")) return undefined;
  for (const path of [join(projectRoot, "works", bookId, "source", "book.json"), join(projectRoot, "books", bookId, "book.json")]) {
    try {
      const genre = (JSON.parse(await readFile(path, "utf8")) as { genre?: unknown }).genre;
      if (typeof genre === "string") return genre;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  return undefined;
}
