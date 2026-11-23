# skill-ab

A/B test for agent skills. It runs the same coding task two times, with the
skill and without it, and a blind grader decides which result is better.

Use it to answer one question before you ship a `SKILL.md`: does this skill make
the agent write better code, or only more code?

## How it works

1. Each case is a task, a list of assertions, and optional starting files.
2. Arm `base` gets the task. Arm `with` gets the task and your skill.
3. Both results are copied to folders named `X` and `Y`. The grader does not know
   which is which.
4. The grader checks each assertion (it can run code) and names the better one.
5. The report shows pass counts, added lines per arm, and the winner.

A case has a `kind`. A `positive` case needs the skill. A `negative` case is a
plain task where the skill must stay out of the way: if the `with` arm grows
there, the report prints `BLOAT`.

## Use

Needs Python 3.9+ and the `claude` CLI, logged in. No other dependency.

```bash
python3 skill_ab.py run examples/lld --with path/to/SKILL.md
```

Options:

- `--base other/SKILL.md`: a skill that is active in both arms. Use it to test
  your skill beside another one.
- `--force`: always load the skill under test. Without it, the agent reads only
  the skill description and decides if it fits, so the test also covers the
  trigger.
- `--case name`: run one case. `--jobs 3`: cases in parallel. `--out runs`.
- `--seed`: changes which arm the grader sees as `X`.

A run that stops can start again with the same command: finished arms are kept.

## Write a case

```
cases/my-case/
  case.json
  fixture/        starting files, optional
```

```json
{
  "kind": "positive",
  "task": "The request, in the words a user would type.",
  "assertions": ["One checkable statement about the result", "Another one"]
}
```

Write assertions about the result, not about the skill. Write at least one
negative case for each skill.

`examples/lld` has four cases from the tests of
[lld-skills](https://github.com/malay44/lld-skills).

## Example report

A real run of two example cases against the `lld` skill, with no other skill active:

```
| case | kind | base pass | with pass | base +lines | with +lines | skills used | better |
|---|---|---|---|---|---|---|---|
| n3-memoize-cli | negative | 2/3 | 2/3 | 7 | 7 | none | tie |
| p3-ordered-rules | positive | 3/4 | 3/4 | 4 | 4 | lld | tie |

with: 0  base: 0  tie: 2  error: 0
```

Read it like this: the skill did not load on the plain task and did not make it
larger. On the task it is made for, it loaded and gave the same result as no
skill. Each case folder keeps `result.json` with the grader's evidence for every
failed assertion.

## Limits

- Each arm runs one time. Agent output varies, so one run is weak evidence. Run
  again with a new `--out` and compare.
- The grader is a model. Read `result.json` and the failed assertions before you
  trust a winner.
- The agent runs shell commands in the case folder with no sandbox. Run only
  cases and skills that you trust.
- Your own plugins and hooks are kept out of both arms with
  `--setting-sources project`. Change `--claude-args` if your setup differs.

## Check

```bash
python3 skill_ab.py selfcheck
```

MIT license.
