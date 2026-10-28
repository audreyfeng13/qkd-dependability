# PAPER_TRACEBACK.md

Paper artifact → notebook/cell traceback, **re-verified against the current repo** (commit `b6b8c8c`) by re-executing notebooks in a scratch copy of the repo (fresh venv, repo files untouched) and comparing outputs.
`RECOVERED_FINDINGS.md` was used as a head start only.

## Notebook names and locations (after the Phase 3 reorganization)

This document was written against the pre-move layout. Cell indices are unchanged by the move; only names and locations differ.

| Name used in this document | Current path |
|---|---|
| `Untitled2` | `notebooks/core/paper_figures_and_reconciliation_fit.ipynb` |
| `Untitled` | `notebooks/exploratory/validation_finite_key_and_reconciliation_model.ipynb` |
| `Untitled1` | `notebooks/exploratory/fabric_site2_network_debugging.ipynb` |
| `sdc_sweeps_all5keys`, `mitigation_v2_redundant_pa_tmr`, `23_finitekey_vs_asymptotic`, `29_poster_figures`, `30_scale_up_experiments`, `20_data_cleaning_and_integrity`, `10_sdc_real`, `28_mitigation_overhead` | `notebooks/core/<same name>.ipynb` |
| every other notebook | `notebooks/exploratory/` |
| `results/<name>.csv` / `.json` | `results/data/<name>` |
| `results/<name>.png` | `results/figures/<name>` |

## Ground rules and limits of this verification

* **The paper text is not in the repo** (only `Feng_Audrey_QCE_References.pdf`). I can verify that notebook outputs match the numbers RECOVERED_FINDINGS.md quotes from the paper, but I **cannot** independently check what the paper says, or which table/figure number a given cell is. Paper-side labels below are inherited from the recovered document and marked accordingly.
* Cell indices are **0-indexed** (position in the notebook JSON). The recovered document mixes conventions, see below.
* Status legend: **CONFIRMED** (re-executed or re-read, matches), **CHANGED** (differs from recovered doc), **UNVERIFIED** (could not check).

### Indexing caveat
RECOVERED_FINDINGS.md used 0-indexed cells for most entries but 1-indexed for a few. Found so far:
* `sdc_sweeps_all5keys` "c16" (ξ₂ remark) is actually **c15** (0-indexed).
* `20_data_cleaning_and_integrity` "c9, c15" are actually **c8, c14**.
* The "Fig 6b cell 20 depends on cells 21-23" statement uses 1-indexing: it means **c19 vs c20-22**.

## Figure / table → notebook mapping

| Paper artifact (label from recovered doc) | Notebook | Cell | Output file | Status |
|---|---|---|---|---|
| Fig 4 | `Untitled2` | c10 | `fig_mismatch_prob_and_qber_all_faults.png` | **CONFIRMED**: pixel-identical on re-run (0 differing px). Note c7 and c9 write the *same filename*; c10 runs last and is the one that survives. |
| Fig 5 | `Untitled2` | c5 | `fig_mock_vs_real.png` | **CONFIRMED** pixel-identical |
| Fig 6a | `Untitled2` | c2 | `fig_naive_vs_proposed.png` | **CONFIRMED** pixel-identical |
| Fig 7 | `Untitled2` | c4 | `fig_redundancy.png` | **CONFIRMED** pixel-identical. **Caveat:** the bar heights are **hard-coded literals** (`[1.0, 0.0]`, `[1.08, 2.69]`), not computed from data. The values agree with `mitigation_v2` c12 / `28_mitigation_overhead`, but nothing links them programmatically. |
| Fig 8 | `Untitled2` | c1 | `fig_model_fit.png` | **CONFIRMED** pixel-identical |
| Fig 9 | `Untitled2` | c8 | `fig_synthetic_qber_sweep.png` | **CONFIRMED** pixel-identical |
| Fig 6b | `Untitled2` | c19 | `fig_reconciliation_fit_pooled.png` | **CHANGED**: reproduces exactly only under a specific execution order (see next section). The recovered "cosmetic legend-font" description is incomplete. |
| Figs 1-3 | n/a | n/a | n/a | Schematics; not in repo. UNVERIFIED (not checkable). |
| Table 4 | `sdc_sweeps_all5keys` | c193 (silent rate by prob, 3 fault types) and c119 | n/a | Cells exist and print per-prob silent rates (e.g. p=0.5: Toeplitz 0.213, final-key 0.460, reconciliation 0.000). **Which table those feed is UNVERIFIED** without the paper. |
| Table 5 | `23_finitekey_vs_asymptotic` c3, c5; `29_poster_figures` c7 | | stdout | **BROKEN against the live data**, see below. |
| b-values, χ²=7.91 | `Untitled2` | c14 (fit), c17 (print b), c20 (χ²) | stdout | **CONFIRMED**: re-run gives χ²=7.91, dof=40, p=1.0000 |
| Leave-one-key-out | `Untitled2` | c21 (no baseline), c22 (with baseline) | stdout | **CONFIRMED**: c21 MAE 0.0359 (χ²=209.15, REJECTED); c22 MAE 0.0107, χ²=7.65, dof=40. (The recovered doc's "MAE 0.036/0.011, χ²=7.65" attributes χ²=7.65 to c22 only; c21's χ² is 209.15.) |
| Toeplitz/final-key χ², CMH | `sdc_sweeps_all5keys` | c119 (Toeplitz χ²=5.63 dof 8 p=0.69; final-key χ²=10.21 dof 8 p=0.25), c123 (CMH Toeplitz 1.946 p=0.163; final-key 0.978 p=0.323) | stdout | **CONFIRMED** (stored outputs) |
| Reconciliation model χ²=93.05 | `sdc_sweeps_all5keys` | c134 (c182 reproduces it) | stdout | **CONFIRMED**, dof=8, p≈0, model REJECTED |
| 1.87x pool-size ratio | `sdc_sweeps_all5keys` | c135 | stdout | **CONFIRMED**: mean ratio 1.870877 over 4000 rows. Keys 0 and 1 are below 1x (c_naive 44.9 and 54.0 vs c≈33: ratios 0.73 and 0.65 in `Untitled2` c17, which uses a slightly different c_naive). |
| Pearson/Spearman | `sdc_sweeps_all5keys` | c160 | stdout | **CONFIRMED**: Pearson 0.893 (p=0.001), Spearman 0.975 |
| ξ₂ negative remark | `sdc_sweeps_all5keys` | **c15** (not c16) | stdout | **CONFIRMED** ξ₁=2.3948, ξ₂=−0.2088. The cell itself prints "published ξ₁ range is [1.05, 1.16] -- CHECK THIS, seems off". |
| ξ₁≈15.69 | `sdc_sweeps_all5keys` | c146 | stdout | **CONFIRMED** (15.6916) and a **different calculation** from c15; do not conflate. |
| RPA 100% detection | `mitigation_v2_redundant_pa_tmr` | c12 | `mitigation_redundant_pa_v3.csv` | Cell reads correctly (compares actual output arrays). Its stored output is empty (never executed in this copy), so the 100% figure is **UNVERIFIED against a saved run**. Compare the superseded `sdc_sweeps_all5keys` c189-190 below. |
| TMR 0/100 corrected | `mitigation_v2` c16-21 (runs 0-19), `30_scale_up_experiments` c5 (runs 20-99) | | `mitigation_tmr_realchannel.csv` | **CONFIRMED from the raw CSV**: 100 rows, all `voted`, 0 corrected, Wilson 95% CI [0, 3.70%]. Mean residual is **11.39 error bits** (SE 0.36). The recovered doc writes "11.39% ± 0.36%": the CSV stores a count, not a percentage, so any "%" in the paper needs a stated denominator. |
| RPA/TMR overhead (1.08x/2.69x) | `28_mitigation_overhead` | c3, c5 | stdout | **Stored outputs match** (1.32→1.42 ms = 1.08x; 22.5→60.5 ms = 2.69x), but **the 1.08x does not reproduce and looks like a measurement artifact** (Phase 5 finding, below). TMR 2.69x re-measures at ~3.0x, consistent with its 3x structure. |
| Jaccard 0.15-0.25 | `mitigation_v2` c25-26 | | | **NOT SUPPORTED**: c26 markdown says ~0.08-0.17; c25 never produced saved output. |
| Zero-fault baseline | `sdc_sweeps_all5keys` | c196-198 | `check1_zerofault_validation.csv` | Output shows **2/37** zero-fault trials with `keys_match=False` (key 2 and key 4, seed 49, `verification_passed=False`, 2 residual errors, `faults_fired={}`). Worth knowing before claiming a clean baseline. |

**Two-notebook structure: CONFIRMED.** `Untitled2` writes the figures (and sets the large-font rcParams in c0/c9/c10); `sdc_sweeps_all5keys` holds almost all statistics. `20_data_cleaning_and_integrity` c8 and c14 write the `*_clean.csv` files that feed Figs 4, 5, 6b.

## Known bugs: re-verification

### 1. Table 5 key contamination: CONFIRMED
* `results/key_pairs_metadata.csv` currently has **10 keys** (rows 5-9 appended by `30_scale_up_experiments` c13/c25, the cells that write it).
* The Table 5 cells iterate `range(len(key_pairs_df))`. Re-run now: **10 rows**, mean reduction **96.05%** (rows 5-9: 96.98, 99.96, 97.65, 97.16, 99.96).
* The stored output (5 rows: 99.18, 99.96, 89.40, 88.83, 91.41) averages **93.76%**, i.e. the paper's 5-row 93.8%. Keys 0-4 in the live file still match those 5 rows exactly.
* Fix applied in Phase 2a (snapshot + README note).

### 2. Fig 6b execution-order dependence: CHANGED (cause identified)
Procedure: fresh kernel, run chosen cell subsets, compare `fig_reconciliation_fit_pooled.png` to the committed PNG pixel by pixel.

| Cells executed before c19 | Differing pixels vs committed PNG |
|---|---|
| c0, c11, c12, c14 only | **0 (identical)** |
| c11, c12, c14 only (no style cell) | 73,679 |
| + c9 and/or c10 (any of them) | 86,702 |
| full linear run c0-c22 | 86,702 |
| c20-c22 executed **before** c19 | 86,702 (same as without them) |

* **The recovered claim ("c19/cell 20 depends on cells 21-23 having run first") is refuted.** c20-c22 have no effect on the figure.
* **Actual cause:** c9 and c10 call `plt.rcParams.update({... "font.size": 20, "axes.labelsize": 22, "lines.linewidth": 3 ...})` at global scope. `plot_reconciliation_fit_pooled` (c19) only overrides `font.size` and the legend size, so axis-label/tick/line sizes leak in from whichever style cell ran last. The committed PNG corresponds to the **c0 style (labelsize 18)**; a normal top-to-bottom run produces a different image.
* The same leak affects **every** figure from c13 onward: `fig_reconciliation_empirical_fit.png`, `fig_reconciliation_baseline_fit.png`, `fig_reconciliation_fit_key0..4.png` and `fig_reconciliation_fit_pooled.png` all differ from the committed versions (84-100k px) after a linear run. Figs 4, 5, 6a, 7, 8, 9 are unaffected.
* Not fixed in this phase. The principled fix is `plt.rc_context(...)` in c19 (and c13/c15/c17), which is an **edit to a cell** and so is left for Audrey; the Phase 5 master notebook sets styles explicitly per section, which removes the dependency there. No `bisect` module collision occurred (the order tests used explicit cell lists, not a stdlib bisect).

### 3. Cell 186: not an inversion
`sdc_sweeps_all5keys` c186 computes `prob_full_correction(3, p=0.5, 2810)` = `(1 − P(≥2 of 3 fire))^2810 = 0.5^2810`, which underflows to 0.000000.
* Direction, sign and comparison are all correct for the formula. At **p=0.5** majority voting of 3 replicas is a coin flip per position, so the true prediction is ~0 for any large pool.
* Independent check of the same formula (pool 2810, N=3, computed with scipy): p=0.5 → 0.0, p=0.1 → 2.2e-35, p=0.01 → 0.43, p=0.001 → 0.992, p=1e-4 → 0.9999. The "near-total correction" the paper text describes holds only for **small p (≈1e-3 or below)**, not for the p=0.5 hard-coded in c186 (its own comment says "match whatever firing probability your reconciliation TMR test used").
* Verdict: the discrepancy is a **mismatch between the p used in c186 and the p in the paper's claim**, not a code inversion. Nothing to fix in code; the paper sentence should state the p.

### 4. Cells 189-190: mislabeling, but not successes-vs-failures
`run_redundant_pa_trial` (c189) defines `repeats_agree = result1.get("keys_match") == result2.get("keys_match")`, a comparison of the two boolean **match flags**, not of the two output keys. When *both* replicas are corrupted, both flags are `False`, so they "agree" and the trial is counted as a `silent_failure`, even though two independent faults almost never produce the same wrong key. The code's own comment calls it a "placeholder -- see caveat below".
* c190's 10 "silent failures" (p=0.1: 1, p=0.3: 3, p=0.5: 6) are exactly the both-replicas-faulted trials. Counting them as silent is the artifact.
* `mitigation_v2` c12 does the check correctly (`np.array_equal(out_1, out_2)` against a clean reference) and its comment calls silent failure "vanishingly rare".
* Not a sign flip and not a `>`/`<` reversal. It is a wrong equality criterion in a superseded draft (also note it is **redundant PA**, not TMR, as the recovered doc says).

### 5. `Block` parity cache: structurally CONFIRMED, not touched
* `qne/cascade/reconciliation.py:42-52`: `correct_orig_key_bit` guards with `corrected_bit_positions` (a bit can never be re-corrected), flips the bit, *then* may flip it back via `maybe_flip_reconciliation_state_bit`, and updates `Block.current_parity` through `flip_parity_in_all_blocks_containing_bit` exactly once. That matches the recovered description of the stale-parity case.
* The `arbitrary_bit` "handled case" was not re-verified.
* Per instructions: do not fix without understanding the effect on already-reported results.

## Paper-text discrepancies (reported, NOT changed)

| Paper claim (per recovered doc) | What the data says | Status |
|---|---|---|
| "52%" | `sdc_realchannel_finalkey_allkeys_asymptotic.csv`, p=0.5: **any-mismatch rate = 0.52**, **silent (verification passed) rate = 0.46**. | **CONFIRMED**: 52% is the any-mismatch rate, not the silent rate. Toeplitz equivalents at p=0.5: any 0.273, silent 0.213. |
| QBER "<0.2%" across keys | Keys 0-4 QBER range **0.26%-1.58%**, mean **0.78%** (`key_pairs_metadata.csv`). With keys 5-9 the range is 0.26%-2.35%. | **CONFIRMED mismatch with the data.** |

Additional observation: in the Toeplitz/final-key sweeps the any-mismatch rate is already **0.06 at p=0.001** while the silent rate is 0.00, so a baseline mismatch exists independent of fault firing (the `20_data_cleaning` baseline-contamination logic addresses part of this). Worth a sentence in the paper if "silent" and "any" are both reported.

## Phase 5 finding: the 1.08x redundant-PA overhead

`notebooks/core/master_reproduction.ipynb` re-measures both overheads. Re-running the `28_mitigation_overhead` c3 method gives **1.8-1.9x**, and dropping the first 5 trials (steady state) gives **2.00x**, which is what two extractions must cost. The stored 1.32 ms "single extraction" mean is dominated by one-time first-call warm-up averaged into 30 trials (here the first call is ~0.28 ms against ~0.09 ms steady state; a few ms of one-off cost on the original machine is enough to produce 1.32 ms), which makes the redundant run look almost free. **The paper's 1.08x should be re-examined** before it is relied on. The TMR ratio (2.69x stored, ~3.0x re-measured) is structurally ~3x and less affected. I have not changed any paper text or the original notebook.

## Master notebook (Phase 5)

`notebooks/core/master_reproduction.ipynb` reproduces all cited numbers and figures in 7 s. Result of the last run: **71 of 71 exact and figure checks pass** (Table 4, both χ² fits, CMH, reconciliation χ²=93.05, 1.87x, b-values/χ²=7.91, both leave-one-key-out results, Pearson/Spearman, ξ₁/ξ₂, ξ₁≈15.69, zero-fault baseline, RPA 100% detection, TMR 0/100 with Wilson CI, **Table 5 from the 5-key snapshot (93.76%)**, and Figs 4, 5, 6a, 6b, 7, 8, 9 pixel-identical to `results/figures/`). The only mismatch is the 1.08x timing above. Every figure uses an explicit `rc_context`, which removes the Fig 6b run-order dependence described in "Known bugs 2". It writes figures to a temp directory and nothing into `results/`.

Not reproducible from data alone: `30_scale_up_experiments` c5 and `mitigation_v2` c16-21 (the TMR collection itself) need the FABRIC slice; the master reproduces their *results* from `mitigation_tmr_realchannel.csv`. Also, `29_poster_figures` c7 (poster Fig 3) iterates the live 10-key metadata, so it shows the 96.0% mean, not the paper's 93.8%; it was not changed.

## Provenance note: `reconciliation_clean.csv` (Figs 4, 6b)

`results/data/reconciliation_clean.csv` (4000 rows, keys 0-4, n=100 per key and probability) is kept as the authoritative input for Figs 4 and 6b. Comparison run on this data versus alternatives (same analysis path):

| Dataset | Rows | Keys | chi-square (dof) |
|---|---|---|---|
| committed `reconciliation_clean.csv` | 4000 | 0-4 | **7.91 (35)**, the cited value |
| raw `..._asymptotic_fixed.csv` | 1600 | 0-1 only | 3.40 (14); leave-one-key-out not possible with 2 keys |
| original clean file (commit `663d9cd`, n=10) | 400 | 0-4 | 10.71 (35) |

Raw n=100 data for keys 0-1 is in the repo and identical to the clean file's keys 0-1 rows. Raw data for keys 2-4 is not in the repo; the clean file's values for them are consistent with keys 0-1 (mean `total_corrections` 32-35). Known provenance gap, not a data-quality issue. Repo decision (author): keep the 4000-row file.

## Cell-index shift after Tier A removal

Tier A (25 empty/duplicate/overwritten-draft/debug cells, approved) was removed from 8 core notebooks. **All cell indices quoted elsewhere in this document and in CLUTTER_REVIEW.md's Phase 1 tables are the pre-removal indices.** To convert: `new = old - (number of removed indices below old)`.

| Notebook | Removed (old indices) |
|---|---|
| `paper_figures_and_reconciliation_fit` | c7, c23 |
| `sdc_sweeps_all5keys` | c25, c34, c44, c51, c57, c65, c66, c88, c108, c127, c139, c188, c191, c199 |
| `mitigation_v2_redundant_pa_tmr` | c9, c30 |
| `23_finitekey_vs_asymptotic` | c12, c13 |
| `29_poster_figures` | c10, c11 |
| `30_scale_up_experiments` | c36 |
| `10_sdc_real` | c13 |
| `28_mitigation_overhead` | c8 |

None of the removed cells is cited. Verification: all 282 surviving code cells in the 8 notebooks have identical execution status before and after the removal (same harness, same machine).

## Second index shift: approved Tier B removals (B1, B2, B3, B4, B5, B9, B14-B18)

Applied after Tier A. Indices below are the indices **after Tier A and before this round**; apply the same rule (`new = old - removed indices below old`) as a second step after the Tier A conversion.

| Notebook | Removed |
|---|---|
| `sdc_sweeps_all5keys` | c13, c16, c23, c32, c34, c132 |
| `10_sdc_real` | c4, c5, c6, c9, c12 |

B1, B2 and B5 wrote result files that are still on disk (`sdc_mock_doseresponse_withverification.csv`, `sdc_mock_allkeys_finitekey.csv`, `fig_allkeys_pooled.png`); the code that produced them is now gone from the notebook (still in git history). B9 held the arbitrary-bit result "49/49 self-corrected" (also in git history). Verified: all 182 surviving code cells in the two notebooks keep identical execution status.

## Third index shift: approved Tier B removals (B6, B7, B8, B10, B11, B12)

Applied after the second shift. Whole cells deleted; indices below are those *after* the Tier A and first Tier B shifts and *before* this one. Rule: `new = old - (number of removed indices below old)`.

| Notebook | Removed (pre-this-shift indices) | Clutter IDs |
|---|---|---|
| `sdc_sweeps_all5keys` | 79, 80, 86, 156 | B6, B7, B8, B10 |
| `mitigation_v2_redundant_pa_tmr` | 12, 23 | B11, B12 |

Notes: B10 was the failed `synthetic_local` sweep (`synthetic_local_recon_sweep.csv` is still on disk; the remaining `synthetic_local` cells are kept). B11 made `results/figures/heatmaps/redundant_pa_sweep.png` (PNG still on disk, referenced nowhere). Safety check: 170 + 15 surviving code cells in the two notebooks have identical execution status before and after.

## Fourth index shift: second-site cells moved out of `30_scale_up_experiments`

The second-site (NCSA <-> TOKY) section was **moved, not deleted**, to `notebooks/exploratory/second_site_ncsa_toky_experiments.ipynb` (cells verbatim, plus an explanatory markdown header and a copy of the shared setup cell 8). Reason: no evidence yet that the paper reports a second site. Moving *does* shift cell indices in the source notebook exactly as deletion would; it is reversible because the original indices are recorded here and in git history (`git revert` of the move commit restores the notebook).

Moved (indices before this shift): markdown 7; code 9, 10, 14, 15, 16, 18, 20, 26-35 (the 13 author-decision cells c10, c15, c18, c26-c35, plus c9, c14, c16, c20 and the section header, which they depend on or which only describe them). Stayed in core: c8 (shared setup), c11-13, c17, c19 (keys 5-9 recovery and the 10-key `key_pairs_metadata.csv`; these are not second-site work), and all other cells. Rule: `new = old - (number of moved indices below old)`.

Safety check: the 15 surviving code cells of `30_scale_up_experiments` have identical execution status before and after; the 17 moved code cells have the same statuses in the new notebook as they had in place. To move back: append those cells to `30_scale_up_experiments` and add the `PAPER_TRACEBACK.md` rows then.
