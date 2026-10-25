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

const KOREAN_SKILL_IDS = ["inkos-long-writing", "inkos-story-review", "inkos-story-deslop", "inkos-short-writing"];

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
    expect(korean.skills.map((skill) => skill.id).sort()).toEqual([...KOREAN_SKILL_IDS].sort());
    const builtinIds = new Set((await loadBuiltinAgentSkills()).skills.map((skill) => skill.id));
    for (const id of KOREAN_SKILL_IDS) expect(builtinIds.has(id), id).toBe(true);
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
      expect(registry.getSkill("inkos-script-writing")?.baseDir).not.toContain("skills-ko");

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

  it("keeps protocol values from the upstream contract", async () => {
    const korean = await loadBuiltinAgentSkills(koreanSkillsRoot());
    const state = (await loadLinkedSkillResources(korean.skills.find((skill) => skill.id === "inkos-long-writing")!))
      .find((resource) => resource.path === "references/state-projection.md")!.body;
    for (const value of ["superseded", "lastAdvancedChapter", "immediate", "near-term", "mid-arc", "slow-burn", "endgame"]) expect(state).toContain(value);
    const review = (await loadLinkedSkillResources(korean.skills.find((skill) => skill.id === "inkos-story-review")!))[0]!.body;
    for (const value of ["`local`", "`structural`", "`unknown`"]) expect(review).toContain(value);
  });
});
