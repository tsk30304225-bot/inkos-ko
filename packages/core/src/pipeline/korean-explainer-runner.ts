import { join } from "node:path";
import { BaseAgent, type AgentContext } from "../agents/base.js";
import { completeLongForm } from "../llm/long-form-completion.js";
import { createWorkManifest, loadWorkManifest, saveWorkManifest } from "../harness/work-store.js";
import { syncWorkSourceArtifacts } from "../harness/source-sync.js";
import { currentExecutionAuthorRequest } from "../harness/execution-evidence.js";
import { EXPLAINER_SCRIPT_PROFILE_ID } from "../harness/korean-profiles.js";
import { checkExplainerScript, explainerTargetRange, renderExplainerCheck, type ExplainerCheckResult } from "../utils/korean-explainer-check.js";
import { mergeRequirements, persistProductionInputs, relPath, resolveSourceText, safeSegment, slugify, textArtifact } from "./script-storyboard-runner.js";

export interface ExplainerScriptInput {
  readonly authorRequest?: string;
  readonly title: string;
  readonly topic: string;
  readonly audience?: string;
  readonly targetLength?: string;
  readonly sourceText?: string;
  readonly requirements?: string;
}

export interface ExplainerScriptRunOptions {
  readonly projectRoot: string;
  readonly runtime: AgentContext;
  readonly title: string;
  readonly topic: string;
  readonly audience?: string;
  /** "long" (default 8–15 min), "shorts", "<n>분", "<n>초", "<a>~<b>분". */
  readonly targetLength?: string;
  readonly sourceText?: string;
  readonly sourcePath?: string;
  readonly requirements?: string;
  readonly projectId?: string;
  readonly onProgress?: (message: string) => void;
}

export interface ExplainerScriptRunResult {
  readonly projectId: string;
  readonly baseDir: string;
  readonly specPath: string;
  readonly scriptPath: string;
  readonly checkPath: string;
  readonly check: ExplainerCheckResult;
}

const SPEC = "explainer-spec.md";
const SCRIPT = "explainer-script.md";
const CHECK = "explainer-check.md";
const CHECK_JSON = "explainer-check.json";

export function renderExplainerSpec(input: ExplainerScriptInput): string {
  const range = explainerTargetRange(input.targetLength);
  return [
    `# ${input.title} 설명 영상 제작 명세`,
    "",
    "## 목표",
    `- 주제: ${input.topic}`,
    `- 대상 시청자: ${input.audience?.trim() || "미지정 — 주제를 처음 접하는 일반 시청자로 가정"}`,
    `- 목표 길이: ${input.targetLength?.trim() || "롱폼(기본)"} → ${range.minSeconds}~${range.maxSeconds}초`,
    "- 산출 형식: 장면 표(장면 | 길이(초) | 내레이션 | 화면 | 레퍼런스 | 출처) + 출처 목록",
    "",
    ...(input.authorRequest?.trim() ? ["## 작가 요청 원문", input.authorRequest, ""] : []),
    "## 제작 지시",
    input.requirements?.trim() || "작가의 요청을 따른다.",
    "",
    "## 원자료",
    input.sourceText?.trim()
      ? `원자료가 제공됐다(약 ${Array.from(input.sourceText.replace(/\s+/gu, "")).length}자, 공백 제외). 사실 주장의 출처는 이 자료에 있는 것만 쓴다.`
      : "원자료가 제공되지 않았다. 확인할 수 없는 사실 주장에는 출처 칸에 `확인 필요`를 적는다.",
  ].join("\n");
}

class ExplainerScriptAgent extends BaseAgent {
  get name(): string {
    return "explainer-script-writer";
  }

  async writeExplainer(input: ExplainerScriptInput): Promise<string> {
    const messages = [
      {
        role: "system" as const,
        content: [
          "Produce the confirmed Korean explainer-video script with the activated explainer-script Skill. Write all human-readable content in Korean.",
          "Follow the scene-table format exactly: headings `# <title>`, `## 개요`, `## 장면 목록`, `## 출처`, and the table columns `장면 | 길이(초) | 내레이션 | 화면 | 레퍼런스 | 출처` in that order.",
          "Every factual claim needs a source number from `## 출처`; never invent sources. Use `확인 필요` for a claim you cannot source and `없음` for scenes without factual claims.",
          "Output Markdown only. No process notes, no self-narration, no \"Here is\" preamble.",
        ].join("\n"),
      },
      {
        role: "user" as const,
        content: [
          "## Creation Spec",
          renderExplainerSpec(input),
          "",
          "## Full Source Material",
          input.sourceText?.trim() || "(none supplied)",
          "",
          "## Output Format",
          `# ${input.title}`,
          "",
          "## 개요",
          "",
          "## 장면 목록",
          "",
          "| 장면 | 길이(초) | 내레이션 | 화면 | 레퍼런스 | 출처 |",
          "| --- | --- | --- | --- | --- | --- |",
          "",
          "## 출처",
        ].join("\n"),
      },
    ];
    const response = await completeLongForm({
      messages,
      language: "ko",
      generate: (continuationMessages) => this.chat(continuationMessages, { temperature: 0.4, maxTokens: this.ctx.client.defaults.maxTokens }),
      onContinuation: (pass) => this.log?.warn(`[explainer] Output limit reached; continuing pass ${pass}.`),
    });
    return response.content.trim();
  }
}

async function ensureExplainerWork(projectRoot: string, projectId: string, title: string): Promise<void> {
  try {
    const existing = await loadWorkManifest(projectRoot, projectId);
    if (existing.profileId !== EXPLAINER_SCRIPT_PROFILE_ID) {
      throw Object.assign(new Error(`Work "${projectId}" is not an explainer-script Work.`), { code: "WORK_PROFILE_MISMATCH" });
    }
    if (existing.artifacts.some((artifact) => artifact.currentRevisionId && artifact.revisions.some((revision) => revision.path === `source/${SCRIPT}`))) {
      throw Object.assign(new Error(`Work "${projectId}" already has a current explainer script.`), { code: "WORK_ALREADY_PRODUCED" });
    }
    return;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  await saveWorkManifest(projectRoot, createWorkManifest({ id: projectId, title, profileId: EXPLAINER_SCRIPT_PROFILE_ID, language: "ko", status: "draft" }));
}

export async function runExplainerScriptCreation(options: ExplainerScriptRunOptions): Promise<ExplainerScriptRunResult> {
  const projectId = safeSegment(options.projectId ?? slugify(options.title));
  const baseDir = relPath("works", projectId, "source");
  const sourceText = await resolveSourceText(options.projectRoot, options.sourceText, options.sourcePath, projectId);
  const input: ExplainerScriptInput = {
    authorRequest: currentExecutionAuthorRequest(),
    title: options.title,
    topic: options.topic,
    audience: options.audience,
    targetLength: options.targetLength,
    sourceText,
    requirements: mergeRequirements(options.topic, options.requirements, "ko"),
  };

  options.onProgress?.("설명 영상 제작 명세를 쓰는 중...");
  const spec = renderExplainerSpec(input);
  await ensureExplainerWork(options.projectRoot, projectId, options.title);
  await persistProductionInputs(options.projectRoot, projectId, [textArtifact(join(baseDir, SPEC), spec)], sourceText);

  options.onProgress?.("설명 영상 대본을 쓰는 중...");
  // bookId lets the worker load this Work's profile skills and the Korean language policy.
  const agent = new ExplainerScriptAgent({ ...options.runtime, bookId: projectId });
  const script = await agent.writeExplainer(input);
  if (!script.trim()) throw new Error("Explainer script is empty.");
  const check = checkExplainerScript(script, options.targetLength);
  await syncWorkSourceArtifacts({
    projectRoot: options.projectRoot,
    workId: projectId,
    accept: true,
    writes: [
      textArtifact(join(baseDir, SPEC), spec),
      textArtifact(join(baseDir, SCRIPT), script),
      textArtifact(join(baseDir, CHECK), renderExplainerCheck(options.title, check)),
      textArtifact(join(baseDir, CHECK_JSON), JSON.stringify(check, null, 2)),
    ],
  });
  return {
    projectId,
    baseDir,
    specPath: relPath(baseDir, SPEC),
    scriptPath: relPath(baseDir, SCRIPT),
    checkPath: relPath(baseDir, CHECK),
    check,
  };
}
