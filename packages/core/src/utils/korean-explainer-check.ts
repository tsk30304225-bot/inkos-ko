/**
 * Deterministic format check for Korean explainer-video scene tables
 * (skills-ko/inkos-ko-explainer-script/references/scene-table.md).
 * Results are observations for review and delivery; they never reject or
 * regenerate the script.
 */
export const EXPLAINER_COLUMNS = ["장면", "길이(초)", "내레이션", "화면", "레퍼런스", "출처"] as const;
export const EXPLAINER_REQUIRED_HEADINGS = ["## 개요", "## 장면 목록", "## 출처"] as const;

export interface ExplainerScene {
  readonly number: number;
  readonly seconds: number;
  readonly narration: string;
  readonly visual: string;
  readonly references: string;
  readonly sources: string;
}

export interface ExplainerCheckIssue {
  readonly code: string;
  readonly summary: string;
  readonly scene?: number;
}

export interface ExplainerCheckResult {
  readonly ok: boolean;
  readonly sceneCount: number;
  readonly totalSeconds: number;
  readonly target: { readonly minSeconds: number; readonly maxSeconds: number };
  readonly scenes: ReadonlyArray<ExplainerScene>;
  /** Blocking format problems: the table cannot be used as delivered. */
  readonly errors: ReadonlyArray<ExplainerCheckIssue>;
  /** Review observations that do not break the format (e.g. "확인 필요" sources, dense narration). */
  readonly observations: ReadonlyArray<ExplainerCheckIssue>;
}

/** Long-form default 8–15 min; "shorts" ≤ 60 s. A numeric target in seconds allows ±15%. */
export function explainerTargetRange(target?: string | number): { minSeconds: number; maxSeconds: number } {
  if (typeof target === "number" && target > 0) return { minSeconds: Math.floor(target * 0.85), maxSeconds: Math.ceil(target * 1.15) };
  const value = typeof target === "string" ? target.trim().toLowerCase() : "";
  if (/^(shorts?|쇼츠|숏츠)$/u.test(value)) return { minSeconds: 15, maxSeconds: 60 };
  const seconds = /^(\d+)\s*(?:s|초)$/u.exec(value);
  if (seconds) return explainerTargetRange(Number(seconds[1]));
  const minutes = /^(\d+)\s*(?:m|min|분)$/u.exec(value);
  if (minutes) return explainerTargetRange(Number(minutes[1]) * 60);
  const range = /^(\d+)\s*[-~]\s*(\d+)\s*(?:m|min|분)$/u.exec(value);
  if (range) return { minSeconds: Number(range[1]) * 60, maxSeconds: Number(range[2]) * 60 };
  return { minSeconds: 480, maxSeconds: 900 };
}

const countKo = (text: string) => Array.from(text.replace(/<br\s*\/?>/giu, "").normalize("NFC").replace(/\s+/gu, "")).length;

function splitRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/u, "").replace(/\|$/u, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function section(lines: ReadonlyArray<string>, heading: string): string[] | undefined {
  const start = lines.findIndex((line) => line.trim() === heading);
  if (start < 0) return undefined;
  const end = lines.findIndex((line, index) => index > start && /^##\s/u.test(line.trim()));
  return lines.slice(start + 1, end < 0 ? undefined : end);
}

export function checkExplainerScript(markdown: string, target?: string | number): ExplainerCheckResult {
  const lines = markdown.split(/\r?\n/u);
  const errors: ExplainerCheckIssue[] = [];
  const observations: ExplainerCheckIssue[] = [];
  const range = explainerTargetRange(target);

  if (!lines.some((line) => /^#\s+\S/u.test(line.trim()))) errors.push({ code: "missing-title", summary: "`# 제목` 줄이 없습니다." });
  for (const heading of EXPLAINER_REQUIRED_HEADINGS) {
    if (!lines.some((line) => line.trim() === heading)) errors.push({ code: "missing-heading", summary: `필수 제목 \`${heading}\`이 없습니다.` });
  }

  const tableLines = (section(lines, "## 장면 목록") ?? []).filter((line) => line.trim().startsWith("|"));
  const scenes: ExplainerScene[] = [];
  if (tableLines.length < 2) {
    errors.push({ code: "missing-table", summary: "`## 장면 목록` 아래에 장면 표가 없습니다." });
  } else {
    const header = splitRow(tableLines[0]!);
    if (header.join("|") !== EXPLAINER_COLUMNS.join("|")) {
      errors.push({ code: "columns", summary: `표의 열이 \`${EXPLAINER_COLUMNS.join(" | ")}\`와 다릅니다: \`${header.join(" | ")}\`` });
    }
    const body = tableLines.slice(1).filter((line) => !/^\|?\s*:?-{3,}/u.test(line.trim()));
    for (const [index, line] of body.entries()) {
      const cells = splitRow(line);
      if (cells.length !== EXPLAINER_COLUMNS.length) {
        errors.push({ code: "cell-count", summary: `${index + 1}번째 장면 행의 칸 수가 ${cells.length}개입니다(필요: ${EXPLAINER_COLUMNS.length}개). 칸 안의 \`|\` 문자를 확인하세요.` });
        continue;
      }
      const [numberCell, secondsCell, narration, visual, references, sources] = cells as [string, string, string, string, string, string];
      const number = /^\d+$/u.test(numberCell) ? Number(numberCell) : NaN;
      const seconds = /^\d+$/u.test(secondsCell) ? Number(secondsCell) : NaN;
      const sceneLabel = Number.isFinite(number) ? number : index + 1;
      if (!Number.isFinite(number)) errors.push({ code: "scene-number", summary: `장면 번호 \`${numberCell}\`가 정수가 아닙니다.`, scene: sceneLabel });
      if (!Number.isFinite(seconds) || seconds <= 0) errors.push({ code: "seconds", summary: `장면 ${sceneLabel}의 길이 \`${secondsCell}\`가 양의 정수(초)가 아닙니다.`, scene: sceneLabel });
      for (const [name, value] of [["내레이션", narration], ["화면", visual], ["레퍼런스", references], ["출처", sources]] as const) {
        if (!value) errors.push({ code: "empty-cell", summary: `장면 ${sceneLabel}의 \`${name}\` 칸이 비어 있습니다.`, scene: sceneLabel });
      }
      scenes.push({ number, seconds, narration, visual, references, sources });
    }
  }

  scenes.forEach((scene, index) => {
    if (Number.isFinite(scene.number) && scene.number !== index + 1) {
      errors.push({ code: "scene-order", summary: `장면 번호가 이어지지 않습니다: ${index + 1}번째 행이 ${scene.number}번입니다.`, scene: scene.number });
    }
  });

  const sourceLines = section(lines, "## 출처") ?? [];
  const listed = new Set([...sourceLines.join("\n").matchAll(/^\s*[-*]\s*\[(\d+)\]/gmu)].map((match) => Number(match[1])));
  const used = new Set<number>();
  for (const scene of scenes) {
    const label = Number.isFinite(scene.number) ? scene.number : undefined;
    const refs = [...scene.sources.matchAll(/\[(\d+)\]/gu)].map((match) => Number(match[1]));
    if (refs.length > 0) {
      for (const ref of refs) {
        used.add(ref);
        if (!listed.has(ref)) errors.push({ code: "unknown-source", summary: `장면 ${label}이 \`## 출처\`에 없는 [${ref}]를 가리킵니다.`, scene: label });
      }
    } else if (scene.sources === "확인 필요") {
      observations.push({ code: "source-needed", summary: `장면 ${label}의 사실 주장에 출처가 없습니다(확인 필요).`, scene: label });
    } else if (scene.sources && scene.sources !== "없음") {
      errors.push({ code: "source-format", summary: `장면 ${label}의 출처 \`${scene.sources}\`는 \`[번호]\`, \`없음\`, \`확인 필요\` 중 하나여야 합니다.`, scene: label });
    }
    if (scene.narration && Number.isFinite(scene.seconds) && scene.seconds > 0) {
      const rate = countKo(scene.narration) / scene.seconds;
      if (rate > 8) observations.push({ code: "narration-dense", summary: `장면 ${label}: 내레이션이 1초에 약 ${rate.toFixed(1)}자(공백 제외)로 빠릅니다(참고 범위 4~7자).`, scene: label });
      else if (rate < 3 && scene.seconds >= 10) observations.push({ code: "narration-sparse", summary: `장면 ${label}: 내레이션이 1초에 약 ${rate.toFixed(1)}자(공백 제외)로 길이에 비해 적습니다(참고 범위 4~7자). 화면만 머무는 의도라면 그대로 두세요.`, scene: label });
    }
  }
  for (const ref of listed) {
    if (!used.has(ref)) observations.push({ code: "unused-source", summary: `출처 [${ref}]가 어느 장면에도 쓰이지 않았습니다.` });
  }

  const totalSeconds = scenes.reduce((sum, scene) => sum + (Number.isFinite(scene.seconds) ? scene.seconds : 0), 0);
  if (scenes.length > 0 && (totalSeconds < range.minSeconds || totalSeconds > range.maxSeconds)) {
    errors.push({ code: "total-length", summary: `장면 길이 합계 ${totalSeconds}초가 목표 범위 ${range.minSeconds}~${range.maxSeconds}초를 벗어납니다.` });
  }

  return { ok: errors.length === 0, sceneCount: scenes.length, totalSeconds, target: range, scenes, errors, observations };
}

export function renderExplainerCheck(title: string, result: ExplainerCheckResult): string {
  const list = (items: ReadonlyArray<ExplainerCheckIssue>) => items.length ? items.map((item) => `- \`${item.code}\` ${item.summary}`) : ["- 없음"];
  return [
    `# ${title} 형식 검사`,
    "",
    `- 결과: ${result.ok ? "통과" : "형식 문제 있음"}`,
    `- 장면 수: ${result.sceneCount}`,
    `- 길이 합계: ${result.totalSeconds}초 (목표 ${result.target.minSeconds}~${result.target.maxSeconds}초)`,
    "",
    "## 형식 문제",
    ...list(result.errors),
    "",
    "## 검수 참고",
    ...list(result.observations),
    "",
    "이 검사는 표의 형식만 확인합니다. 사실 주장과 출처가 맞는지는 검수에서 확인해야 합니다.",
    "",
  ].join("\n");
}
