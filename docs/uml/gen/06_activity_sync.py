"""06 — Activity diagram: Synchronize with the local folder (UC14), with swimlanes.

Lanes: User | Desktop client (Renderer) | Desktop client (Main / SyncEngine) | API.
Layout is a (lane, row) grid with one node per cell.  Every bent flow carries explicit
waypoints (absolute page coordinates from X()/Y(), which mirror ActivityDiagram._place)
so that no flow passes through another node.

runSyncPlan does not iterate over a single mixed list: the skipped actions are counted once
up front and then two independent loops run, first every upload and then every download.  The
diagram follows that shape — two UML loop idioms in a row, each with a merge above its
"[more …?]" decision; the back-edge leaves the last action of the body downwards and runs up
the outer channel of the API lane, the exit runs down the left channel of the Main lane.  There
is no plan preview: the panel shows a progress bar during the run and the report after it.
"""
from _common import *

LANES = ["User", "Desktop client (Renderer)", "Desktop client (Main / SyncEngine)", "API"]
USER, REN, MAIN, API = 0, 1, 2, 3
LW, RH, HH = 250, 90, 30          # lane width, row height, lane header height

a = ActivityDiagram("Activity diagram — Synchronize with the local folder (UC14)",
                    lanes=LANES, lane_w=LW, row_h=RH, header_h=HH,
                    lane_colors=["blue", "purple", "purple", "grey"])


def X(lane: int, dx: float = 0) -> float:
    """Absolute x of a cell centre (waypoints are page coordinates)."""
    return lane * LW + LW / 2 + dx


def Y(row: int, dy: float = 0) -> float:
    """Absolute y of a cell centre."""
    return HH + 20 + row * RH + RH / 2 + dy


# ActivityDiagram.decision() always draws the question to the RIGHT of the diamond.  In
# this diagram the right corner of every decision is used by an outgoing flow, so the
# question is placed on a free side instead (same rhombus, different label position;
# no wrapping so the question stays on one line).
_RHOMBUS = "rhombus;html=1;fontSize=10;"
_LABEL_POS = {
    "above": "labelPosition=center;verticalLabelPosition=top;align=center;verticalAlign=bottom;spacingBottom=2;",
    "below": "labelPosition=center;verticalLabelPosition=bottom;align=center;verticalAlign=top;spacingTop=2;",
    "upper-left": "labelPosition=left;verticalLabelPosition=top;align=right;verticalAlign=bottom;"
                  "spacingRight=2;spacingBottom=2;",
}


def decision(label: str, lane: int, row: int, where: str, **kw) -> str:
    return a._add(lane, row, 60, 60, label, _RHOMBUS + _LABEL_POS[where], **kw)


def down(src: str, dst: str, label: str = "") -> str:
    return a.flow(src, dst, label, exit_=(0.5, 1), entry=(0.5, 0))


def right(src: str, dst: str, label: str = "") -> str:
    return a.flow(src, dst, label, exit_=(1, 0.5), entry=(0, 0.5))


def left(src: str, dst: str, label: str = "") -> str:
    return a.flow(src, dst, label, exit_=(0, 0.5), entry=(1, 0.5))


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
# start + bound-folder precondition (UC13)
s = a.start(USER, 0)
n_watch = a.note("Desktop: FolderWatcher can trigger\nthis flow automatically (debounced)", REN, 0, w=210)
click = a.action("Click «Synchronize»", USER, 1, SYNC)
d_bound = decision("[folder bound?]", REN, 2, "above")
pick = a.action("Open folder picker", MAIN, 3, SYNC)
save = a.action("Save bound folder path", MAIN, 4, SYNC)
m_bound = a.merge(MAIN, 5)

# scan both sides in parallel, then plan
fork = a.bar(MAIN, 6, w=220)
scan = a.action("Scan local folder\n(LocalFolderScanner)", MAIN, 7, SYNC)
lst = a.action("GET /files\n(list remote FileDto[])", API, 7, LIST)
join = a.bar(MAIN, 8, w=220)
plan = a.action("computeSyncPlan(local, remote)", MAIN, 9, SYNC)
n_rules = a.note("only local → upload;\nonly remote → download;\nboth: same size and\n"
                 "|mtime − updatedAt| ≤ 2 s → skip;\nunparsable remote updatedAt\n→ download;\n"
                 "else the newer side wins;\ndeletions never propagate",
                 API, 9, w=200)
n_ledger = a.note("Web client only: the plan is\nbuilt from reconcileWithLedger(\n"
                  "scanned, ledger); recordTransfer\nand pruneLedger keep the\n"
                  "localStorage ledger in step", REN, 10, w=200)
skipped = a.action("report.skipped =\nplan.skipped.length", MAIN, 10, SYNC)

# execute the plan: first every upload, then every download (runSyncPlan)
# API actions are narrowed and shifted left so that a vertical channel fits on the right of
# the API lane for the two loop back-edges.
API_DX, API_W = -30, 150
m_up = a.merge(MAIN, 11)
d_up = decision("[more uploads?]", MAIN, 12, "upper-left")
post = a.action("POST /files\n(multipart)", API, 12, OPS, w=API_W, dx=API_DX)
upd = a.action("Update FileEntry\n(size, updatedAt,\nmodifiedBy)", API, 13, OPS, w=API_W, h=56, dx=API_DX)
utimes = a.action("utimes(mtime = updatedAt)", MAIN, 14, SYNC)

m_dn = a.merge(MAIN, 16)
d_dn = decision("[more downloads?]", MAIN, 17, "upper-left")
get = a.action("GET\n/files/:id/content", API, 17, OPS, w=API_W, dx=API_DX)
write = a.action("Write file,\nset mtime = updatedAt", MAIN, 18, SYNC)

report = a.action("Show SyncReport", REN, 20, SYNC)
e = a.end(REN, 21)

# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------
a.note_link(n_watch, s)
down(s, click)
a.flow(click, d_bound, points=[(X(USER), Y(2))], exit_=(0.5, 1), entry=(0, 0.5))
f_no_bound = a.flow(d_bound, pick, points=[(X(MAIN), Y(2))], exit_=(1, 0.5), entry=(0.5, 0))
f_yes_bound = a.flow(d_bound, m_bound, points=[(X(REN), Y(5))], exit_=(0.5, 1), entry=(0, 0.5))
down(pick, save)
down(save, m_bound)
down(m_bound, fork)

# fork: scan locally and list remotely in parallel, then join
down(fork, scan)
a.flow(fork, lst, points=[(X(API), Y(6))], exit_=(1, 0.5), entry=(0.5, 0))
down(scan, join)
a.flow(lst, join, points=[(X(API), Y(8))], exit_=(0.5, 1), entry=(1, 0.5))
down(join, plan)
a.note_link(n_rules, plan)
a.note_link(n_ledger, plan)
down(plan, skipped)
down(skipped, m_up)

X_LEFT = X(MAIN, -105)                 # left channel of the Main lane (loop exits)
X_BACK = X(API, 110)                   # outermost channel of the API lane (loop back-edges)

# ---- loop 1: every upload -------------------------------------------------
down(m_up, d_up)
right(d_up, post, "[yes]")
down(post, upd)
a.flow(upd, utimes, points=[(X(API, API_DX), Y(14))], exit_=(0.5, 1), entry=(1, 0.5))
# the back-edge leaves downwards into the gap between two rows, so it never shares the
# y of the "Update FileEntry → utimes" segment
a.flow(utimes, m_up, points=[(X(MAIN), Y(14, 42)), (X_BACK, Y(14, 42)), (X_BACK, Y(11))],
       exit_=(0.5, 1), entry=(1, 0.5))
f_up_done = a.flow(d_up, m_dn, points=[(X_LEFT, Y(12)), (X_LEFT, Y(16))], exit_=(0, 0.5), entry=(0, 0.5))

# ---- loop 2: every download ------------------------------------------------
down(m_dn, d_dn)
right(d_dn, get, "[yes]")
a.flow(get, write, points=[(X(API, API_DX), Y(18))], exit_=(0.5, 1), entry=(1, 0.5))
a.flow(write, m_dn, points=[(X(MAIN), Y(18, 42)), (X_BACK, Y(18, 42)), (X_BACK, Y(16))],
       exit_=(0.5, 1), entry=(1, 0.5))
f_dn_done = a.flow(d_dn, report, points=[(X_LEFT, Y(17)), (X_LEFT, Y(20))], exit_=(0, 0.5), entry=(1, 0.5))

down(report, e)

# Guards of the L-shaped flows are attached as positioned edge labels near the source end
# (draw.io would otherwise centre them on the path, far from the diamond).  Edges exist
# only after _build(); save() skips the rebuild once the lanes exist.
a._build()
a.add_edge_label(f_no_bound, "[no]", pos=-0.7)
a.add_edge_label(f_yes_bound, "[yes]", pos=-0.85)
a.add_edge_label(f_up_done, "[no]", pos=-0.85)
a.add_edge_label(f_dn_done, "[no]", pos=-0.85)

a.save(OUT("06-activity-sync"))
