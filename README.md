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
├── scripts/                  # FABRIC deployment & environment setup scripts
│   ├── deploy_fabric.py      # Automated slice orchestrator and sweep runner
│   ├── install_bmv2.sh       # BMv2 switch dependency installation script
│   ├── setup_switch_docker.sh# Docker environment builder for P4 switch
│   ├── setup_sequence_env.sh # SeQUeNCe virtualenv provisioner
│   └── setup_netsquid_env.sh # NetSquid virtualenv provisioner
│
├── notebooks/                # Numbered analysis & experiment notebooks
│   ├── 00_overview.ipynb               # Overview and execution order
│   ├── 01_setup_slice.ipynb             # FABRIC 3-node slice provisioning
│   ├── 02_run_experiment.ipynb         # Single BB84 run on FABRIC
│   ├── 03_cross_validation.ipynb       # Comparing QFabric vs SeQUeNCe / NetSquid
│   ├── 04_analysis.ipynb               # Result plotting & photon pipeline analysis
│   ├── 05_run_all_scenarios.ipynb      # Batch scenario sweep execution
│   ├── 06_network_effects.ipynb        # Classical network impairment evaluation
│   ├── 07_baseline_runs.ipynb          # Baseline statistical runs
│   ├── 08_uncertainty_sampling.ipynb   # Machine learning / sampling analysis
│   └── archive/                        # Archived scratch notebooks
│
├── results/                  # Experimental results and figures
│   ├── heatmaps/             # Generated parameter sweep heatmaps
│   └── old messy results/    # Archived raw data runs
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
python -m validation.compare scenarios/sweep_distance.yml --plot results/distance_comparison.png
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

## 📜 License

This project is licensed under the [Apache 2.0 License](LICENSE).
