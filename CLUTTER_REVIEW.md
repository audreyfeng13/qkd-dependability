# CLUTTER_REVIEW.md

**Status: re-derived from scratch against the current repo. Nothing has been removed.**
Phase 4 will broaden this (unused variables, duplicates, orphaned snippets) and no deletion happens until Audrey approves a list.

Cell indices are **0-indexed** (the position in the `.ipynb` JSON `cells` array). Note that RECOVERED_FINDINGS.md mixed 0- and 1-indexing (see PAPER_TRACEBACK.md, "Indexing caveat").

## Notebook names and locations (after the Phase 3 reorganization)

This document was written against the pre-move layout. Cell indices are unchanged by the move; only names and locations differ.

| Name used in this document | Current path |
|---|---|
| `Untitled2` | `notebooks/core/paper_figures_and_reconciliation_fit.ipynb` |
| `Untitled` | `notebooks/exploratory/validation_finite_key_and_reconciliation_model.ipynb` |
| `Untitled1` | `notebooks/exploratory/fabric_site2_network_debugging.ipynb` |
| `sdc_sweeps_all5keys`, `mitigation_v2_redundant_pa_tmr`, `23_finitekey_vs_asymptotic`, `29_poster_figures (2)`, `30_scale_up_experiments`, `20_data_cleaning_and_integrity`, `10_sdc_real`, `28_mitigation_overhead` | `notebooks/core/<same name>.ipynb` |
| every other notebook | `notebooks/exploratory/` |
| `results/<name>.csv` / `.json` | `results/data/<name>` |
| `results/<name>.png` | `results/figures/<name>` |

## Method (and its limits)

Static def-use analysis (`ast`), seeded from the cited cells in PAPER_TRACEBACK.md:

* A cell is **KEEP-cited** if it is a seed, and **KEEP-dependency** if a seed (transitively) reads a name it defines (nearest earlier definition, in file order, only counting names read before being stored within the cell) or reads a file it writes (string-literal match, including f-string fragments).
* Everything else is tiered:
  * **T1 (recommend remove):** empty, ended in an error, never executed (`execution_count` is null), duplicate of an earlier cell, or produced no output and wrote no file.
  * **T2 (probably remove, real but superseded):** defines a function that is redefined in a later cell, print/diagnostic-only, or part of `Untitled1` (pure FABRIC network debugging).
  * **T3 (uncited but real, recommend KEEP):** ran OK, produced output/figure/file, but is not reached from any cited cell.
* Name-based slicing cannot see through `eval`, `getattr`, `from x import *`, or paths assembled at runtime. The seed list is only as good as my reading of the cited cells, because **the paper text is not in the repo** (only the references PDF). Anything the paper cites that I did not seed will show up as T3/T2/T1 here and must be rescued by Audrey.
* "Never executed" is evidence of staleness, **not** proof of clutter: several notebooks have had their outputs stripped (e.g. `30_scale_up_experiments` c5 has no execution count but wrote the 100-row TMR CSV that the paper cites).

## Re-verification of the recovered T1/T2/T3 classification

| Recovered claim | Status |
|---|---|
| T1=70 / T2=85 / T3=59 / 67 flagged nothing / 34 keep | **Cannot confirm.** The prior algorithm is not recoverable; my independent counts (below) use different seeds and definitions, so the totals are not comparable. |
| "59 of the 70 T1 cells are in `sdc_sweeps_all5keys`" | **Does not hold under the current analysis:** I find 11 T1 + 13 T2 there. The large remaining mass in that notebook (106 cells) is T3, uncited-but-real. The recovered tiering was probably more aggressive about calling uncited exploration "stale". |
| `sdc_sweeps_all5keys` c16 (ξ₂ remark) is not clutter | **Holds, with the index corrected:** the remark is **c15** (0-indexed). c16 is an unexecuted mock-sweep cell. |
| `mitigation_v2` c25-26 not clutter (Jaccard 0.15-0.25 source) | **Partly refuted.** c25 has no execution count (never ran here), and c26's markdown says Jaccard "~0.08-0.17", not 0.15-0.25. No saved output supports 0.15-0.25. Keep both cells until Audrey decides; I flag the number as unsupported. |
| `20_data_cleaning_and_integrity` c9, c15 write `mock_clean.csv` via f-string | **Holds, index off by one.** In this notebook the writers are 0-indexed **c8 and c14** (c9 is markdown; the notebook has only 15 cells). My analysis keeps both (c14's f-string write is found). |
| `10_sdc_real`: 4 of 13 code cells load-bearing (imports, connect, key-0 PE split, 5-key collection) | **Holds:** cells 0, 1, 2, 7 are the seeds; there are 13 non-empty code cells. The other 9 are early sweeps/duplicates (see per-notebook table). |
| `sdc_sweeps_all5keys` c182 duplicates c134 (chi²=93.05) | **Holds functionally** (identical printed output, chi²=93.05, dof=8). The sources are not byte-identical (c182 adds imports and a reload of `reconciliation_clean.csv`), so a whitespace-normalized duplicate check misses it. Keep c134 as cited. |
| `sdc_sweeps_all5keys` c185 is a QBER-vs-silent-rate figure, not a TMR cell | **Holds:** c185 plots silent rate vs QBER per fault type. |
| Second-site section of `30_scale_up_experiments`: citation status unknown | **Still cannot confirm.** See below. |
| No `glob`/wildcard in core notebooks | **Holds.** `grep` finds no `glob.glob`/`.glob(`/`rglob`/`fnmatch` in any notebook. Library/scripts hits: `scripts/deploy_fabric.py:273,287` (scenario YAML listing) and `scripts/package_artifact.sh:63-65` (globs `*/notebooks/*.ipynb` of an *output* dir). Neither is affected by Phase 3 provided `scenarios/` stays put. |
| Initial scan found no dead commented-out code | Not re-run in this phase; Phase 4 covers it. |

### Second-site section (30_scale_up_experiments c7-c20, c26-c35)
Unresolved. Evidence it is *real*: `results/sdc_site2_toeplitz_finalkey_doseresponse.csv` and several `*_site2.json` files exist, and c20 runs a site-1-vs-site-2 CMH test. Evidence for/against citation: the README does not mention site 2, and there is no paper text in the repo. **Needs Audrey: is the NCSA<->TOKY (site 2) result in the paper?** Until answered it is listed as "needs author decision", not removed.

### Specific suspicious cells (sdc_sweeps_all5keys), diagnosed in Phase 2c
See PAPER_TRACEBACK.md. In short: c186 is arithmetically correct for p=0.5 (not inverted); c189-190 use a draft "placeholder" agreement test that is superseded by `mitigation_v2` c12.

## Independent classification (current repo)

| Notebook | code cells | cited | dependency | T1 | T2 | T3 |
|---|---|---|---|---|---|---|
| `Untitled2` | 24 | 16 | 4 | 1 | 0 | 3 |
| `sdc_sweeps_all5keys` | 194 | 9 | 55 | 11 | 13 | 106 |
| `mitigation_v2_redundant_pa_tmr` | 19 | 7 | 4 | 4 | 0 | 4 |
| `23_finitekey_vs_asymptotic` | 10 | 3 | 0 | 2 | 0 | 5 |
| `29_poster_figures (2)` | 8 | 2 | 0 | 2 | 0 | 4 |
| `30_scale_up_experiments` | 33 | 1 | 16 | 8 | 2 | 6 |
| `20_data_cleaning_and_integrity` | 8 | 4 | 1 | 0 | 0 | 3 |
| `10_sdc_real` | 14 | 4 | 2 | 6 | 0 | 2 |
| `28_mitigation_overhead` | 5 | 4 | 0 | 1 | 0 | 0 |
| `Untitled` | 49 | 0 | 4 | 3 | 6 | 36 |
| `Untitled1` | 17 | 0 | 0 | 4 | 13 | 0 |
| **total** | 381 | 50 | 86 | 42 | 34 | 169 |

`Untitled` / `Untitled1` were not seeded (no paper artifact is attributed to them in the recovered mapping), so everything in them is dependency-by-file-read, T1, T2 or T3. `Untitled` holds the data-validation/finite-key validation work and a full reconciliation fault model; it should be reviewed by Audrey rather than judged by this heuristic.

## Per-notebook cell lists

### `Untitled2`
* **KEEP-cited:** 0-2, 4-5, 8, 10-12, 14, 17-22
* **KEEP-dependency:** 3, 6-7, 9
* **T1:**
  * c23 (exec=None): empty cell — ``
* **T3 (keep):** 13, 15-16

### `sdc_sweeps_all5keys`
* **KEEP-cited:** 15, 119, 123, 134-135, 146, 160, 186, 193
* **KEEP-dependency:** 1-2, 6, 9, 11-12, 18-21, 24, 26, 40-42, 58-59, 63, 67-69, 71-72, 77, 98, 100, 103-107, 109-110, 120, 126, 138, 142, 144, 150, 155, 159, 167, 172-173, 175, 181, 184-185, 187-190, 192, 194, 196
* **T1:**
  * c13 (exec=None): never executed — `n_bits = alice_key.get_nr_bits()`
  * c16 (exec=None): never executed — `from qne.cascade.finite_key import h, v, finite_key_output_length, optimize_nu`
  * c23 (exec=23): ended in error output — `REALCHANNEL_N_RUNS = 100  # adjust if you want a faster first pass`
  * c25 (exec=10): duplicate of earlier cell — `stdout, _ = bob.execute("ps aux / grep -E 'cascade/python3 scripts'", quiet=True)`
  * c33 (exec=None): never executed — `files_to_check = [`
  * c34 (exec=None): empty cell — ``
  * c36 (exec=None): never executed — `import matplotlib.pyplot as plt`
  * c44 (exec=12): ended in error output — `recon_fk_df = pd.read_csv(recon_fk_path)`
  * c57 (exec=11): ended in error output — `import numpy as np`
  * c130 (exec=26): ended in error output — `print("=== Reconciliation: mismatch outcome by prob, split by verification_passed ===")`
  * c199 (exec=None): empty cell — ``
* **T2:**
  * c70 (exec=38): print/diagnostic only; defines nothing — `print(recovered.groupby("fault_type").size())`
  * c82 (exec=58): superseded: count_fires redefined in cell 126 — `# Re-extract faults_fired for every recovered bob file (this was missing before)`
  * c92 (exec=73): superseded: predicted_mismatch_toeplitz,predicted_mismatch_finalkey,chi_square_fit redefined in cell 195 — `# --- 3. Chi-square model fit, corrected comparison, on the full merged data ---`
  * c93 (exec=74): superseded: cmh_manual,build_tables redefined in cell 181 — `# --- 4. Mock-vs-real pooled CMH test, corrected comparison, on the full merged data ---`
  * c95 (exec=78): print/diagnostic only; defines nothing — `print("is_baseline_contaminated value counts in toeplitz_clean.csv:")`
  * c99 (exec=82): superseded: predicted_mismatch_toeplitz redefined in cell 195 — `# --- Final chi-square model fit, correct formula, clean data only ---`
  * c143 (exec=11): superseded: parse_fired redefined in cell 145 — `import ast`
  * c148 (exec=21): print/diagnostic only; defines nothing — `print(per_key)`
  * c157 (exec=28): print/diagnostic only; defines nothing — `print(per_key.sort_values("qber"))`
  * c162 (exec=33): print/diagnostic only; defines nothing — `print(f"RECON_PROB used in sweep: {RECON_PROB}")`
  * c163 (exec=34): print/diagnostic only; defines nothing — `print(synthetic_df.groupby("true_qber")["pool_size_exact"].first())`
  * c164 (exec=36): print/diagnostic only; defines nothing — `print(list(synthetic_df.columns))`
  * c177 (exec=62): superseded: predicted_mismatch redefined in cell 179 — `def predicted_mismatch(prob, pool_size):`
* **T3 (keep):** 3-5, 7, 14, 22, 27-31, 37-39, 43, 45-56, 60-62, 64-66, 73-76, 78-81, 83-91, 94, 96-97, 101-102, 108, 111-118, 121-122, 124-125, 127-129, 131-133, 136-137, 139-141, 145, 147, 149, 151-154, 156, 158, 161, 165-166, 168-171, 174, 176, 178-180, 182-183, 191, 195, 197-198

### `mitigation_v2_redundant_pa_tmr`
* **KEEP-cited:** 12, 16-21
* **KEEP-dependency:** 1, 3, 5, 7
* **T1:**
  * c13 (exec=None): never executed — `fig, ax = plt.subplots(1, 2, figsize=(11, 4))`
  * c24 (exec=None): never executed — `def analyze_tmr_error_overlap(replicas_bits, alice_key):`
  * c25 (exec=None): never executed — `# Requires the per-replica bit arrays -- check whether the raw JSONs are still`
  * c30 (exec=None): empty cell — ``
* **T3 (keep):** 9, 22, 28-29

### `23_finitekey_vs_asymptotic`
* **KEEP-cited:** 1, 3, 5
* **T1:**
  * c12 (exec=8): empty cell — ``
  * c13 (exec=None): empty cell — ``
* **T3 (keep):** 7-11

### `29_poster_figures (2)`
* **KEEP-cited:** 1, 7
* **T1:**
  * c10 (exec=1): ended in error output — `import pandas as pd`
  * c11 (exec=None): empty cell — ``
* **T3 (keep):** 3, 5, 8-9

### `30_scale_up_experiments`
* **KEEP-cited:** 5
* **KEEP-dependency:** 2-4, 8-9, 11-13, 16-17, 19, 22-23, 25, 31-32
* **T1:**
  * c6 (exec=None): never executed — `# --- Recompute the Wilson 95% CI on the correction rate at n=100 (replaces the`
  * c14 (exec=8): ended in error output — `import sys`
  * c15 (exec=7): no output, no file written — `CSV_SITE2 = RESULTS / "sdc_site2_toeplitz_finalkey_doseresponse.csv"`
  * c24 (exec=14): ended in error output — `# --- Recompute Table 2 (finite-key vs. asymptotic length) for all 10 keys ---`
  * c27 (exec=None): never executed — `import pandas as pd`
  * c30 (exec=5): ended in error output — `# --- 1. Install the deps install_deps() actually missed, on both site-2 nodes ---`
  * c35 (exec=None): never executed — `from qne.cascade.sweep_utils import run_real_channel_trial`
  * c36 (exec=None): empty cell — ``
* **T2:**
  * c20 (exec=8): superseded: cmh_manual redefined in cell 27 — `# --- Site-1 vs. site-2 CMH test, matched to your existing mock-vs-real methodology`
  * c29 (exec=4): print/diagnostic only; defines nothing — `print("=== raw_stdout ===")`
* **T3 (keep):** 10, 18, 26, 28, 33-34

### `20_data_cleaning_and_integrity`
* **KEEP-cited:** 1, 3, 8, 14
* **KEEP-dependency:** 7
* **T3 (keep):** 5, 10, 12

### `10_sdc_real`
* **KEEP-cited:** 0-2, 7
* **KEEP-dependency:** 10-11
* **T1:**
  * c4 (exec=None): never executed — `recon_probs = [0.3, 0.1, 0.03, 0.01, 0.003, 0.001]`
  * c5 (exec=None): never executed — `conditions = [("toeplitz_only", {"toeplitz_prob": 0.5}), ("final_key_only", {"final_key_pr`
  * c6 (exec=None): never executed — `existing_df = pd.read_csv(str(PROJECT_DIR / "results" / "sdc_real_channel_toeplitz_finalke`
  * c9 (exec=None): never executed — `# Fixed: use k AND qber from the SAME source (key_pairs_df's freshly-collected`
  * c12 (exec=None): never executed — `"""`
  * c13 (exec=None): empty cell — ``
* **T3 (keep):** 3, 8

### `28_mitigation_overhead`
* **KEEP-cited:** 1, 3, 5, 7
* **T1:**
  * c8 (exec=None): empty cell — ``

### `Untitled`
* **KEEP-dependency:** 44-47
* **T1:**
  * c14 (exec=18): no output, no file written — `from qne.cascade.finite_key import h, v, finite_key_output_length, optimize_nu`
  * c38 (exec=42): no output, no file written — `def mismatch_series(df, col="keys_match"):`
  * c48 (exec=None): empty cell — ``
* **T2:**
  * c0 (exec=3): superseded: ell_asymptotic_actual,is_baseline_contaminated,block_size_schedule,prob_odd_count_hypergeom,prob_even_count_hypergeom_excl,background_error_decay,survival_probability_per_pass,mismatch_prob_given_pass_injection,full_reconciliation_prediction redefined in cell 18 — `import sys, json, math, os`
  * c10 (exec=14): superseded: is_baseline_contaminated redefined in cell 12 — `def is_baseline_contaminated(row):`
  * c19 (exec=23): superseded: plot_validation redefined in cell 21 — `def plot_validation(df_clean, key_pairs_df, ell_func, p1, label, ax, fault_type="toeplitz"`
  * c23 (exec=27): superseded: chi_square_goodness_of_fit_reconciliation redefined in cell 39 — `def chi_square_goodness_of_fit_reconciliation(df, key_pairs_df, M=4):`
  * c27 (exec=31): superseded: ell_finite_key_actual redefined in cell 36 — `def ell_finite_key_actual(n, k_pe, Q):`
  * c43 (exec=6): superseded: m_block,P_survive_point_estimate,P_odd_point redefined in cell 44 — `"""`
* **T3 (keep):** 1-9, 11-13, 15-18, 20-22, 24-26, 28-37, 39-42

### `Untitled1`
* **T1:**
  * c0 (exec=1): ended in error output — `import sys, json`
  * c2 (exec=None): never executed — `from qne.config import ScenarioConfig`
  * c3 (exec=None): never executed — `for node, name in [(alice_2, "alice"), (bob_2, "bob")]:`
  * c16 (exec=None): empty cell — ``
* **T2:**
  * c1 (exec=2): FABRIC site-2 network debugging; no paper artifact — `SCENARIO = 'validation/scenarios/fabric_1km.yml'`
  * c4 (exec=12): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c5 (exec=2): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c6 (exec=4): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c7 (exec=5): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c8 (exec=6): FABRIC site-2 network debugging; no paper artifact — `# 1. Bring up the switch's own interfaces -- likely the actual root cause`
  * c9 (exec=7): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c10 (exec=8): FABRIC site-2 network debugging; no paper artifact — `bob_node = slice_obj_2.get_node("bob")`
  * c11 (exec=9): FABRIC site-2 network debugging; no paper artifact — `switch.execute("sudo ip link set enp7s0 down", quiet=True)`
  * c12 (exec=11): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c13 (exec=12): FABRIC site-2 network debugging; no paper artifact — `import time`
  * c14 (exec=13): FABRIC site-2 network debugging; no paper artifact — `# Did the listener actually start and bind?`
  * c15 (exec=14): FABRIC site-2 network debugging; no paper artifact — `import time`
