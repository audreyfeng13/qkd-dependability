"""Local netem control for scoping classical-channel impairment to exactly
the Cascade reconciliation phase, run directly on the node executing
bob_cascade_driver.py / alice_cascade_responder.py.

This mirrors the existing apply_classical_netem() / clear_classical_netem()
pattern in scripts/deploy_fabric.py (prio qdisc + u32 filter on src/dst TCP
port, so only the targeted port is impaired), but runs `tc` via a local
subprocess instead of over an SSH-based FABlib node.execute() call, because
these driver scripts are themselves executing on the Alice/Bob nodes.

Assumes passwordless sudo for `tc` on this node -- the same assumption
deploy_fabric.py's apply_classical_netem() already makes.
"""
from __future__ import annotations

import subprocess
import time
from typing import Any


def _run(cmd: str) -> tuple[int, str]:
    """Run a shell command, returning (returncode, combined stdout+stderr)."""
    proc = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    return proc.returncode, proc.stdout


def arm_cascade_netem(
    iface: str, port: int, delay_ms: float = 0.0, jitter_ms: float = 0.0,
    loss_pct: float = 0.0,
) -> dict[str, Any]:
    """Impair ONLY TCP:port traffic on `iface`. Raises RuntimeError if the
    tc commands fail (fail loud -- a silently-not-applied delay would
    corrupt the experiment without anyone noticing, exactly the kind of
    thing this project has been bitten by before).

    Returns a dict recording exactly what was applied and a `tc qdisc show`
    snapshot taken immediately after, so callers can persist proof the
    impairment actually took effect (not just that the command exited 0).
    """
    netem = "netem"
    if delay_ms:
        netem += f" delay {delay_ms}ms" + (f" {jitter_ms}ms" if jitter_ms else "")
    if loss_pct:
        netem += f" loss {loss_pct}%"

    cmd = (
        f"sudo tc qdisc del dev {iface} root 2>/dev/null; "
        f"sudo tc qdisc add dev {iface} root handle 1: prio && "
        f"sudo tc qdisc add dev {iface} parent 1:3 handle 30: {netem} && "
        f"sudo tc filter add dev {iface} parent 1:0 protocol ip prio 1 u32 "
        f"match ip dport {port} 0xffff flowid 1:3 && "
        f"sudo tc filter add dev {iface} parent 1:0 protocol ip prio 1 u32 "
        f"match ip sport {port} 0xffff flowid 1:3"
    )
    rc, out = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"arm_cascade_netem failed on {iface}:{port} (rc={rc}): {out}")

    _, verify = _run(f"sudo tc qdisc show dev {iface}")
    return {
        "armed_at": time.time(),
        "iface": iface,
        "port": port,
        "netem_spec": netem,
        "verify_qdisc_show": verify.strip(),
    }


def disarm_cascade_netem(iface: str) -> dict[str, Any]:
    """Remove any netem/tc qdisc previously installed on `iface`. Always
    call this in a `finally` -- a non-convergent Cascade run (or any other
    exception) must never leave the interface impaired for whatever the
    process (or the next sweep point) runs next. Safe to call even if
    nothing was armed."""
    _run(f"sudo tc qdisc del dev {iface} root 2>/dev/null || true")
    _, verify = _run(f"sudo tc qdisc show dev {iface}")
    return {
        "disarmed_at": time.time(),
        "iface": iface,
        "verify_qdisc_show": verify.strip(),
    }
