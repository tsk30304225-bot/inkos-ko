import { Command } from "commander";
import {
  EXPLAINER_SCRIPT_PROFILE_ID,
  PipelineRunner,
  confirmedCapabilityBinding,
  createBuiltInWorkProfileRegistry,
  createExplainerScriptTool,
  createScriptCreationTool,
  executeExplicitCapabilityTool,
  loadAvailableAgentSkills,
  resolveProfileSkillActivations,
} from "@actalk/inkos-core";
import { parseWritingLanguage, type WritingLanguage } from "../language-options.js";
import { buildPipelineConfig, findProjectRoot, loadConfig, log, logError } from "../utils.js";

// Explicit script commands so agent sessions (bridge) can create scripts
// without driving the chat agent. zh/en behaviour of existing commands is unchanged.

async function profileSkills(root: string, profileId: string) {
  const available = await loadAvailableAgentSkills({ projectRoot: root });
  return resolveProfileSkillActivations(available.skills, createBuiltInWorkProfileRegistry(root).require(profileId));
}

function progressLogger(json: boolean | undefined) {
  return json ? undefined : (update: unknown) => {
    const text = (update as { content?: Array<{ type?: string; text?: string }> }).content
      ?.filter((item) => item.type === "text").map((item) => item.text ?? "").join("\n").trim();
    if (text) log(text);
  };
}

function report(result: { summary?: string; content?: string; data?: unknown }, json: boolean | undefined) {
  log(json ? JSON.stringify(result, null, 2) : result.content ?? result.summary ?? "");
}

function fail(prefix: string, error: unknown, json: boolean | undefined) {
  if (json) log(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }));
  else logError(`${prefix}: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}

function positiveInteger(value: string | undefined, name: string): number | undefined {
  if (value === undefined) return undefined;
  const number = Number(value);
  if (!Number.isInteger(number) || number <= 0) throw new Error(`${name} must be a positive integer.`);
  return number;
}

export const scriptCommand = new Command("script")
  .description("Script production (drama scripts; Korean projects default to vertical short drama)");

scriptCommand.command("create")
  .description("Create a script Work from an idea, outline or source text")
  .requiredOption("--title <title>", "Script title")
  .requiredOption("--instruction <text>", "Confirmed script instruction (story, format, preferences)")
  .option("--format <format>", "vertical_short_drama | screenplay | miniseries | audio_drama | interactive_script | general_script, or free text")
  .option("--episodes <n>", "Episode count")
  .option("--episode-duration <text>", "Per-episode duration, e.g. \"2분\"")
  .option("--source <path>", "Project-relative source material path")
  .option("--source-kind <text>", "Source type, e.g. novel excerpt, original idea")
  .option("--requirements <text>", "Production constraints and tone")
  .option("--id <id>", "Work id (derived from the title when omitted)")
  .option("--lang <language>", "Writing language (defaults to the project language)", parseWritingLanguage)
  .option("--json", "Output JSON")
  .action(async (opts) => {
    try {
      const root = findProjectRoot();
      const config = await loadConfig({ projectRoot: root });
      const language = (opts.lang ?? config.language ?? "zh") as WritingLanguage;
      const pipeline = new PipelineRunner(buildPipelineConfig(config, root, { quiet: Boolean(opts.json) }));
      const result = await executeExplicitCapabilityTool({
        projectRoot: root,
        binding: confirmedCapabilityBinding("script_create")!,
        tool: createScriptCreationTool(pipeline, root, { language, defaultSkills: await profileSkills(root, "script") }),
        parameters: {
          title: opts.title,
          instruction: opts.instruction,
          ...(opts.format ? { targetFormat: opts.format } : {}),
          ...(opts.sourceKind ? { sourceKind: opts.sourceKind } : {}),
          ...(opts.source ? { sourcePath: opts.source } : {}),
          ...(opts.requirements ? { requirements: opts.requirements } : {}),
          ...(opts.episodes ? { episodeCount: positiveInteger(opts.episodes, "episodes") } : {}),
          ...(opts.episodeDuration ? { episodeDuration: opts.episodeDuration } : {}),
          ...(opts.id ? { projectId: opts.id } : {}),
        },
        onUpdate: progressLogger(opts.json),
      });
      report(result, opts.json);
    } catch (error) { fail("Script creation failed", error, opts.json); }
  });

export const explainerCommand = new Command("explainer")
  .description("Korean explainer-video scripts as scene tables (Korean projects only)");

explainerCommand.command("create")
  .description("Create an explainer-video script Work (scene table with narration, visuals, references and sources)")
  .requiredOption("--title <title>", "Video title")
  .requiredOption("--topic <text>", "Topic and central question")
  .option("--audience <text>", "Target viewers")
  .option("--length <text>", "long (default, 8–15분) | shorts | <n>분 | <n>초 | <a>~<b>분")
  .option("--source <path>", "Project-relative source material; factual claims may cite only this")
  .option("--requirements <text>", "Tone, visual style and reference requirements")
  .option("--id <id>", "Work id (derived from the title when omitted)")
  .option("--json", "Output JSON")
  .action(async (opts) => {
    try {
      const root = findProjectRoot();
      const config = await loadConfig({ projectRoot: root });
      if (config.language !== "ko") throw new Error("explainer create is available in Korean projects only (inkos init --lang ko).");
      const pipeline = new PipelineRunner(buildPipelineConfig(config, root, { quiet: Boolean(opts.json) }));
      const result = await executeExplicitCapabilityTool({
        projectRoot: root,
        binding: { capabilityId: EXPLAINER_SCRIPT_PROFILE_ID, actionId: "explainer_script_create", profileId: EXPLAINER_SCRIPT_PROFILE_ID, risk: "recoverable-write" },
        tool: createExplainerScriptTool(pipeline, root, { defaultSkills: await profileSkills(root, EXPLAINER_SCRIPT_PROFILE_ID) }),
        parameters: {
          title: opts.title,
          topic: opts.topic,
          ...(opts.audience ? { audience: opts.audience } : {}),
          ...(opts.length ? { targetLength: opts.length } : {}),
          ...(opts.source ? { sourcePath: opts.source } : {}),
          ...(opts.requirements ? { requirements: opts.requirements } : {}),
          ...(opts.id ? { projectId: opts.id } : {}),
        },
        onUpdate: progressLogger(opts.json),
      });
      report(result, opts.json);
    } catch (error) { fail("Explainer creation failed", error, opts.json); }
  });
