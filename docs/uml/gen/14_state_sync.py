"""14 — State diagram: synchronization session (SyncEngine).

One synchronization run of the client (spec §5, "Sync session"):
    Idle → Scanning → Planning → Transferring → Completed | Failed → Idle
plus the folder picker (PickingFolder, entered when no local folder is bound yet, UC13) and
the desktop-only FolderWatcher loop (Watching → Scanning on a debounced file-system event,
UC14a).  Colours: purple = synchronization, blue = folder picker dialog (user interaction),
green = successful completion, red = error.

Layout (LR): col 0 initial / final, col 1 Idle, col 2 Watching (top) / PickingFolder
(bottom), cols 3-5 Scanning → Planning → Transferring, col 6 Completed (top) / Failed
(bottom).

Library workarounds (drawio.py is not modified):
* The two short back-transitions Watching → Idle and PickingFolder → Idle are hidden from
  Graphviz (`skip_dot`) and drawn as arcs (`bend`) next to their forward transitions; Graphviz
  would otherwise route them as long loops under Idle that cross the other transitions.
* The three long loop-backs (Completed → Idle, Failed → Idle, Completed → Watching) are also
  hidden from Graphviz and re-routed after layout as orthogonal lanes above / below the state
  chain (`route()` below), so they never pass through a state box.
"""
from _common import *  # noqa: F401,F403

d = GraphDiagram("State diagram — synchronization session (SyncEngine)", routing=STRAIGHT)

# ---------------------------------------------------------------------------
# States (declaration order seeds the top-to-bottom order inside a column)
# ---------------------------------------------------------------------------
start = d.initial()
end = d.final()
idle = d.state("Idle", color=SYNC)
watching = d.state("Watching",
                   ["do / FolderWatcher.start(dir, onChange)",
                    "paused while a run is in progress,",
                    "resumed 3 s after it (cooldown)"], SYNC)
picking = d.state("PickingFolder", ["do / dialog.showOpenDialog"], ACCESS)
scanning = d.state("Scanning", ["do / LocalFolderScanner.scan()", "do / ApiClient.listFiles()"], SYNC)
planning = d.state("Planning", ["do / computeSyncPlan()"], SYNC)
transferring = d.state("Transferring",
                       ["do / upload | download per SyncAction", "exit / build SyncReport"], SYNC)
completed = d.state("Completed", color=LIST)
failed = d.state("Failed", color="red")

# ---------------------------------------------------------------------------
# Transitions (out-edge order per node = top-to-bottom order of the targets)
# Two-line labels keep the rank gaps narrow (in LR mode a label widens its rank gap).
# ---------------------------------------------------------------------------
d.transition(start, idle)
d.transition(idle, end, "app quit", dot_reverse=True)            # final sits in column 0, under initial

# Idle -> column 2 / Scanning
d.transition(idle, watching, "sync.watch(true)\n/ FolderWatcher.start()")
d.transition(idle, scanning, "synchronize()\n[folder bound]")
d.transition(idle, picking, "synchronize()\n[no folder]")

# short returns to Idle: arcs bent into the wedge between the forward transition and the
# Idle -> Scanning line, labels shifted towards the source so they sit where the wedge is wide
e_stop = d.transition(watching, idle, "sync.watch(false)\n/ FolderWatcher.stop()",
                      bend=-36, label_offset=(-0.35, 0))
e_cancel = d.transition(picking, idle, "cancelled", bend=36, label_offset=(-0.35, 0))

# into the main chain
d.transition(watching, scanning, "fs event\n(debounced 2 s)")
d.transition(picking, scanning, "folder chosen\n/ save path")
d.transition(scanning, planning, "local + remote lists")
d.transition(planning, transferring, "plan ready\n(runSyncPlan; an empty\nplan runs too)")
d.transition(transferring, completed, "all actions done")
d.transition(transferring, failed, "the whole run throws\n/ failedSyncReport")

# long loop-backs, routed by hand after layout (see route() below)
e_done = d.transition(completed, idle, "report shown")
e_fail = d.transition(failed, idle, "report shown")
e_watch = d.transition(completed, watching, "[watching]")

for e in (e_stop, e_cancel, e_done, e_fail, e_watch):
    e.skip_dot = True

# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------
n_fail = d.note("A failed upload or download is caught per action:\nit is counted in SyncReport.failed / errors and the run\nstill ends in Completed.  Failed is reached only when the\nwhole run throws (no folder, IPC error) — the report is\nthen failedSyncReport(message).", w=330)
d.note_link(n_fail, failed, place="right")

legend = d.legend(
    "Notation: rounded rectangle = state (do / … = activity while in the state, exit / … = action on leaving);\n"
    "filled circle = initial pseudo-state; bull's-eye = final state; arrow = transition «event [guard] / action».\n"
    "Colours: purple = synchronization, blue = folder picker dialog, green = completion, red = aborted run.\n"
    "Watching (FolderWatcher, UC14a) exists in the desktop client only; the web client always returns to Idle.",
    w=680)

# ---------------------------------------------------------------------------
# Layout + manual lane routing of the loop-back transitions
# ---------------------------------------------------------------------------
d.layout(rankdir="LR", nodesep=0.8, ranksep=0.55)

_cells = {c.id: c for c in d.cells}


def box(nid):
    c = _cells[nid]
    return c.x, c.y, c.w, c.h


def cx(nid):
    x, _, w, _ = box(nid)
    return x + w / 2


def cy(nid):
    _, y, _, h = box(nid)
    return y + h / 2


def route(src, dst, points, ports=""):
    """Give the emitted edge src->dst a polyline path with rounded corners and fixed ports."""
    for c in d.cells:
        if not c.vertex and c.source == src and c.target == dst:
            c.points = points
            c.style = c.style.replace("curved=1;", "") + "rounded=1;arcSize=20;" + ports
            return
    raise KeyError((src, dst))


TOP = "exitX=0.5;exitY=0;exitDx=0;exitDy=0;"
BOTTOM = "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
RIGHT = "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
INTO_TOP = "entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
INTO_BOTTOM = "entryX=0.5;entryY=1;entryDx=0;entryDy=0;"

states = [start, end, idle, watching, picking, scanning, planning, transferring, completed, failed]
top = min(box(n)[1] for n in states)
bottom = max(box(n)[1] + box(n)[3] for n in states)
LANE = 50
lane_watch = top - LANE          # Completed -> Watching   (upper lane, closest to the chain)
lane_done = top - 2 * LANE       # Completed -> Idle       (topmost lane)
lane_fail = bottom + LANE        # Failed -> Idle          (bottom lane)

right_c = box(completed)[0] + box(completed)[2]
route(completed, watching, [(cx(completed), lane_watch), (cx(watching), lane_watch)], TOP + INTO_TOP)
route(completed, idle, [(right_c + 40, cy(completed)), (right_c + 40, lane_done), (cx(idle), lane_done)],
      RIGHT + INTO_TOP)
route(failed, idle, [(cx(failed), lane_fail), (cx(idle), lane_fail)], BOTTOM + INTO_BOTTOM)

# Graphviz centred the "synchronize() [no folder]" label on its line, next to the "cancelled" arc;
# nudge it below-left of the line into the free space
for c in d.cells:
    if not c.vertex and c.source == idle and c.target == picking:
        ox, oy = c.abs_offset or (0.0, 0.0)
        c.abs_offset = (ox - 26, oy + 14)

# the legend was placed 40 px under the lowest state; push it below the bottom lane
_cells[legend].y = lane_fail + 40

d.save(OUT("14-state-sync"))
