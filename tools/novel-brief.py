#!/usr/bin/env python3
"""Author questions and next-chapter briefings for Korean InkOS works.

The agent asks the author only what is still undecided and shows a
next-chapter briefing before each chapter. Everything here is read from the
work's files (brief, design, state, hooks, volume map); nothing comes from the
agent's memory. A field the files do not have is printed as "없음".
Standard library only.

  novel-brief.py interview <brief.md> [--answer N=선택 ...] [--json]
      Before `book create`: questions for brief items that are missing or 미정.
      --answer records an answer (option number, or free text) into the brief.
  novel-brief.py interview --work <works/ID> [--answer N=선택 ...] [--json]
      After the design: questions for author choices the design left 미정,
      skipping what the brief or author_directions.md already answers.
  novel-brief.py next <works/ID> [--json]
      Briefing for the next chapter, ending with numbered choices.
  novel-brief.py direct <works/ID> (--choice K | --text TEXT | --plan) [-o FILE]
      Builds the chapter's --context text, appends it verbatim to
      source/story/author_directions.md and writes it to FILE (default:
      print). Pass the same FILE to `inkos write next --context-file FILE`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NONE = "없음"
DIRECTIONS = "author_directions.md"
DIRECTIONS_HEADER = (
    "# 작가 지시 기록\n\n"
    "작가가 고른 답과 회차별 지시를 그대로 남긴다. 회차 항목의 본문은 그 회차 "
    "`write next --context`로 넘긴 원문과 같다.\n"
)
DESIGN_SECTION = "설계 후 작가 선택"
FENCE = "~~~"

# Brief items asked before `book create`. Options are suggestions; "기타" is always free text.
BRIEF_ITEMS = [
    ("장르", ["라이트 무협 (light-martial)", "판타지 (fantasy)", "현대판타지 (modern-fantasy)"], 0, ""),
    ("서술 시점", ["3인칭 주인공 제한", "1인칭 주인공", "3인칭 다중 시점"], 0, "장르 관행, 정보 통제 쉬움"),
    ("주인공 장치", ["장치 없음 (토박이 주인공)", "회귀", "빙의·환생", "헌터·게이트"], 0,
     "회귀·빙의·헌터는 고를 수 있는 장치일 뿐 강제하지 않는다"),
    ("톤·수위", ["밝고 가벼움, 폭력은 결과 중심", "진지함, 폭력 묘사 절제", "어둡고 무거움, 수위 높음"], 0, ""),
    ("회차 수·회당 분량", ["30화 · 회당 3,000자", "50화 · 회당 3,000자", "100화 · 회당 4,000자"], 0, ""),
    ("금지 사항", ["따로 없음", "잔혹 묘사·성적 묘사 금지"], 1, ""),
    ("결말 방향", ["성장·성취 (해피엔딩)", "씁쓸한 승리", "열린 결말"], 0, ""),
]

# Design 미정 items: known names get options; the brief heading that may already answer them.
DESIGN_ITEMS = {
    "서술 인칭": (["3인칭 주인공 제한", "1인칭 주인공", "3인칭 다중 시점"], 0, "서술 시점"),
    "로맨스 비중": (["없음", "곁가지(감정선만)", "주요 줄기"], 1, None),
    "폭력 수위": (["결과 중심, 잔혹 묘사 없음", "절제된 묘사", "직접적 묘사"], 0, "톤·수위"),
    "연재 플랫폼": (["정하지 않음(범용)", "웹소설 플랫폼 연재", "개인 연재"], 0, None),
}
DESIGN_ALIASES = {"narrativePerson": "서술 인칭", "서술 시점": "서술 인칭", "폭력·연애 표현의 수위": "폭력 수위"}
# An item the design names but this table does not know still gets a number to answer with.
UNKNOWN_ITEM_OPTIONS = ["지금은 정하지 않는다(미정 유지)"]
PLAN_WORDS = {"심기", "심고", "진전", "회수", "예정"}


def die(message: str, code: int = 1):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def source_dir(work: str) -> Path:
    path = Path(work)
    for candidate in (path / "source", path):
        if (candidate / "story").is_dir():
            return candidate
    die(f"not a work folder (no source/story): {work}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def sections(markdown: str) -> dict[str, str]:
    """`## 제목` sections of a markdown file, body stripped."""
    found: dict[str, str] = {}
    current = None
    lines: list[str] = []
    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                found[current] = "\n".join(lines).strip()
            current, lines = match.group(1), []
        elif current is not None:
            lines.append(line)
    if current is not None:
        found[current] = "\n".join(lines).strip()
    return found


def decided(value: str | None) -> bool:
    return bool(value) and not value.strip().startswith("미정")


def question_block(number: int, title: str, options: list[str], recommended: int | None, why: str) -> str:
    lines = [f"[선택 {number}] {title}"]
    for index, option in enumerate(options, 1):
        note = ""
        if recommended is not None and index - 1 == recommended:
            note = f" (추천{': ' + why if why else ''})"
        lines.append(f"  {index}) {option}{note}")
    lines.append(" 기타) 직접 입력")
    return "\n".join(lines)


def resolve_answer(raw: str, options: list[str]) -> str:
    raw = raw.strip()
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1]
    if raw.startswith("기타:"):
        raw = raw[3:].strip()
    if not raw:
        die("empty answer")
    return raw


def parse_answers(values: list[str]) -> dict[int, str]:
    answers: dict[int, str] = {}
    for value in values:
        if "=" not in value:
            die(f"--answer needs N=선택: {value}")
        key, answer = value.split("=", 1)
        if not key.strip().isdigit():
            die(f"--answer needs a question number: {value}")
        answers[int(key)] = answer
    return answers


# ---------- interview (brief) ----------

def brief_questions(brief_text: str) -> list[dict]:
    found = sections(brief_text)
    questions = []
    for title, options, recommended, why in BRIEF_ITEMS:
        if decided(found.get(title)):
            continue
        questions.append({"title": title, "options": options, "recommended": recommended, "why": why})
    return questions


def set_section(markdown: str, title: str, body: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$\n?(.*?)(?=^##\s|\Z)", re.M | re.S)
    replacement = f"## {title}\n{body}\n\n"
    if pattern.search(markdown):
        return pattern.sub(lambda _m: replacement, markdown, count=1).rstrip() + "\n"
    if not markdown.strip():
        markdown = "# 작품 브리프\n\n"
    return markdown.rstrip() + "\n\n" + replacement.rstrip() + "\n"


def interview_brief(path: Path, answers: dict[int, str], as_json: bool) -> None:
    text = read_text(path)
    questions = brief_questions(text)
    if answers:
        for number, raw in sorted(answers.items()):
            if not 1 <= number <= len(questions):
                die(f"no question {number} (open questions: {len(questions)})")
            question = questions[number - 1]
            text = set_section(text, question["title"], resolve_answer(raw, question["options"]))
        path.write_text(text, encoding="utf-8")
        questions = brief_questions(text)
    emit(questions, as_json, path)


# ---------- interview (after design) ----------

def design_open_items(src: Path) -> list[str]:
    """Author choices the design marked 미정(작가 선택), in file order, without duplicates."""
    story = src / "story"
    items: list[str] = []
    for name in ("book_rules.md", "outline/story_frame.md", "author_intent.md"):
        for match in re.finditer(r"미정\s*\(작가 선택\)\s*[:：]\s*([^\n]+)", read_text(story / name)):
            body = re.split(r"[.。]", match.group(1))[0]
            for part in re.split(r"[,，、]", body):
                item = re.sub(r"\(.*?\)", "", part).strip()
                item = DESIGN_ALIASES.get(item, item)
                if item and item not in items:
                    items.append(item)
    return items


def design_answers(src: Path) -> dict[str, str]:
    body = sections(read_text(src / "story" / DIRECTIONS)).get(DESIGN_SECTION, "")
    answers = {}
    for line in body.splitlines():
        match = re.match(r"^-\s*(.+?):\s*(.+)$", line)
        if match:
            answers[match.group(1).strip()] = match.group(2).strip()
    return answers


def design_questions(src: Path) -> tuple[list[dict], list[str]]:
    brief = sections(read_text(src / "story" / "brief.md"))
    answered = design_answers(src)
    questions, settled = [], []
    for item in design_open_items(src):
        options, recommended, brief_key = DESIGN_ITEMS.get(item, (UNKNOWN_ITEM_OPTIONS, None, None))
        if item in answered:
            settled.append(f"{item}: {answered[item]} (작가 지시 기록)")
        elif brief_key and decided(brief.get(brief_key)):
            settled.append(f"{item}: {brief[brief_key].splitlines()[0]} (브리프 '{brief_key}')")
        else:
            questions.append({"title": item, "options": options, "recommended": recommended, "why": ""})
    return questions, settled


def append_design_answers(src: Path, entries: list[tuple[str, str]]) -> None:
    path = src / "story" / DIRECTIONS
    text = read_text(path) or DIRECTIONS_HEADER
    lines = "\n".join(f"- {title}: {answer}" for title, answer in entries)
    existing = sections(text).get(DESIGN_SECTION)
    if existing is None:
        text = text.rstrip() + f"\n\n## {DESIGN_SECTION}\n{lines}\n"
    else:
        text = set_section(text, DESIGN_SECTION, (existing + "\n" + lines).strip())
    path.write_text(text, encoding="utf-8")


def interview_work(src: Path, answers: dict[int, str], as_json: bool) -> None:
    questions, settled = design_questions(src)
    if answers:
        entries = []
        for number, raw in sorted(answers.items()):
            if not 1 <= number <= len(questions):
                die(f"no question {number} (open questions: {len(questions)})")
            question = questions[number - 1]
            entries.append((question["title"], resolve_answer(raw, question["options"])))
        append_design_answers(src, entries)
        questions, settled = design_questions(src)
    emit(questions, as_json, src / "story" / DIRECTIONS, settled)


def emit(questions: list[dict], as_json: bool, target: Path, settled: list[str] | None = None) -> None:
    if as_json:
        print(json.dumps({"questions": questions, "settled": settled or [], "file": str(target)}, ensure_ascii=False, indent=2))
        return
    for line in settled or []:
        print(f"정해짐: {line}")
    if not questions:
        print("물을 항목 없음")
        return
    print("\n\n".join(
        question_block(number, q["title"], q["options"], q["recommended"], q["why"])
        for number, q in enumerate(questions, 1)
    ))


# ---------- next-chapter briefing ----------

def next_chapter(src: Path) -> int:
    index = read_json(src / "chapters" / "index.json") or []
    return max([entry.get("number", 0) for entry in index] + [0]) + 1


def last_summary(src: Path, chapter: int) -> str:
    rows = (read_json(src / "story" / "state" / "chapter_summaries.json") or {}).get("rows", [])
    previous = [row for row in rows if row.get("chapter") == chapter - 1]
    if not previous:
        return NONE
    row = previous[-1]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", row.get("events", "")) if s.strip()]
    return f"{row.get('chapter')}화 「{row.get('title', '')}」 " + " ".join(sentences[:3])


def open_hooks(src: Path) -> list[dict]:
    hooks = (read_json(src / "story" / "state" / "hooks.json") or {}).get("hooks", [])
    active = [hook for hook in hooks if hook.get("status") in ("open", "progressing")]
    return sorted(active, key=lambda hook: (hook.get("lastAdvancedChapter", 0), hook.get("hookId", "")))


def planned_hooks(src: Path, chapter: int) -> list[tuple[dict, str]]:
    """Design-time (deferred) hooks whose notes plan something for this chapter ("1화", "1~2화"),
    each with the notes clause that names the chapter (not the payoff, so nothing is revealed early)."""
    hooks = (read_json(src / "story" / "state" / "hooks.json") or {}).get("hooks", [])
    planned = []
    for hook in hooks:
        if hook.get("status") != "deferred":
            continue
        for clause in re.split(r"[,，]\s*|[.。]\s+", hook.get("notes", "")):
            if any(int(m.group(1)) <= chapter <= int(m.group(2) or m.group(1))
                   for m in re.finditer(r"(?<![\d~])(\d+)(?:~(\d+))?화", clause)):
                planned.append((hook, clause.strip()))
                break
    return planned


def volume_beat(src: Path, chapter: int) -> str:
    for line in read_text(src / "story" / "outline" / "volume_map.md").splitlines():
        match = re.match(rf"^\s*{chapter}\.\s+(.+)$", line)
        if match:
            return match.group(1).strip()
    return NONE


def short(text: str, limit: int = 90) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def briefing(src: Path) -> dict:
    chapter = next_chapter(src)
    manifest = read_json(src / "story" / "state" / "manifest.json") or {}
    hooks = open_hooks(src)
    planned = planned_hooks(src, chapter)
    beat = volume_beat(src, chapter)
    choices = []
    if beat != NONE:
        choices.append({"label": f"계획대로 진행 — {beat}", "context": f"{chapter}화는 권 지도 계획대로 쓴다: {beat}"})
    lead = f"{chapter}화 계획에 더해 " if beat != NONE else f"{chapter}화에서 "
    candidates = [(hook, f"{hook['hookId']} 진전 — " + short(hook.get("expectedPayoff", "") or hook.get("notes", ""), 60),
                   f"{lead}복선 {hook['hookId']}({short(hook.get('expectedPayoff', '') or hook.get('notes', ''), 60)})를 한 걸음 진전시킨다. 회수는 하지 않는다.")
                  for hook in hooks]
    # A planned hook whose clause shares a word with the beat is already part of "계획대로 진행".
    candidates += [(hook, f"{hook['hookId']} 심기 — {clause}",
                    f"{lead}설계에 적힌 복선 {hook['hookId']}의 다음 계획을 장면으로 분명히 보인다: {clause}. 회수는 하지 않는다.")
                   for hook, clause in planned
                   if beat == NONE or not any(word in beat for word in set(re.findall(r"[가-힣]{2,}", clause)) - PLAN_WORDS)]
    for _hook, label, context in candidates[: (2 if beat != NONE else 3) if candidates else 0]:
        choices.append({"label": label, "context": context})
    return {
        "chapter": chapter,
        "lastAppliedChapter": manifest.get("lastAppliedChapter", NONE),
        "summary": last_summary(src, chapter),
        "hooks": [
            f"{hook['hookId']} ({hook.get('type', '')}, {hook.get('status')}, 최근 진전 {hook.get('lastAdvancedChapter', 0)}화) — "
            + short(hook.get("expectedPayoff", "") or hook.get("notes", ""))
            for hook in hooks
        ] or [NONE],
        "plannedHooks": [f"{hook['hookId']} ({hook.get('type', '')}) — {clause}" for hook, clause in planned] or [NONE],
        "beat": beat,
        "authorChoices": [f"{k}: {v}" for k, v in design_answers(src).items()] or [NONE],
        "choices": choices,
    }


def print_briefing(src: Path, as_json: bool) -> None:
    data = briefing(src)
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(f"[다음 화 브리핑] {data['chapter']}화")
    print(f"직전 화 요약: {data['summary']}")
    print(f"상태 마지막 반영: {data['lastAppliedChapter']}화" if data["lastAppliedChapter"] != NONE else f"상태 마지막 반영: {NONE}")
    print("이번 화에 다룰 만한 열린 복선:")
    for line in data["hooks"]:
        print(f"  - {line}")
    print("이 화에 심을 계획인 복선(설계):")
    for line in data["plannedHooks"]:
        print(f"  - {line}")
    print(f"권 지도상 다음 박자: {data['beat']}")
    print("정해진 작가 선택: " + "; ".join(data["authorChoices"]))
    print()
    options = [choice["label"] for choice in data["choices"]]
    print(question_block(1, f"{data['chapter']}화 전개", options, 0 if options else None, "").replace(" 기타) 직접 입력", " 기타) 직접 지시"))


# ---------- direct: build, record and write the --context text ----------

def context_text(src: Path, chapter: int, body: str) -> str:
    choices = design_answers(src)
    lines = [body.strip()]
    if choices:
        lines.append("작가가 정한 선택: " + "; ".join(f"{k} = {v}" for k, v in choices.items()) + ".")
    return "\n".join(lines) + "\n"


def record_direction(src: Path, chapter: int, mode: str, context: str) -> Path:
    path = src / "story" / DIRECTIONS
    text = read_text(path) or DIRECTIONS_HEADER
    if re.search(rf"^##\s+{chapter}화\s*$", text, re.M):
        die(f"{chapter}화 지시가 이미 기록돼 있다: {path}")
    text = text.rstrip() + f"\n\n## {chapter}화\n- 방식: {mode}\n{FENCE}\n{context}{FENCE}\n"
    path.write_text(text, encoding="utf-8")
    return path


def direct(src: Path, choice: int | None, text: str | None, plan: bool, output: str | None) -> None:
    data = briefing(src)
    chapter = data["chapter"]
    if text is not None:
        mode, body = "대화형(직접 지시)", text
    elif plan:
        if data["beat"] == NONE:
            mode, body = "일괄(계획대로)", f"{chapter}화는 저장된 설계와 상태를 따라 쓴다."
        else:
            mode, body = "일괄(계획대로)", data["choices"][0]["context"]
    else:
        if not 1 <= choice <= len(data["choices"]):
            die(f"no choice {choice} (choices: {len(data['choices'])})")
        mode, body = f"대화형(선택 {choice})", data["choices"][choice - 1]["context"]
    context = context_text(src, chapter, body)
    path = record_direction(src, chapter, mode, context)
    if output:
        Path(output).write_text(context, encoding="utf-8")
        print(f"{chapter}화 지시 기록: {path}")
        print(f"--context-file: {output}")
    else:
        sys.stdout.write(context)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("interview"); p.add_argument("brief", nargs="?"); p.add_argument("--work")
    p.add_argument("--answer", action="append", default=[]); p.add_argument("--json", action="store_true")
    p = sub.add_parser("next"); p.add_argument("work"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("direct"); p.add_argument("work")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--choice", type=int); group.add_argument("--text"); group.add_argument("--plan", action="store_true")
    p.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    if args.command == "interview":
        answers = parse_answers(args.answer)
        if args.work:
            interview_work(source_dir(args.work), answers, args.json)
        elif args.brief:
            interview_brief(Path(args.brief), answers, args.json)
        else:
            die("interview needs <brief.md> or --work <works/ID>")
    elif args.command == "next":
        print_briefing(source_dir(args.work), args.json)
    elif args.command == "direct":
        direct(source_dir(args.work), args.choice, args.text, args.plan, args.output)


if __name__ == "__main__":
    main()
