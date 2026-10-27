import { describe, expect, it, vi } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { checkKoreanProse, renderKoreanProseFindings } from "../utils/korean-prose-check.js";
import { parseFatigueWords } from "../agents/korean-audit-evidence.js";
import { ContinuityAuditor } from "../agents/continuity.js";
import { numberReviewSource } from "../models/observation.js";

const codes = (text: string, options = {}) => checkKoreanProse(text, options).map((finding) => finding.code);

describe("Korean prose checks", () => {
  it("finds a run of identical endings in narration only", () => {
    const text = "그는 문을 열었다. 바람이 불어왔다. 등불이 흔들렸다. 개가 짖었다.\n\n\"알았다.\" \"그랬다.\" \"맞았다.\" \"좋았다.\"";
    expect(codes(text)).not.toContain("ending-repetition");
    const repeated = "그는 웃고 말았다. 그녀도 울고 말았다.\n모두 지쳐 말았다. 결국 잠들고 말았다.";
    const finding = checkKoreanProse(repeated).find((item) => item.code === "ending-repetition")!;
    expect(finding.summary).toContain("`~았다`");
    expect(finding.lines).toEqual([1, 2]);
  });

  it("finds repeated sentence openings", () => {
    const finding = checkKoreanProse("그는 일어났다. 그는 창을 봤다. 그는 숨을 골랐다.").find((item) => item.code === "opening-repetition")!;
    expect(finding.summary).toContain("`그는`");
  });

  it("lists translationese candidates with the numbered source lines", () => {
    const text = "첫 줄.\n그것은 그가 하는 것이었다.\n문이 열려지고 결정이 되어졌다.\n그 일에 있어서 중요했다.\n둘은 대화를 가졌다.";
    const findings = checkKoreanProse(text).filter((finding) => finding.code === "translationese");
    expect(findings.map((finding) => finding.lines)).toEqual([[2], [3], [4], [5]]);
    expect(numberReviewSource(text).split("\n")[2]).toBe("3\t문이 열려지고 결정이 되어졌다.");
  });

  it("counts 그녀 and work fatigue words", () => {
    expect(codes("그녀는 웃었다. 그녀가 섰다. 그녀의 손. 그녀를 봤다. 그녀와 갔다.")).toContain("translationese");
    expect(parseFatigueWords("# 피로어\n- 순간\n* 미묘한\n\n")).toEqual(["순간", "미묘한"]);
    const finding = checkKoreanProse("그 순간 멈췄다.\n다음 순간 웃었다.", { fatigueWords: ["순간"] })[0]!;
    expect(finding).toEqual({ code: "fatigue-word", summary: "작품의 피로어 `순간`가 2번 쓰였습니다.", lines: [1, 2] });
  });

  it("finds phrases repeated from earlier chapters", () => {
    const finding = checkKoreanProse("새벽\n그는 차가운 칼날 끝을 바라보며 숨을 골랐다", {
      previousChapters: [{ number: 2, text: "어제도 그는 차가운 칼날 끝을 바라보며 웃었다" }],
    }).find((item) => item.code === "cross-chapter-repetition")!;
    expect(finding.summary).toContain("2화");
    expect(finding.lines).toEqual([2]);
  });

  it("stays silent on clean prose and renders nothing", () => {
    const clean = "민지는 문을 열었다. 바람이 들이쳤다.\n\"누구세요?\"\n대답 대신 발소리가 멀어졌다.";
    expect(checkKoreanProse(clean)).toEqual([]);
    expect(renderKoreanProseFindings([], "chapter-1")).toBe("");
  });
});

describe("Korean prose checks in the auditor prompt", () => {
  async function auditMessages(language: "ko" | "en") {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-audit-"));
    try {
      const bookDir = join(root, "book");
      await mkdir(join(bookDir, "chapters"), { recursive: true });
      await mkdir(join(bookDir, "story"), { recursive: true });
      await writeFile(join(bookDir, "story", "korean_fatigue_words.md"), "- 순간\n");
      await writeFile(join(bookDir, "chapters", "0001_시작.md"), "# 제1화 시작\n\n그는 차가운 칼날 끝을 바라보며 웃었다.\n");
      const auditor = new ContinuityAuditor({ client: { defaults: { maxTokens: 4096 } }, model: "m", projectRoot: root } as never);
      let captured: ReadonlyArray<{ role: string; content: string }> = [];
      vi.spyOn(auditor as unknown as { submitSourcedReview: (...args: unknown[]) => unknown }, "submitSourcedReview").mockImplementation(async (messages: unknown) => {
        captured = messages as typeof captured;
        return { result: { summary: "", observations: [] }, usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 } };
      });
      const chapter = "그 순간 멈췄다.\n그는 차가운 칼날 끝을 바라보며 숨을 골랐다.\n다음 순간 그 일에 있어서 망설였다.";
      await auditor.auditChapter(bookDir, chapter, 2, undefined, { language, contextPackage: { selectedContext: [] } as never });
      return captured;
    } finally { await rm(root, { recursive: true, force: true }); }
  }

  it("adds the deterministic block for ko and nothing for en", async () => {
    const ko = (await auditMessages("ko")).map((message) => message.content).join("\n");
    expect(ko).toContain("## 한국어 문장 점검");
    expect(ko).toContain("`fatigue-word` 작품의 피로어 `순간`가 2번 쓰였습니다. (줄 1, 3)");
    expect(ko).toContain("`cross-chapter-repetition`");
    expect(ko).toContain("`translationese` 번역투 후보 `~에 있어서`: 1곳. (줄 3)");
    const en = (await auditMessages("en")).map((message) => message.content).join("\n");
    expect(en).not.toContain("한국어 문장 점검");
  });
});
