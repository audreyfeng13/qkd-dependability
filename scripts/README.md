# scripts/

Command-line code that **runs on or against FABRIC nodes**, plus environment setup and one offline analysis tool. This directory is distinct from the repo-root `README.md` (project overview) and from `notebooks/README.md` (analysis notebooks).

## Contents

| File | Purpose | Runs where |
|---|---|---|
| `deploy_fabric.py` | Provisions the 3-node FABRIC slice (Alice, BMv2 switch, Bob), installs BMv2, compiles the P4 program, runs BB84 and the parameter sweeps. Imported as a module by the notebooks (`import deploy_fabric as deploy`). | locally, drives FABRIC |
| `bob_cascade_driver.py` | Bob side of a real-channel Cascade reconciliation + Toeplitz privacy-amplification run, with optional SDC fault injection at all four points and a post-PA verification step. Computes the output length once and sends it to Alice. | on a FABRIC node |
| `alice_cascade_responder.py` | Alice side of the same run (parity responder + extraction + verification). | on a FABRIC node |
| `netem.py` | Applies/clears `tc netem` impairment on the classical Cascade port only. | on a FABRIC node |
| `run_single_axis_sweep_driver.py` | Standalone entry point for the full single-axis fault sweep, intended to run under `tmux` so it survives disconnects. | from the environment that holds the FABRIC slice |
| `analyze_new_keys.py` | Offline analysis of any collected key-pair set (peeling-model prediction per key). Needs no FABRIC connection; takes a metadata CSV path, e.g. `python scripts/analyze_new_keys.py results/data/key_pairs_metadata.csv`. | locally |
| `install_bmv2.sh`, `setup_switch_docker.sh`, `setup_sequence_env.sh`, `setup_netsquid_env.sh` | Environment provisioning (BMv2, switch Docker image, SeQUeNCe / NetSquid virtualenvs). | on FABRIC nodes |
| `package_artifact.sh` | Stages a copy of the repo for artifact submission and **strips notebook outputs and execution counts**. Handles notebooks in any subfolder of `notebooks/`. | locally |
| `(old) bob_cascade_driver.py` | Earlier version of `bob_cascade_driver.py`, kept for reference. Superseded; the space/parentheses in the name make it awkward to import. Candidate for removal. | not used |

## How this relates to the notebooks (core / exploratory)

* The **core** notebooks in `notebooks/core/` that *collect* data (`01_real_channel_setup_and_collection`, `05_scale_up_tmr_n100_and_keys_5_9`, `04_mitigation_redundant_pa_tmr`) call these scripts indirectly: the notebooks upload the project to the nodes (`deploy.upload_project`), `qne/cascade/sweep_utils.py` executes `bob_cascade_driver.py` / `alice_cascade_responder.py` there over SSH, and the result files are downloaded into `results/data/`.
* The core notebooks that *analyse* data (`08_paper_figures_and_reconciliation_fit`, `03_sdc_fault_models_and_statistics`, `07_finitekey_vs_asymptotic`, ...) and the **`00_master_reproduction.ipynb`** need **none** of these scripts. They read `results/data/` and import `qne`.
* The **exploratory** notebooks (setup walkthroughs `x01`-`x05`, network-effect sweeps `x06`-`x08`, netem tests `x23`-`x26`, ...) use `deploy_fabric.py` and the netem helpers to drive FABRIC experiments.

## Path conventions

* `deploy_fabric.py` writes local outputs to `results/data/` (relative to the repo root).
* Paths such as `results/bob_sifted_bits.json` **inside the driver/responder commands refer to the remote node's own `~/qfabric/results/` directory**, not to this repository's `results/data/`. They are intentionally unchanged by the repository reorganization.
* Absolute paths of the form `/home/fabric/work/...` in older notebooks and in `results/data/key_pairs_metadata.csv` are FABRIC-node paths and do not resolve on a local checkout.
