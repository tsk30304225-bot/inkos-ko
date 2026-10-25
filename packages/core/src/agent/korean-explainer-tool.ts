import { Type, type Static } from "@sinclair/typebox";
import type { AgentTool, AgentToolResult } from "@mariozechner/pi-agent-core";
import type { PipelineRunner } from "../pipeline/runner.js";
import type { ActivatedSkillGuidance } from "./skill-tool.js";
import { runExplainerScriptCreation } from "../pipeline/korean-explainer-runner.js";
import { activatedSkillIds, mergeActivatedSkillGuidance } from "../skills/activations.js";

export const EXPLAINER_CREATE_TOOL = "explainer_script_create";

export const ExplainerCreateParams = Type.Object({
  title: Type.String({ description: "Video title." }),
  topic: Type.String({ description: "Confirmed topic and central question of the explainer video." }),
  audience: Type.Optional(Type.String({ description: "Target viewers." })),
  targetLength: Type.Optional(Type.String({ description: "long (default 8–15 min), shorts, <n>분, <n>초 or <a>~<b>분." })),
  sourceText: Type.Optional(Type.String({ description: "Source material; factual claims may cite only this material." })),
  sourcePath: Type.Optional(Type.String({ description: "Project-relative source material path." })),
  requirements: Type.Optional(Type.String({ description: "Tone, style, visual and reference requirements." })),
  projectId: Type.Optional(Type.String({ description: "Work id; derived from the title when omitted." })),
});
type ExplainerCreateParamsType = Static<typeof ExplainerCreateParams>;

export function createExplainerScriptTool(
  pipeline: PipelineRunner,
  projectRoot: string,
  options: { readonly defaultSkills?: ReadonlyArray<ActivatedSkillGuidance>; readonly activeSkills?: () => ReadonlyArray<ActivatedSkillGuidance> } = {},
): AgentTool<typeof ExplainerCreateParams> {
  return {
    name: EXPLAINER_CREATE_TOOL,
    description: "Create a Korean explainer-video script Work as a scene table (duration, narration, visuals, references, sources) and record a deterministic format check.",
    label: "Explainer Script Creation",
    parameters: ExplainerCreateParams,
    async execute(_toolCallId: string, params: ExplainerCreateParamsType, signal?: AbortSignal, onUpdate?): Promise<AgentToolResult<unknown>> {
      const skills = mergeActivatedSkillGuidance(options.defaultSkills ?? [], options.activeSkills?.() ?? []);
      const progress = (text: string) => onUpdate?.({ content: [{ type: "text", text }], details: undefined });
      const result = await pipeline.runWithAgentContext({ signal, activatedSkills: skills }, () => runExplainerScriptCreation({
        projectRoot,
        runtime: pipeline.createAgentContext("explainer-script"),
        ...params,
        onProgress: progress,
      }));
      const text = [
        `설명 영상 대본 "${result.projectId}"을(를) 만들었습니다.`,
        `명세: ${result.specPath}`,
        `대본: ${result.scriptPath}`,
        `형식 검사: ${result.checkPath} — ${result.check.ok ? "통과" : `형식 문제 ${result.check.errors.length}건`}, 장면 ${result.check.sceneCount}개, ${result.check.totalSeconds}초`,
      ].join("\n");
      return { content: [{ type: "text", text }], details: { kind: "explainer_script_created", workId: result.projectId, ...result, skillIds: activatedSkillIds(skills) } };
    },
  };
}
