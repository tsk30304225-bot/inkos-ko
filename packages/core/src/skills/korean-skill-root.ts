import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Korean edition skills live beside the built-in skills and reuse their IDs.
 * They are layered directly above the built-ins only for projects whose
 * `inkos.json` language is `ko`, so user and project skills still win and
 * zh/en projects keep the upstream skills.
 */
export function koreanSkillsRoot(): string {
  return fileURLToPath(new URL("../../skills-ko", import.meta.url));
}

export async function usesKoreanSkills(projectRoot: string): Promise<boolean> {
  if (!projectRoot) return false;
  try {
    const config = JSON.parse(await readFile(join(projectRoot, "inkos.json"), "utf8")) as { language?: unknown };
    return config.language === "ko";
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT" || code === "ENOTDIR" || error instanceof SyntaxError) return false;
    throw error;
  }
}
