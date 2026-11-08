# Did it actually happen?

Swarm Alignment Hackathon 2026 (Apart Research), Track 4, Multi-Agent Oversight and Control.

When an agent in a pipeline says "done", the next agent acts on it. This repo measures how often a false "done" corrupts the final result, and which checker catches it before the next agent acts. Three scripted workers run a bookstore pipeline on a fake SQLite database, with planted false completion reports (skip, partial, wrong_side, fabricated). Six checkers are compared: trust, an exact code postcondition, and Jev (TypeSafe's System One model) reading the claim, the worker's own evidence, a monitor-computed database diff, or diff plus evidence.

Headline, 120 held-out seeds, 360 steps: with no check, 101 of 101 runs with a fault ended wrong. Jev reading only the claim had AUROC 0.50, reading the worker's evidence 0.67, reading a monitor-computed diff 0.94. At a threshold picked on pilot seeds, the diff checker caught 88.9% of faulty steps and blocked 0.5% of honest ones. It missed all 19 cases of wrong values that matched the claim, which only the code check caught. The preregistered threshold of 0.5 failed 4 of 5 hypotheses because Jev blocked most honest steps. Full report: `report/report.pdf`.

## Run it

```sh
export TYPESAFE_API_KEY=...            # Jev key
cd src
uv run --with typesafe-sdk python run.py --tag main_t05 --seeds 0-119
uv run --with typesafe-sdk python run.py --tag main_tpilot --seeds 0-119 --thresholds ../results/pilot_thresholds.json
cd .. && uv run --with matplotlib python src/analyze.py
```

Each config makes 1,440 Jev requests, about 940k input tokens, about $0.04 at $0.042 per million tokens.

## Files

| Path | What it is |
| --- | --- |
| `PREREG.md` | Hypotheses and seed split, written before any run, plus the post-pilot addendum written before the main run |
| `src/env.py` | Fake database, the three workers, planted faults, monitor diff, exact postconditions |
| `src/run.py` | Runs each checker over the seeds and logs every step and Jev answer |
| `src/analyze.py` | Metrics, bootstrap CIs, hypothesis scoring, figures |
| `results/` | Raw logs for the pilots and both main configurations, `summary.json` |
| `report/` | Report HTML, PDF and figures |

## Prior work

No code written before the sprint is used. The verify-the-handoff framing comes from the author's earlier WorldProof project, which shares no code with this repo.

All data is fake. MIT license.
