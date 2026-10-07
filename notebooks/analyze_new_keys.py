"""
Analysis script for any set of collected key pairs -- site-1's original/extended
10 keys, the new Tokyo<->NCSA site-2 keys, or anything collected later.

No FABRIC connection needed, no galois/randextract needed (the peeling model
only uses numpy/scipy). Run this against a metadata CSV + its key JSON files.

For each key it reports:
  - q_hat      : the PE-sample QBER estimate (what the real protocol has at runtime)
  - true_qber  : the true generation-portion QBER, IF the raw bit files are present
                 locally (privileged/retrospective only -- not something a real
                 deployment can know)
  - b_deployable : peeling-model prediction using ONLY q_hat (for both noise and
                 block-sizing) -- the honest, deployable estimate
  - b_retrospective : peeling-model prediction using true_qber for noise and q_hat
                 for block-sizing (matches what actually happened, if true_qber
                 is available) -- explains a specific dataset, not deployable

VALIDATION STATUS (read before trusting these numbers):
  - b_deployable and b_retrospective are well-validated (matches the real
    Reconciliation class to within ~10%) WHEN q_hat and true_qber are close
    (e.g. keys 0, 1, 4 in the site-1 dataset: ratio 0.65-1.95x).
  - b_retrospective is NOT yet well-validated when q_hat and true_qber differ
    by a large factor (e.g. keys 2, 3: ratio ~4x). Spot-checking key 2's
    mismatched-qber zero-fault case against the real Reconciliation class
    gave 0.107 vs. this model's 0.198 -- a ~1.85x overshoot, similar in size
    to the ORIGINAL (unfixed) pair model's bias, even though the sequential
    pass-ordering fix resolved this almost completely for the matched case.
    The cause isn't identified yet (possibly the tie-break rule for which bit
    gets "corrected" in multi-error blocks diverging from real binary search
    at higher local error density). Treat b_retrospective as directionally
    right but only order-of-magnitude reliable for large-mismatch keys until
    this is resolved -- flagged automatically below when qber_ratio is large.

Usage:
    python analyze_new_keys.py /path/to/key_pairs_metadata.csv
    python analyze_new_keys.py /path/to/key_pairs_metadata_site2.csv
"""
import sys
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


# --- Validated sequential peeling model (see conversation for derivation/validation) ---

def m_block(iteration_nr, qber):
    """Cascade's real block-size schedule: pass 1 = ceil(0.73/qber), doubling."""
    if iteration_nr == 1:
        return math.ceil(0.73 / qber)
    return 2 * m_block(iteration_nr - 1, qber)


def peeling_simulation_sequential(N, K, block_qber, n_passes, rng):
    """One trial. Passes are introduced ONE AT A TIME, matching the real
    Reconciliation class's structure (self.iterations only contains passes
    created so far -- pass i's drain can only backtrack into passes < i,
    not future ones). Within each newly-expanded set of active passes, drain
    to a fixed point one correction at a time (queue semantics)."""
    m_sizes = [m_block(i, block_qber) for i in range(1, n_passes + 1)]
    block_labels = np.zeros((K, n_passes), dtype=np.int64)
    for p, m in enumerate(m_sizes):
        positions = rng.choice(N, size=K, replace=False)  # fresh reshuffle each pass
        block_labels[:, p] = positions // m

    unresolved = set(range(K))
    for active_passes in range(1, n_passes + 1):
        while True:
            found = None
            for p in range(active_passes):
                groups = {}
                for e in unresolved:
                    groups.setdefault(block_labels[e, p], []).append(e)
                for members in groups.values():
                    if len(members) % 2 == 1:
                        found = members[0]
                        break
                if found is not None:
                    break
            if found is None:
                break
            unresolved.discard(found)
    return len(unresolved)


def peeling_baseline_probability(N, noise_qber, block_qber, n_sims=5000, seed=0):
    """P(mismatch | no injected fault). noise_qber drives the actual error
    process; block_qber is what Cascade uses to size its blocks -- these
    differ whenever the protocol's own QBER estimate is imperfect, which is
    the normal case (see conversation: this mismatch is the real mechanism,
    not a bug to paper over)."""
    K = round(N * noise_qber)
    if K == 0:
        return 0.0
    rng = np.random.default_rng(seed)
    mismatches = sum(
        1 for _ in range(n_sims)
        if peeling_simulation_sequential(N, K, block_qber, n_passes=4, rng=rng) > 0
    )
    return mismatches / n_sims


# --- Per-key analysis ---

def analyze_keys(metadata_csv_path, n_sims=5000):
    metadata_csv_path = Path(metadata_csv_path)
    results_dir = metadata_csv_path.parent
    meta = pd.read_csv(str(metadata_csv_path))

    rows = []
    for _, row in meta.iterrows():
        idx = int(row["index"])
        n_bits = int(row["n_bits"])
        q_hat = float(row["qber"])

        # Try to recover the true generation-portion QBER directly from the
        # raw bit files, if they're present locally -- this is privileged
        # (retrospective-only) information, kept separate from the
        # deployable prediction.
        true_qber = None
        for col in ("alice_path", "bob_path"):
            if col not in row or pd.isna(row[col]):
                break
        else:
            alice_path = results_dir / Path(row["alice_path"]).name
            bob_path = results_dir / Path(row["bob_path"]).name
            if alice_path.exists() and bob_path.exists():
                with open(alice_path) as f:
                    alice_bits = np.array(json.load(f)["alice_bits"], dtype=np.uint8)
                with open(bob_path) as f:
                    bob_bits = np.array(json.load(f)["bob_bits"], dtype=np.uint8)
                true_qber = int(np.sum(alice_bits != bob_bits)) / n_bits

        b_deployable = peeling_baseline_probability(
            n_bits, noise_qber=q_hat, block_qber=q_hat, n_sims=n_sims, seed=idx
        )

        b_retrospective = None
        if true_qber is not None:
            b_retrospective = peeling_baseline_probability(
                n_bits, noise_qber=true_qber, block_qber=q_hat, n_sims=n_sims, seed=idx + 100000
            )

        rows.append({
            "index": idx, "n_bits": n_bits, "q_hat": q_hat, "true_qber": true_qber,
            "qber_ratio": (true_qber / q_hat) if true_qber else None,
            "b_deployable": b_deployable, "b_retrospective": b_retrospective,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    df = analyze_keys(sys.argv[1])
    pd.set_option("display.float_format", lambda x: f"{x:.5f}")
    print(df.to_string(index=False))

    print("\n--- Summary ---")
    print(f"mean b_deployable (honest, uses only q_hat): {df['b_deployable'].mean():.5f}")
    if df["b_retrospective"].notna().any():
        print(f"mean b_retrospective (uses true qber, retrospective only): "
              f"{df['b_retrospective'].mean():.5f}")
        flagged = df[df["qber_ratio"].notna() & ((df["qber_ratio"] > 2) | (df["qber_ratio"] < 0.5))]
        if len(flagged):
            print(f"\n*** WARNING: b_retrospective is NOT validated for these keys (qber_ratio "
                  f"deviates >2x) -- spot-checks show it can overshoot the real Reconciliation "
                  f"class by ~1.85x in this regime. Treat these specific values as order-of-"
                  f"magnitude only, not precise: ***")
            print(flagged[["index", "q_hat", "true_qber", "qber_ratio", "b_retrospective"]].to_string(index=False))
