#!/usr/bin/env python3
"""Offline test of tools/novel-brief.py on a small fake work (no InkOS, no model)."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "novel-brief.py"
results = []


def check(name, condition, detail=""):
    results.append(bool(condition))
    print(("PASS " if condition else "FAIL ") + name + (f" — {detail}" if detail and not condition else ""))


def run(*args):
    return subprocess.run([sys.executable, "-I", str(TOOL), *args], capture_output=True, text=True)


tmp = Path(tempfile.mkdtemp(prefix="novel-brief-test-"))

# ---------- interview before book create ----------
brief = tmp / "brief.md"
r = run("interview", str(brief))
check("missing brief asks all seven items", r.returncode == 0 and r.stdout.count("[선택 ") == 7, r.stdout + r.stderr)
check("question format: numbered options, recommendation and free text",
      "[선택 2] 서술 시점\n  1) 3인칭 주인공 제한 (추천: 장르 관행, 정보 통제 쉬움)\n  2) 1인칭 주인공\n  3) 3인칭 다중 시점\n 기타) 직접 입력" in r.stdout, r.stdout)
check("the protagonist device is optional, not forced", "강제하지 않는다" in r.stdout and "장치 없음" in r.stdout)

r = run("interview", str(brief), "--answer", "1=1", "--answer", "2=기타:3인칭 주인공 제한, 가끔 악역 시점")
text = brief.read_text(encoding="utf-8")
check("--answer writes the chosen option and free text into the brief",
      "## 장르\n라이트 무협 (light-martial)" in text and "## 서술 시점\n3인칭 주인공 제한, 가끔 악역 시점" in text, text)
check("answered items are not asked again", r.stdout.count("[선택 ") == 5 and "장르" not in r.stdout.split("\n")[0], r.stdout)

brief.write_text(text.replace("## 서술 시점\n3인칭 주인공 제한, 가끔 악역 시점", "## 서술 시점\n미정"), encoding="utf-8")
r = run("interview", str(brief), "--json")
titles = [q["title"] for q in json.loads(r.stdout)["questions"]]
check("a section written as 미정 is still asked", titles[0] == "서술 시점" and "장르" not in titles, str(titles))
r = run("interview", str(brief), "--answer", "9=1")
check("an answer for a question that is not open fails", r.returncode != 0 and "no question 9" in r.stderr, r.stderr)

# ---------- a fake work ----------
work = tmp / "works" / "test-murim"
story = work / "source" / "story"
(story / "state").mkdir(parents=True)
(story / "outline").mkdir()
(work / "source" / "chapters").mkdir()
(story / "brief.md").write_text("# 작품 브리프\n\n## 장르\n라이트 무협\n\n## 서술 시점\n3인칭 주인공 제한\n", encoding="utf-8")
(story / "book_rules.md").write_text("- 미정(작가 선택): 서술 인칭, 로맨스 비중, 연재 플랫폼. 이 규칙은 확정하지 않는다.\n", encoding="utf-8")
(story / "outline" / "story_frame.md").write_text("- 미정(작가 선택): 서술 인칭(narrativePerson), 폭력 수위, 실존 지역 연결 여부.\n", encoding="utf-8")

r = run("next", str(work))
check("a work with no chapters, state or map prints 없음 for every field",
      "[다음 화 브리핑] 1화" in r.stdout and "직전 화 요약: 없음" in r.stdout and "  - 없음" in r.stdout
      and "권 지도상 다음 박자: 없음" in r.stdout and "정해진 작가 선택: 없음" in r.stdout, r.stdout + r.stderr)

r = run("interview", "--work", str(work), "--json")
data = json.loads(r.stdout)
titles = [q["title"] for q in data["questions"]]
check("design 미정 items are collected once, in file order", titles == ["로맨스 비중", "연재 플랫폼", "폭력 수위", "실존 지역 연결 여부"], str(titles))
check("an item without known options can still be answered by number",
      data["questions"][3]["options"] == ["지금은 정하지 않는다(미정 유지)"], str(data["questions"][3]))
check("an item the brief already answers is not asked again",
      any(s.startswith("서술 인칭: 3인칭 주인공 제한 (브리프 '서술 시점')") for s in data["settled"]), str(data["settled"]))

r = run("interview", "--work", str(work), "--answer", "1=2", "--answer", "3=1")
directions = (story / "author_directions.md").read_text(encoding="utf-8")
check("design answers are recorded in author_directions.md",
      "## 설계 후 작가 선택\n- 로맨스 비중: 곁가지(감정선만)\n- 폭력 수위: 결과 중심, 잔혹 묘사 없음" in directions, directions)
check("recorded design answers are not asked again", r.stdout.count("[선택 ") == 2 and "] 연재 플랫폼" in r.stdout and "] 로맨스" not in r.stdout
      and "정해짐: 로맨스 비중: 곁가지(감정선만) (작가 지시 기록)" in r.stdout, r.stdout)

# ---------- next-chapter briefing ----------
(work / "source" / "chapters" / "index.json").write_text(json.dumps([{"number": 1}, {"number": 2}]), encoding="utf-8")
(story / "state" / "manifest.json").write_text(json.dumps({"lastAppliedChapter": 2}), encoding="utf-8")
(story / "state" / "chapter_summaries.json").write_text(json.dumps({"rows": [
    {"chapter": 1, "title": "첫 칼", "events": "하나. 둘."},
    {"chapter": 2, "title": "굴대", "events": "첫 문장이다. 둘째 문장이다. 셋째 문장이다. 넷째 문장은 빠진다."},
]}, ensure_ascii=False), encoding="utf-8")
(story / "state" / "hooks.json").write_text(json.dumps({"hooks": [
    {"hookId": "H01", "type": "mystery", "status": "deferred", "lastAdvancedChapter": 0, "expectedPayoff": "잠든 씨앗"},
    {"hookId": "H02", "type": "secret", "status": "progressing", "lastAdvancedChapter": 2, "expectedPayoff": "맹세의 이유"},
    {"hookId": "hook", "type": "pressure", "status": "open", "lastAdvancedChapter": 1, "expectedPayoff": "상단의 재방문"},
    {"hookId": "H03", "type": "clue", "status": "resolved", "lastAdvancedChapter": 2, "expectedPayoff": "회수됨"},
    {"hookId": "H05", "type": "mystery", "status": "deferred", "lastAdvancedChapter": 0, "expectedPayoff": "범인이 밝혀진다",
     "notes": "계획만 있음. 심기 3화(낡은 쪽지), 진전 9화, 회수 13화 예정."},
    {"hookId": "H06", "type": "promise", "status": "deferred", "lastAdvancedChapter": 0, "expectedPayoff": "꿈을 이룬다",
     "notes": "3~4화 장터 싸움 장면에서 심는다. 회수 30화."},
]}, ensure_ascii=False), encoding="utf-8")
(story / "outline" / "volume_map.md").write_text("## 1권\n1. 첫 칼이 금 간다.\n2. 굴대를 고친다.\n3. 장터 싸움에서 손을 덴다.\n13. 다른 권.\n", encoding="utf-8")

r = run("next", str(work), "--json")
data = json.loads(r.stdout)
check("next chapter comes from the chapter index", data["chapter"] == 3, str(data["chapter"]))
check("the summary is the previous chapter's first three sentences",
      data["summary"] == "2화 「굴대」 첫 문장이다. 둘째 문장이다. 셋째 문장이다.", data["summary"])
check("only open/progressing hooks are listed, least recently advanced first",
      [line.split(" ")[0] for line in data["hooks"]] == ["hook", "H02"], str(data["hooks"]))
check("the beat is the volume-map line for that chapter number", data["beat"] == "장터 싸움에서 손을 덴다.", data["beat"])
check("author choices come from the recorded design answers",
      data["authorChoices"] == ["로맨스 비중: 곁가지(감정선만)", "폭력 수위: 결과 중심, 잔혹 묘사 없음"], str(data["authorChoices"]))
r = run("next", str(work))
check("the briefing ends with plan, hook choices and direct instruction",
      "[선택 1] 3화 전개\n  1) 계획대로 진행 — 장터 싸움에서 손을 덴다. (추천)\n  2) hook 진전 — 상단의 재방문\n  3) H02 진전 — 맹세의 이유\n 기타) 직접 지시" in r.stdout, r.stdout)

check("design hooks planned for this chapter are listed with their plan clause, not the payoff",
      data["plannedHooks"] == ["H05 (mystery) — 심기 3화(낡은 쪽지)", "H06 (promise) — 3~4화 장터 싸움 장면에서 심는다"], str(data["plannedHooks"]))
hooks_file = story / "state" / "hooks.json"
saved_hooks = hooks_file.read_text(encoding="utf-8")
hooks_file.write_text(json.dumps({"hooks": [h for h in json.loads(saved_hooks)["hooks"] if h["status"] == "deferred"]}, ensure_ascii=False), encoding="utf-8")
labels = [c["label"] for c in json.loads(run("next", str(work), "--json").stdout)["choices"]]
check("planned hooks become choices, except one the beat already covers",
      labels == ["계획대로 진행 — 장터 싸움에서 손을 덴다.", "H05 심기 — 심기 3화(낡은 쪽지)"], str(labels))
hooks_file.write_text(saved_hooks, encoding="utf-8")

# ---------- direct: the recorded text equals the --context file ----------
context_file = tmp / "ch3.txt"
r = run("direct", str(work), "--choice", "2", "-o", str(context_file))
context = context_file.read_text(encoding="utf-8")
directions = (story / "author_directions.md").read_text(encoding="utf-8")
block = re.search(r"## 3화\n- 방식: (.+)\n~~~\n(.*?)~~~\n", directions, re.S)
check("direct records the chapter with its mode", r.returncode == 0 and block and block.group(1) == "대화형(선택 2)", directions + r.stderr)
check("the recorded block is byte-identical to the --context file", block and block.group(2) == context, repr(context))
check("the context carries the choice and the standing author choices",
      context == "3화 계획에 더해 복선 hook(상단의 재방문)를 한 걸음 진전시킨다. 회수는 하지 않는다.\n"
                 "작가가 정한 선택: 로맨스 비중 = 곁가지(감정선만); 폭력 수위 = 결과 중심, 잔혹 묘사 없음.\n", repr(context))
r = run("direct", str(work), "--plan")
check("a chapter is recorded only once", r.returncode != 0 and "이미 기록" in r.stderr, r.stderr)

(work / "source" / "chapters" / "index.json").write_text(json.dumps([{"number": n} for n in (1, 2, 3)]), encoding="utf-8")
r = run("direct", str(work), "--plan")
check("--plan (batch) prints the context and records 일괄",
      r.stdout.startswith("4화는 저장된 설계와 상태를 따라 쓴다.") and "## 4화\n- 방식: 일괄(계획대로)" in (story / "author_directions.md").read_text(encoding="utf-8"), r.stdout)
(work / "source" / "chapters" / "index.json").write_text(json.dumps([{"number": n} for n in (1, 2, 3, 4)]), encoding="utf-8")
r = run("direct", str(work), "--text", "5화는 장터 대신 대장간 안에서만 진행한다.")
check("--text records the author's own words first",
      r.stdout.startswith("5화는 장터 대신 대장간 안에서만 진행한다.\n작가가 정한 선택:") and "- 방식: 대화형(직접 지시)" in (story / "author_directions.md").read_text(encoding="utf-8"), r.stdout)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
