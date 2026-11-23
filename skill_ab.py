#!/usr/bin/env python3
"""skill-ab: A/B test an agent skill. Same task, with and without the skill, graded blind.

  python3 skill_ab.py run cases/ --with path/to/SKILL.md [--base other/SKILL.md] [--out runs]
  python3 skill_ab.py report runs

Needs the `claude` CLI on PATH. Standard library only.
"""
import argparse, difflib, hashlib, json, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ARMS = ("base", "with")
FINAL = "FINAL_MESSAGE.md"


def arm_prompt(task, base, extra, force):
    p = []
    if base:
        p.append("These skills are active. Read each file fully before you start and follow it:\n"
                 + "\n".join(f"- {s}" for s in base))
    if extra and force:
        p.append("Also read each of these skill files fully and follow it:\n" + "\n".join(f"- {s}" for s in extra))
    elif extra:
        p.append("These skills are also installed:\n" + "\n".join(f"- {s}" for s in extra)
                 + "\nFirst read ONLY the YAML frontmatter (the description) of each. Use a skill only if its "
                   "description fits the task: then read the whole file and follow it. If none fits, use none.")
    p.append(f"Work only in the current directory.\n\nTASK: {task}\n\nWhen done, write your final message "
             f"to the user to {FINAL} and, on its last line, `skills-used: <names or none>`.")
    return "\n\n".join(p)


def grade_prompt(task, assertions):
    lines = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(assertions))
    return f"""You grade two solutions to one coding task. Judge only the files.
Task given to both: {task}
Starting files, if any: ./start/   Solution X: ./X/   Solution Y: ./Y/
{FINAL} in each is the message the author sent to the user. Ignore its `skills-used:` line.

Grade every assertion for each solution, with evidence. Where running code can settle an assertion,
write a throwaway script in ./scratch/ and run it. Do not edit the solutions.
Assertions:
{lines}

Then name the better solution for an engineer who wants the smallest correct change that will not
hurt at the next change. A tie is allowed.

Your LAST output must be one JSON object and nothing after it:
{{"X": [{{"assertion": 1, "passed": true, "evidence": "..."}}], "Y": [...], "better": "X|Y|tie", "why": "..."}}"""


def claude(prompt, cwd, extra_args):
    cmd = ["claude", "-p", prompt, "--output-format", "json", *extra_args]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        out = {"is_error": True, "result": r.stdout + r.stderr}
    if r.returncode or out.get("is_error"):  # a dead CLI must not look like two failed solutions
        raise SystemExit(f"claude failed in {cwd}: {str(out.get('result'))[:300]}")
    return out.get("result", "")


def last_json(text):
    """Last balanced {...} in text that parses as JSON."""
    for start in reversed([m.start() for m in re.finditer(r"\{", text)]):
        depth = 0
        for i in range(start, len(text)):
            depth += (text[i] == "{") - (text[i] == "}")
            if depth == 0:
                try:
                    obj = json.loads(text[start:i + 1])
                    if "better" in obj:
                        return obj
                except json.JSONDecodeError:
                    pass
                break
    return None


def x_arm(case_name, seed):
    """Which arm the grader sees as X. Stable per (case, seed), unknown to the grader."""
    return ARMS[hashlib.sha256(f"{seed}:{case_name}".encode()).digest()[0] % 2]


def added_lines(start, work):
    """Lines added or changed against the starting files. Tests and the final message do not count."""
    n = 0
    for f in sorted(work.rglob("*")):
        rel = f.relative_to(work)
        if (not f.is_file() or f.name == FINAL or "test" in f.name.lower()
                or any(p.startswith((".", "__")) for p in rel.parts)):
            continue
        try:
            new = f.read_text().splitlines()
            old = (start / rel).read_text().splitlines() if (start / rel).is_file() else []
        except UnicodeDecodeError:
            continue
        n += sum(1 for l in difflib.ndiff(old, new) if l.startswith("+ ") and l[2:].strip())
    return n


def run_case(case_dir, out, a):
    spec = json.loads((case_dir / "case.json").read_text())
    start = case_dir / "fixture"
    cdir = out / case_dir.name
    for arm in ARMS:
        work = cdir / arm
        if (work / FINAL).exists():
            continue  # resume: this arm is done
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(start, work) if start.is_dir() else work.mkdir(parents=True)
        extra = a.with_ if arm == "with" else []
        log = claude(arm_prompt(spec["task"], a.base, extra, a.force), work, a.run_args)
        (cdir / f"{arm}.log").write_text(log)
    g = cdir / "_grade"
    shutil.rmtree(g, ignore_errors=True)
    xa = x_arm(case_dir.name, a.seed)
    ya = ARMS[1 - ARMS.index(xa)]
    for label, arm in (("X", xa), ("Y", ya)):
        shutil.copytree(cdir / arm, g / label)
    if start.is_dir():
        shutil.copytree(start, g / "start")
    (g / "scratch").mkdir()
    raw = claude(grade_prompt(spec["task"], spec["assertions"]), g, a.run_args)
    verdict = last_json(raw) or {"X": [], "Y": [], "better": "error", "why": raw[-500:]}
    arm_of = {"X": xa, "Y": ya, "tie": "tie", "error": "error"}
    result = {"case": case_dir.name, "kind": spec.get("kind", ""), "better": arm_of.get(verdict["better"], "error"),
              "why": verdict.get("why", ""), "total": len(spec["assertions"])}
    for label, arm in (("X", xa), ("Y", ya)):
        rows = verdict.get(label, [])
        final = (cdir / arm / FINAL).read_text() if (cdir / arm / FINAL).exists() else ""
        used = re.findall(r"skills-used:\s*(.*)", final)
        result[arm] = {"passed": sum(1 for r in rows if r.get("passed")),
                       "failed": [f'{r.get("assertion")}: {r.get("evidence", "")}' for r in rows if not r.get("passed")],
                       "added_lines": added_lines(start, cdir / arm), "skills_used": used[-1] if used else "?"}
    (cdir / "result.json").write_text(json.dumps(result, indent=2))
    print(f"{case_dir.name}: better={result['better']}", flush=True)
    return result


def report(out):
    rows = [json.loads(p.read_text()) for p in sorted(out.glob("*/result.json"))]
    t = ["| case | kind | base pass | with pass | base +lines | with +lines | skills used | better |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b, w = r["base"], r["with"]
        t.append(f"| {r['case']} | {r['kind']} | {b['passed']}/{r['total']} | {w['passed']}/{r['total']} | "
                 f"{b['added_lines']} | {w['added_lines']} | {w['skills_used']} | {r['better']} |")
    wins = {k: sum(1 for r in rows if r["better"] == k) for k in ("with", "base", "tie", "error")}
    t.append(f"\nwith: {wins['with']}  base: {wins['base']}  tie: {wins['tie']}  error: {wins['error']}")
    bloat = [r["case"] for r in rows if r["kind"] == "negative" and r["with"]["added_lines"] > 1.3 * r["base"]["added_lines"] + 2]
    if bloat:
        t.append(f"BLOAT on negative cases (skill made the plain task bigger): {', '.join(bloat)}")
    text = "\n".join(t)
    (out / "report.md").write_text(text + "\n")
    print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("cases", type=Path)
    r.add_argument("--with", dest="with_", action="append", default=[], required=True, help="skill under test (SKILL.md path); repeatable")
    r.add_argument("--base", action="append", default=[], help="skill active in both arms; repeatable")
    r.add_argument("--force", action="store_true", help="always load the skill under test (skip the trigger decision)")
    r.add_argument("--out", type=Path, default=Path("runs"))
    r.add_argument("--case", action="append", help="run only this case; repeatable")
    r.add_argument("--jobs", type=int, default=3)
    r.add_argument("--seed", default="0", help="changes which arm the grader sees as X")
    # setting-sources project: the user's own plugins and hooks must not leak into either arm.
    r.add_argument("--claude-args", dest="run_args", type=lambda s: s.split(),
                   default="--setting-sources project --permission-mode acceptEdits --allowedTools Bash Read Write Edit Glob Grep".split())
    p = sub.add_parser("report")
    p.add_argument("out", type=Path)
    a = ap.parse_args()
    if a.cmd == "run":
        a.base = [str(Path(s).resolve()) for s in a.base]
        a.with_ = [str(Path(s).resolve()) for s in a.with_]
        a.out = a.out.resolve()
        cases = [d for d in sorted(a.cases.iterdir()) if (d / "case.json").exists() and (not a.case or d.name in a.case)]
        with ThreadPoolExecutor(a.jobs) as ex:
            list(ex.map(lambda d: run_case(d.resolve(), a.out, a), cases))
        report(a.out)
    else:
        report(a.out)


def _selfcheck():
    assert last_json('noise {"a": 1} more {"X": [], "Y": [], "better": "tie", "why": "{x}"} tail')["better"] == "tie"
    assert last_json("no json") is None
    assert {x_arm(f"c{i}", "0") for i in range(40)} == set(ARMS)  # both orders occur
    assert x_arm("c1", "0") == x_arm("c1", "0")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        s, w = Path(d, "s"), Path(d, "w")
        s.mkdir(); w.mkdir()
        (s / "a.py").write_text("x = 1\n")
        (w / "a.py").write_text("x = 1\ny = 2\n\n")
        (w / "test_a.py").write_text("assert True\n")
        (w / FINAL).write_text("done\n")
        assert added_lines(s, w) == 1
    print("ok")


if __name__ == "__main__":
    _selfcheck() if sys.argv[1:] == ["selfcheck"] else main()
