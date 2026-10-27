import { describe, expect, it } from "vitest";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { ComposerAgent } from "../agents/composer.js";
import { createInitialRuntimeState } from "../state/runtime-state-store.js";

async function composeWithStoryFrame(language: "ko" | "zh" | "en", storyFrame: string) {
  const root = await mkdtemp(join(tmpdir(), `inkos-${language}-anchors-`));
  const bookDir = join(root, "works", "story", "source");
  await createInitialRuntimeState({ bookDir, language });
  await mkdir(join(bookDir, "story", "outline"), { recursive: true });
  await writeFile(join(bookDir, "story", "outline", "story_frame.md"), storyFrame);
  // No model is configured: with a large budget the composer keeps the complete corpus.
  const composer = new ComposerAgent({ client: { defaults: { maxTokens: 1024 } }, model: "unused", projectRoot: root } as never);
  const goal = "Continue.";
  const plan = { intent: { chapter: 1, goal }, memo: { chapter: 1, goal, body: goal, threadRefs: [] }, intentMarkdown: goal, runtimePath: "runtime/chapter-1.intent.md", plannerInputs: [] };
  const book = { id: "story", title: "Story", genre: "general", platform: "other" as const, status: "active" as const, targetChapters: 3, chapterWordCount: 1000, language, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
  try {
    const result = await composer.composeChapter({ book, bookDir, chapterNumber: 1, plan, contextBudget: { contextWindowTokens: 100000, reservedOutputTokens: 1000 } } as never);
    return result.contextPackage.selectedContext.filter((entry) => entry.source.startsWith("story/outline/story_frame.md#"));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

describe("outline section anchors", () => {
  it("keeps every Korean heading section of the story frame as its own source", async () => {
    const frame = "# 청운객잔 — 이야기 틀\n\n## 전제\n객잔은 중립지다.\n\n## 힘의 규칙\n문턱 안에서 칼을 뽑으면 채권을 잃는다.\n\n## 시점과 정보 공개\n막삼이 보고 들은 범위.\n";
    const entries = await composeWithStoryFrame("ko", frame);
    expect(entries.map((entry) => entry.source)).toEqual([
      "story/outline/story_frame.md#청운객잔-이야기-틀",
      "story/outline/story_frame.md#전제",
      "story/outline/story_frame.md#힘의-규칙",
      "story/outline/story_frame.md#시점과-정보-공개",
    ]);
    expect(entries.map((entry) => entry.excerpt).join("\n")).toContain("문턱 안에서 칼을 뽑으면 채권을 잃는다.");
  });

  it("leaves zh and en anchors unchanged", async () => {
    expect((await composeWithStoryFrame("en", "# Departure\nThe witness leaves.\n# Return\nThe witness returns.")).map((entry) => entry.source))
      .toEqual(["story/outline/story_frame.md#departure", "story/outline/story_frame.md#return"]);
    expect((await composeWithStoryFrame("zh", "# 离开\n证人离开。\n# 归来\n证人回来。")).map((entry) => entry.source))
      .toEqual(["story/outline/story_frame.md#离开", "story/outline/story_frame.md#归来"]);
  });
});
