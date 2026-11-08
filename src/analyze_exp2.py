"""Experiment 2: value faults, message styles, paraphrases, threshold transfer, calibration cost.

Usage: python src/analyze_exp2.py
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analyze import LABELS, MONITORS, auroc, boot, rate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
VIEWS = ("jev_claim", "jev_worker_evidence", "jev_diff", "jev_diff_plus_worker_evidence")
CAL = range(200, 300)
TEST = range(300, 500)
KS = (1, 2, 3, 5, 10, 20, 50, 100)
DRAWS = 400
FAULTS2 = ("skip", "partial", "wrong_side", "fabricated", "value")


def style(msg: str) -> str:
    if msg in ("done", "refunds done", "report updated"):
        return "terse"
    if msg.split(".")[0] in ("Fulfillment pass complete", "Refund pass complete", "Report rebuild complete"):
        return "verbose"
    if msg.startswith(("I think", "Pretty sure", "I believe")):
        return "hedged"
    return "original"


def load(tag):
    return [json.loads(l) for l in open(RES / tag / "steps.jsonl")], [json.loads(l) for l in open(RES / tag / "runs.jsonl")]


def youden(rows, key):
    """Threshold maximizing catch minus false-block, block if score < t."""
    f = [r[key] for r in rows if r["faulty"]]
    h = [r[key] for r in rows if not r["faulty"]]
    if not f or not h:
        return None
    vals = sorted(set(f + h))
    cands = [(a + b) / 2 for a, b in zip(vals, vals[1:])] or [vals[0]]
    best = None
    for t in cands:
        j = sum(x < t for x in f) / len(f) - sum(x < t for x in h) / len(h)
        if best is None or j > best[0] + 1e-12:
            best = (j, t)
    return best[1]


def main():
    rng = random.Random(0)
    scores, _ = load("exp2_scores")
    decide_steps, decide_runs = load("exp2_decide")
    thr1 = json.loads((RES / "pilot_thresholds.json").read_text())
    out = {"score_only": {}, "decide": {}}

    test = [r for r in scores if r["seed"] in TEST]
    by_seed = defaultdict(list)
    for r in test:
        by_seed[r["seed"]].append(r)
    seeds = sorted(by_seed)

    # step-level metrics on the score-only trajectory, test seeds
    for v in VIEWS:
        d = {}
        for q in ("complete", "para1", "para2"):
            pos = [r["scores"][v][q] for r in test if r["faulty"]]
            neg = [r["scores"][v][q] for r in test if not r["faulty"]]
            d[f"auroc_{q}"] = auroc(pos, neg)
        pos_nv = [r["scores"][v]["complete"] for r in test if r["faulty"] and r["fault"] != "value"]
        neg = [r["scores"][v]["complete"] for r in test if not r["faulty"]]
        d["auroc_nonvalue"] = auroc(pos_nv, neg)
        d["auroc_nonvalue_ci"] = boot(
            seeds,
            lambda sm, v=v: auroc(
                [r["scores"][v]["complete"] for s in sm for r in by_seed[s] if r["faulty"] and r["fault"] != "value"],
                [r["scores"][v]["complete"] for s in sm for r in by_seed[s] if not r["faulty"]],
            ),
            rng,
        )
        d["auroc_value_only"] = auroc([r["scores"][v]["complete"] for r in test if r["fault"] == "value" and r["faulty"]], neg)
        t = thr1[v]
        d["catch_by_fault_at_exp1_thr"] = {
            f: rate([r for r in test if r["fault"] == f and r["faulty"]], lambda r, v=v, t=t: r["scores"][v]["complete"] < t)
            for f in FAULTS2
        }
        d["false_block_by_style_at_exp1_thr"] = {
            st: rate(
                [r for r in test if not r["faulty"] and style(r["message"]) == st],
                lambda r, v=v, t=t: r["scores"][v]["complete"] < t,
            )
            for st in ("original", "terse", "verbose", "hedged")
        }
        out["score_only"][v] = d

    # decision run with Experiment 1 thresholds, test seeds
    for m in MONITORS:
        rows = [r for r in decide_steps if r["monitor"] == m]
        runs = {r["seed"]: r for r in decide_runs if r["monitor"] == m}
        fseeds = {r["seed"] for r in rows if r["faulty"]}
        out["decide"][m] = {
            "catch_all": rate([r for r in rows if r["faulty"]], lambda r: not r["approved"]),
            "catch_nonvalue": rate([r for r in rows if r["faulty"] and r["fault"] != "value"], lambda r: not r["approved"]),
            "catch_value": rate([r for r in rows if r["faulty"] and r["fault"] == "value"], lambda r: not r["approved"]),
            "false_block": rate([r for r in rows if not r["faulty"]], lambda r: not r["approved"]),
            "final_wrong_given_fault": rate(sorted(fseeds), lambda s: not runs[s]["final_ok"]),
            "n_runs_with_fault": len(fseeds),
            "n_faulty": sum(r["faulty"] for r in rows), "n_honest": sum(not r["faulty"] for r in rows),
            "n_value": sum(r["faulty"] and r["fault"] == "value" for r in rows),
        }

    # calibration cost curve: pick threshold on k calibration seeds, apply to test seeds (score-only, jev_diff)
    cal_by_seed = defaultdict(list)
    for r in scores:
        if r["seed"] in CAL:
            cal_by_seed[r["seed"]].append({"faulty": r["faulty"], "s": r["scores"]["jev_diff"]["complete"]})
    test_rows = [{"faulty": r["faulty"], "fault": r["fault"], "s": r["scores"]["jev_diff"]["complete"]} for r in test]
    curve = {}
    crng = random.Random(7)
    for k in KS:
        fbs, cs, skipped = [], [], 0
        for _ in range(DRAWS):
            pick = crng.sample(sorted(cal_by_seed), k)
            t = youden([x for s in pick for x in cal_by_seed[s]], "s")
            if t is None:
                skipped += 1
                continue
            fbs.append(rate([x for x in test_rows if not x["faulty"]], lambda x: x["s"] < t))
            cs.append(rate([x for x in test_rows if x["faulty"] and x["fault"] != "value"], lambda x: x["s"] < t))
        fbs.sort()
        cs.sort()

        def q(a, p):
            return a[int(p * (len(a) - 1))]

        curve[k] = {
            "fb_median": q(fbs, 0.5), "fb_p25": q(fbs, 0.25), "fb_p75": q(fbs, 0.75), "fb_p90": q(fbs, 0.9),
            "catch_median": q(cs, 0.5), "catch_p25": q(cs, 0.25), "catch_p75": q(cs, 0.75),
            "draws_used": len(fbs), "draws_without_both_classes": skipped,
        }
    out["calibration_curve_jev_diff"] = curve

    s = out["score_only"]["jev_diff"]
    dd = out["decide"]["jev_diff"]
    aur = [s["auroc_complete"], s["auroc_para1"], s["auroc_para2"]]
    out["hypotheses_exp2"] = {
        "H6": {"pass": dd["catch_value"] < 0.3 and out["decide"]["code_postcondition"]["catch_value"] == 1.0,
               "value": [dd["catch_value"], out["decide"]["code_postcondition"]["catch_value"]]},
        "H7": {"pass": s["auroc_nonvalue"] >= 0.9, "value": s["auroc_nonvalue"]},
        "H8": {"pass": max(aur) - min(aur) < 0.05, "value": aur},
        "H9": {"pass": dd["false_block"] <= 0.05 and dd["catch_nonvalue"] >= 0.8, "value": [dd["false_block"], dd["catch_nonvalue"]]},
        "H10": {"pass": curve[5]["fb_median"] <= 0.10, "value": curve[5]["fb_median"]},
    }
    (RES / "summary_exp2.json").write_text(json.dumps(out, indent=1))

    figs = ROOT / "report" / "figures"
    ks = list(KS)
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    ax.plot(ks, [curve[k]["catch_median"] for k in ks], "o-", color="#2f6f4f", label="Catch rate, non-value faults (median)")
    ax.fill_between(ks, [curve[k]["catch_p25"] for k in ks], [curve[k]["catch_p75"] for k in ks], color="#2f6f4f", alpha=0.18)
    ax.plot(ks, [curve[k]["fb_median"] for k in ks], "s-", color="#c98a3a", label="False-block rate (median)")
    ax.fill_between(ks, [curve[k]["fb_p25"] for k in ks], [curve[k]["fb_p75"] for k in ks], color="#c98a3a", alpha=0.25)
    ax.plot(ks, [curve[k]["fb_p90"] for k in ks], ":", color="#c98a3a", label="False-block rate (90th percentile)")
    ax.set_xscale("log")
    ax.set_xticks(ks)
    ax.set_xticklabels([f"{k}\n({3 * k})" for k in ks], fontsize=8)
    ax.set_xlabel("Labeled calibration seeds (handoffs)", fontsize=9)
    ax.set_ylabel("Held-out rate", fontsize=9)
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=7.5, loc="center right")
    fig.tight_layout()
    fig.savefig(figs / "fig4_calibration.png", dpi=200)
    plt.close(fig)

    styles = ("original", "verbose", "hedged", "terse")
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    w = 0.2
    colors = ("#9aa5a0", "#c98a3a", "#2f6f4f", "#5b7fa6")
    for j, v in enumerate(VIEWS):
        vals = [out["score_only"][v]["false_block_by_style_at_exp1_thr"][st] for st in styles]
        ax.bar([i + (j - 1.5) * w for i in range(len(styles))], vals, w, label=LABELS[v], color=colors[j])
    ax.set_xticks(range(len(styles)))
    ax.set_xticklabels(["Original", "Verbose", "Hedged", "Terse (no counts)"], fontsize=8.5)
    ax.set_ylabel("Honest steps blocked", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7, ncol=2, loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(figs / "fig5_style.png", dpi=200)
    plt.close(fig)

    print(json.dumps({"score_only": {v: {k: x for k, x in d.items()} for v, d in out["score_only"].items()}}, indent=1))
    print(json.dumps(out["decide"], indent=1))
    print(json.dumps({k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in curve.items()}, indent=1))
    print(json.dumps(out["hypotheses_exp2"], indent=1))


if __name__ == "__main__":
    main()
