import { describe, expect, it } from "vitest";
import { mkdtemp, mkdir, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadAvailableAgentSkills, loadBuiltinAgentSkills } from "../skills/builtin-loader.js";
import { createSkillRegistry } from "../skills/registry.js";
import { koreanSkillsRoot } from "../skills/korean-skill-root.js";
import { loadLinkedSkillResources } from "../agent/skill-tool.js";
import { prepareWorkerMessages } from "../agents/base.js";
import { createWorkManifest, saveWorkManifest } from "../harness/work-store.js";
import { KOREAN_GENRE_IDS, resolveKoreanGenre } from "../skills/korean-genre-references.js";

// Korean versions of upstream skills (same IDs) and Korean-only skills.
const KOREAN_SKILL_IDS = ["inkos-long-writing", "inkos-story-review", "inkos-story-deslop", "inkos-short-writing", "inkos-script-writing"];
const KOREAN_ONLY_SKILL_IDS = ["inkos-ko-explainer-script"];

async function projectWith(language: string | undefined) {
  const root = await mkdtemp(join(tmpdir(), "inkos-ko-skills-"));
  await writeFile(join(root, "inkos.json"), JSON.stringify(language ? { name: "t", language } : { name: "t" }));
  return root;
}

async function skillsFor(root: string) {
  const loaded = await loadAvailableAgentSkills({ projectRoot: root, env: {}, homeDir: join(root, "home") });
  expect(loaded.diagnostics).toEqual([]);
  return createSkillRegistry({ skills: loaded.skills });
}

describe("Korean skill layer", () => {
  it("ships exactly the Korean overrides with upstream IDs", async () => {
    const korean = await loadBuiltinAgentSkills(koreanSkillsRoot());
    expect(korean.diagnostics).toEqual([]);
    expect(korean.skills.map((skill) => skill.id).sort()).toEqual([...KOREAN_SKILL_IDS, ...KOREAN_ONLY_SKILL_IDS].sort());
    const builtinIds = new Set((await loadBuiltinAgentSkills()).skills.map((skill) => skill.id));
    for (const id of KOREAN_SKILL_IDS) expect(builtinIds.has(id), id).toBe(true);
    for (const id of KOREAN_ONLY_SKILL_IDS) expect(builtinIds.has(id), id).toBe(false);
    expect(await readdir(koreanSkillsRoot())).toEqual(expect.arrayContaining(KOREAN_SKILL_IDS));
  });

  it("keeps upstream skills for zh, en and unset projects", async () => {
    for (const language of ["zh", "en", undefined]) {
      const root = await projectWith(language);
      try {
        const registry = await skillsFor(root);
        for (const id of KOREAN_SKILL_IDS) {
          const skill = registry.getSkill(id)!;
          expect(skill.baseDir, `${language}:${id}`).not.toContain("skills-ko");
          expect(skill.body).not.toMatch(/[가-힣]/);
        }
      } finally { await rm(root, { recursive: true, force: true }); }
    }
  });

  it("uses Korean skills for a ko project while project skills still win", async () => {
    const root = await projectWith("ko");
    try {
      const registry = await skillsFor(root);
      for (const id of KOREAN_SKILL_IDS) {
        const skill = registry.getSkill(id)!;
        expect(skill.baseDir, id).toContain("skills-ko");
        expect(skill.source).toBe("builtin");
        expect(skill.body).toMatch(/[가-힣]/);
      }
      // Skills without a Korean version stay available from the built-ins.
      expect(registry.getSkill("inkos-storyboard")?.baseDir).not.toContain("skills-ko");
      expect(registry.getSkill("inkos-ko-explainer-script")?.baseDir).toContain("skills-ko");

      const override = join(root, "skills", "inkos-long-writing");
      await mkdir(override, { recursive: true });
      await writeFile(join(override, "SKILL.md"), "---\nname: inkos-long-writing\ndescription: project override\n---\nproject body\n");
      const overridden = (await skillsFor(root)).getSkill("inkos-long-writing")!;
      expect(overridden.source).toBe("project");
      expect(overridden.body).toBe("project body");
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("loads every linked Korean reference", async () => {
    const korean = await loadBuiltinAgentSkills(koreanSkillsRoot());
    const longWriting = korean.skills.find((skill) => skill.id === "inkos-long-writing")!;
    const linked = await loadLinkedSkillResources(longWriting);
    expect(linked.map((resource) => resource.path).sort()).toEqual([
      "references/foundation-design.md",
      "references/korean-prose.md",
      "references/reader-contract-and-progression.md",
      "references/scene-dialogue-and-length-budget.md",
      "references/state-projection.md",
    ]);
    for (const skill of korean.skills) {
      for (const resource of await loadLinkedSkillResources(skill)) expect(resource.body, `${skill.id}/${resource.path}`).toMatch(/[가-힣]/);
    }
  });

  it("puts the Korean method into a long-form worker prompt only for a ko project", async () => {
    for (const [language, korean] of [["ko", true], ["en", false]] as const) {
      const root = await projectWith(language);
      try {
        await saveWorkManifest(root, createWorkManifest({ id: "work", title: "work", profileId: "longform-novel", language }));
        const client = { defaults: { maxTokens: 4096 } } as unknown as Parameters<typeof prepareWorkerMessages>[0]["client"];
        const messages = await prepareWorkerMessages({ client, projectRoot: root, bookId: "work" }, [{ role: "user", content: "write the next chapter" }], 4096, "writer");
        const prompt = messages.map((message) => message.content).join("\n");
        expect(prompt.includes("# 한국어 장편 집필 방법"), language).toBe(korean);
        expect(prompt.includes("# 한국어 문장 기준"), language).toBe(korean);
        expect(prompt.includes("# Long-form narrative craft"), language).toBe(!korean);
      } finally { await rm(root, { recursive: true, force: true }); }
    }
  });

  it("adds the Korean review skill to ko chapter audits and revisions only", async () => {
    const client = { defaults: { maxTokens: 4096 } } as unknown as Parameters<typeof prepareWorkerMessages>[0]["client"];
    for (const [language, korean] of [["ko", true], ["en", false], ["zh", false]] as const) {
      const root = await projectWith(language);
      try {
        await saveWorkManifest(root, createWorkManifest({ id: "work", title: "work", profileId: "longform-novel", language }));
        for (const [worker, review] of [["continuity-auditor", korean], ["reviser", korean], ["writer", false], ["state-validator", false]] as const) {
          const messages = await prepareWorkerMessages({ client, projectRoot: root, bookId: "work" }, [{ role: "user", content: "audit chapter 3" }], 4096, worker);
          const prompt = messages.map((message) => message.content).join("\n");
          expect(prompt.includes("# 한국어 원고 검수"), `${language} ${worker}`).toBe(review);
          expect(prompt.includes("# 검수 기준표"), `${language} ${worker} matrix`).toBe(review);
          expect(prompt.includes("등급을 낮추지 않는다"), `${language} ${worker} severity`).toBe(review);
        }
      } finally { await rm(root, { recursive: true, force: true }); }
    }
  });

  it("gives Korean review criteria to ko script and explainer artifact reviews", async () => {
    const client = { defaults: { maxTokens: 4096 } } as unknown as Parameters<typeof prepareWorkerMessages>[0]["client"];
    const cases = [
      ["ko", "script", "artifact-method", ["# 한국어 원고 검수", "# 검수 기준표", "등급을 낮추지 않는다"], []],
      ["ko", "script", "writer", [], ["# 한국어 원고 검수"]],
      ["en", "script", "artifact-method", [], ["# 한국어 원고 검수", "등급을 낮추지 않는다"]],
      ["zh", "script", "artifact-method", [], ["# 한국어 원고 검수"]],
      ["ko", "explainer-script", "artifact-method", ["# 설명 영상 검수 질문", "등급을 낮추지 않는다", "인용은 해당 문장만"], ["# 한국어 원고 검수"]],
    ] as const;
    for (const [language, profileId, worker, present, absent] of cases) {
      const root = await projectWith(language);
      try {
        await saveWorkManifest(root, createWorkManifest({ id: "work", title: "work", profileId, language }));
        const messages = await prepareWorkerMessages({ client, projectRoot: root, bookId: "work" }, [{ role: "user", content: "review this artifact" }], 4096, worker);
        const prompt = messages.map((message) => message.content).join("\n");
        for (const text of present) expect(prompt.includes(text), `${language} ${profileId} ${worker} has ${text}`).toBe(true);
        for (const text of absent) expect(prompt.includes(text), `${language} ${profileId} ${worker} lacks ${text}`).toBe(false);
      } finally { await rm(root, { recursive: true, force: true }); }
    }
  });

  it("maps genre values and Korean names to genre references", () => {
    expect(resolveKoreanGenre("light-martial")).toBe("light-martial");
    expect(resolveKoreanGenre("무협")).toBe("light-martial");
    expect(resolveKoreanGenre("korean-martial")).toBe("light-martial");
    expect(resolveKoreanGenre("현대판타지")).toBe("modern-fantasy");
    expect(resolveKoreanGenre("Modern Fantasy")).toBe("modern-fantasy");
    expect(resolveKoreanGenre("판타지")).toBe("fantasy");
    expect(resolveKoreanGenre("xuanhuan")).toBeUndefined();
    expect(resolveKoreanGenre("other")).toBeUndefined();
  });

  it("attaches exactly the selected genre reference to Korean long-form workers", async () => {
    const titles: Record<string, string> = {
      "light-martial": "# 장르 기준: 한국 라이트 무협",
      "fantasy": "# 장르 기준: 판타지 (fantasy)",
      "modern-fantasy": "# 장르 기준: 현대판타지",
    };
    const prompts: Record<string, string> = {};
    for (const genre of [...KOREAN_GENRE_IDS, "other"]) {
      const root = await projectWith("ko");
      try {
        await saveWorkManifest(root, createWorkManifest({ id: "work", title: "work", profileId: "longform-novel", language: "ko", metadata: { genre } }));
        const client = { defaults: { maxTokens: 4096 } } as unknown as Parameters<typeof prepareWorkerMessages>[0]["client"];
        // The query mentions every genre so that lexical retrieval would pull all genre files if they were not filtered.
        const messages = await prepareWorkerMessages({ client, projectRoot: root, bookId: "work" }, [{ role: "user", content: "무협 판타지 현대판타지 마법 내공 게이트 등급 회차를 써라" }], 4096, "architect");
        prompts[genre] = messages.map((message) => message.content).join("\n");
      } finally { await rm(root, { recursive: true, force: true }); }
    }
    for (const genre of KOREAN_GENRE_IDS) {
      for (const [other, title] of Object.entries(titles)) expect(prompts[genre]!.includes(title), `${genre} has ${other}`).toBe(other === genre);
    }
    for (const title of Object.values(titles)) expect(prompts.other!.includes(title)).toBe(false);
  });

  it("does not attach Korean genre references to zh/en works", async () => {
    const root = await projectWith("en");
    try {
      await saveWorkManifest(root, createWorkManifest({ id: "work", title: "work", profileId: "longform-novel", language: "en", metadata: { genre: "fantasy" } }));
      const client = { defaults: { maxTokens: 4096 } } as unknown as Parameters<typeof prepareWorkerMessages>[0]["client"];
      const messages = await prepareWorkerMessages({ client, projectRoot: root, bookId: "work" }, [{ role: "user", content: "write" }], 4096, "architect");
      expect(messages.map((message) => message.content).join("\n")).not.toContain("장르 기준");
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("keeps protocol values from the upstream contract", async () => {
    const korean = await loadBuiltinAgentSkills(koreanSkillsRoot());
    const state = (await loadLinkedSkillResources(korean.skills.find((skill) => skill.id === "inkos-long-writing")!))
      .find((resource) => resource.path === "references/state-projection.md")!.body;
    for (const value of ["superseded", "lastAdvancedChapter", "immediate", "near-term", "mid-arc", "slow-burn", "endgame"]) expect(state).toContain(value);
    const review = (await loadLinkedSkillResources(korean.skills.find((skill) => skill.id === "inkos-story-review")!))[0]!.body;
    for (const value of ["`local`", "`structural`", "`unknown`"]) expect(review).toContain(value);
  });

  it("states that engine-normalized values are not state contradictions", async () => {
    const korean = await loadBuiltinAgentSkills(koreanSkillsRoot());
    const state = (await loadLinkedSkillResources(korean.skills.find((skill) => skill.id === "inkos-long-writing")!))
      .find((resource) => resource.path === "references/state-projection.md")!.body;
    expect(state).toContain("## 상태 검증의 판정 기준");
    for (const value of ["`startChapter`", "`reconciliationRequired: true`", "본문과 상태 사이의 사실 충돌만"]) expect(state).toContain(value);
    const review = (await loadLinkedSkillResources(korean.skills.find((skill) => skill.id === "inkos-story-review")!))[0]!.body;
    expect(review).toContain("상태 검증의 판정 기준");
  });

  it("asks Korean reviews to quote only the sentence that shows the issue", async () => {
    const korean = await loadBuiltinAgentSkills(koreanSkillsRoot());
    expect(korean.skills.find((skill) => skill.id === "inkos-story-review")!.body).toContain("인용은 해당 문장만");
  });
});
