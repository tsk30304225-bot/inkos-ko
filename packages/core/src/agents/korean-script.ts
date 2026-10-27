/**
 * Korean (ko) branches for script creation. Upstream renders zh/en; these
 * functions keep Korean works on Korean spec text, Korean deliverable headings
 * and the Korean default format (vertical short drama) without changing zh/en.
 */
import type { ScriptCreationInput, ScriptTargetFormat } from "./script-storyboard.js";

/** Korean deliverable headings. `## 장소` lets the studio fix location references. */
export const KOREAN_SCRIPT_HEADINGS = ["## 등장인물", "## 장소", "## 대본"] as const;

/** Default when a Korean script does not name a format (2026-10-25 user decision). */
export const KOREAN_DEFAULT_SCRIPT_FORMAT = "vertical_short_drama";

export function koreanScriptTargetLabel(value: ScriptTargetFormat | undefined): string {
  const format = value?.trim() || KOREAN_DEFAULT_SCRIPT_FORMAT;
  switch (format) {
    case "vertical_short_drama": return "세로형 숏드라마";
    case "screenplay":
    case "miniseries": return "미니시리즈형 드라마 대본";
    case "audio_drama": return "오디오 드라마";
    case "interactive_script": return "인터랙티브 대본";
    case "general_script": return "일반 대본";
    default: return format;
  }
}

export function koreanSourceSummary(sourceText: string | undefined): string {
  const text = sourceText?.replace(/\s+/g, " ").trim();
  if (!text) return "전체 원작 자료가 제공되지 않았다.";
  return `전체 원작 자료가 제공됐다(약 ${Array.from(text.replace(/\s+/g, "")).length}자, 공백 제외). 생성할 때 전체 내용을 읽는다.`;
}

function koreanProductionBrief(input: { authorRequest?: string; requirements?: string }): string[] {
  return [
    ...(input.authorRequest?.trim() ? ["## 작가 요청 원문", input.authorRequest, ""] : []),
    "## 제작 지시",
    "아래 지시는 작업을 풀어 쓴 것이다. 덧붙인 제작상의 선택은 작가의 제약 안에서 조정할 수 있다.",
    input.requirements?.trim() || "작가의 요청을 따른다.",
  ];
}

export function renderKoreanScriptSpec(input: ScriptCreationInput): string {
  return [
    `# ${input.title} 대본 제작 명세`,
    "",
    "## 목표",
    `- 납품 형식: ${koreanScriptTargetLabel(input.targetFormat)}`,
    input.episodeCount ? `- 회차 수: ${input.episodeCount}` : "- 회차 수: 미지정 — 원작과 요청에 따라 판단",
    input.episodeDuration ? `- 회당 길이: ${input.episodeDuration}` : "- 회당 길이: 미지정",
    input.sourceKind ? `- 원작 자료: ${input.sourceKind}` : "- 원작 자료: 사용자 입력·대화 요청",
    "",
    ...koreanProductionBrief(input),
    "",
    "## 원작 자료 요약",
    koreanSourceSummary(input.sourceText),
  ].join("\n");
}

export function buildKoreanScriptSystemPrompt(): string {
  return [
    "Produce the confirmed script artifact with the activated script-writing Skill. Write the script in Korean.",
    `The deliverable must include the exact Markdown headings ${KOREAN_SCRIPT_HEADINGS.map((heading) => `\`${heading}\``).join(", ")} in this order, followed by a complete performable Korean script rather than a proposal or outline.`,
    "Output Markdown. No process notes, no model self-narration, no \"Here is\" preamble.",
  ].join("\n");
}

export function buildKoreanScriptUserPrompt(input: ScriptCreationInput): string {
  return [
    "## Creation Spec",
    renderKoreanScriptSpec(input),
    "",
    "## Full Source Material",
    input.sourceText?.trim()
      || "The user did not provide full source material; write an extensible script draft strictly from the creation spec and user requirements.",
    "",
    "## Output Format",
    `# ${input.title}`,
    "",
    ...KOREAN_SCRIPT_HEADINGS.flatMap((heading) => [heading, ""]),
    "Use the target format defined by the activated Skill and confirmed spec.",
  ].join("\n");
}

/** Split the cast and location sections into a separate reference sheet for video tools. */
export function extractKoreanScriptReferences(title: string, script: string): string | undefined {
  const section = (heading: string) => {
    const lines = script.split(/\r?\n/u);
    const start = lines.findIndex((line) => line.trim() === heading);
    if (start < 0) return undefined;
    const end = lines.findIndex((line, index) => index > start && /^##\s/u.test(line.trim()));
    return lines.slice(start + 1, end < 0 ? undefined : end).join("\n").trim();
  };
  const cast = section("## 등장인물");
  const places = section("## 장소");
  if (!cast && !places) return undefined;
  return [`# ${title} 등장인물·장소 목록`, "", "## 등장인물", "", cast || "(대본에 없음)", "", "## 장소", "", places || "(대본에 없음)", ""].join("\n");
}
