# Did it actually happen?

Swarm Alignment Hackathon 2026 (Apart Research), Track 4, Multi-Agent Oversight and Control.

When an agent in a pipeline says "done", the next agent acts on it. This repo measures how often a false "done" corrupts the final result, and which checker catches it before the next agent acts. Three scripted workers run a bookstore pipeline on a fake SQLite database, with planted false completion reports (skip, partial, wrong_side, fabricated). Six checkers are compared: trust, an exact code postcondition, and Jev (TypeSafe's System One model) reading the claim, the worker's own evidence, a monitor-computed database diff, or diff plus evidence.

Headline, three preregistered experiments, 1,260 steps: with no check, 280 of 280 runs with a fault ended with a wrong database. Jev reading only the claim had AUROC 0.50 to 0.52, reading the worker's own evidence 0.67 to 0.71, reading a monitor-computed diff 0.94 to 0.98 on structural faults. Checkers without the diff graded writing style, blocking 59% to 100% of honest hedged or terse messages, while the diff checker blocked 0% to 2% in every style. A threshold from Experiment 1 transferred to Experiment 2 unchanged, with 0 of 301 honest steps blocked and 92% of structural faults caught. Wrong values in the right rows were invisible to every Jev view (0 of 52), and only exact code postconditions caught them. Stable thresholds needed about 150 labeled handoffs. Experiment 3 gave Claude Sonnet 5.5 the same states on 300 held-out steps and it followed the same pattern (AUROC 0.57 claim, 0.73 evidence, 0.99 diff, paired gap to Jev's diff 0.011) at about $4.43 per 1,000 checks against Jev's $0.03. The preregistered 0.5 threshold failed 4 of 5 Experiment 1 hypotheses, all 5 Experiment 2 hypotheses passed, and 4 of 5 Experiment 3 hypotheses passed (H14 missed by one step). Full report: `report/report.pdf`.

## Run it

```sh
export TYPESAFE_API_KEY=...            # Jev key
cd src
uv run --with typesafe-sdk python run.py --tag main_t05 --seeds 0-119
uv run --with typesafe-sdk python run.py --tag main_tpilot --seeds 0-119 --thresholds ../results/pilot_thresholds.json
uv run --with typesafe-sdk python run.py --tag exp2_scores --seeds 200-499 --exp2 --score-only
uv run --with typesafe-sdk python run.py --tag exp2_decide --seeds 300-499 --exp2 --thresholds ../results/pilot_thresholds.json
cd .. && uv run --with matplotlib python src/analyze.py && uv run --with matplotlib python src/analyze_exp2.py
# Experiment 3, needs a logged-in Claude Code CLI
python3 src/llm_judge.py --seeds 300-399 --concurrency 5
uv run --with matplotlib python src/analyze_exp3.py
```

All runs together, pilots included, made 9,264 Jev requests with 7.16M input tokens, about $0.30 at $0.042 per million input tokens.

## Files

| Path | What it is |
| --- | --- |
| `PREREG.md` | Hypotheses and seed split, written before any run, plus the post-pilot addendum written before the main run |
| `src/env.py` | Fake database, the three workers, planted faults, monitor diff, exact postconditions |
| `src/run.py` | Runs each checker over the seeds and logs every step and Jev answer |
| `src/analyze.py` | Experiment 1 metrics, bootstrap CIs, hypothesis scoring, figures |
| `src/analyze_exp2.py` | Experiment 2: value faults, message styles, paraphrases, threshold transfer, calibration curve |
| `src/llm_judge.py` | Experiment 3: Claude Sonnet 5.5 judges the same states Jev read, one step per call |
| `src/analyze_exp3.py` | Experiment 3: paired AUROC against Jev, catch rates, style false blocks, hypotheses |
| `results/` | Raw logs for the pilots and both main configurations, `summary.json` |
| `report/` | Report HTML, PDF and figures |

## Prior work

No code written before the sprint is used. The verify-the-handoff framing comes from the author's earlier WorldProof project, which shares no code with this repo.

All data is fake. MIT license.
