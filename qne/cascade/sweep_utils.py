"""
Reusable sweep orchestration for SDC fault-injection experiments:
local (Mock-session) sweeps and real-channel (FABRIC node) sweeps.
"""
import re
import json as _json
import pandas as pd
from qne.cascade.sdc_runs import run_sdc_experiment_safe
import subprocess
import datetime


def extract_output_path(stdout_text, marker):
    """Parse the actual, timestamped output filename from a driver
    script's printed stdout."""
    match = re.search(rf"{marker} (\S+\.json)", stdout_text)
    return match.group(1) if match else None


def run_condition_sweep(alice_key, bob_key, qber, label, n_runs=10, base_seed=42, **fault_kwargs):
    """Run n_runs trials of a local (Mock-session) fault condition and
    collect results into a DataFrame."""
    rows = []
    for run in range(n_runs):
        result = run_sdc_experiment_safe(
            alice_key=alice_key, bob_key=bob_key, qber=qber,
            seed=base_seed + run, **fault_kwargs,
        )
        result["condition"] = label
        result["run"] = run
        rows.append(result)
        print(f"  run {run}: non_convergent={result['non_convergent']}, "
              f"keys_match={result.get('keys_match')}")
    return pd.DataFrame(rows)


def summarize_outcomes(df, label):
    """Summarize outcomes into disjoint buckets, distinguishing measurement
    failures from confirmed mismatches, and (if present) verification
    outcomes from raw key-match outcomes."""
    non_convergent = df["non_convergent"].sum()
    converged = ~df["non_convergent"]

    measurement_failed = converged & df["keys_match"].isna()
    matched = converged & (df["keys_match"] == True)
    mismatched = converged & (df["keys_match"] == False)

    n = len(df)
    print(f"\n=== {label} (n={n}) ===")
    print(f"  Non-convergent:            {non_convergent}/{n}")
    print(f"  Converged, matched:        {matched.sum()}/{n}")
    print(f"  Converged, mismatched:     {mismatched.sum()}/{n}")
    print(f"  Converged, unmeasurable:   {measurement_failed.sum()}/{n}")

    result = {
        "condition": label, "n": n,
        "non_convergent": non_convergent,
        "converged_matched": matched.sum(),
        "converged_mismatched": mismatched.sum(),
        "converged_measurement_failed": measurement_failed.sum(),
    }

    if "verification_passed" in df.columns:
        undetected = converged & mismatched & (df["verification_passed"] == True)
        detected = converged & mismatched & (df["verification_passed"] == False)
        print(f"  Mismatched, UNDETECTED by verification: {undetected.sum()}/{n}  <-- silent corruption")
        print(f"  Mismatched, detected by verification:   {detected.sum()}/{n}")
        result["undetected_mismatch"] = undetected.sum()
        result["detected_mismatch"] = detected.sum()

    if measurement_failed.sum() > 0:
        print(f"  WARNING: {measurement_failed.sum()} run(s) had confirmed "
              f"convergence but no measurable key-match result -- these "
              f"are NOT confirmed mismatches and should not be counted as "
              f"SDC detections.")

    return result

def get_code_version():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"git_error: {result.stderr.strip()[:50]}"
    except Exception as e:
        return f"exception: {str(e)[:50]}"


def run_real_channel_trial(bob, alice, bob_ip, real_qber, run, seed, k=0,
                             toeplitz_prob=0.0, final_key_prob=0.0,
                             verify_digest_prob=0.0, timeout=180, length_mode="placeholder"):
    bob_thread = bob.execute_thread(
        f"cd ~/qfabric && ~/qfabric/.venv/bin/python3 scripts/bob_cascade_driver.py "
        f"--key-json results/bob_sifted_bits.json --alice-key-json results/alice_sifted_bits.json "
        f"--host {bob_ip} --port 5200 --qber {real_qber} --k {k} --seed {seed} "
        f"--toeplitz-prob {toeplitz_prob} --final-key-prob {final_key_prob} "
        f"--verify-digest-prob {verify_digest_prob} --length-mode {length_mode} "
        f"--output results/bob_realchannel_run.json"
    )
    alice_thread = alice.execute_thread(
        f"cd ~/qfabric && ~/qfabric/.venv/bin/python3 scripts/alice_cascade_responder.py "
        f"--key-json results/alice_sifted_bits.json --bob-host {bob_ip} --port 5200 "
        f"--seed {seed} --output results/alice_realchannel_run.json"
    )
    bob_out = bob_thread.result(timeout=timeout)
    alice_error = None
    try:
        alice_out = alice_thread.result(timeout=timeout)
    except Exception as e:
        alice_out = ("", str(e))
        alice_error = str(e)

    bob_output_path = extract_output_path(bob_out[0], "Result written to")
    alice_output_path = extract_output_path(alice_out[0], "final key written to")

    if bob_output_path is None:
        return {
            "run": run, "seed": seed, "error": "no bob output path found in stdout",
            "raw_stdout": bob_out[0], "raw_stderr": bob_out[1],
            "keys_match": None, "verification_passed": None, "non_convergent": True,
            "code_version": get_code_version(),
            "collection_timestamp": datetime.datetime.now().isoformat(),
        }

    stdout_bob, _ = bob.execute(f"cat ~/qfabric/{bob_output_path}", quiet=True)
    try:
        bob_result = _json.loads(stdout_bob)
    except _json.JSONDecodeError:
        bob_result = {"error": "no bob output", "raw_stdout": bob_out[0], "raw_stderr": bob_out[1]}

    alice_final_key = None
    if alice_output_path is not None:
        stdout_alice, _ = alice.execute(f"cat ~/qfabric/{alice_output_path}", quiet=True)
        try:
            alice_result = _json.loads(stdout_alice)
            alice_final_key = alice_result.get("alice_final_key")
        except _json.JSONDecodeError:
            pass

    bob_final_key = bob_result.get("bob_final_key")
    if bob_final_key is not None and alice_final_key is not None:
        keys_match = (bob_final_key == alice_final_key)
    else:
        keys_match = None  # measurement failure, NOT a confirmed mismatch

    bob_result["keys_match"] = keys_match
    bob_result["verification_passed"] = bob_result.get("verification_passed")
    bob_result["alice_measurement_error"] = alice_error
    bob_result.pop("bob_final_key", None)
    bob_result.pop("bob_reconciled_bits", None)
    bob_result["run"] = run
    bob_result["seed"] = seed
    bob_result["bob_output_path"] = bob_output_path
    bob_result["alice_output_path"] = alice_output_path

    # --- Provenance: which code version + when, so a future data-quality
    # question ("was this before or after the keys_match fix?") is a column
    # lookup instead of a debugging session. ---
    bob_result["code_version"] = get_code_version()
    bob_result["collection_timestamp"] = datetime.datetime.now().isoformat()

    return bob_result


def run_real_channel_reconciliation_trial(bob, alice, bob_ip, real_qber, run, seed,
                                             reconciliation_prob, k=0, timeout=180,
                                             length_mode="placeholder"):
    bob_thread = bob.execute_thread(
        f"cd ~/qfabric && ~/qfabric/.venv/bin/python3 scripts/bob_cascade_driver.py "
        f"--key-json results/bob_sifted_bits.json --alice-key-json results/alice_sifted_bits.json "
        f"--host {bob_ip} --port 5200 --qber {real_qber} --k {k} --seed {seed} "
        f"--reconciliation-prob {reconciliation_prob} --length-mode {length_mode} "
        f"--output results/bob_recon_run.json"
    )
    alice_thread = alice.execute_thread(
        f"cd ~/qfabric && ~/qfabric/.venv/bin/python3 scripts/alice_cascade_responder.py "
        f"--key-json results/alice_sifted_bits.json --bob-host {bob_ip} --port 5200 "
        f"--seed {seed} --output results/alice_recon_run.json"
    )
    bob_out = bob_thread.result(timeout=timeout)
    alice_error = None
    alice_out = None
    try:
        alice_out = alice_thread.result(timeout=timeout // 2)
    except Exception as e:
        alice_error = str(e)

    bob_output_path = extract_output_path(bob_out[0], "Result written to")
    if bob_output_path is None:
        return {
            "run": run, "seed": seed, "reconciliation_prob": reconciliation_prob,
            "non_convergent": True, "error": bob_out[1],
            "alice_error": alice_error, "keys_match": None,
            "code_version": get_code_version(),
            "collection_timestamp": datetime.datetime.now().isoformat(),
        }

    stdout, _ = bob.execute(f"cat ~/qfabric/{bob_output_path}", quiet=True)
    try:
        result = _json.loads(stdout)
        result["non_convergent"] = False
    except _json.JSONDecodeError:
        result = {"non_convergent": True, "error": bob_out[1], "reconciliation_prob": reconciliation_prob}

    keys_match = None
    alice_output_path = None
    if alice_out is not None:
        alice_output_path = extract_output_path(alice_out[0], "final key written to")
    if alice_output_path is not None and result.get("bob_final_key") is not None:
        alice_stdout, _ = alice.execute(f"cat ~/qfabric/{alice_output_path}", quiet=True)
        try:
            alice_result = _json.loads(alice_stdout)
            alice_final_key = alice_result.get("alice_final_key")
            if alice_final_key is not None:
                keys_match = bool(alice_final_key == result["bob_final_key"])
        except _json.JSONDecodeError:
            pass

    result["keys_match"] = keys_match
    result["alice_error"] = alice_error
    result["alice_output_path"] = alice_output_path
    result.pop("bob_final_key", None)
    result.pop("bob_reconciled_bits", None)
    result["run"] = run
    result["seed"] = seed
    result["bob_output_path"] = bob_output_path

    # --- Provenance, matching run_real_channel_trial ---
    result["code_version"] = get_code_version()
    result["collection_timestamp"] = datetime.datetime.now().isoformat()

    return result


def run_real_channel_cascade_netem_trial(bob, alice, bob_ip, real_qber, run, seed,
                                            bob_iface, alice_iface,
                                            cascade_delay_ms=0.0, cascade_jitter_ms=0.0,
                                            cascade_loss_pct=0.0, k=0, timeout=180,
                                            length_mode="placeholder",
                                            bob_key_json="results/bob_sifted_bits.json",
                                            alice_key_json="results/alice_sifted_bits.json"):
    """Real-channel trial isolating classical-network conditions (delay/
    jitter/loss) to exactly the Cascade reconciliation phase, via
    bob_cascade_driver.py's --cascade-iface/--cascade-delay-ms/... flags.
    tc is armed immediately before reconciliation.reconcile() and disarmed
    immediately after (on both success and the non-convergent RuntimeError
    path) -- PA/verification always run un-impaired. See qne/netem.py.

    No SDC faults are injected here (toeplitz/final-key/reconciliation/
    verify-digest all default to 0 in bob_cascade_driver.py) -- this
    measures the effect of real network conditions alone, not fault
    injection. Do NOT pass --force-non-convergent through this function or
    include it in any sweep grid -- it is a test-only hook (see
    bob_cascade_driver.py) and does not represent a real fault.
    """
    cascade_flags = ""
    if cascade_delay_ms or cascade_loss_pct:
        cascade_flags = (
            f"--cascade-delay-ms {cascade_delay_ms} "
            f"--cascade-jitter-ms {cascade_jitter_ms} "
            f"--cascade-loss-pct {cascade_loss_pct} "
        )
    bob_cascade_flags = f"--cascade-iface {bob_iface} {cascade_flags}" if cascade_flags else ""
    alice_cascade_flags = f"--cascade-iface {alice_iface} {cascade_flags}" if cascade_flags else ""

    bob_thread = bob.execute_thread(
        f"cd ~/qfabric && ~/qfabric/.venv/bin/python3 scripts/bob_cascade_driver.py "
        f"--key-json {bob_key_json} --alice-key-json {alice_key_json} "
        f"--host {bob_ip} --port 5200 --qber {real_qber} --k {k} --seed {seed} "
        f"--length-mode {length_mode} {bob_cascade_flags} "
        f"--output results/bob_cascadenetem_run.json"
    )
    alice_thread = alice.execute_thread(
        f"cd ~/qfabric && ~/qfabric/.venv/bin/python3 scripts/alice_cascade_responder.py "
        f"--key-json {alice_key_json} --bob-host {bob_ip} --port 5200 "
        f"--seed {seed} {alice_cascade_flags} "
        f"--output results/alice_cascadenetem_run.json"
    )
    bob_out = bob_thread.result(timeout=timeout)
    alice_error = None
    alice_out = None
    try:
        alice_out = alice_thread.result(timeout=timeout // 2)
    except Exception as e:
        alice_error = str(e)

    condition_cols = {
        "cascade_delay_ms": cascade_delay_ms, "cascade_jitter_ms": cascade_jitter_ms,
        "cascade_loss_pct": cascade_loss_pct,
    }

    bob_output_path = extract_output_path(bob_out[0], "Result written to")
    if bob_output_path is None:
        return {
            "run": run, "seed": seed, **condition_cols,
            "non_convergent": True, "error": bob_out[1], "alice_error": alice_error,
            "keys_match": None,
            "code_version": get_code_version(),
            "collection_timestamp": datetime.datetime.now().isoformat(),
        }

    stdout, _ = bob.execute(f"cat ~/qfabric/{bob_output_path}", quiet=True)
    try:
        result = _json.loads(stdout)
    except _json.JSONDecodeError:
        result = {"non_convergent": True, "error": bob_out[1]}

    keys_match = None
    alice_output_path = None
    if alice_out is not None:
        alice_output_path = extract_output_path(alice_out[0], "final key written to")
    if alice_output_path is not None and result.get("bob_final_key") is not None:
        alice_stdout, _ = alice.execute(f"cat ~/qfabric/{alice_output_path}", quiet=True)
        try:
            alice_result = _json.loads(alice_stdout)
            alice_final_key = alice_result.get("alice_final_key")
            if alice_final_key is not None:
                keys_match = bool(alice_final_key == result["bob_final_key"])
        except _json.JSONDecodeError:
            pass

    result["keys_match"] = keys_match
    result["alice_error"] = alice_error
    result["alice_output_path"] = alice_output_path
    result.update(condition_cols)
    result.pop("bob_final_key", None)
    result.pop("bob_reconciled_bits", None)
    result["run"] = run
    result["seed"] = seed
    result["bob_output_path"] = bob_output_path

    # --- Provenance, matching run_real_channel_trial / run_real_channel_reconciliation_trial ---
    result["code_version"] = get_code_version()
    result["collection_timestamp"] = datetime.datetime.now().isoformat()

    return result


def collect_key_pairs(deploy, slice_obj, alice, bob, bob_ip, project_dir, n_keys=5,
                        scenario_path="validation/scenarios/fabric_1km.yml",
                        pe_sample_fraction=0.1, pe_seed_base=100000):
    """Collect n_keys sifted key pairs from real FABRIC BB84 runs, then
    perform a genuine parameter-estimation split on each. Saves per-key
    metadata (k_pe, n_bits, qber) to key_pairs_metadata.csv so downstream
    notebooks can look up the correct k/qber WITHOUT recomputing QBER by
    comparing the (already-split) generation bits directly -- doing so
    would re-measure error rate on bits that are supposed to remain
    unmeasured outside the disjoint PE sample."""
    from qne.cascade.key import key_from_sifted_json
    from qne.cascade.parameter_estimation import split_pe_and_generation

    alice_mac = alice.get_interface(network_name="net_alice_switch").get_mac()
    bob_mac = bob.get_interface(network_name="net_switch_bob").get_mac()
    sw_alice_mac = slice_obj.get_node("switch").get_interface(network_name="net_alice_switch").get_mac()

    key_pairs = []
    for i in range(n_keys):
        print(f"\n=== Collecting key pair {i} ===")
        deploy.run_bb84(slice_obj, scenario_path, alice_mac, bob_mac,
                          sw_alice_mac=sw_alice_mac, bob_data_ip=bob_ip)

        stdout, _ = alice.execute("cat ~/qfabric/results/alice_sifted_bits.json", quiet=True)
        alice_raw_path = project_dir / "results" / f"alice_sifted_bits_key{i}_raw.json"
        alice_raw_path.write_text(stdout)

        stdout, _ = bob.execute("cat ~/qfabric/results/bob_sifted_bits.json", quiet=True)
        bob_raw_path = project_dir / "results" / f"bob_sifted_bits_key{i}_raw.json"
        bob_raw_path.write_text(stdout)

        alice_key_full, alice_idx_full = key_from_sifted_json(str(alice_raw_path), "alice_bits")
        bob_key_full, bob_idx_full = key_from_sifted_json(str(bob_raw_path), "bob_bits")

        if alice_idx_full != bob_idx_full:
            print(f"  key pair {i}: index mismatch -- skipping (raw files saved for inspection)")
            continue

        try:
            split = split_pe_and_generation(
                alice_key_full, bob_key_full,
                sample_fraction=pe_sample_fraction, seed=pe_seed_base + i,
            )
        except ValueError as e:
            print(f"  key pair {i}: PE split failed ({e}) -- skipping")
            continue

        m, k, n = split["m"], split["k"], split["n"]
        qber_i = split["qber"]
        alice_key_i, bob_key_i = split["alice_gen"], split["bob_gen"]

        print(f"  key pair {i}: m={m} sifted, k={k} PE sample, n={n} generation bits, "
              f"QBER (from PE sample only) = {qber_i:.4f}")

        alice_path = project_dir / "results" / f"alice_sifted_bits_key{i}.json"
        bob_path = project_dir / "results" / f"bob_sifted_bits_key{i}.json"

        gen_indices = split["gen_indices"]
        alice_matching_indices_gen = [alice_idx_full[idx] for idx in gen_indices]

        alice_path.write_text(_json.dumps({
            "alice_bits": alice_key_i.bits.tolist(),
            "matching_indices": alice_matching_indices_gen,
        }))
        bob_path.write_text(_json.dumps({
            "bob_bits": bob_key_i.bits.tolist(),
            "matching_indices": alice_matching_indices_gen,
        }))

        key_pairs.append({
            "index": i, "m_sifted": m, "k_pe": k, "n_bits": n, "qber": qber_i,
            "alice_path": str(alice_path), "bob_path": str(bob_path),
            "alice_raw_path": str(alice_raw_path), "bob_raw_path": str(bob_raw_path),
        })

        bob.upload_file(str(alice_path), f"qfabric/results/alice_sifted_bits_key{i}.json")
        bob.upload_file(str(bob_path), f"qfabric/results/bob_sifted_bits_key{i}.json")

    df = pd.DataFrame(key_pairs)
    metadata_path = project_dir / "results" / "key_pairs_metadata.csv"
    df.to_csv(str(metadata_path), index=False)
    print(f"\nSaved key-pair metadata (k_pe, n_bits, qber) -> {metadata_path}")
    return df