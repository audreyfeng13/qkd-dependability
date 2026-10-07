#!/usr/bin/env python3
"""Standalone driver for the full single-axis fault-injection sweep (all 8 axes,
15 reps per grid point), run under tmux so it survives disconnects.

Results stream incrementally to results/single_axis_sweeps.json (rewritten after
every single run, inside run_single_axis_sweeps itself). This script just
provides the entry point + a clear start/end banner for the log.
"""
import sys
import time

PROJECT_DIR = "/home/fabric/work/qkd-dependability"
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR + "/scripts")
import deploy_fabric as df

SLICE_NAME = "qfabric-bb84-2"
SCENARIO = "validation/scenarios/fabric_1km.yml"
N_RUNS = 15

print(f"=== single-axis sweep driver starting at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} ===", flush=True)
print(f"n_runs (reps per grid point) = {N_RUNS}", flush=True)

fablib = df.get_fablib()
slice_obj = fablib.get_slice(name=SLICE_NAME)
print(f"Slice '{SLICE_NAME}' state: {slice_obj.get_state()}", flush=True)

rows = df.run_single_axis_sweeps(slice_obj, scenario_path=SCENARIO, n_runs=N_RUNS)

print(f"\n=== DONE at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}: {len(rows)} total rows ===", flush=True)
