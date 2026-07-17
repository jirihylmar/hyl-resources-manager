#!/usr/bin/env python3
"""server-report: host capacity + per-project usage, on ANY host.

DESIGN RULE — the whole point of this file:

    Resolve by PROBING. Never identify the host and look up its rule.

An if-EC2-elif-WSL branch is just a longer hardcoded list, and it is silently wrong
on the first host nobody thought of. Where a probe genuinely cannot resolve a value,
say "unknown" HONESTLY. A wrong confident number is far worse than "could not
resolve": the failure class this file exists to avoid is code that SUCCEEDS WRONGLY
and reports success.

Every number below is either MEASURED or explicitly labelled unresolved. There is no
residual plug: the previous version defined `other := used - sum(rows)`, which made
its own headline claim ("rows sum EXACTLY to RAM used") true BY CONSTRUCTION and
therefore unfalsifiable. See VERIFICATION-2026-07-16.md.

Provenance of the design: skills/server-report/VERIFICATION-2026-07-16.md
(14 agents, 235 tool calls, adversarial; measured on WSL2, a read-only EC2 t3.large,
and Docker containers incl. a private cgroup namespace and --cgroupns=host).
"""
import collections
import glob
import gzip
import os
import re
import subprocess
import sys
import time

CLK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
CGROUP2_MAGIC = 0x63677270

# Rendering of a ceiling: is it the real limit, or only an upper bound?
EXACT = "="
BOUNDED = "<="


def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""


def _read1(path):
    return _read(path).strip()


def human(n):
    if n is None:
        return "unknown"
    n = float(n)
    for u in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return "%.0f%s" % (n, u)
        n /= 1024
    return "%.0fP" % n


# ---------------------------------------------------------------------------
# STEP 0 — THE VISIBILITY GATE.  One stat(). Every ceiling below depends on it.
# ---------------------------------------------------------------------------
def visibility():
    """Can I see the true root of the cgroup hierarchy, or am I inside a namespace
    whose ancestors are invisible to me?

    The kernel never creates `cgroup.type` on the true root of a v2 hierarchy. So:
      absent  -> the cgroup root I can see IS the true root. Limits are exact.
      present -> /sys/fs/cgroup is a NON-root cgroup: I am inside a cgroup namespace,
                 ancestors exist above me and I cannot read them. Every limit I can
                 see is an UPPER BOUND — an ancestor may impose a lower one.

    This is what makes the report honest inside a container WITHOUT any container
    detection at all: no /.dockerenv, no /proc/1/cgroup (which returns "0::/" from
    INSIDE a container), no systemd-detect-virt (which reports "wsl" from inside
    Docker on WSL). One stat, ~1ms.

    Test cgroup.type and NOT memory.max: cgroup.type is controller-independent,
    whereas an absent memory.max is ambiguous (true root vs. "memory" simply not
    enabled in the parent's subtree_control).
    """
    try:
        st = os.statvfs("/sys/fs/cgroup")
    except OSError:
        return BOUNDED, "cgroup limits not visible (no /sys/fs/cgroup)"
    if getattr(st, "f_type", None) not in (CGROUP2_MAGIC, None):
        # statvfs may not expose f_type on every libc; fall through to the stat test.
        pass
    if not os.path.isdir("/sys/fs/cgroup"):
        return BOUNDED, "cgroup limits not visible"
    if os.path.exists("/sys/fs/cgroup/cgroup.type"):
        return BOUNDED, ("ancestors above the cgroup-ns root are not visible; "
                         "effective limit may be lower")
    if not os.path.exists("/sys/fs/cgroup/cgroup.controllers"):
        # Not a v2 hierarchy at this path (v1, hybrid, or something else). The v1
        # layout is UNTESTED CODE — say so rather than pretend.
        return BOUNDED, "cgroup v2 not mounted here; v1/hybrid layout is untested — treating limits as unverified"
    return EXACT, ""


def _cgroup_chain():
    """The cgroup directories from my leaf up to /sys/fs/cgroup, inclusive.

    A limit may sit on ANY ancestor (this is exactly what `docker --cgroup-parent`
    and every k8s pod do), so reading only the leaf is not enough. Under a cgroup
    namespace the chain stops at the ns root — hence the BOUNDED rendering above.
    """
    line = _read1("/proc/self/cgroup")
    rel = ""
    for ln in line.splitlines():
        parts = ln.split(":", 2)
        if len(parts) == 3 and parts[0] == "0":  # v2 unified
            rel = parts[2]
            break
    base = "/sys/fs/cgroup"
    chain, cur = [], base + rel
    while True:
        chain.append(cur)
        if os.path.normpath(cur) == base or not cur.startswith(base):
            break
        cur = os.path.dirname(cur)
    return [d for d in chain if os.path.isdir(d)]


def _cgroup_limits(filename):
    """Every numeric limit named `filename` on my cgroup chain.

    The v2 sentinel for "no limit" is the STRING "max" — special-case it before
    int(), or it raises and the whole probe dies.
    """
    out = []
    for d in _cgroup_chain():
        v = _read1(os.path.join(d, filename))
        if not v or v == "max":
            continue
        try:
            out.append(int(v.split()[0]))
        except (ValueError, IndexError):
            continue
    return out


# ---------------------------------------------------------------------------
# RAM
# ---------------------------------------------------------------------------
def meminfo():
    mem = {}
    for line in _read("/proc/meminfo").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            try:
                mem[k.strip()] = int(v.strip().split()[0]) * 1024
            except (ValueError, IndexError):
                pass
    return mem


def kernel_mem():
    """Memory the kernel accounts to ITSELF, measured independently of any process walk.

    This is what makes the reconciliation falsifiable. The residual
    (RAM used − attributed) is by definition whatever is left over, so on its own it
    can absorb any attribution error — which is precisely how the previous version's
    "sums EXACTLY" claim became unfalsifiable. Comparing the residual against a
    SEPARATELY MEASURED figure turns it back into a real check: if the two disagree,
    the attribution is wrong and the report must say so.

    Counted here: only the non-reclaimable parts, because `used` is defined as
    MemTotal − MemAvailable and MemAvailable already credits back SReclaimable and
    reclaimable page cache.
    """
    mi = meminfo()
    keys = ("SUnreclaim", "PageTables", "KernelStack", "Percpu", "VmallocUsed", "Shmem")
    got = {k: mi[k] for k in keys if k in mi}
    return sum(got.values()), got


def ram(vis):
    """(ceiling, used, source, bound) — the number to flag against, and what it is.

    MemTotal is NOT the ceiling in a cgroup-bound process: /proc/meminfo reports the
    NODE's RAM, so a 512M container reads 23G and says "plenty free" while it is
    about to be OOM-killed. Measured: 47x out.
    """
    mi = meminfo()
    total = mi.get("MemTotal")
    if not total:
        return None, None, "unresolved (/proc/meminfo unreadable)", BOUNDED
    limits = _cgroup_limits("memory.max")
    # Sentinel guard: some kernels expose an absurd near-2^63 value rather than "max".
    limits = [v for v in limits if 0 < v < (1 << 62)]
    if limits and min(limits) < total:
        ceiling = min(limits)
        source = "cgroup memory.max"
        # Under a cgroup bound, MemAvailable is the NODE's view and is meaningless
        # here (measured: it moved 0.3G of 18.4G while the cgroup went to 61%).
        cur = _cgroup_limits("memory.current")
        inactive = 0
        for d in _cgroup_chain():
            st = _read(os.path.join(d, "memory.stat"))
            m = re.search(r"^inactive_file (\d+)$", st, re.M)
            if m:
                inactive = int(m.group(1))  # memory.stat is BYTES, not pages, not kB
                break
        used = max(0, (max(cur) if cur else 0) - inactive)
        return ceiling, used, source, vis
    return total, total - mi.get("MemAvailable", 0), "meminfo MemTotal", vis


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------
def cpu_capacity(vis):
    """(cores, source, bound). Neither affinity nor quota subsumes the other —
    measured in both directions — so take the binding minimum of both."""
    try:
        affinity = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        affinity = os.cpu_count() or 1
    quotas = []
    for d in _cgroup_chain():
        v = _read1(os.path.join(d, "cpu.max"))
        if not v or v.startswith("max"):
            continue
        try:
            quota, period = v.split()[:2]
            quotas.append(int(quota) / int(period))
        except (ValueError, ZeroDivisionError, IndexError):
            continue
    if quotas and min(quotas) < affinity:
        return min(quotas), "cgroup cpu.max quota", vis
    return float(affinity), "sched_getaffinity", vis


def proc_stat_busy():
    """(busy_ticks, total_ticks) from the /proc/stat AGGREGATE.

    This — never the sum of per-pid deltas — is the host total. Processes that exit
    mid-window vanish from a per-pid sum: measured 3.375% against this aggregate's
    10.130%, a 3.0x UNDER-read that prints OK while the cores are genuinely busy.
    """
    for line in _read("/proc/stat").splitlines():
        if line.startswith("cpu "):
            f = [int(x) for x in line.split()[1:]]
            idle = f[3] + (f[4] if len(f) > 4 else 0)  # idle + iowait
            return sum(f) - idle, sum(f)
    return 0, 0


def steal_ticks():
    for line in _read("/proc/stat").splitlines():
        if line.startswith("cpu "):
            f = line.split()[1:]
            return int(f[7]) if len(f) > 7 else 0
    return 0


# ---------------------------------------------------------------------------
# DISK
# ---------------------------------------------------------------------------
def _mount_of(path):
    """The mount point backing `path` — walk up while st_dev stays the same.

    "/" is the wrong target when the project lives on another filesystem.
    """
    path = os.path.abspath(path)
    try:
        dev = os.stat(path).st_dev
    except OSError:
        return "/"
    while path != "/":
        parent = os.path.dirname(path)
        try:
            if os.stat(parent).st_dev != dev:
                return path
        except OSError:
            return path
        path = parent
    return "/"


def _source_dev(mount):
    for line in _read("/proc/mounts").splitlines():
        f = line.split()
        if len(f) >= 2 and f[1] == mount:
            return f[0]
    return ""


def _thin_provenance(mount):
    """VERIFIED / KNOWN THIN / UNKNOWN.

    Thin provisioning is not a WSL quirk: sparse VM disks (qcow2, VMDK thin, vhdx),
    LVM thin pools and overlayfs on a smaller store all report free space they cannot
    honour. There is NO generic way to learn the backing store's real ceiling from
    inside the guest, so the honest output is PROVENANCE, not a number.

    Do NOT "fix" this by probing an overlay upperdir: measured 0/5 resolvable, and the
    obvious repair returns the naive number STAMPED VERIFIED — worse than not trying.
    """
    dev = _source_dev(mount)
    base = os.path.basename(dev)
    base = re.sub(r"\d+$", "", base) if base.startswith(("sd", "vd", "hd")) else base
    for p in glob.glob("/sys/block/%s/device/scsi_disk/*/thin_provisioning" % base):
        if _read1(p) == "1":
            return "UNVERIFIED — KNOWN THIN", ("device reports thin provisioning: free space is not "
                                               "guaranteed by the backing store")
    if not base or not os.path.isdir("/sys/block/%s" % base):
        return "UNVERIFIED — UNKNOWN", "cannot identify the backing device"
    # Attribute absent (e.g. NVMe): absence is NOT evidence of thick provisioning.
    return "UNVERIFIED — UNKNOWN", "backing store cannot be verified from inside this host"


def disk(project_path):
    mount = _mount_of(project_path)
    try:
        v = os.statvfs(mount)
    except OSError:
        return None
    # used must use f_bfree, NOT f_bavail: f_bavail excludes root-reserved blocks, so
    # (f_blocks - f_bavail) counts the reserve as USED. Measured: 51G / 5.1pp out on
    # WSL, 16M on EC2 — from the same code.
    total = v.f_blocks * v.f_frsize
    used = (v.f_blocks - v.f_bfree) * v.f_frsize
    avail = v.f_bavail * v.f_frsize
    prov, why = _thin_provenance(mount)
    return {"mount": mount, "total": total, "used": used, "avail": avail,
            "pct": 100.0 * used / total if total else 0.0, "prov": prov, "why": why}


# ---------------------------------------------------------------------------
# OOM
# ---------------------------------------------------------------------------
def oom(vis):
    """Two independent counters, then every readable detail source MERGED.

    Never rank-and-stop: measured, `journalctl -k` works where dmesg is EPERM, and
    a source that correctly reports zero must not be discarded (a `cmd | grep`
    presence test does exactly that — grep exits 1 on zero matches).

    Never say "since boot": the two real 14GB kills on this estate PREDATE the current
    boot, so vmstat cannot see them and journalctl cannot either. Only kern.log held
    them. Each source's window is derived from ITS OWN content.
    """
    out = {"counters": [], "events": [], "notes": []}

    # Tier 1a — cgroup counter. Absent at the true root: that is "unavailable", NOT 0.
    found = False
    for d in _cgroup_chain():
        ev = _read(os.path.join(d, "memory.events"))
        m = re.search(r"^oom_kill (\d+)$", ev, re.M)
        if m:
            out["counters"].append(("cgroup memory.events", int(m.group(1)),
                                    "this cgroup subtree, since the cgroup was created"))
            found = True
            break
    if not found:
        out["counters"].append(("cgroup memory.events", None,
                                "unavailable (no memory.events on this cgroup chain)"))

    # Tier 1b — kernel counter. NOT namespaced: inside a container it counts other
    # tenants' kills too, so it must not be attributed to this session.
    m = re.search(r"^oom_kill (\d+)$", _read("/proc/vmstat"), re.M)
    if m:
        # NOT namespaced. Inside a cgroup namespace this counts the whole HOST's
        # kills, including other tenants' — printing it bare would imply "you were
        # killed N times" when you may have been killed none.
        window = ("since boot, host-wide — NOT namespaced: under a cgroup namespace "
                  "these may belong to another tenant, do not attribute them here"
                  if vis == BOUNDED else "since boot, host-wide")
        out["counters"].append(("/proc/vmstat oom_kill", int(m.group(1)), window))
    else:
        out["counters"].append(("/proc/vmstat oom_kill", None, "unavailable"))

    # Tier 2 — detail. Merge everything readable; label each source's own window.
    pat = re.compile(r"(Out of memory|oom-kill|Killed process)", re.I)
    kill = re.compile(r"Killed process (\d+) \(([^)]*)\).*?anon-rss:(\d+)kB", re.I)

    def _scan(name, text, window):
        if not text:
            return
        hits = [ln for ln in text.splitlines() if pat.search(ln)]
        out["events"].append({"source": name, "window": window, "count": len(hits),
                              "detail": [kill.search(h).groups() for h in hits if kill.search(h)]})

    if _read1("/proc/sys/kernel/dmesg_restrict") == "0":
        try:
            r = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                _scan("dmesg", r.stdout, "kernel ring buffer — wiped by a restart")
        except (OSError, subprocess.SubprocessError):
            out["notes"].append("dmesg: could not run")
    else:
        out["notes"].append("dmesg: restricted (kernel.dmesg_restrict) — NOT evidence of zero kills")

    try:
        r = subprocess.run(["journalctl", "-k", "--no-pager", "-q"],
                           capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            _scan("journalctl -k", r.stdout, "journal retention")
        else:
            out["notes"].append("journalctl -k: unavailable — NOT evidence of zero kills")
    except (OSError, subprocess.SubprocessError):
        out["notes"].append("journalctl: not present — NOT evidence of zero kills")

    logs = sorted(glob.glob("/var/log/kern.log*"))
    text = ""
    for f in logs:
        try:
            if f.endswith(".gz"):
                with gzip.open(f, "rt", errors="replace") as fh:
                    text += fh.read()
            else:
                text += _read(f)
        except OSError:
            out["notes"].append("%s: unreadable" % f)
    if text:
        _scan("kern.log (+rotations)", text, "log rotation window — typically weeks")
    elif logs:
        out["notes"].append("kern.log present but unreadable — NOT evidence of zero kills")

    return out


# ---------------------------------------------------------------------------
# IDENTITY — a rendering, never a gate
# ---------------------------------------------------------------------------
def identity():
    """Print what the firmware DECLARES. Never infer the host from it.

    Banned, each disproven by running it:
      /proc/1/cgroup      -> "0::/" FROM INSIDE a container
      systemd-detect-virt -> "wsl", rc=0, from inside Docker ON a WSL host
      /sys/hypervisor/uuid-> absent on real Nitro EC2 AND on WSL (0 of 3 hosts)
      /etc/os-release     -> the IMAGE's distro, not the host's
    """
    bits = []
    dmi = {k: _read1("/sys/class/dmi/id/" + k) for k in
           ("sys_vendor", "product_name", "board_asset_tag", "chassis_asset_tag")}
    dmi = {k: v for k, v in dmi.items() if v and v not in ("None", "Not Specified")}
    if dmi.get("sys_vendor"):
        bits.append(dmi["sys_vendor"])
    if dmi.get("product_name"):
        bits.append(dmi["product_name"])
    markers = []
    for path, tag in (("/.dockerenv", "docker marker"), ("/run/.containerenv", "podman marker"),
                      ("/run/WSL", "WSL marker")):
        if os.path.exists(path):
            markers.append(tag)
    for env, tag in (("container", "$container"), ("KUBERNETES_SERVICE_HOST", "k8s env")):
        if os.environ.get(env):
            markers.append(tag)
    kernel = (_read1("/proc/sys/kernel/osrelease") or "?")
    host = (_read1("/proc/sys/kernel/hostname") or "?")
    if not bits and not markers:
        return "%s · unidentified host · kernel %s · no DMI, no container markers" % (host, kernel)
    line = "%s · %s" % (host, " ".join(bits) if bits else "no DMI vendor declaration")
    line += " · kernel %s (KERNEL, not host)" % kernel
    if markers:
        line += " · markers: " + ", ".join(markers)
    return line


def imds_az():
    """NAMED EXCEPTION 3 — the only probe permitted to touch the network, and only
    when the AZ is explicitly asked for (--az).

    Gated on the firmware declaring the vendor that owns this proprietary protocol.
    Even past the gate it stays off by default: DMI already yields instance id and
    type byte-identical to IMDS, so the call buys ONLY the AZ. Reachability is not
    identity — never infer the host from whether 169.254.169.254 answers.
    """
    vendor_fields = ("sys_vendor", "chassis_asset_tag", "board_vendor", "bios_vendor")
    if not any(_read1("/sys/class/dmi/id/" + f) == "Amazon EC2" for f in vendor_fields):
        return None, "az unknown (IMDS not queried: no DMI vendor declaration)"
    import urllib.request
    base = "http://169.254.169.254/latest"
    try:
        req = urllib.request.Request(base + "/api/token", method="PUT",
                                     headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"})
        tok = urllib.request.urlopen(req, timeout=1.5).read().decode()
        req = urllib.request.Request(base + "/meta-data/placement/availability-zone",
                                     headers={"X-aws-ec2-metadata-token": tok})
        return urllib.request.urlopen(req, timeout=1.5).read().decode(), ""
    except Exception:
        return None, "az unknown (DMI declares EC2 but IMDS did not answer)"


# ---------------------------------------------------------------------------
# PROCESS ATTRIBUTION
# ---------------------------------------------------------------------------
def snapshot():
    out = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        st = _read("/proc/%s/stat" % pid)
        if not st or ")" not in st:
            continue
        try:
            tail = st[st.rfind(")") + 2:].split()
            out[int(pid)] = {
                "ppid": int(tail[1]),
                "sid": int(tail[3]),
                "cpu": int(tail[11]) + int(tail[12]),
                "rss": int(tail[21]) * PAGE,
                "comm": st[st.find("(") + 1:st.rfind(")")],
                "cmd": _read("/proc/%s/cmdline" % pid).replace("\0", " ").strip(),
            }
        except (ValueError, IndexError):
            continue
    return out


def _pss(pid, fallback):
    """PSS if we may read it; RSS otherwise — and the caller is told which, because a
    mixed PSS/RSS column cannot honestly claim to be either."""
    try:
        for line in open("/proc/%d/smaps_rollup" % pid):
            if line.startswith("Pss:"):
                return int(line.split()[1]) * 1024, True
    except (OSError, ValueError):
        pass
    return fallback, False


def _is_mcp(pid):
    """Structural, not textual: an MCP server speaks JSON-RPC over stdio, so fd0 AND
    fd1 are both a socket or a pipe.

    The old substring rule ("mcp" in cmdline) over-counted 2x ON THE BOX (4 procs for
    2 servers) and false-positived a bare sleeper, bash wrappers and an ssh — and it
    fed the headline divisor, so the headline inherited the error.
    """
    try:
        m0 = os.stat("/proc/%d/fd/0" % pid).st_mode
        m1 = os.stat("/proc/%d/fd/1" % pid).st_mode
    except OSError:
        return False
    import stat as _s
    ok = lambda m: _s.S_ISSOCK(m) or _s.S_ISFIFO(m)
    return ok(m0) and ok(m1)


def _cwd(pid):
    try:
        return os.readlink("/proc/%d/cwd" % pid)
    except OSError:
        return None


def sessions(snap):
    """Group by project, keyed on each claude root's cwd.

    Attribution = union(ppid subtree, SID group). Measured: NEITHER is a superset of
    the other — `setsid` leaves the process tree (and on WSL orphans reparent to the
    Relay process, NOT pid 1, so a pid-1 check misses them), while `env -i` scrubs the
    session id. Using either alone silently loses memory into the unattributed row.
    """
    children = collections.defaultdict(list)
    for pid, p in snap.items():
        children[p["ppid"]].append(pid)

    def subtree(root, seen, depth=0):
        # Depth cap: an unbounded recursive walk is a crash surface on a deep tree.
        if depth > 200:
            return []
        acc = [root]
        for c in children.get(root, []):
            if c not in seen:
                seen.add(c)
                acc += subtree(c, seen, depth + 1)
        return acc

    by_sid = collections.defaultdict(list)
    for pid, p in snap.items():
        by_sid[p["sid"]].append(pid)

    roots = [pid for pid, p in snap.items() if p["comm"] == "claude" and "claude" in p["cmd"]]
    claimed, groups = set(), []
    for r in roots:
        # Read `claimed` INSIDE the loop: a nested root (a session running `claude -p`
        # from a Bash tool) is inside an outer root's subtree and would otherwise be
        # counted twice — invisibly, because the old residual shrank by exactly that.
        if r in claimed:
            continue
        members = set(subtree(r, {r})) | set(by_sid.get(snap[r]["sid"], []))
        members -= claimed
        claimed |= members
        groups.append((r, members))
    return roots, claimed, groups


def flag(pct, warn, crit, trustworthy=True):
    if not trustworthy:
        return "UNVERIFIED"
    return "FULL" if pct >= crit else "WATCH" if pct >= warn else "OK"


def main():
    argv = sys.argv[1:]
    want_az = "--az" in argv
    interval = 2.0
    for a in argv:
        if a.startswith("--sample="):
            try:
                interval = max(0.2, float(a.split("=", 1)[1]))
            except ValueError:
                pass

    vis, vis_note = visibility()

    # --- sample ---
    b0, t0 = proc_stat_busy()
    st0 = steal_ticks()
    s0 = snapshot()
    time.sleep(interval)
    s1 = snapshot()
    b1, t1 = proc_stat_busy()
    st1 = steal_ticks()

    cores, cpu_src, cpu_bound = cpu_capacity(vis)
    # Host busy% comes from the /proc/stat AGGREGATE — never the per-pid sum.
    busy_pct = 100.0 * (b1 - b0) / (t1 - t0) if t1 > t0 else 0.0
    steal_pct = 100.0 * (st1 - st0) / (t1 - t0) if t1 > t0 else 0.0

    for pid, p in s1.items():
        prev = s0.get(pid, {}).get("cpu", p["cpu"])
        p["pct"] = 100.0 * (p["cpu"] - prev) / (interval * CLK * max(cores, 0.01))

    roots, claimed, groups = sessions(s1)
    rss_fallbacks = [0]

    def mem_of(pids):
        tot = 0
        for pid in pids:
            if pid not in s1:
                continue
            v, is_pss = _pss(pid, s1[pid]["rss"])
            if not is_pss:
                rss_fallbacks[0] += 1
            tot += v
        return tot

    per_project = collections.defaultdict(
        lambda: {"sessions": 0, "procs": 0, "mcp": 0, "mem": 0, "pct": 0.0})
    for r, members in groups:
        cwd = _cwd(r)
        proj = (cwd.replace(os.path.expanduser("~"), "~") if cwd else "(cwd unreadable)")
        d = per_project[proj]
        d["sessions"] += 1
        d["procs"] += len(members)
        d["mcp"] += sum(1 for m in members if m != r and _is_mcp(m))
        d["mem"] += mem_of(members)
        d["pct"] += sum(s1[m]["pct"] for m in members if m in s1)

    # Everything not attributed to a session, MEASURED — not a remainder.
    unclaimed = [pid for pid in s1 if pid not in claimed]
    unattr_mem = mem_of(unclaimed)
    unattr_pct = sum(s1[pid]["pct"] for pid in unclaimed)

    ceiling, mem_used, mem_src, mem_bound = ram(vis)
    mi = meminfo()
    swap_total = mi.get("SwapTotal", 0)
    swap_used = swap_total - mi.get("SwapFree", 0)
    d = disk(os.getcwd())
    sess_mem = sum(v["mem"] for v in per_project.values())
    sess_pct = sum(v["pct"] for v in per_project.values())

    pct_of = lambda n: (100.0 * n / ceiling) if ceiling else 0.0

    # --- render ---
    print("HOST CAPACITY REPORT")
    print("host: %s" % identity())
    if want_az:
        az, why = imds_az()
        print("az:   %s" % (az or why))
    if vis == BOUNDED:
        print("!!    limits are UPPER BOUNDS: %s" % vis_note)
    print()

    print("CAPACITY")
    cb = "" if cpu_bound == EXACT else "<= "
    print("  CPU   %s%.2f cores (%s) · %.0f%% busy over %.0fs  [%s]"
          % (cb, cores, cpu_src, busy_pct, interval,
             flag(busy_pct, 70, 90, cpu_bound == EXACT)))
    if steal_pct >= 0.5:
        print("        steal %.0f%% — this host is not getting the CPU it asked for" % steal_pct)
    print("        sustained ceiling unknown (a burstable instance's credit balance is not "
          "exposed to the guest)")
    if ceiling:
        mb = "" if mem_bound == EXACT else "<= "
        print("  RAM   %s / %s%s used (%.0f%%) · source: %s  [%s]"
              % (human(mem_used), mb, human(ceiling), pct_of(mem_used), mem_src,
                 flag(pct_of(mem_used), 75, 90, mem_bound == EXACT)))
    else:
        print("  RAM   unknown — %s" % mem_src)
    if swap_total:
        note = "  (host-wide; swap is not namespaced)" if vis == BOUNDED else ""
        print("  SWAP  %s / %s used (%.0f%%)%s" % (human(swap_used), human(swap_total),
                                                   100.0 * swap_used / swap_total, note))
    else:
        print("  SWAP  none configured")
    if d:
        # The flag fires on USED%, which is a real measurement of this filesystem —
        # statvfs does not lie about how full the fs is. What thin provisioning makes
        # unverifiable is whether the FREE space can actually be written: the backing
        # store may not be able to honour it. So the flag stands and the caveat
        # attaches to `free`, where it belongs. (Suppressing the flag on UNVERIFIED
        # would kill it outright: no tested host resolves to VERIFIED.)
        print("  DISK  %s / %s used (%.0f%%) · mount %s  [%s]"
              % (human(d["used"]), human(d["total"]), d["pct"], d["mount"],
                 flag(d["pct"], 80, 90)))
        if d["prov"].startswith("VERIFIED"):
            print("        free %s (backing store verified)" % human(d["avail"]))
        else:
            print("        free %s — %s" % (human(d["avail"]), d["prov"]))
            print("        %s" % d["why"])
    else:
        print("  DISK  unknown — statvfs failed")
    print()

    print("OOM KILLS")
    o = oom(vis)
    for name, n, window in o["counters"]:
        print("  %-24s %-9s (%s)" % (name, "unavailable" if n is None else n, window))
    for e in o["events"]:
        print("  %-24s %-9s (%s)" % (e["source"], e["count"], e["window"]))
        for pid, comm, kb in e["detail"][-3:]:
            print("        killed pid %s (%s) anon-rss %s" % (pid, comm, human(int(kb) * 1024)))
    for n in o["notes"]:
        print("  ! %s" % n)
    cg = [n for name, n, _ in o["counters"] if n and name.startswith("cgroup")]
    counted = [n for _, n, _ in o["counters"] if n]
    if (cg or (counted and vis == EXACT)) and not any(e["count"] for e in o["events"]):
        print("  ! a counter reports kills but no detail source could name them — detail source blind")
    elif counted and vis == BOUNDED and not any(e["count"] for e in o["events"]):
        print("  (the host-wide counter above is non-zero, but nothing here can attribute those")
        print("   kills to this cgroup — they may be another tenant's)")
    if not counted and not any(e["count"] for e in o["events"]):
        print("  none recorded by this kernel (a kill enforced above the guest — e.g. by a")
        print("  hypervisor or host OS — leaves no trace here, so this is not proof none occurred)")
    print()

    print("USAGE BY PROJECT (claude session cwd)")
    print("  %-34s%5s%6s%5s%7s%9s%7s" % ("project", "sess", "proc", "mcp", "cpu%", "mem", "mem%"))
    print("  " + "-" * 73)
    for proj, v in sorted(per_project.items(), key=lambda kv: -kv[1]["mem"]):
        print("  %-34s%5d%6d%5d%6.0f%%%9s%6.1f%%"
              % (proj[:34], v["sessions"], v["procs"], v["mcp"], v["pct"],
                 human(v["mem"]), pct_of(v["mem"])))
    print("  %-34s%5s%6d%5s%6.0f%%%9s%6.1f%%"
          % ("unattributed processes", "", len(unclaimed), "", unattr_pct,
             human(unattr_mem), pct_of(unattr_mem)))
    print("  " + "-" * 73)

    # Reconciliation is a CHECK, not a claim. The residual is printed as its own
    # measured gap — it is never back-filled to force the columns to agree. The
    # previous version defined the residual as the difference, which made its
    # "sums EXACTLY" claim true by construction and therefore unfalsifiable.
    if ceiling and mem_used is not None:
        residual = mem_used - sess_mem - unattr_mem
        kmem, kparts = kernel_mem()
        print("  %-34s%5s%6s%5s%7s%9s%6.1f%%"
              % ("residual (RAM used - attributed)", "", "", "", "", human(residual),
                 pct_of(residual)))
        print("  %-34s%5s%6s%5s%7s%9s%6.1f%%"
              % ("kernel, measured independently", "", "", "", "", human(kmem), pct_of(kmem)))
        # THE CHECK. The residual is a subtraction and can absorb anything; kernel_mem
        # is an independent measurement. Agreement is evidence. Disagreement is a
        # finding, and it is REPORTED — never back-filled to make the columns agree.
        drift = residual - kmem
        tol = max(256 * 1024 * 1024, 0.10 * mem_used)
        if abs(drift) <= tol:
            print("  CHECK PASS: residual %s vs kernel accounting %s (drift %s, within %s)"
                  % (human(residual), human(kmem), human(drift), human(tol)))
            print("  (tolerance is coarse ON PURPOSE: `used` is MemTotal-MemAvailable, and")
            print("   MemAvailable is a kernel HEURISTIC. Exact reconciliation against an")
            print("   estimate is not achievable — the old claim of it was false twice over.)"
                  )
        else:
            print("  CHECK FAIL: residual %s does NOT match kernel accounting %s — drift %s."
                  % (human(residual), human(kmem), human(drift)))
            print("  ! %s memory is unexplained. The per-project rows are NOT accounting for"
                  % human(abs(drift)))
            print("  ! this host. Do not trust the attribution above. (kernel parts: %s)"
                  % ", ".join("%s=%s" % (k, human(v)) for k, v in kparts.items()))
    # COVERAGE CHECK — a different question from the reconciliation above, and the
    # one that catches a broken root-finder. Deleting every session root does NOT
    # break accounting: the memory simply moves into the (measured) unattributed row
    # and the residual is unchanged. What it breaks is ATTRIBUTION — and the symptom
    # is visible: claude processes sitting in the unattributed row.
    orphans = [pid for pid in unclaimed
               if s1[pid]["comm"] == "claude" and "claude" in s1[pid]["cmd"]]
    if orphans:
        print("  ! ATTRIBUTION FAILURE: %d claude process(es) are unattributed (pids %s)."
              % (len(orphans), ", ".join(str(p) for p in orphans[:5])))
        print("  ! The root-finder is not recognising live sessions. The per-project rows")
        print("  ! below-count by an unknown amount. Do not trust them.")

    cpu_gap = busy_pct - sess_pct - unattr_pct
    if abs(cpu_gap) >= 1.0:
        print("  ! cpu attribution misses %.0f%% of host busy (processes that exited mid-window)"
              % cpu_gap)
    if rss_fallbacks[0]:
        print("  ! %d process(es) fell back from PSS to RSS (not readable) — those rows over-count"
              % rss_fallbacks[0])
    print("  mem is PSS where readable. Rows are ATTRIBUTION; the host total is measured")
    print("  independently (RAM from %s, CPU from the /proc/stat aggregate)." % mem_src)
    print()

    # --- headline ---
    cands = []
    if ceiling:
        cands.append(("RAM", pct_of(mem_used), mem_bound == EXACT))
    if d:
        cands.append(("disk", d["pct"], d["prov"].startswith("VERIFIED")))
    cands.append(("CPU", busy_pct, cpu_bound == EXACT))
    binder = max(cands, key=lambda x: x[1])
    print("BINDING CONSTRAINT: %s at %.0f%%%s."
          % (binder[0], binder[1], "" if binder[2] else " (an UPPER BOUND — the real figure may be worse)"))
    if per_project:
        heaviest = max(per_project.items(), key=lambda kv: kv[1]["mem"])
        lightest = min(per_project.items(), key=lambda kv: kv[1]["mem"])
        print("  heaviest project: %s at %s; lightest %s. Sessions are NOT interchangeable —"
              % (heaviest[0], human(heaviest[1]["mem"]), human(lightest[1]["mem"])))
        print("  size a new one against the HEAVIEST, not the mean.")
    # No "N more sessions fit": that promise divides free RAM by a mean, and the
    # measured failures on this estate were single sessions ~14x the mean. It is
    # withheld entirely on a bounded/unverified ceiling, where it would be a guess
    # wearing a number.
    if vis == BOUNDED or (ceiling and mem_bound != EXACT):
        print("  headroom is NOT estimated: the ceiling is an upper bound, so any estimate")
        print("  would be a guess wearing a number.")


if __name__ == "__main__":
    main()
