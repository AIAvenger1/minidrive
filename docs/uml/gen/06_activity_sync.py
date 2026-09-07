"""06 — Activity diagram: Synchronize with the local folder (UC14), with swimlanes.

Lanes: User | Desktop client (Renderer) | Desktop client (Main / SyncEngine) | API.
Layout is a (lane, row) grid with one node per cell.  Every bent flow carries explicit
waypoints (absolute page coordinates from X()/Y(), which mirror ActivityDiagram._place)
so that no flow passes through another node.  The plan-execution loop is drawn with the
UML loop idiom: a merge node sits directly above the "[next action?]" decision and
receives both the entry flow and the "[more actions?] [yes]" back-edge, which runs along
the right side of the API lane.  Each decision therefore has one entry and every exit
leaves from its own corner (no two guards share a segment).
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
                 "|mtime − updatedAt| ≤ 2 s → skip,\nelse newest wins;\ndeletions never propagate",
                 API, 9, w=200)
show = a.action("Show plan:\nuploads / downloads / skipped", REN, 10, SYNC)

# execute the plan: loop over SyncAction[]
m_loop = a.merge(MAIN, 11)
d_next = decision("[next action?]", MAIN, 12, "upper-left")
# API actions are narrowed and shifted left so that two vertical channels fit on the
# right of the API lane: X_RIGHT (Update FileEntry → merge) and X_BACK (loop back-edge).
API_DX, API_W = -30, 150
post = a.action("POST /files\n(multipart)", API, 12, OPS, w=API_W, dx=API_DX)
upd = a.action("Update FileEntry\n(updatedAt,\nmodifiedBy)", API, 13, OPS, w=API_W, h=56, dx=API_DX)
get = a.action("GET\n/files/:id/content", API, 14, OPS, w=API_W, dx=API_DX)
write = a.action("Write file,\nset mtime = updatedAt", MAIN, 15, SYNC)
m_next = a.merge(MAIN, 16)
d_more = decision("[more actions?]", MAIN, 17, "below")
report = a.action("Show SyncReport", REN, 17, SYNC)
e = a.end(REN, 18)

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

a.flow(plan, show, points=[(X(REN), Y(9))], exit_=(0, 0.5), entry=(0.5, 0))
a.flow(show, m_loop, points=[(X(REN), Y(11))], exit_=(0.5, 1), entry=(0, 0.5))
down(m_loop, d_next)

# three-way split: right = upload, bottom = download, left = skip
X_SKIP = X(MAIN, -105)                 # left channel of the Main lane
X_RIGHT = X(API, 70)                   # right channel of the API lane
X_BACK = X(API, 110)                   # outermost channel of the API lane (back-edge)
right(d_next, post, "[upload]")
f_download = a.flow(d_next, get, points=[(X(MAIN), Y(14))], exit_=(0.5, 1), entry=(0, 0.5))
f_skip = a.flow(d_next, m_next, points=[(X_SKIP, Y(12)), (X_SKIP, Y(16))], exit_=(0, 0.5), entry=(0, 0.5))

down(post, upd)
a.flow(upd, m_next, points=[(X_RIGHT, Y(13)), (X_RIGHT, Y(16))], exit_=(1, 0.5), entry=(1, 0.5))
a.flow(get, write, points=[(X(API, API_DX), Y(15))], exit_=(0.5, 1), entry=(1, 0.5))
down(write, m_next)
down(m_next, d_more)

# back-edge of the loop: right, up along the right side of the API lane, into the merge
f_more = a.flow(d_more, m_loop, points=[(X_BACK, Y(17)), (X_BACK, Y(11))], exit_=(1, 0.5), entry=(1, 0.5))
left(d_more, report, "[no]")
down(report, e)

# Guards of the L-shaped flows are attached as positioned edge labels near the source end
# (draw.io would otherwise centre them on the path, far from the diamond).  Edges exist
# only after _build(); save() skips the rebuild once the lanes exist.
a._build()
a.add_edge_label(f_no_bound, "[no]", pos=-0.7)
a.add_edge_label(f_yes_bound, "[yes]", pos=-0.85)
a.add_edge_label(f_download, "[download]", pos=-0.7)
a.add_edge_label(f_skip, "[skip]", pos=-0.85)
a.add_edge_label(f_more, "[yes]", pos=-0.93)

a.save(OUT("06-activity-sync"))
