import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { ActivatedSkillGuidance, ActivatedSkillResource } from "../agent/skill-tool.js";
import type { WorkManifest } from "../harness/contracts.js";
import type { LLMMessage } from "../llm/provider.js";
import { loadAvailableAgentSkills } from "./builtin-loader.js";
import { readBookGenre, resolveKoreanGenre } from "./korean-genre-references.js";
import { koreanSkillsRoot } from "./korean-skill-root.js";

/**
 * Korean genre style skills chosen per work (a style preset), not per genre.
 * The light-murim comic style is attached only to a Korean light-martial work
 * whose story/korean_style_preset file says `light-murim-comic`. Each worker
 * receives fixed sections; the skill's references are never retrieved by
 * search, so no other piece of this skill can leak in.
 */
export const LIGHT_MURIM_SKILL_ID = "inkos-ko-light-murim";
export const LIGHT_MURIM_PRESET = "light-murim-comic";
export const KOREAN_STYLE_PRESET_FILE = "story/korean_style_preset";
/** Bytes this skill may add to the writer's prompt; above it the writer gets only what the memo chose. */
// 45KB in the stage-9 directive; 50KB by the user's decision (2026-10-27) after measuring the narrowed writer.
export const LIGHT_MURIM_WRITER_BYTE_LIMIT = 50 * 1024;

const COMBAT = "references/combat-patterns.md";
const SCENE = "references/scene-patterns.md";
const EXAMPLES = "references/examples.md";
// The writer's second call settles runtime state; writer.ts appends this fixed heading to it.
const SETTLEMENT_MARKER = "## Settlement baseline";

type Pick = "all" | ReadonlyArray<string>;
interface WorkerPlan { readonly skill: Pick; readonly files: Readonly<Record<string, Pick>> }

export const LIGHT_MURIM_WORKER_PLANS: Readonly<Record<string, WorkerPlan>> = {
  planner: { skill: "all", files: { [COMBAT]: ["고르기 표", "조합 예시"], [SCENE]: ["유형 목록"] } },
  writer: { skill: "all", files: { [COMBAT]: "all", [SCENE]: "all", [EXAMPLES]: "all" } },
  "continuity-auditor": { skill: ["금지", "검수 판정 기준", "다른 규칙과의 관계"], files: { [COMBAT]: ["흔한 실패"], [SCENE]: ["흔한 실패"] } },
  reviser: { skill: "all", files: { [COMBAT]: "all", [SCENE]: "all" } },
};

export const LIGHT_MURIM_SCENE_TYPES = ["일상", "분노", "허세", "수련", "회상", "화 끝 훅"] as const;
// Examples shared by every scene; the rest of examples.md is chosen with the memo's cards and scene types.
const COMMON_EXAMPLE_SECTIONS = ["서술 목소리", "리듬", "개그 문법", "온도 전환", "금지"];
// When the writer must be narrowed it drops what other workers use: the audit criteria and the
// auditor's list of engine-rule conflicts (auditor, reviser) and the selection summaries the
// planner already used to write the memo.
const WRITER_NARROW_SKIP = ["검수 판정 기준", "장면 유형 고르기", "전투 패턴 고르기"];
const AUDITOR_ONLY_SUBSECTION = "### 엔진 기본 규칙과 부딪히는 장치";

const PLANNER_INSTRUCTION = [
  "## 이번 작업에서 지킬 것 (planner, 라이트 무협 코믹 프리셋)",
  "chapter memo에 이번 회차의 장면 유형을 `장면 유형: 일상 → 화 끝 훅`처럼 한 줄로 적는다(일상, 분노, 허세, 수련, 회상, 화 끝 훅 가운데 쓰는 순서대로).",
  "전투가 있는 회차는 `전투 패턴: C? → C?` 한 줄도 적는다(예: `전투 패턴: C2 → C9`). 아래 고르기 표로 카드를 고르고 조합 순서대로 적는다. 전투가 없는 회차는 이 줄을 적지 않는다.",
].join("\n");

interface Section { readonly title: string; readonly start: number; readonly end: number }

/** Top-level (`## `) or card-level (`### `) sections of a markdown file, by heading text. */
export function markdownSections(body: string, level = 2): Section[] {
  const marker = `${"#".repeat(level)} `;
  const starts: Array<{ title: string; start: number }> = [];
  let offset = 0;
  for (const line of body.split("\n")) {
    if (line.startsWith(marker)) starts.push({ title: line.slice(marker.length).trim(), start: offset });
    else if (level === 3 && line.startsWith("## ")) starts.push({ title: "", start: offset });
    offset += line.length + 1;
  }
  return starts.map((item, i) => ({ title: item.title, start: item.start, end: starts[i + 1]?.start ?? body.length }))
    .filter((item) => item.title);
}

function matches(title: string, wanted: string): boolean {
  return title === wanted || title.startsWith(`${wanted} `) || title.startsWith(`${wanted}(`);
}

function pickResources(path: string, body: string, pick: Pick): ActivatedSkillResource[] {
  if (pick === "all") return [{ path, body, charStart: 0, charEnd: body.length }];
  return markdownSections(body).filter((section) => pick.some((wanted) => matches(section.title, wanted)))
    .map((section) => ({ path, heading: section.title, body: body.slice(section.start, section.end).trimEnd(), charStart: section.start, charEnd: section.end }));
}

function pickSkillBody(body: string, pick: Pick, skip: ReadonlyArray<string> = []): string {
  if (pick === "all" && skip.length === 0) return body;
  const sections = markdownSections(body);
  const intro = body.slice(0, sections[0]?.start ?? body.length).trimEnd();
  return [intro, ...sections.filter((section) => (pick === "all" || pick.some((wanted) => matches(section.title, wanted)))
    && !skip.some((wanted) => matches(section.title, wanted)))
    .map((section) => body.slice(section.start, section.end).trimEnd())].join("\n\n");
}

function userText(messages: ReadonlyArray<LLMMessage>): string {
  return messages.filter((message) => message.role === "user").map((message) => message.content).join("\n");
}

/** Combat card codes the planner put in the memo (`전투 패턴: C2 → C9`). */
export function memoCombatCards(messages: ReadonlyArray<LLMMessage>): string[] {
  const codes = new Set<string>();
  for (const line of userText(messages).match(/전투\s*패턴\s*[:：][^\n]*/gu) ?? []) {
    for (const code of line.match(/C(?:10|[1-9])(?![0-9])/g) ?? []) codes.add(code);
  }
  return [...codes];
}

/** Scene types the planner put in the memo (`장면 유형: 일상 → 화 끝 훅`), in the skill's order. */
export function memoSceneTypes(messages: ReadonlyArray<LLMMessage>): string[] {
  const lines = (userText(messages).match(/장면\s*유형\s*[:：][^\n]*/gu) ?? []).join("\n");
  return LIGHT_MURIM_SCENE_TYPES.filter((type) => lines.includes(type));
}

/** Remove one `### ` subsection (up to the next `### ` or `## ` heading). */
function dropSubsection(body: string, heading: string): string {
  const start = body.indexOf(`\n${heading}\n`);
  if (start < 0) return body;
  const rest = body.slice(start + 1);
  const next = rest.slice(heading.length).search(/\n#{2,3} /);
  return body.slice(0, start + 1) + (next < 0 ? "" : rest.slice(heading.length + next + 1));
}

/** Combat file narrowed to the memo's cards, or to the selection table when the memo names none. */
function narrowCombat(body: string, cards: ReadonlyArray<string>): ActivatedSkillResource[] {
  if (cards.length === 0) return pickResources(COMBAT, body, ["고르기 표"]);
  return markdownSections(body, 3).filter((section) => cards.some((code) => section.title.startsWith(`${code} `)))
    .map((section) => ({ path: COMBAT, heading: section.title, body: body.slice(section.start, section.end).trimEnd(), charStart: section.start, charEnd: section.end }));
}

export function guidanceBytes(activation: ActivatedSkillGuidance): number {
  return Buffer.byteLength(activation.skill.body, "utf8")
    + activation.resources.reduce((sum, resource) => sum + Buffer.byteLength(resource.body, "utf8"), 0);
}

export async function koreanStylePreset(projectRoot?: string, bookId?: string): Promise<string | undefined> {
  if (!projectRoot || !bookId || !/^[\p{L}\p{N}][\p{L}\p{N}._-]*$/u.test(bookId) || bookId.includes("..")) return undefined;
  for (const path of [join(projectRoot, "works", bookId, "source", KOREAN_STYLE_PRESET_FILE), join(projectRoot, "books", bookId, KOREAN_STYLE_PRESET_FILE)]) {
    try {
      return (await readFile(path, "utf8")).trim();
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  return undefined;
}

/**
 * Add the light-murim style skill for the workers that need it. Does nothing
 * unless the work is Korean, its genre resolves to light-martial and its
 * style preset is `light-murim-comic`; zh/en projects never load the skill.
 */
export async function attachKoreanGenreSkill(
  activations: ReadonlyArray<ActivatedSkillGuidance> | undefined,
  input: {
    readonly work: WorkManifest | null; readonly projectRoot?: string; readonly bookId?: string;
    readonly workerId: string; readonly messages: ReadonlyArray<LLMMessage>;
  },
): Promise<ReadonlyArray<ActivatedSkillGuidance> | undefined> {
  const plan = LIGHT_MURIM_WORKER_PLANS[input.workerId];
  if (!plan || !input.projectRoot) return activations;
  if (input.workerId === "writer" && input.messages.some((message) => message.content.includes(SETTLEMENT_MARKER))) return activations;
  if (input.work && input.work.language !== "ko") return activations;
  const bookId = input.work?.id ?? input.bookId;
  if (await koreanStylePreset(input.projectRoot, bookId) !== LIGHT_MURIM_PRESET) return activations;
  const genre = input.work?.metadata.genre ?? await readBookGenre(input.projectRoot, bookId);
  if (resolveKoreanGenre(genre) !== "light-martial") return activations;
  const skill = (await loadAvailableAgentSkills({ projectRoot: input.projectRoot })).skills
    .find((item) => item.id === LIGHT_MURIM_SKILL_ID && item.baseDir === join(koreanSkillsRoot(), LIGHT_MURIM_SKILL_ID));
  if (!skill?.baseDir) return activations;

  const read = (path: string) => readFile(join(skill.baseDir!, path), "utf8");
  const build = async (memo?: { readonly cards: ReadonlyArray<string>; readonly scenes: ReadonlyArray<string> }): Promise<ActivatedSkillGuidance> => {
    const resources: ActivatedSkillResource[] = [];
    for (const [path, pick] of Object.entries(plan.files)) {
      const body = await read(path);
      if (!memo) resources.push(...pickResources(path, body, pick));
      else if (path === COMBAT) resources.push(...narrowCombat(body, memo.cards));
      else if (path === SCENE) resources.push(...pickResources(path, body, ["유형 목록", ...memo.scenes]));
      else if (path === EXAMPLES) resources.push(...pickResources(path, body, [...COMMON_EXAMPLE_SECTIONS, ...memo.cards, ...memo.scenes]));
    }
    let body = pickSkillBody(skill.body, plan.skill, memo ? WRITER_NARROW_SKIP : []);
    if (memo) body = dropSubsection(body, AUDITOR_ONLY_SUBSECTION);
    if (input.workerId === "planner") body = `${PLANNER_INSTRUCTION}\n\n${body}`;
    return { skill: { ...skill, body }, resources };
  };
  let activation = await build();
  if (input.workerId === "writer" && guidanceBytes(activation) > LIGHT_MURIM_WRITER_BYTE_LIMIT) {
    activation = await build({ cards: memoCombatCards(input.messages), scenes: memoSceneTypes(input.messages) });
  }
  return [...(activations ?? []).filter((item) => item.skill.id !== LIGHT_MURIM_SKILL_ID), activation];
}
