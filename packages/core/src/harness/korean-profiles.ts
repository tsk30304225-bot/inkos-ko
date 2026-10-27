import { readFileSync } from "node:fs";
import { join } from "node:path";
import { WorkProfileSchema, type WorkProfile } from "./contracts.js";

/**
 * Work profiles that exist only in Korean (ko) projects. They are registered
 * beside the upstream built-ins when the project's inkos.json language is ko,
 * so zh/en projects keep exactly the upstream profile list.
 */
export const EXPLAINER_SCRIPT_PROFILE_ID = "explainer-script";
export const EXPLAINER_SCRIPT_SKILL_ID = "inkos-ko-explainer-script";

export function koreanWorkProfiles(): ReadonlyArray<WorkProfile> {
  return [WorkProfileSchema.parse({
    version: 2,
    id: EXPLAINER_SCRIPT_PROFILE_ID,
    title: "Explainer video script",
    description: "Korean explainer-video script as a scene table with narration, visuals, references and sources.",
    capabilityIds: ["workspace", EXPLAINER_SCRIPT_PROFILE_ID],
    requiredSkillIds: [EXPLAINER_SCRIPT_SKILL_ID],
    recommendedSkillIds: [],
    artifactKinds: ["script-spec", "script", "review"],
    contextRecipe: { id: EXPLAINER_SCRIPT_PROFILE_ID, sourceIds: ["task", "skills", "work"] },
    artifactSchemas: {},
    qualityCriteria: [],
    production: {},
    confirmation: {
      inferredMutation: "execute",
      explicitRecoverableMutation: "execute",
      destructiveMutation: "confirm",
    },
  })];
}

export function isKoreanProjectSync(projectRoot: string | undefined): boolean {
  if (!projectRoot) return false;
  try {
    return (JSON.parse(readFileSync(join(projectRoot, "inkos.json"), "utf8")) as { language?: unknown }).language === "ko";
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT" || code === "ENOTDIR" || error instanceof SyntaxError) return false;
    throw error;
  }
}
