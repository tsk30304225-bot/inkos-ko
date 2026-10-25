/**
 * Deterministic Korean prose checks (stage 3). They produce line-numbered
 * observations that the auditor may cite; they never score, reject or
 * rewrite a chapter (2.0 review contract). Line numbers match
 * numberReviewSource() for the same text.
 */
import { sourceLineBodies } from "./source-text.js";

export interface KoreanProseFinding {
  readonly code: "ending-repetition" | "opening-repetition" | "translationese" | "fatigue-word" | "cross-chapter-repetition";
  readonly summary: string;
  readonly lines: ReadonlyArray<number>;
}

export interface KoreanProseCheckOptions {
  /** Work-specific fatigue words (e.g. from story/korean_fatigue_words.md). */
  readonly fatigueWords?: ReadonlyArray<string>;
  /** Earlier chapters to compare for repeated phrases. */
  readonly previousChapters?: ReadonlyArray<{ readonly number: number; readonly text: string }>;
}

const ENDING_RUN = 4;
const OPENING_RUN = 3;
const PHRASE_WORDS = 5;
const MAX_PER_CODE = 6;

const TRANSLATIONESE: ReadonlyArray<{ readonly pattern: RegExp; readonly label: string }> = [
  { pattern: /[는은ㄴ] 것이었다/u, label: "`~는 것이었다`(설명조)" },
  { pattern: /되어(?:지|졌|진|져)/u, label: "`되어지다`(이중 피동)" },
  { pattern: /에 의해(?:서)?\s/u, label: "`~에 의해`(피동 번역투)" },
  { pattern: /에 있어(?:서)?\s/u, label: "`~에 있어서`" },
  { pattern: /(?:시간|회의|대화|만남|휴식|관계|자리)[을를] 가(?:지|졌|진|져|질)/u, label: "`~을 가지다`(have 직역)" },
  { pattern: /(?:함|임)에도 불구하고/u, label: "`~함에도 불구하고`" },
  { pattern: /임에 틀림(?:이)? 없/u, label: "`~임에 틀림없다`" },
  { pattern: /가장 \S+ \S*\s?중 하나/u, label: "`가장 ~한 ~ 중 하나`" },
];

const isDialogue = (line: string) => /^\s*["“'‘「『(]/u.test(line);
const words = (text: string) => text.normalize("NFC").replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/u).filter(Boolean);

interface Sentence { readonly line: number; readonly text: string }

function narrationSentences(lines: ReadonlyArray<string>): Sentence[] {
  const out: Sentence[] = [];
  lines.forEach((raw, index) => {
    const line = raw.trim();
    if (!line || line.startsWith("#") || isDialogue(line)) return;
    for (const sentence of line.split(/(?<=[.!?…])\s+/u)) {
      const text = sentence.trim();
      if (/[가-힣]/u.test(text)) out.push({ line: index + 1, text });
    }
  });
  return out;
}

function endingKey(sentence: string): string | undefined {
  const last = words(sentence).at(-1);
  if (!last) return undefined;
  const syllables = Array.from(last).filter((char) => /[가-힣]/u.test(char));
  return syllables.length >= 2 ? syllables.slice(-2).join("") : undefined;
}

function runs<T>(items: ReadonlyArray<T>, key: (item: T) => string | undefined, min: number): T[][] {
  const result: T[][] = [];
  let current: T[] = [];
  let currentKey: string | undefined;
  const flush = () => { if (current.length >= min) result.push(current); };
  for (const item of items) {
    const k = key(item);
    if (k !== undefined && k === currentKey) { current.push(item); continue; }
    flush();
    current = k === undefined ? [] : [item];
    currentKey = k;
  }
  flush();
  return result;
}

const uniqueLines = (sentences: ReadonlyArray<Sentence>) => [...new Set(sentences.map((sentence) => sentence.line))];

export function checkKoreanProse(text: string, options: KoreanProseCheckOptions = {}): KoreanProseFinding[] {
  const lines = sourceLineBodies(text);
  const sentences = narrationSentences(lines);
  const findings: KoreanProseFinding[] = [];

  for (const run of runs(sentences, (sentence) => endingKey(sentence.text), ENDING_RUN).slice(0, MAX_PER_CODE)) {
    findings.push({ code: "ending-repetition", summary: `서술 문장 ${run.length}개가 연달아 \`~${endingKey(run[0]!.text)}\`로 끝납니다.`, lines: uniqueLines(run) });
  }
  for (const run of runs(sentences, (sentence) => words(sentence.text)[0], OPENING_RUN).slice(0, MAX_PER_CODE)) {
    findings.push({ code: "opening-repetition", summary: `서술 문장 ${run.length}개가 연달아 \`${words(run[0]!.text)[0]}\`(으)로 시작합니다.`, lines: uniqueLines(run) });
  }

  for (const { pattern, label } of TRANSLATIONESE) {
    const hits = lines.flatMap((line, index) => pattern.test(line) ? [index + 1] : []);
    if (hits.length) findings.push({ code: "translationese", summary: `번역투 후보 ${label}: ${hits.length}곳.`, lines: hits.slice(0, MAX_PER_CODE * 2) });
  }
  const pronounLines = lines.flatMap((line, index) => /그녀/u.test(line) ? [index + 1] : []);
  const pronounCount = lines.reduce((sum, line) => sum + (line.match(/그녀/gu)?.length ?? 0), 0);
  if (pronounCount >= 5) findings.push({ code: "translationese", summary: `\`그녀\`가 ${pronounCount}번 쓰였습니다. 이름·호칭·주어 생략으로 바꿀 수 있는지 보세요.`, lines: pronounLines.slice(0, MAX_PER_CODE * 2) });

  for (const word of options.fatigueWords ?? []) {
    const target = word.normalize("NFC").trim();
    if (!target) continue;
    const count = lines.reduce((sum, line) => sum + line.normalize("NFC").split(target).length - 1, 0);
    if (count >= 2) {
      findings.push({ code: "fatigue-word", summary: `작품의 피로어 \`${target}\`가 ${count}번 쓰였습니다.`, lines: lines.flatMap((line, index) => line.normalize("NFC").includes(target) ? [index + 1] : []).slice(0, MAX_PER_CODE * 2) });
    }
  }

  const previous = new Map<string, number>();
  for (const chapter of options.previousChapters ?? []) {
    const tokens = words(chapter.text);
    for (let i = 0; i + PHRASE_WORDS <= tokens.length; i += 1) previous.set(tokens.slice(i, i + PHRASE_WORDS).join(" "), chapter.number);
  }
  if (previous.size) {
    const seen = new Set<string>();
    let reported = 0;
    lines.forEach((line, index) => {
      if (reported >= MAX_PER_CODE) return;
      const tokens = words(line);
      for (let i = 0; i + PHRASE_WORDS <= tokens.length; i += 1) {
        const phrase = tokens.slice(i, i + PHRASE_WORDS).join(" ");
        const from = previous.get(phrase);
        if (from === undefined || seen.has(phrase) || !/[가-힣]/u.test(phrase)) continue;
        seen.add(phrase);
        findings.push({ code: "cross-chapter-repetition", summary: `\`${phrase}\` 구절이 ${from}화에도 똑같이 나옵니다.`, lines: [index + 1] });
        reported += 1;
        break;
      }
    });
  }
  return findings;
}

/** Prompt block for the auditor. Empty when there is nothing to report. */
export function renderKoreanProseFindings(findings: ReadonlyArray<KoreanProseFinding>, sourceId: string): string {
  if (!findings.length) return "";
  return [
    "## 한국어 문장 점검 (host가 계산한 결정론적 관찰)",
    `아래는 \`${sourceId}\`의 번호 매긴 줄을 기준으로 한 기계적 점검 결과다. 자동 실패 기준이 아니다.`,
    "실제로 읽기를 방해하거나 작품 문체와 맞지 않는 것만 관찰로 남기고, 그때는 해당 줄을 sourceRefs로 인용한다. 작가가 의도한 문체(반복의 리듬, 사극 말투 등)라면 남기지 않는다.",
    "",
    ...findings.map((finding) => `- \`${finding.code}\` ${finding.summary} (줄 ${finding.lines.join(", ")})`),
  ].join("\n");
}
