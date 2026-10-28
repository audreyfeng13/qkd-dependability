# notebooks/

Analysis and experiment notebooks. This is distinct from the repo-root `README.md` (project overview) and from `scripts/README.md` (FABRIC-side scripts).

## The core / exploratory split

| Folder | What belongs here | Rule |
|---|---|---|
| `core/` | Notebooks that **produce a number, table or figure cited in the paper**, plus `master_reproduction.ipynb`. | Traced in `PAPER_TRACEBACK.md` (paper artifact → notebook → cell). |
| `exploratory/` | Real analysis that the paper does **not** cite: setup walkthroughs (`00`-`05`), network-effect and baseline sweeps (`06`-`08`), netem tests (`16`-`18`), alternative models, site-2 (`second_site_ncsa_toky_experiments`) and FABRIC debugging, plus `archive/` (older copies of notebooks). | Kept for provenance; may be stale. |

If a notebook gains a paper citation, move it to `core/` and add it to `PAPER_TRACEBACK.md`.

## Start here: `core/master_reproduction.ipynb`

One notebook that reproduces every cited figure, table and number from the committed data in `results/data/` in about 7 seconds, no FABRIC access needed. It compares each result with the expected value (and each figure pixel-by-pixel with `results/figures/`) and ends with a summary table. It uses `results/data/key_pairs_metadata_table5_5keys.csv` for Table 5.

## Core notebooks and what they produce

| Notebook | Role | Paper artifacts |
|---|---|---|
| `master_reproduction.ipynb` | everything, end to end | all of the below |
| `paper_figures_and_reconciliation_fit.ipynb` | figures and reconciliation-model fit | Figs 4, 5, 6a, 6b, 7, 8, 9; b-values and χ²=7.91; leave-one-key-out |
| `sdc_sweeps_all5keys.ipynb` | most of the statistics (large, partly exploratory) | Table 4, χ² fits, CMH, 1.87x ratio, Pearson/Spearman, ξ₁/ξ₂ |
| `20_data_cleaning_and_integrity.ipynb` | **writes** the `*_clean.csv` files used by the figures | inputs to Figs 4, 5, 6b |
| `23_finitekey_vs_asymptotic.ipynb` | finite-key vs asymptotic length | Table 5 (use the 5-key snapshot, see below) |
| `mitigation_v2_redundant_pa_tmr.ipynb` | redundant PA and TMR | RPA detection; TMR runs 0-19 |
| `30_scale_up_experiments.ipynb` | TMR n=100, keys 5-9 (second-site cells moved to `exploratory/second_site_ncsa_toky_experiments.ipynb`) | TMR 0/100 and CI; 10-key metadata |
| `28_mitigation_overhead.ipynb` | overhead timing | overhead ratios (see the 1.08x caveat in `PAPER_TRACEBACK.md`) |
| `29_poster_figures.ipynb` | poster / headline figures | poster Figs 1-3 |
| `10_sdc_real.ipynb` | real-channel setup and key collection | inputs |

Which core notebooks need FABRIC: cells that call `deploy.get_fablib()`, `bob.execute(...)`, `upload_file`, etc. only run with a live slice. The analysis cells run locally.

## Conventions

* **Project root.** Every notebook finds the repo root with `next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "pyproject.toml").exists())`, so it works from `core/`, `exploratory/` or `exploratory/archive/`. Run Jupyter from anywhere inside the repo.
* **Where data lives.** CSV/JSON inputs and outputs: `results/data/`. Figures: `results/figures/`. Backups and superseded raw runs awaiting review: `results/_review_before_delete/`.
* **Table 5 input.** `results/data/key_pairs_metadata.csv` now has 10 keys (keys 5-9 were appended later). Table 5 must use `results/data/key_pairs_metadata_table5_5keys.csv` (93.76%); the live file gives 96.05%.
* **rcParams leakage.** `paper_figures_and_reconciliation_fit` sets global matplotlib styles in several cells, so running it top-to-bottom changes Fig 6b and the per-key fit figures compared with the committed PNGs. `master_reproduction.ipynb` uses an explicit `rc_context` per figure and does not have this problem.
* **Remote paths** like `results/bob_sifted_bits.json` in commands sent to FABRIC nodes are the nodes' own directories; see `scripts/README.md`.

## Pending cleanup

Proposed deletions of clutter cells are listed in `CLUTTER_REVIEW.md` (Phase 4) and are **not applied** until approved. Cell indices quoted in `PAPER_TRACEBACK.md` refer to the current layout and will be regenerated after any approved removal.
