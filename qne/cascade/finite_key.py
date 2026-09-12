"""
Finite-key secret key length calculation, combining:
- Tomamichel-Leverrier (2017): overall finite-key security bound
- Tomamichel, Martinez-Mateo, Pacher, Elkouss (2014), Corollary 2:
  finite-size-corrected Cascade leakage estimate
"""
import math
from scipy.stats import norm
from scipy.optimize import minimize_scalar


def h(x):
    if x <= 0 or x >= 1:
        return 0.0
    return -x * math.log2(x) - (1 - x) * math.log2(1 - x)


def v(x):
    if x <= 0 or x >= 1:
        return 0.0
    return x * (1 - x) * (math.log2(x / (1 - x)))**2


def cascade_leakage(n, Q, epsilon):
    xi = 1 + (1 / math.sqrt(n)) * math.sqrt(v(Q) / h(Q)) * norm.ppf(1 - epsilon)
    return xi * n * h(Q)


def eps_nu(nu, n, k):
    """eps(nu), Tomamichel-Leverrier Eq. (79) / Serfling's inequality
    (Lemma 6). m = n + k; n = key-gen length, k = PE sample size."""
    m = n + k
    return math.exp(-(m - k) * k**2 * nu**2 / (m * (k + 1)))


def key_length_at_nu(nu, n, k, Q, eps_ec, eps_pa, c_bar, r_override=None):
    budget = eps_pa - 2 * eps_nu(nu, n, k)
    if budget <= 0:
        return -math.inf
    r = r_override if r_override is not None else cascade_leakage(n, Q, eps_ec)
    t = math.log2(n)
    return n * (math.log2(1 / c_bar) - h(Q + nu)) - r - t + 2 + 2 * math.log2(budget)


def optimize_nu(n, k, Q, eps_ec=1e-10, eps_pa=1e-10, c_bar=0.5, n_grid=2000, r_override=None):
    nu_max = 0.5 - Q
    if nu_max <= 0:
        raise ValueError("Q must be < 0.5")
    grid = [nu_max * (i + 1) / (n_grid + 1) for i in range(n_grid)]
    vals = [key_length_at_nu(nu, n, k, Q, eps_ec, eps_pa, c_bar, r_override=r_override) for nu in grid]
    best_i = max(range(len(vals)), key=lambda i: vals[i])
    if vals[best_i] == -math.inf:
        raise ValueError(f"No feasible nu in (0, {nu_max:.4f}) for n={n}, k={k}, eps_pa={eps_pa}.")
    lo = grid[max(best_i - 2, 0)]
    hi = grid[min(best_i + 2, len(grid) - 1)]
    res = minimize_scalar(
        lambda nu: -key_length_at_nu(nu, n, k, Q, eps_ec, eps_pa, c_bar, r_override=r_override),
        bounds=(lo, hi), method='bounded'
    )
    best_nu = res.x
    best_term = key_length_at_nu(best_nu, n, k, Q, eps_ec, eps_pa, c_bar, r_override=r_override)
    r = r_override if r_override is not None else cascade_leakage(n, Q, eps_ec)
    t = math.log2(n)
    return best_nu, best_term, r, t


def finite_key_output_length(n, k, Q, eps_pa=1e-10, eps_ec=1e-10, c_bar=0.5):
    """n = generation-string length, k = PE sample size (m = n + k)."""
    best_nu, term, r, t = optimize_nu(n, k, Q, eps_ec=eps_ec, eps_pa=eps_pa, c_bar=c_bar)
    return max(1, int(term)), r, t, best_nu


def asymptotic_key_length(n, Q):
    return int(n * max(0, 1 - 2 * h(Q)))