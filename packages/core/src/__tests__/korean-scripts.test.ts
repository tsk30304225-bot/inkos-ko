import { describe, expect, it } from "vitest";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { renderScriptSpec } from "../agents/script-storyboard.js";
import { extractKoreanScriptReferences, koreanScriptTargetLabel } from "../agents/korean-script.js";
import { checkExplainerScript, explainerTargetRange } from "../utils/korean-explainer-check.js";
import { createBuiltInWorkProfileRegistry } from "../harness/builtin-profiles.js";
import { EXPLAINER_SCRIPT_PROFILE_ID } from "../harness/korean-profiles.js";

const row = (n: number, seconds: number, source = "없음") => `| ${n} | ${seconds} | ${n}번 장면 내레이션입니다. | ${n}번 화면 | 화풍: 수채화; 배경: 서울 | ${source} |`;
const explainer = (rows: string[], sources = ["- [1] 자료 — 기관, 2024"]) => [
  "# 시험 영상",
  "",
  "## 개요",
  "- 중심 질문: 왜?",
  "",
  "## 장면 목록",
  "",
  "| 장면 | 길이(초) | 내레이션 | 화면 | 레퍼런스 | 출처 |",
  "| --- | --- | --- | --- | --- | --- |",
  ...rows,
  "",
  "## 출처",
  ...sources,
].join("\n");

describe("Korean drama scripts", () => {
  it("renders a Korean spec with the vertical short-drama default and keeps zh/en specs", () => {
    const ko = renderScriptSpec({ title: "새벽 배달", language: "ko" });
    expect(ko).toContain("# 새벽 배달 대본 제작 명세");
    expect(ko).toContain("- 납품 형식: 세로형 숏드라마");
    expect(ko).not.toMatch(/[一-鿿]/u);
    expect(renderScriptSpec({ title: "Dawn", language: "en" })).toContain("- Deliverable: general script");
    expect(renderScriptSpec({ title: "黎明" })).toContain("- 交付类型：通用剧本");
    expect(koreanScriptTargetLabel("miniseries")).toBe("미니시리즈형 드라마 대본");
    expect(koreanScriptTargetLabel("웹드라마 8부작")).toBe("웹드라마 8부작");
  });

  it("extracts the cast and location sheet for video tools", () => {
    const script = "# 새벽 배달\n\n## 등장인물\n- 민지(28): 배달 기사\n\n## 장소\n- 편의점: 형광등\n\n## 대본\n\nS#1. 편의점 (새벽)\n";
    const sheet = extractKoreanScriptReferences("새벽 배달", script)!;
    expect(sheet).toContain("- 민지(28): 배달 기사");
    expect(sheet).toContain("- 편의점: 형광등");
    expect(sheet).not.toContain("S#1");
    expect(extractKoreanScriptReferences("x", "## 대본\n본문")).toBeUndefined();
  });
});

describe("Korean explainer scene-table check", () => {
  it("passes a complete long-form table", () => {
    const rows = Array.from({ length: 20 }, (_, i) => row(i + 1, 30, i === 3 ? "[1]" : "없음"));
    const result = checkExplainerScript(explainer(rows));
    expect(result.errors).toEqual([]);
    expect(result.ok).toBe(true);
    expect(result.sceneCount).toBe(20);
    expect(result.totalSeconds).toBe(600);
  });

  it("reports format problems without guessing", () => {
    const result = checkExplainerScript(explainer([row(1, 30), row(3, 0, "[2]"), "| 4 | 10 | 짧음 |"], []), "10분");
    const codes = result.errors.map((issue) => issue.code);
    expect(codes).toEqual(expect.arrayContaining(["seconds", "scene-order", "unknown-source", "cell-count", "total-length"]));
    expect(result.ok).toBe(false);
  });

  it("flags unsourced claims and dense narration as review observations", () => {
    const dense = `| 2 | 2 | ${"가".repeat(40)} | 화면 | 없음 | 확인 필요 |`;
    const result = checkExplainerScript(explainer([row(1, 40), dense], ["- [1] 쓰이지 않은 자료"]), "shorts");
    expect(result.errors).toEqual([]);
    expect(result.observations.map((issue) => issue.code).sort()).toEqual(["narration-dense", "narration-sparse", "source-needed", "unused-source"]);
  });

  it("flags narration that is too sparse for its duration", () => {
    const result = checkExplainerScript(explainer([`| 1 | 40 | 짧은 말 | 화면 | 없음 | 없음 |`]), "shorts");
    expect(result.observations.map((issue) => issue.code)).toEqual(["narration-sparse", "unused-source"]);
  });

  it("requires the headings and exact columns", () => {
    const result = checkExplainerScript("# 제목\n\n## 장면 목록\n\n| 번호 | 초 | 내레이션 | 화면 | 레퍼런스 | 출처 |\n| --- | --- | --- | --- | --- | --- |\n| 1 | 30 | a | b | c | 없음 |");
    expect(result.errors.map((issue) => issue.code)).toEqual(expect.arrayContaining(["missing-heading", "columns"]));
  });

  it("maps target lengths", () => {
    expect(explainerTargetRange()).toEqual({ minSeconds: 480, maxSeconds: 900 });
    expect(explainerTargetRange("쇼츠")).toEqual({ minSeconds: 15, maxSeconds: 60 });
    expect(explainerTargetRange("10분")).toEqual({ minSeconds: 510, maxSeconds: 690 });
    expect(explainerTargetRange("8~12분")).toEqual({ minSeconds: 480, maxSeconds: 720 });
  });
});

describe("Korean-only work profiles", () => {
  it("registers explainer-script only in ko projects", async () => {
    const root = await mkdtemp(join(tmpdir(), "inkos-ko-profile-"));
    try {
      expect(createBuiltInWorkProfileRegistry().get?.(EXPLAINER_SCRIPT_PROFILE_ID)).toBeUndefined();
      for (const language of ["zh", "en"]) {
        await writeFile(join(root, "inkos.json"), JSON.stringify({ language }));
        expect(() => createBuiltInWorkProfileRegistry(root).require(EXPLAINER_SCRIPT_PROFILE_ID)).toThrow();
      }
      await writeFile(join(root, "inkos.json"), JSON.stringify({ language: "ko" }));
      const profile = createBuiltInWorkProfileRegistry(root).require(EXPLAINER_SCRIPT_PROFILE_ID);
      expect(profile.requiredSkillIds).toEqual(["inkos-ko-explainer-script"]);
      expect(profile.capabilityIds).toContain(EXPLAINER_SCRIPT_PROFILE_ID);
    } finally { await rm(root, { recursive: true, force: true }); }
  });
});
