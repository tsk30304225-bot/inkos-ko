import { describe, expect, it } from "vitest";
import { access, mkdir, mkdtemp, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ArchitectAgent, type ArchitectOutput } from "../agents/architect.js";
import { StateManager } from "../state/manager.js";
import { readRoleCards } from "../utils/outline-paths.js";
import { roleTierDirectory } from "../utils/korean-language.js";

const output: ArchitectOutput = {
  storyFrame: "# 골격",
  volumeMap: "# 권 지도",
  roles: [
    { tier: "major", name: "단소매", content: "# 단소매\n고매원 막내." },
    { tier: "minor", name: "한도겸", content: "# 한도겸\n정검회 총관." },
  ],
  bookRules: "# 규칙",
  bookRulesData: { version: "2", prohibitions: [], enableFullCastTracking: false, allowedDeviations: [] },
  pendingHooks: "",
  initialHooks: [],
};

const exists = (path: string) => access(path).then(() => true, () => false);

describe("Korean role-card folders", () => {
  it("maps tiers to major/minor for ko and keeps upstream folders for zh/en", () => {
    expect(roleTierDirectory("ko", "major")).toBe("major");
    expect(roleTierDirectory("ko", "minor")).toBe("minor");
    expect(roleTierDirectory("en", "major")).toBe("主要角色");
    expect(roleTierDirectory("zh", "minor")).toBe("次要角色");
  });

  it("writes ko cards to roles/major and roles/minor, and zh/en cards to the upstream folders", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-roles-"));
    try {
      const architect = new ArchitectAgent({ client: { defaults: { maxTokens: 1024 } }, model: "m", projectRoot: root } as never);
      for (const [language, major, minor] of [["ko", "major", "minor"], ["en", "主要角色", "次要角色"], ["zh", "主要角色", "次要角色"]] as const) {
        const bookDir = join(root, language);
        await architect.writeFoundationFiles(bookDir, output, language);
        expect(await exists(join(bookDir, "story", "roles", major, "단소매.md")), language).toBe(true);
        expect(await exists(join(bookDir, "story", "roles", minor, "한도겸.md")), language).toBe(true);
        const cards = await readRoleCards(bookDir);
        expect(cards.map((card) => [card.tier, card.name]).sort()).toEqual([["major", "단소매"], ["minor", "한도겸"]]);
      }
      expect(await exists(join(root, "ko", "story", "roles", "主要角色"))).toBe(false);
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("clears older upstream-named ko cards when a foundation is revised", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-roles-revise-"));
    try {
      const bookDir = join(root, "book");
      await mkdir(join(bookDir, "story", "roles", "主要角色"), { recursive: true });
      await writeFile(join(bookDir, "story", "roles", "主要角色", "옛인물.md"), "# 옛인물\n");
      const architect = new ArchitectAgent({ client: { defaults: { maxTokens: 1024 } }, model: "m", projectRoot: root } as never);
      await architect.writeFoundationFiles(bookDir, output, "ko", "revise");
      expect(await readdir(join(bookDir, "story", "roles", "主要角色"))).toEqual([]);
      expect(await readdir(join(bookDir, "story", "roles", "major"))).toEqual(["단소매.md"]);
    } finally { await rm(root, { recursive: true, force: true }); }
  });

  it("creates the matching empty role folders for control documents", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-roles-control-"));
    try {
      const state = new StateManager(root);
      await state.ensureControlDocumentsAt(join(root, "ko"), "ko");
      await state.ensureControlDocumentsAt(join(root, "en"), "en");
      expect((await readdir(join(root, "ko", "story", "roles"))).sort()).toEqual(["major", "minor"]);
      expect((await readdir(join(root, "en", "story", "roles"))).sort()).toEqual(["主要角色", "次要角色"]);
    } finally { await rm(root, { recursive: true, force: true }); }
  });
});
