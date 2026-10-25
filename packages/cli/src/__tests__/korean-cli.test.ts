import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseWritingLanguage } from "../language-options.js";
import { formatBookCreateCreated, formatChapterSyncChange, resolveCliLanguage } from "../localization.js";

// Exercise language validation and the persisted project contract, not LLM fixtures.
describe("Korean CLI language contract", () => {
  const originalHome = process.env.HOME;
  let directory: string;
  beforeEach(async () => {
    directory = await mkdtemp(join(tmpdir(), "inkos-ko-cli-"));
    process.env.HOME = directory;
  });
  afterEach(async () => {
    process.env.HOME = originalHome;
    await rm(directory, { recursive: true, force: true });
  });
  it("accepts Korean regional tags and preserves English/Chinese choices", () => {
    expect(parseWritingLanguage("ko")).toBe("ko");
    expect(parseWritingLanguage(" ko-KR ")).toBe("ko");
    expect(parseWritingLanguage("KO_kr")).toBe("ko");
    expect(parseWritingLanguage("en-US")).toBe("en");
    expect(parseWritingLanguage("zh-CN")).toBe("zh");
    expect(() => parseWritingLanguage("fr")).toThrow();
    expect(() => parseWritingLanguage("korean")).toThrow();
  });
  it("persists Korean as the default for a new project", async () => {
    const { initializeProjectDirectory } = await import("../project-bootstrap.js");
    await initializeProjectDirectory(directory);
    const config = JSON.parse(await readFile(join(directory, "inkos.json"), "utf8"));
    expect(config.language).toBe("ko");
  });
  it("keeps explicit English project language", async () => {
    const { initializeProjectDirectory } = await import("../project-bootstrap.js");
    await initializeProjectDirectory(directory, { language: "en" });
    const config = JSON.parse(await readFile(join(directory, "inkos.json"), "utf8"));
    expect(config.language).toBe("en");
  });
  it("uses Korean slash-command instructions without changing intent", async () => {
    const { resolveTuiAgentRoute } = await import("../tui/agent-input.js");
    const session = { sessionKind: "book" } as Parameters<typeof resolveTuiAgentRoute>[1];
    const write = resolveTuiAgentRoute("/write", session, "한글-작품", "ko");
    expect(write.requestedIntent).toBe("write_next");
    expect(write.userMessage).toBe("다음 회차를 집필해 주세요");
    expect(resolveTuiAgentRoute("/confirm", session, "한글-작품", "ko").localResponse).toBe("확인할 작업이 없습니다.");
  });
  it("uses Korean summaries and character units", () => {
    expect(resolveCliLanguage("ko", { LANG: "zh_CN.UTF-8" })).toBe("ko");
    expect(resolveCliLanguage(undefined, { LANG: "ko_KR.UTF-8" })).toBe("ko");
    expect(formatBookCreateCreated("ko", "한글-작품")).toContain("한글-작품");
    expect(formatBookCreateCreated("ko", "한글-작품")).toMatch(/[가-힣]/);
    expect(formatChapterSyncChange("ko", { number: 2, title: "새벽", previousWordCount: 2000, wordCount: 2100 }, "ko_chars")).toBe("  2화 새벽: 2000자 → 2100자");
  });
});
