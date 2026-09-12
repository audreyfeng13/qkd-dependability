"""
Shared statistical/data-cleaning helpers used across the validation notebooks.

Consolidated from Untitled.ipynb, where several of these (is_baseline_contaminated,
chi_square_goodness_of_fit_reconciliation, wilson_ci) were independently redefined
3-4 times with minor drift between copies. This is the single source of truth going
forward -- import from here rather than redefining locally in a notebook.

Save this alongside your notebooks (e.g. in qne/cascade/) and import with:
    from qne.cascade.validation_utils import *
"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import chi2


def wilson_ci(successes, n, confidence=0.95):
    """Wilson score interval for a binomial proportion -- better-behaved than the
    normal approximation at small n or p near 0/1, both common here."""
    if n == 0:
        return 0.0, 0.0, 0.0
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half_width = (z / denom) * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    return p_hat, max(0, center - half_width), min(1, center + half_width)


def two_proportion_ztest(successes1, n1, successes2, n2):
    """Two-sample z-test for equality of proportions (e.g. real-channel vs. Mock)."""
    p1, p2 = successes1 / n1, successes2 / n2
    p_pool = (successes1 + successes2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return np.nan, np.nan
    z = (p1 - p2) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    return z, p_value


def cohens_h(p1, p2):
    """Effect size for comparing two proportions. |h| < 0.2: small, ~0.5: medium,
    ~0.8: large (Cohen's own conventions) -- use alongside the z-test's p-value,
    since a huge sample can make a trivially small difference 'significant'."""
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))


def mismatch_series(df, col="keys_match"):
    """Dtype-safe mismatch indicator. Prefer this over `~df[col]` directly --
    raw `~` on a nullable/object column silently does the wrong thing on NaNs."""
    return ~df[col].fillna(True).astype(bool)


def is_baseline_contaminated(row):
    """A row is baseline-contaminated if reconciliation left residual errors
    even though this run was meant to be fault-free at this stage (i.e. the
    mismatch didn't come from the fault you think you're studying)."""
    resid = row.get("remaining_errors_after_reconciliation", 0)
    resid = 0 if pd.isna(resid) else resid
    return resid > 0


def is_baseline_failure(row):
    """Stricter check used once, early in the original investigation: fires only
    when NO fault fired at all (faults_fired == {}) and residual errors are still
    present. Kept separate from is_baseline_contaminated (which doesn't care
    whether a fault fired) -- the two ask different questions, don't conflate them."""
    fired = row.get("faults_fired")
    fired_empty = (fired == "{}" or fired == {} or (isinstance(fired, str) and fired.strip() == "{}"))
    resid = row.get("remaining_errors_after_reconciliation", 0)
    resid = 0 if pd.isna(resid) else resid
    return fired_empty and resid > 0


def clean_fault_df(df):
    """Standard cleaning pipeline for a toeplitz/final_key/verify_digest fault
    dataframe: adds `mismatch` and `is_baseline_contaminated`, returns (full_df,
    cleaned_df) so callers can report contamination stats before dropping rows."""
    df = df.copy()
    df["mismatch"] = mismatch_series(df)
    df["is_baseline_contaminated"] = df.apply(is_baseline_contaminated, axis=1)
    clean = df[~df["is_baseline_contaminated"]].copy()
    return df, clean


def chi_square_goodness_of_fit(df_clean, key_pairs_df, predicted_p_func, group_col="prob"):
    """Generic chi-square goodness-of-fit: predicted_p_func(key_row, prob) -> predicted
    mismatch probability. Works for any fault type -- pass a closure over whichever
    ell_func/p1 you're testing."""
    chi2_stat, dof = 0.0, 0
    for key_idx in sorted(df_clean["key_index"].unique()):
        krow = key_pairs_df.iloc[key_idx]
        sub = df_clean[df_clean["key_index"] == key_idx]
        for prob in sorted(sub[group_col].unique()):
            trials = sub[sub[group_col] == prob]
            n_trials = len(trials)
            observed_successes = trials["mismatch"].sum()
            predicted_p = predicted_p_func(krow, prob)
            predicted_p = min(max(predicted_p, 1e-6), 1 - 1e-6)
            expected_successes = n_trials * predicted_p
            expected_failures = n_trials * (1 - predicted_p)
            observed_failures = n_trials - observed_successes
            if expected_successes > 0:
                chi2_stat += (observed_successes - expected_successes) ** 2 / expected_successes
            if expected_failures > 0:
                chi2_stat += (observed_failures - expected_failures) ** 2 / expected_failures
            dof += 1
    p_value = 1 - chi2.cdf(chi2_stat, dof) if dof > 0 else float("nan")
    return chi2_stat, dof, p_value


def report_fit(label, chi2_stat, dof, p_val):
    verdict = "NOT rejected (good fit)" if p_val > 0.05 else "REJECTED -- systematic deviation"
    print(f"{label}: chi2={chi2_stat:.2f}, dof={dof}, p={p_val:.4f} -- {verdict}")
