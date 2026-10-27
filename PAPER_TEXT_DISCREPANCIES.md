# Paper text vs. verified data

**For discussion with the advisor. The paper text has not been changed.**

## Important limit on the "claimed" column

The only paper PDFs I could find (`~/Downloads/QCE26_submission_1845_POS-2PAP_v2.pdf` and `QCE26_POS1845.pdf`; the repo has only `Feng_Audrey_QCE_References.pdf`) are the **2-page poster abstract**. Their text is identical and contains **none** of these claims: no "52", "0.2%", "1.08", "11.39", "Jaccard", no Tables 4/5, no TMR/redundant-PA/silent-mismatch results (searched case-insensitively, 0 hits each). The "claimed" column below is therefore taken from `RECOVERED_FINDINGS.md`, a reconstruction from an earlier session's conversation record, **not** from the paper. Please check each wording against the actual results-paper draft before quoting it.

## The six items

| # | Claimed (per RECOVERED_FINDINGS.md) | Verified data value | Source | Verdict |
|---|---|---|---|---|
| 1 | "52%" framed as a **silent** (undetected) mismatch rate for final-key faults | At p=0.5, final-key faults: **any-mismatch rate = 0.52**, **silent rate (verification passed) = 0.46**. Toeplitz at p=0.5: any 0.273, silent 0.213. | `sdc_realchannel_finalkey_allkeys_asymptotic.csv` (1200 rows); `master_reproduction` Table 4 | 52% is the *any-mismatch* rate. The silent rate is 46%. |
| 2 | QBER stays "<0.2%" across keys | Keys 0-4: **0.26%-1.58%**, mean **0.78%**. Including keys 5-9: 0.26%-2.35%. | `key_pairs_metadata_table5_5keys.csv`, `key_pairs_metadata.csv` | Contradicted by the data. Only keys 2 and 3 (0.27%, 0.26%) are anywhere near 0.2%, and they exceed it. |
| 3 | Redundant-PA overhead **1.08x** | Original notebook output: 1.32 ms (single) vs 1.42 ms (redundant) = 1.08x. Re-measured with the same method: **1.83-1.89x**. Steady state (first 5 trials dropped): **1.99-2.00x**. First single call ~0.28 ms vs ~0.09 ms steady. | `28_mitigation_overhead` c3; `master_reproduction` section 4c | Does not reproduce. Two extractions must cost ~2x; the stored 1.32 ms single mean is inflated by first-call warm-up. I infer this from steady-state timing here, not from the original machine. TMR (2.69x stored, ~3.0x re-measured) is consistent with its 3x structure. |
| 4 | Model "predicts near-total correction" on a Toeplitz-sized pool (ℓ=2810), at the p used in `sdc_sweeps_all5keys` c186 | c186 hard-codes **p=0.5** and prints **0.000000**, which is correct for that p (majority vote of 3 is a coin flip per position). Same formula, pool 2810, N=3: p=0.5 → 0; p=0.1 → 2.2e-35; **p=0.01 → 0.43; p=1e-3 → 0.992**; p=1e-4 → 0.9999. | `master_reproduction` section 4b | Not a code error. The claim holds only for small p (about 1e-3 or below); the paper sentence should state the p it refers to. |
| 5 | Jaccard overlap **0.15-0.25** between TMR replica error sets | `mitigation_v2` markdown states **~0.08-0.17**. The cell that would compute it (c25) has never produced a saved output. No file or output supports 0.15-0.25. | `mitigation_v2_redundant_pa_tmr` c25-26 (pre-removal indices) | Unsupported by anything in the repo; the only number present disagrees. |
| 6 | TMR residual "**11.39% ± 0.36%**" | The CSV stores a **count**: mean **11.39 residual error bits** (SE 0.36) over 100 voted runs; 0/100 corrected, Wilson 95% CI [0, 3.70%] on the *correction rate*. | `mitigation_tmr_realchannel.csv` | The numbers match but the unit is wrong: bits, not percent. A percentage needs an explicit denominator (e.g. key length). |

## Tokyo / second site search (decision 4)

* Searched both QCE26 PDFs for `toky`, `japan`, `site 2`, `second site`, `second pair`, `NCSA`, `EDUKY`, `kentucky`: **0 matches** for all of them. The only site names in the text are **HAWI** and **FIU** (Fig. 1 caption), and "Urbana, Illinois" in the author affiliation.
* This does **not** settle the question: the PDF is a proposal-style 2-page abstract ("We expect to produce…"), written before the results, and it does not mention the first site pair (NCSA↔EDUKY) either. Neither the results paper nor any other draft was found on this machine (also checked `~/research`, `~/Downloads/qkd-dependability-main.zip`, which holds only the references PDF).
* So absence from this PDF is **not evidence** the NCSA↔TOKY second site is uncited in the results paper. The 13 second-site cells in `30_scale_up_experiments` remain untouched pending your decision.
