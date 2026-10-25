import type { WorkManifest, WorkProfile } from "../harness/contracts.js";

/**
 * Workers that judge or repair a saved chapter. In the agent session upstream
 * gives them the profile's recommended skills (inkos-story-review for
 * long-form); the CLI chapter pipeline passes no worker skills, so its audits
 * got only the required writing skill. For ko works the same recommended
 * skills are added here, so the Korean review criteria reach chapter audits
 * and revisions on every path. zh/en works are unchanged.
 */
const KOREAN_REVIEW_WORKERS: ReadonlySet<string> = new Set(["continuity-auditor", "reviser"]);

export function koreanReviewSkillIds(
  profile: Pick<WorkProfile, "recommendedSkillIds">,
  work: Pick<WorkManifest, "language"> | null,
  workerId: string,
): string[] {
  if (work?.language !== "ko" || !KOREAN_REVIEW_WORKERS.has(workerId)) return [];
  return [...profile.recommendedSkillIds];
}
