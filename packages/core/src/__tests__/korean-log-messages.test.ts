import { describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { koreanLogMessage, withKoreanLogMessage } from "../utils/korean-log-messages.js";
import { pickByLanguage } from "../utils/korean-language.js";

const SOURCES = ["pipeline/runner.ts", "agents/writer.ts", "pipeline/chapter-state-recovery.ts", "pipeline/chapter-truth-validation.ts"];

/** zh texts of every logStage/logInfo/logWarn call, with interpolations replaced by 7. */
async function loggedZhTexts(): Promise<string[]> {
  const texts: string[] = [];
  for (const file of SOURCES) {
    const source = await readFile(join(import.meta.dirname, "..", file), "utf8");
    for (const call of source.matchAll(/(?:logStage|logInfo|logWarn\??\.?)\((?:\w+, )?\{\s*zh: ([`"])(.*?)\1/gs)) {
      texts.push(call[2]!.replace(/\$\{[^}]+\}/g, "7"));
    }
  }
  return texts;
}

describe("Korean pipeline log messages", () => {
  it("covers every progress and warning log of the chapter pipeline", async () => {
    const texts = await loggedZhTexts();
    expect(texts.length).toBeGreaterThanOrEqual(30);
    expect(texts.filter((zh) => koreanLogMessage({ zh }) === undefined)).toEqual([]);
  });

  it("renders the numbers into Korean text", () => {
    expect(koreanLogMessage({ zh: "撰写章节草稿" })).toBe("회차 초고 쓰기");
    expect(koreanLogMessage({ zh: "更新第3章索引与快照" })).toBe("3화 색인과 스냅샷 갱신");
    expect(koreanLogMessage({ zh: "阶段 2：状态结算（第2章，2880字）" })).toBe("2단계: 2화 상태 정산 (2880자)");
    expect(koreanLogMessage({ zh: "状态校验：第1章发现 2 条观察" })).toBe("상태 검증: 1화 의견 2건");
    expect(koreanLogMessage({ zh: "unknown" })).toBeUndefined();
  });

  it("leaves zh and en output unchanged", () => {
    const message = { zh: "修订第3章", en: "revising chapter 3" };
    const filled = withKoreanLogMessage(message);
    expect(pickByLanguage("zh", filled)).toBe("修订第3章");
    expect(pickByLanguage("en", filled)).toBe("revising chapter 3");
    expect(pickByLanguage("ko", filled)).toBe("3화 수정");
    expect(pickByLanguage("ko", withKoreanLogMessage({ zh: "unknown", en: "unknown en" }))).toBe("unknown en");
  });
});
