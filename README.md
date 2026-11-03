# SignalMap: conservative org-chart inference

**[Open the live demo](https://shai-harsh.github.io/signalmap-org-chart-inference/)**

SignalMap turns an observed flat employee roster into an **inferred forest** of reporting lines. It is deliberately willing to leave gaps: when several managers are equally plausible, a title is uninformative, or calibrated confidence is below 85%, it emits no line. The interactive explorer lets you switch among 500 companies, search the roster, inspect the evidence and walk up the visible reporting chain. All companies and people are fictional.

> The reported accuracy is on generated data. It is a measure of recovery of this generator—not a claim about real-world org charts. The inference rules and synthetic generator encode some of the same assumptions.

## Run locally

Requirements: Python 3.10+ and a modern browser. There are no runtime packages, keys, or external APIs.

```bash
python3 scripts/generate.py       # regenerate roster and separate truth (fixed seed)
python3 scripts/build_data.py     # calibrate, evaluate, and build the app data
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory dist
```

Open <http://localhost:8000>. The application is static: prediction runs offline at build time, and each selected company is fetched as a small JSON file. The app does not expose the truth file. The large synthetic roster, truth and per-company outputs are generated locally rather than checked in. The calibration and evaluation summaries are included for review.

## Data design

`scripts/generate.py` creates reporting trees **before** creating the flat observations. Each company has an executive team, function leaders, specialty managers and individual contributors across 11 functions. The observed roster hides a random subset of managers and corrupts titles (abbreviations, generic or missing titles), departments and locations. Some specialties have several managers with the same title; where they sit is only partially informative. Data, security and product leadership have multiple possible executive reporting lines. Company sizes and industries vary.

- 500 companies, **106,250 observed employees**, 132–384 per company.
- 2,600 blank titles; 16,952 blank departments; 20,243 blank locations.
- `data/people.jsonl` is the only employee input to inference; `data/truth.jsonl` separately maps observed people to true managers, including managers absent from the roster.
- Company-level split: 300 development, 100 calibration, 100 test. An entire company belongs to one split. Seeds and resulting splits are fixed.

The synthetic workforce is deliberately imperfect, but it remains stylized: every industry uses the same core function templates, title vocabulary is limited, and some senior reporting lines are deterministic. Real companies, industries, geographies, matrix organizations and job-title conventions are more varied.

## Inference and confidence

1. Parse the **title** into function, specialty, and an ordinal role. In particular, `Product Manager` and `Customer Success Manager` are treated as individual-contributor titles; `Team Lead` is not assumed to manage people. Missing or generic titles are unplaceable. Department and industry are retained for exploration but not used to choose a manager.
2. Generate only candidates from the same company with a higher inferred role and compatible function/specialty. An employee can match a specialty manager; a manager can match a function head; certain function heads can match an executive; an executive can match a CEO. Location is weak supporting evidence, not a hard rule. Candidates must already be in the observed roster, and an employee is not jumped directly to a head when no specialty manager is observed. If the true manager is absent but another plausible candidate remains, the system can still make an incorrect match.
3. Rank candidates using interpretable rules. Abstain on ties and missing candidates. The strictly increasing inferred role prevents cycles. A known CEO has no inferred manager.
4. Learn a monotone score-to-correctness mapping with pooled-adjacent-violators on **calibration companies only**, with Beta(1,1) smoothing. Emit a line only at calibrated confidence ≥ 0.85. UI confidence is conditional on the synthetic data distribution; it is not a universal probability.

`candidates_for_company` receives observed rows only; it has no access to truth. `scripts/build_data.py` reads labels exclusively to fit the calibration mapping and calculate evaluation, after candidates have been generated. Test-company labels never enter calibration. The 85% operating threshold was set before inspecting the held-out results, and the extra thresholds below expose the tradeoff rather than being a claim that every operating point is suitable.

## Evaluation: 100 held-out companies

The denominator is every observed employee whose true manager is non-null, **including people whose manager was hidden**. There are 22,066 eligible people; 1,894 have a true manager absent from the observed roster. Of the 471 wrong emitted lines, 110 point to someone else when the true manager is missing.

| Method / confidence threshold | Correct / emitted | Precision | Coverage | Edge recall |
| --- | ---: | ---: | ---: | ---: |
| Conservative, ≥85% | 7,383 / 7,854 | **94.0%** | 35.6% | 33.5% |
| Conservative, ≥90% | 3,102 / 3,102 | 100.0% | 14.1% | 14.1% |
| Conservative, ≥80% | 10,887 / 12,095 | 90.0% | 54.8% | 49.3% |
| Nearest-higher-seniority baseline | 6,749 / 18,503 | 36.5% | 83.9% | 30.6% |

Precision = correct/emitted; coverage = emitted/eligible; edge recall = correct/eligible. The baseline chooses the closest higher parsed role in the same function, breaking ties by ID; it does not abstain for competing managers. For the default model, the 95% **company bootstrap** precision interval is 93.1–94.9% (2,000 resamples, fixed seed); this preserves shared-company dependence better than an edge-level interval. Even this interval does not address a different real-world data distribution.

Calibration on accepted test candidates: the 89.44% confidence group had 4,281/4,752 correct (90.1%); the 99.97% group had 3,102/3,102 correct in this synthetic test. The latter is a property of this highly regular generator, not evidence that such confidence would transfer to real data. Full machine-readable results, alternative thresholds, and calibration blocks are in `data/evaluation.json` and `data/calibration.json`.

## Project structure

```text
scripts/generate.py       # seeded synthetic organization + noisy observations
scripts/inference.py      # title parsing, candidate generation, simple baseline
scripts/build_data.py     # held-out calibration, evaluation, static app data
scripts/                  # standard library Python; no network or API keys
data/                     # checked-in metrics; generated inputs and truth after setup
dist/                     # static explorer and per-company inferred outputs
tests/                    # behavioral, leakage-boundary and graph invariants
AI_WORKFLOW.md            # transparent record of AI-assisted development
```

## Production path

Before applying this to real company data, assemble an independently labeled, time-stamped evaluation set with company-disjoint splits and hidden-manager examples. Measure error and coverage by function, region, seniority and company size; recalibrate per data source; detect stale titles and ambiguous entities; and collect reviewer feedback with an auditable source trail. A bounded LLM-assisted title-normalization step could propose a typed function/seniority and explanation, but must support an `unknown` result, caching, versioning, evaluation and human review. It should not invent a manager or replace empirical calibration.

## AI-assisted development

An AI coding assistant helped bring Harsh Yadav’s idea to life by supporting implementation, refining features, and assisting with testing and documentation.
