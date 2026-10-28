# Data provenance notes (found while reviewing Tier B)

## 1. Why the chi-square values differ (B6, B7, B8 vs. the cited c119)

| Version | Data | "Observed" counts | Result |
|---|---|---|---|
| old B6 (`chi_square_fit`, "full merged") | Existing + recovered runs concatenated with **no dedup by seed** (1365 Toeplitz / 1184 final-key rows; unequal n per prob) | **any** mismatch | χ²=451.09 (final-key), rejected |
| old B8 ("Final ... clean data only") | `toeplitz_clean.csv` / `final_key_clean.csv` = **384 rows, seeds 42-51 only** (10 runs per key/prob, baseline-contaminated runs dropped) | any mismatch (= silent after cleaning) | Toeplitz 9.66, final-key 4.11; not rejected |
| **c119 (cited)** | `sdc_realchannel_*_allkeys_asymptotic.csv` = **1200 rows, 30 unique seeds (42-71) per key x prob, zero duplicate seeds** | **silent only** (keys differ **and** verification passed) | Toeplitz 5.63 (p=0.69), final-key 10.21 (p=0.25); not rejected |

* B6 and B8 are different analyses on different data **and** a different observed quantity. The model `p*l/(l+t)*0.5` predicts *silent* mismatches, so comparing it with *any* mismatch is wrong whenever baseline (no-fault) mismatches exist: on the current raw CSV, any-mismatch gives χ² of 1567.5 (Toeplitz) and 751.6 (final key) purely because of baseline mismatches (63 and 64 rows with no fault fired).
* **c119 does not have the staleness problem.** It reads the current raw CSV (30 unique seeds per cell), and there are **0 silent rows with no fault fired**, so baseline contamination cannot leak into a silent-only count. It reproduces exactly in `master_reproduction`.
* **Caveat that does apply to c119:** its denominator still includes the 63/64 baseline-contaminated runs (reconciliation failed by itself, caught by verification, so they are non-silent but still counted as trials). Dropping them is not neutral: the same silent-only test on the (stale, smaller) cleaned file gives 9.66 / 4.11. The conclusion (model not rejected) is unchanged either way, but the paper should say which denominator it uses.

## 2. The committed `*_clean.csv` files do not match what the cleaning notebook produces today

Re-running `20_data_cleaning_and_integrity` **alone** in a fresh copy of the repo (all cells succeed) gives different files from the committed ones:

| File | Committed rows | Regenerated rows |
|---|---|---|
| `toeplitz_clean.csv`, `final_key_clean.csv` | 384 | 1128 |
| `toeplitz_fk_clean.csv` / `final_key_fk_clean.csv` | 384 / 384 | 773 / 768 |
| `verify_digest_clean.csv` / `verify_digest_fk_clean.csv` | 384 / 384 | 384 / 768 |
| `reconciliation_clean.csv` | **4000** (100 runs per key x prob, seeds 42-141) | **1600** |
| `reconciliation_fk_clean.csv` | 400 | 800 |
| `mock_clean.csv` | 4800 | 4800 (content differs) |

* The committed Toeplitz/final-key clean files are from the **older n=10 collection** (seeds 42-51); the raw CSVs were later extended to n=30.
* **`reconciliation_clean.csv` feeds Figs 4 and 6b and the reconciliation statistics.** The committed 4000-row file has 100 runs per cell, but the only raw reconciliation file in the repo (`sdc_realchannel_reconciliation_allkeys_asymptotic_fixed.csv`) has 1600 rows. **The raw data behind the 4000-row file is not in the repo**, and `20_data_cleaning_and_integrity` c7 cannot recreate it. The master notebook reproduces the cited numbers from the committed 4000-row file, so the *numbers* are reproducible, but their upstream provenance is not.
* Not changed. Needs the author to locate the raw n=100 reconciliation collection (or confirm how the 4000-row file was built).

## 3. B13 / "Table 2"

`finitekey_vs_asymptotic_table2_10keys.csv` is the **same finite-key table as Table 5**, computed deliberately for all 10 keys (the notebook states it responds to reviewer feedback #9, "de-risk Table 2 from being sensitive to any one key"). Same root cause as the Table 5 issue (keys 5-9 exist), but not a bug: it is a self-contained 10-row CSV, mean 96.05% for 10 keys, 93.76% for the first 5. The table is called "Table 1", "Table 2" and "Table 5" in different cells, so numbering is unstable across drafts. If the paper reports 10 keys, the master notebook's Table 5 section should switch from the snapshot to this table; if it reports 5, the snapshot fix already covers it. The paper PDFs available contain only "Table I" (fault-injection parameters), so I cannot say which applies.

## 4. `all_results.tar.gz` vs. other copies

The tarball is an early archived set of 5 JSON files. The differences are **different experiments, not metadata**: e.g. `fabric_alice_results.json` in the tar has `scenario_name='polarization_fidelity=1.0'`, 100000 photons sent, QBER 0.0, whereas `results/data/` has `fabric_1km`, 10000 photons, QBER 0.0105, and `old messy results/` has `dist_50`, QBER 0.0052. `network_effects.json` in the tar is a 167-key list (many conditions); the other copies hold a single run (`baseline_run_1` or `lhs_0`). `fabric_bob_results.json` exists only in the tar. These file names are overwritten by each run, so the tar preserves values the current copies lost.

## Resolved: Table 5 reports 5 keys (author confirmation)

The paper's Table 5 reports **5 keys**. The master notebook's Table 5 section therefore stays on `results/data/key_pairs_metadata_table5_5keys.csv` (93.76%). `finitekey_vs_asymptotic_table2_10keys.csv` (B13's output, 10 keys, 96.05%) answers a different reviewer question (feedback #9, all 10 keys); it is exploratory and not used by the master notebook. B13 itself is still in `30_scale_up_experiments` (undecided).
