import type { ActivatedSkillGuidance } from "../agent/skill-tool.js";
import type { WorkManifest, WorkProfile } from "../harness/contracts.js";
import type { AgentSkill } from "./types.js";

/**
 * Workers that judge or repair saved text. In the agent session upstream gives
 * the long-form auditor and reviser the profile's recommended skills
 * (inkos-story-review); the CLI chapter pipeline passes no worker skills, so
 * its audits got only the required writing skill, and a script's artifact
 * review gets only the script-writing skill. For ko works the Korean review
 * skill is added here, so Korean review criteria reach every review path.
 * zh/en works are unchanged.
 */
const KOREAN_REVIEW_WORKERS: ReadonlySet<string> = new Set(["continuity-auditor", "reviser", "artifact-method"]);
const KOREAN_REVIEW_SKILL_ID = "inkos-story-review";
// Profiles whose own skills carry no Korean review criteria. The explainer
// skill has its own review questions, so it is not listed.
const PROFILES_WITHOUT_REVIEW_CRITERIA: ReadonlySet<string> = new Set(["script"]);

export function koreanReviewSkillIds(
  profile: Pick<WorkProfile, "id" | "recommendedSkillIds">,
  work: Pick<WorkManifest, "language"> | null,
  workerId: string,
): string[] {
  if (work?.language !== "ko" || !KOREAN_REVIEW_WORKERS.has(workerId)) return [];
  const ids = [...profile.recommendedSkillIds];
  if (PROFILES_WITHOUT_REVIEW_CRITERIA.has(profile.id)) ids.push(KOREAN_REVIEW_SKILL_ID);
  return [...new Set(ids)];
}

export function koreanReviewSkillActivations(
  availableSkills: ReadonlyArray<AgentSkill>,
  ids: ReadonlyArray<string>,
): ActivatedSkillGuidance[] {
  // Same resolution as resolveProfileSkillActivations: a later skill with the same id
  // (the Korean override of an upstream skill) wins.
  const byId = new Map(availableSkills.map((skill) => [skill.id, skill]));
  return ids.flatMap((id) => {
    const skill = byId.get(id);
    return skill ? [{ skill, resources: [] }] : [];
  });
}
