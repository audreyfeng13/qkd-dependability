from math import comb, ceil
import numpy as np
import pandas as pd
from pathlib import Path

def m_block(iteration_nr, qber):
    if iteration_nr == 1:
        return ceil(0.73 / qber)
    return 2 * m_block(iteration_nr - 1, qber)

def P_survive_point_estimate(K, N, m):
    K = int(round(K))
    pop = N - 1
    sample = m - 1
    denom = comb(pop, sample)
    s = 0
    for i in range(1, sample + 1, 2):  # ODD i -- fault contributes 1 (odd) already; need odd+odd=even total to survive
        if i <= K and (sample - i) <= (pop - K):
            s += comb(K, i) * comb(pop - K, sample - i)
    return s / denom

def P_odd_point(K, N, m):
    K = int(round(K))
    denom = comb(N, m)
    s = 0
    for i in range(1, m + 1, 2):
        if i <= K and (m - i) <= (N - K):
            s += comb(K, i) * comb(N - K, m - i)
    return s / denom

metadata_path = Path(__file__).resolve().parent.parent / "results" / "key_pairs_metadata.csv"
key_pairs_df = pd.read_csv(str(metadata_path))
key_pairs = key_pairs_df[["index", "n_bits", "qber"]].to_dict("records")

print(f"{'idx':<4}{'n_bits':<8}{'QBER':<10}{'blocks (m1..m4)':<24}{'per-pass survive: p1':<10}{'p2':<10}{'p3':<10}{'p4':<10}   |  {'P(mm|p1)':<12}{'P(mm|p2)':<12}{'P(mm|p3)':<12}{'P(mm|p4)':<12}")
results = []
for kp in key_pairs:
    n_i, q_i = kp["n_bits"], kp["qber"]
    m_sizes = [m_block(i, q_i) for i in range(1, 5)]
    K = n_i * q_i
    survive = []
    for m in m_sizes:
        ps = P_survive_point_estimate(K, n_i, m)
        survive.append(ps)
        K = K - (n_i / m) * P_odd_point(K, n_i, m)
    mismatch_from = [float(np.prod(survive[i:])) for i in range(4)]
    results.append({"index": kp["index"], "n_bits": n_i, "qber": q_i,
                     "blocks": m_sizes, "per_pass_survive": survive,
                     "mismatch_from_pass": mismatch_from})
    print(f"{kp['index']:<4}{n_i:<8}{q_i:<10.5f}{str(m_sizes):<24}"
          f"{survive[0]:<10.5f}{survive[1]:<10.5f}{survive[2]:<10.5f}{survive[3]:<10.5f}   |  "
          f"{mismatch_from[0]:<12.5f}{mismatch_from[1]:<12.5f}{mismatch_from[2]:<12.5f}{mismatch_from[3]:<12.5f}")
