# QFabric: QKD Dependability & Cross-Validation Framework

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

**QFabric** is a quantum network emulation framework that models **BB84 Quantum Key Distribution (QKD)** over programmable hardware (**P4 / BMv2 switches**) and real-world testbeds (such as **FABRIC**). This repository contains the node emulation software, P4 data-plane specifications, cross-validation suite, deployment scripts, parameter sweeps, and analysis notebooks.

---

## 🌟 Architecture Overview

```
                      +-------------------+
                      |   Alice (QNE)     |
                      +---------+---------+
                                |
             +------------------+------------------+
             | Quantum Channel                     | Classical TCP
             | (Custom Ethernet EthernetType)      | (Sifting / Basis)
             v                                     v
   +--------------------+               +--------------------+
   |   BMv2 P4 Switch   |               |     Bob (QNE)      |
   | (Fiber Loss Model) | ------------> | (Single Photon Det)|
   +--------------------+               +--------------------+
```

1. **QNE (`qne/`)**: The Quantum Node Emulator package implementing Alice, Bob, single-photon detection models, BB84 protocol sifting, and classical TCP channel signaling.
2. **P4 Data Plane (`p4/`)**: `quantum_channel.p4` implements probabilistic photon attenuation in P4_16 V1Model: $P(\text{loss}) = 1 - 10^{-\alpha \cdot L / 10}$.
3. **Cross-Validation (`validation/`)**: Standardized scenario loader and statistical comparison runner comparing QFabric against **SeQUeNCe**, **NetSquid**, and analytical reference models.
4. **FABRIC Testbed Scripts (`scripts/`)**: Automates node provisioning, P4 compilation, container setup, and remote experiment deployment.
5. **Analysis Notebooks (`notebooks/`)**: Interactive walkthroughs from slice setup to baseline evaluation, cross-validation, and uncertainty sampling.

---

## 📁 Repository Structure

```
qkd-dependability/
├── README.md                 # Project documentation and quickstart guide
├── pyproject.toml            # Python package specification
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore patterns
│
├── qne/                      # Quantum Node Emulator Python package
│   ├── __init__.py           # Package exports (Alice, Bob, Detector, etc.)
│   ├── alice.py              # Alice (photon sender) implementation
│   ├── bob.py                # Bob (photon receiver & detector) implementation
│   ├── bb84.py               # BB84 protocol sifting & QBER estimation
│   ├── channel.py            # TCP classical sifting channel
│   ├── detector.py           # Single-photon detector model (dark count, efficiency)
│   ├── photon.py             # Custom Ethernet photon frame definition
│   ├── config.py             # Scenario YAML parser & configuration classes
│   └── metrics.py            # Latency, throughput, and error metric logger
│
├── p4/                       # P4_16 BMv2 switch data plane
│   ├── bmv2/                 # P4 source files (quantum_channel.p4, headers, parser)
│   └── tests/                # PTF data plane loss model test suite
│
├── validation/               # Cross-validation engine
│   ├── scenario.py           # Platform-neutral ValidationScenario & Result dataclasses
│   ├── run_qfabric.py        # QFabric simulation adapter
│   ├── run_sequence.py       # SeQUeNCe simulator adapter
│   ├── run_netsquid.py       # NetSquid simulator adapter
│   ├── reference_bb84.py     # Independent analytic reference Monte Carlo
│   └── compare.py            # Statistical agreement test & plotting runner
│
├── scenarios/                # Canonical scenario definition YAMLs (symlinked)
│   ├── baseline_1km.yml      # Standard 1km baseline scenario
│   ├── fabric_1km.yml        # FABRIC testbed deployment configuration
│   ├── quick_test.yml        # Lightweight sanity-check scenario
│   ├── sweep_attenuation.yml # Attenuation parameter sweep
│   ├── sweep_dark_count.yml  # Dark count rate sweep
│   ├── sweep_distance.yml    # Fiber distance sweep
│   ├── sweep_efficiency.yml  # Detector efficiency sweep
│   └── sweep_polarization.yml# Polarization fidelity sweep
│
├── scripts/                  # FABRIC deployment, Cascade drivers & environment setup scripts
│   ├── deploy_fabric.py      # Automated slice orchestrator and sweep runner
│   ├── install_bmv2.sh       # BMv2 switch dependency installation script
│   ├── setup_switch_docker.sh# Docker environment builder for P4 switch
│   ├── setup_sequence_env.sh # SeQUeNCe virtualenv provisioner
│   └── setup_netsquid_env.sh # NetSquid virtualenv provisioner
│
├── notebooks/
│   ├── core/                 # Paper-cited notebooks only (see PAPER_TRACEBACK.md)
│   │   ├── master_reproduction.ipynb                    # ONE notebook reproducing every cited figure/table/number
│   │   ├── paper_figures_and_reconciliation_fit.ipynb   # Figs 4-9, b-values, leave-one-key-out
│   │   ├── sdc_sweeps_all5keys.ipynb                    # Most of the paper's statistics
│   │   ├── 20_data_cleaning_and_integrity.ipynb         # Writes the *_clean.csv files
│   │   ├── 23_finitekey_vs_asymptotic.ipynb             # Table 5 (use the 5-key snapshot)
│   │   ├── mitigation_v2_redundant_pa_tmr.ipynb         # Redundant PA / TMR
│   │   ├── 28_mitigation_overhead.ipynb                 # Mitigation overhead
│   │   ├── 29_poster_figures (2).ipynb                  # Poster/paper figures
│   │   ├── 30_scale_up_experiments.ipynb                # TMR n=100, 10 keys, second site
│   │   └── 10_sdc_real.ipynb                            # Real-channel setup and key collection
│   └── exploratory/          # Real but uncited analysis, setup walkthroughs, FABRIC debugging
│       └── archive/          # Older scratch copies
│
├── results/
│   ├── figures/              # All generated figures (heatmaps/, poster_figures/ inside)
│   ├── data/                 # All CSV / JSON data (incl. key_pairs_metadata.csv and the Table 5 snapshot)
│   └── _review_before_delete/# Backups and superseded raw runs, kept only until reviewed
│
└── tests/                    # Unit tests for QNE and validation modules
    ├── test_qne.py           # QNE package unit tests
    └── test_validation.py    # Validation engine unit tests
```

---

## 🚀 Quickstart Guide

### 1. Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/audreyfeng13/qkd-dependability.git
cd qkd-dependability
pip install -e .
```

### 2. Run QFabric Simulation

To run a single BB84 scenario in simulated mode (without requiring P4 hardware or root privileges):

```bash
python -m validation.run_qfabric scenarios/baseline_1km.yml
```

### 3. Run Cross-Validation

Compare QFabric results against simulator backends (SeQUeNCe / NetSquid / Reference):

```bash
python -m validation.compare scenarios/baseline_1km.yml
```

To run a parameter sweep cross-validation and output a plot:

```bash
python -m validation.compare scenarios/sweep_distance.yml --plot results/figures/distance_comparison.png
```

### 4. Run Unit Tests

Verify package integrity and tests:

```bash
python3 -m unittest discover tests
```

---

## 🔬 Scenario Definition Schema

Scenarios are defined in standard YAML format:

```yaml
name: baseline_1km
channel:
  distance_km: 1.0
  attenuation_db_per_km: 0.2
  polarization_fidelity: 1.0
detector:
  efficiency: 0.8
  dark_count_rate: 10.0
protocol:
  num_photons: 100000
  sample_fraction: 0.1
seed: 42
```

---

## 🔁 Reproducibility Notes

**Table 5 (finite-key vs. asymptotic length): use the 5-key snapshot.**
`results/key_pairs_metadata.csv` is a live file: `notebooks/30_scale_up_experiments.ipynb` appended keys 5-9, so it now has 10 rows. The Table 5 cells (`23_finitekey_vs_asymptotic` and `29_poster_figures (2)`) loop over every row of that file, so running them against the live file gives 10 rows and a 96.05% mean reduction instead of the paper's 5 rows and 93.76%.
`results/data/key_pairs_metadata_table5_5keys.csv` is the original 5-key file (verbatim from commit `663d9cd`, from before keys 5-9 were added). **That snapshot is the authoritative input for reproducing Table 5 specifically**: computed from it, the per-key reductions are 99.18, 99.96, 89.40, 88.83 and 91.41%, mean 93.76%. The live file is still correct for analyses that intentionally use all 10 keys.

## 📜 License

This project is licensed under the [Apache 2.0 License](LICENSE).
