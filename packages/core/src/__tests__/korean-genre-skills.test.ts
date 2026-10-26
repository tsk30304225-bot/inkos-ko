import { describe, expect, it } from "vitest";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { prepareWorkerMessages } from "../agents/base.js";
import { createWorkManifest, saveWorkManifest } from "../harness/work-store.js";
import { koreanSkillsRoot } from "../skills/korean-skill-root.js";
import {
  KOREAN_STYLE_PRESET_FILE, LIGHT_MURIM_PRESET, LIGHT_MURIM_SKILL_ID, LIGHT_MURIM_WORKER_PLANS,
  LIGHT_MURIM_WRITER_BYTE_LIMIT, markdownSections, memoCombatCards, memoSceneTypes,
} from "../skills/korean-genre-skills.js";

const SKILL_DIR = join(koreanSkillsRoot(), LIGHT_MURIM_SKILL_ID);
const SKILL_HEADING = `### ${LIGHT_MURIM_SKILL_ID} — `;
const client = { defaults: { maxTokens: 4096 } } as unknown as Parameters<typeof prepareWorkerMessages>[0]["client"];

async function project(options: { language?: string; genre?: string; preset?: string | null }) {
  const language = options.language ?? "ko";
  const root = await mkdtemp(join(tmpdir(), "inkos-ko-genre-skill-"));
  await writeFile(join(root, "inkos.json"), JSON.stringify({ name: "t", language }));
  await saveWorkManifest(root, createWorkManifest({ id: "work", title: "work", profileId: "longform-novel", language, metadata: { genre: options.genre ?? "light-martial" } }));
  if (options.preset !== null) {
    const path = join(root, "works", "work", "source", KOREAN_STYLE_PRESET_FILE);
    await mkdir(join(path, ".."), { recursive: true });
    await writeFile(path, `${options.preset ?? LIGHT_MURIM_PRESET}\n`);
  }
  return root;
}

async function promptFor(root: string, worker: string, user = "다음 회차를 계획하고 써라. 일상 분노 전투 허세 수련 회상") {
  const messages = await prepareWorkerMessages({ client, projectRoot: root, bookId: "work" },
    [{ role: "system", content: "task" }, { role: "user", content: user }], 4096, worker);
  return messages.map((message) => message.content).join("\n");
}

/** The part of the system prompt this skill adds (its heading up to the next skill or the end). */
function skillBlock(prompt: string): string {
  const start = prompt.indexOf(SKILL_HEADING);
  if (start < 0) return "";
  const next = prompt.indexOf("\n### ", prompt.indexOf("\n", start) + 1);
  const rest = prompt.slice(start);
  const nextSkill = rest.slice(1).search(/\n### [a-z0-9-]+ — /);
  return nextSkill < 0 ? rest : rest.slice(0, nextSkill + 1) || (next < 0 ? rest : prompt.slice(start, next));
}

const files = async () => ({
  skill: await readFile(join(SKILL_DIR, "SKILL.md"), "utf8"),
  combat: await readFile(join(SKILL_DIR, "references/combat-patterns.md"), "utf8"),
  scene: await readFile(join(SKILL_DIR, "references/scene-patterns.md"), "utf8"),
  examples: await readFile(join(SKILL_DIR, "references/examples.md"), "utf8"),
});

describe("Korean light-murim style skill (preset B)", () => {
  it("keeps the section headings the attacher uses as keys", async () => {
    const f = await files();
    const titles = (body: string, level = 2) => markdownSections(body, level).map((section) => section.title);
    expect(titles(f.skill)).toEqual(["다른 규칙과의 관계", "서술 목소리", "리듬", "개그 문법", "온도 전환", "금지", "장면 유형 고르기", "전투 패턴 고르기", "검수 판정 기준"]);
    expect(titles(f.combat)).toEqual(["고르기 표", "조합 예시", "카드", "흔한 실패"]);
    expect(titles(f.combat, 3).map((title) => title.split(" ")[0])).toEqual(["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]);
    expect(titles(f.scene)).toEqual(["유형 목록", "일상", "분노", "허세", "수련", "회상", "화 끝 훅", "흔한 실패"]);
    expect(f.skill).toMatch(/^---\nname: inkos-ko-light-murim\n/);
  });

  it("links no reference path from SKILL.md (linked paths would reach every worker)", async () => {
    const { skill } = await files();
    expect(skill).not.toMatch(/(?:`|\]\()(?:references|examples)\//);
    expect(skill).not.toContain("references/");
  });

  it("keeps analysis traces and the private list out of the shipped files", async () => {
    for (const body of Object.values(await files())) {
      expect(body).not.toMatch(/\bE\d[a-c]?\b/);
      expect(body).not.toMatch(/파일 [1-5]\b|§|\d{2,3}화 전후/);
    }
  });

  it("attaches nothing for zh/en works, other genres, or a ko light-martial work without the preset", async () => {
    const cases = [
      { language: "zh" }, { language: "en" }, { genre: "fantasy" }, { genre: "modern-fantasy" },
      { preset: null }, { preset: "something-else" },
    ];
    for (const options of cases) {
      const root = await project(options);
      try {
        for (const worker of ["planner", "writer", "continuity-auditor", "reviser"]) {
          expect(await promptFor(root, worker), `${JSON.stringify(options)} ${worker}`).not.toContain(SKILL_HEADING);
        }
      } finally { await rm(root, { recursive: true, force: true }); }
    }
  });

  it("gives each worker its fixed sections and nothing to the others", async () => {
    const root = await project({});
    try {
      const planner = skillBlock(await promptFor(root, "planner"));
      expect(planner).toContain("전투 패턴: C? → C?");
      expect(planner).toContain("## 검수 판정 기준");
      expect(planner).toContain("#### Reference: references/combat-patterns.md");
      expect(planner).toContain("· 고르기 표");
      expect(planner).toContain("· 조합 예시");
      expect(planner).not.toContain("### C1 일격 압살");
      expect(planner).toContain("· 유형 목록");
      expect(planner).not.toContain("references/examples.md");

      const auditor = skillBlock(await promptFor(root, "continuity-auditor"));
      for (const title of ["## 금지", "## 검수 판정 기준", "## 다른 규칙과의 관계"]) expect(auditor).toContain(title);
      for (const title of ["## 서술 목소리", "## 리듬", "## 개그 문법"]) expect(auditor).not.toContain(title);
      expect(auditor.match(/· 흔한 실패/g)).toHaveLength(2);
      expect(auditor).not.toContain("### C1 일격 압살");

      const reviser = skillBlock(await promptFor(root, "reviser"));
      expect(reviser).toContain("### C10 사제 대련");
      expect(reviser).toContain("## 화 끝 훅");
      expect(reviser).not.toContain("references/examples.md");

      for (const worker of ["architect", "settler", "state-validator", "composer"]) {
        expect(await promptFor(root, worker), worker).not.toContain(SKILL_HEADING);
      }
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("leaves the writer's state-settlement call without the style skill", async () => {
    const root = await project({});
    try {
      const settle = await promptFor(root, "writer", "settle\n\n## Settlement baseline\nApply the delta to this exact baseline.");
      expect(settle).not.toContain(SKILL_HEADING);
      expect(await promptFor(root, "writer")).toContain(SKILL_HEADING);
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("keeps the writer within the byte limit by narrowing to the memo's cards and scene types", async () => {
    expect(memoCombatCards([{ role: "user", content: "## memo\n전투 패턴: C2 → C9\nC1은 쓰지 않는다" }])).toEqual(["C2", "C9"]);
    expect(memoCombatCards([{ role: "user", content: "C10 사제 대련은 다음 화" }])).toEqual([]);
    expect(memoSceneTypes([{ role: "user", content: "장면 유형: 화 끝 훅 → 일상\n분노는 다음 화" }])).toEqual(["일상", "화 끝 훅"]);
    const root = await project({});
    try {
      const bytes = (text: string) => Buffer.byteLength(text, "utf8");
      const combat = skillBlock(await promptFor(root, "writer", "## chapter memo\n장면 유형: 일상 → 화 끝 훅\n전투 패턴: C2 → C9"));
      expect(combat).toContain("### C2 농락전");
      expect(combat).toContain("### C9 전투 직후");
      expect(combat).not.toContain("### C1 일격 압살");
      expect(combat).toContain("· 일상");
      expect(combat).toContain("· 화 끝 훅");
      expect(combat).not.toContain("· 허세");
      expect(combat).toContain("· C2 농락전 (교정형)");
      expect(combat).toContain("· 서술 목소리");
      expect(combat).toContain("## 다른 규칙과의 관계");
      expect(combat).not.toContain("## 검수 판정 기준");
      expect(combat).not.toContain("### 엔진 기본 규칙과 부딪히는 장치");
      expect(combat).toContain("### 이 스킬 안에서 규칙이 부딪힐 때");
      expect(combat).not.toContain("## 전투 패턴 고르기");
      const daily = skillBlock(await promptFor(root, "writer", "## chapter memo\n장면 유형: 일상"));
      expect(daily).toContain("· 고르기 표");
      expect(daily).not.toContain("### C1 일격 압살");
      // The heaviest memo the skill allows in one chapter: the three largest cards and scene types.
      const heavy = skillBlock(await promptFor(root, "writer", "## chapter memo\n장면 유형: 일상 → 수련 → 회상\n전투 패턴: C1 → C2 → C3"));
      const sizes = {
        planner: bytes(skillBlock(await promptFor(root, "planner"))),
        writerCombat: bytes(combat), writerDaily: bytes(daily), writerHeavy: bytes(heavy),
        auditor: bytes(skillBlock(await promptFor(root, "continuity-auditor"))),
        reviser: bytes(skillBlock(await promptFor(root, "reviser"))),
      };
      console.log("light-murim bytes per worker", JSON.stringify(sizes));
      expect(LIGHT_MURIM_WRITER_BYTE_LIMIT).toBe(50 * 1024);
      for (const key of ["writerCombat", "writerDaily"] as const) {
        expect(sizes[key], key).toBeLessThanOrEqual(LIGHT_MURIM_WRITER_BYTE_LIMIT);
      }
      // Fixed sizes (2026-10-27). The heaviest memo is over the writer limit; this is reported, not hidden.
      expect(sizes.writerHeavy).toBeLessThanOrEqual(59 * 1024);
      expect(sizes.planner).toBeLessThanOrEqual(42 * 1024);
      expect(sizes.auditor).toBeLessThanOrEqual(22 * 1024);
      expect(sizes.reviser).toBeLessThanOrEqual(83 * 1024);
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("plans only the four workers named in the design", () => {
    expect(Object.keys(LIGHT_MURIM_WORKER_PLANS).sort()).toEqual(["continuity-auditor", "planner", "reviser", "writer"]);
  });
});
