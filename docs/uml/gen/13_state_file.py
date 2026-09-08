"""13 — State diagram: lifecycle of one file name during synchronization (UC14).

Left → right (LR): initial ● → choice ◇ → LocalOnly / RemoteOnly → Uploading / Downloading →
Synced (same column, middle row) → ModifiedLocally / ModifiedRemotely (final ◉ between them).
Local path on the top row, remote path on the bottom row.
Colours: purple = synchronization states, yellow = transfer in progress, green = synchronized.

There is no Conflict state: computeSyncPlan never detects "changed on both sides".  It compares
the local mtime with the remote updatedAt for every name and the newer side simply wins, so a
two-sided change is already covered by ModifiedLocally / ModifiedRemotely (spec §4.2).

Library workarounds (drawio.py is not modified):
* UML «choice» pseudo-state = simple_box with shape=rhombus.
* Uploading → Synced and Downloading → Synced are flat (same-rank) edges; they are drawn by
  draw.io as straight vertical lines with the label pushed to the side.
"""
from _common import *  # noqa: F401,F403

d = GraphDiagram("State diagram — file lifecycle during synchronization", routing=STRAIGHT)

# transition style = library E_FLOW + smaller font (labels are event [guard] / action strings)
TR = E_FLOW + "fontSize=10;"


def tr(a, b, label="", **kw):
    return d.edge(a, b, TR, label, **kw)


# ---------------------------------------------------------------------------
# Nodes (declaration order seeds the top-to-bottom order inside each column)
# ---------------------------------------------------------------------------
init = d.initial()
choice = d.simple_box("", "white", w=40, h=40, extra="shape=rhombus;")   # «choice» pseudo-state

local_only = d.state("LocalOnly", color=SYNC)
remote_only = d.state("RemoteOnly", color=SYNC)

uploading = d.state("Uploading", color=OPS)
synced = d.state("Synced", color=LIST)
downloading = d.state("Downloading", color=OPS)

mod_local = d.state("ModifiedLocally", color=SYNC)
fin = d.final()
mod_remote = d.state("ModifiedRemotely", color=SYNC)

# Notes
n_local = d.note("deleted on server → LocalOnly:\ndeletions never propagate;\nnext sync re-uploads the file")
n_remote = d.note("deleted locally → RemoteOnly:\nnext sync re-downloads the file")

# ---------------------------------------------------------------------------
# Transitions (event [guard] / action).  Graphviz ranks: forward edges define the columns,
# back edges are declared with dot_reverse so Graphviz still sees a DAG.
# ---------------------------------------------------------------------------
tr(init, choice)
tr(choice, local_only, "[created in the\nbound folder]")
tr(choice, remote_only, "[uploaded from another\nclient or the web]")

# first synchronization of a one-sided file
tr(local_only, uploading, "sync: upload", weight=4)
tr(remote_only, downloading, "sync: download", weight=4)

# transfer finished → Synced (flat edges inside the middle column, drawn by draw.io)
e_up_ok = tr(uploading, synced, "FileDto received", label_offset=(0.0, 62.0))
e_dn_ok = tr(downloading, synced, "written, mtime set", label_offset=(0.0, -66.0))
for e in (e_up_ok, e_dn_ok):
    e.skip_dot = True
    e.constraint = False

# Synced → changed on one side / removed on both sides
tr(synced, mod_local, "local edit\n(mtime changes)")
tr(synced, fin, "delete in app + delete locally\n/ removed on both sides")
tr(synced, mod_remote, "remote update\n(updatedAt changes)")

# one-sided change → transfer again (newest wins); transfer error → back to the modified state
tr(mod_local, uploading, "sync: upload (newest wins)", dot_reverse=True)
tr(uploading, mod_local, "error / failed → retry next sync")
tr(mod_remote, downloading, "sync: download", dot_reverse=True)
tr(downloading, mod_remote, "error / failed → retry next sync")

# deletions never propagate: the file becomes one-sided again.  Straight draw.io lines (Graphviz
# would kink the lower one around Downloading); the straight chord crosses nothing.
e_del_srv = tr(synced, local_only, "deleted on server", label_offset=(0.0, -14.0))
e_del_loc = tr(synced, remote_only, "deleted locally", label_offset=(0.0, 14.0))
for e in (e_del_srv, e_del_loc):
    e.skip_dot = True
    e.constraint = False

# Notes
d.note_link(n_local, local_only, place="above")
d.note_link(n_remote, remote_only, place="below")


# columns
d.same_rank(uploading, synced, downloading)
d.same_rank(mod_local, fin, mod_remote)

d.legend(
    "Legend — lifecycle of one file name as seen by SyncEngine (computeSyncPlan, UC14)\n"
    "States: purple = synchronization (one-sided / modified), yellow = transfer in progress, "
    "green = synchronized\n"
    "Transition label: event [guard] / action.   ◇ = choice pseudo-state,  ● = initial,  "
    "◉ = final (Deleted: file removed on both sides)\n"
    "Planning rule (packages/shared/sync.ts): equal size and |mtime − updatedAt| ≤ 2 s → Synced (skip); an unparsable\n"
    "remote updatedAt → download; otherwise the newer side wins.  «Changed on both sides» is never detected as a separate\n"
    "situation and nothing is ever merged, so the model has no Conflict state (spec §4.2).\n"
    "Web client only: reconcileWithLedger re-stamps a file whose size and mtime still match the localStorage ledger with\n"
    "the server's updatedAt before planning, so a freshly written download is recognised as Synced.",
    w=760,
)

# ---------------------------------------------------------------------------
d.layout(rankdir="LR", nodesep=0.9, ranksep=1.0)


# ---- post-layout re-routing ---------------------------------------------------------------------
def _cell(cid):
    return next(c for c in d.cells if c.id == cid)


def _edge(a, b):
    return next(c for c in d.cells if not c.vertex and c.source == a and c.target == b)


# Row alignment: Graphviz cannot pin rows in LR mode, so ModifiedLocally / ModifiedRemotely are
# lifted onto the rows of Uploading / Downloading (every edge touching them is a straight chord,
# so the boxes can move; stray Graphviz waypoints on those edges are dropped).
def _center(cid):
    c = _cell(cid)
    return c.x + c.w / 2, c.y + c.h / 2


def rebend(a, b, bend, label_px):
    """Re-draw a → b as a curve with one middle waypoint `bend` px off the chord (right-hand
    normal of the travel direction) and the label pushed `label_px` off the curve."""
    e = _edge(a, b)
    (x1, y1), (x2, y2) = _center(a), _center(b)
    dx, dy = x2 - x1, y2 - y1
    ln = (dx * dx + dy * dy) ** 0.5 or 1.0
    e.points = [((x1 + x2) / 2 - dy / ln * bend, (y1 + y2) / 2 + dx / ln * bend)]
    if "curved=1;" not in e.style:
        e.style += "curved=1;"
    e.offset, e.abs_offset = (0.0, label_px), None


for moved, ref in ((mod_local, uploading), (mod_remote, downloading)):
    _cell(moved).y = _cell(ref).y + (_cell(ref).h - _cell(moved).h) / 2
    for c in d.cells:
        if not c.vertex and moved in (c.source, c.target):
            c.points = None

# Graphviz placed the Synced → Modified* labels for the old rows; re-centre them on the chords,
# nudged towards the middle row (away from the error labels of the pairs)
for a, b, px in ((synced, mod_local, -14.0), (synced, mod_remote, 14.0)):
    e = _edge(a, b)
    e.offset, e.abs_offset = (0.0, px), None

# the two opposite-direction pairs become parallel curves again (outer curve = "sync", inner = error)
rebend(mod_local, uploading, 28, -12)       # upper curve, label above
rebend(uploading, mod_local, 28, -12)       # lower curve, label below
rebend(mod_remote, downloading, 28, -12)    # upper curve, label above
rebend(downloading, mod_remote, 28, -12)    # lower curve, label below

d.save(OUT("13-state-file"))
