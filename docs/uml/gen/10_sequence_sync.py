"""10 — Sequence diagram: Synchronize with the local folder (UC14).

Desktop flow: the user presses «Synchronize» in SyncPanel (renderer), the request crosses the
Electron IPC boundary into SyncEngine (main process), which scans the bound folder and fetches
the remote list *concurrently* (Promise.all, hence the `par` fragment), computes the SyncPlan
(computeSyncPlan from packages/shared) and executes it with runSyncPlan.  Execution is two
sequential loops — first every upload, then every download — while the skipped actions are only
counted once; there is no per-action alt.  The trailing `opt` shows the automatic tracking
(UC14a): FolderWatcher re-triggers synchronize() after a debounced file-system change.
"""
from _common import *  # noqa: F401,F403

q = SequenceDiagram("Sequence diagram — Synchronize with the local folder (UC14)", spacing=170, step=38)

# ---- participants (left to right) -----------------------------------------
user = q.participant("User", "actor")
panel = q.participant("SyncPanel", "boundary")
engine = q.participant("SyncEngine", "control")
scanner = q.participant("LocalFolderScanner", "participant", SYNC)
api = q.participant("ApiClient", "control")
files = q.participant("FilesController", "participant", INFRA)
watcher = q.participant("FolderWatcher", "participant", SYNC)

# ---- manual synchronisation (UC14) ----------------------------------------
q.message(user, panel, "click «Synchronize»")
q.message(panel, engine, "synchronize(dir)")
q.note(panel, "via Electron IPC\n(PreloadBridge →\nregisterIpc)", w=130)

q.fragment("par", "[Promise.all — both lists at once]")
q.message(engine, scanner, "scan(dir)")
q.ret(scanner, engine, "LocalFileInfo[]")
q.fragment_else("")
q.message(engine, api, "listFiles()")
q.message(api, files, "GET /files")
q.ret(files, api, "FileDto[]")
q.ret(api, engine)
q.end_fragment()   # par
q.gap(1)

q.self_message(engine, "plan = computeSyncPlan(\nlocal, remote)")
q.note(engine, "equal size and\n|mtime − updatedAt| ≤ 2 s\n→ skip; otherwise the\nnewer side wins;\ndeletions never propagate", w=150)
q.gap(3)           # the 5-line note needs the room before the next self-message label
q.self_message(engine, "report.skipped =\nplan.skipped.length")

q.fragment("loop", "[for each action in plan.uploads]")
q.message(engine, api, "upload(name, bytes)")
q.message(api, files, "POST /files")
q.ret(files, api, "FileDto")
q.ret(api, engine)
q.self_message(engine, "utimes(mtime = updatedAt)")
q.end_fragment()   # loop over the uploads

q.fragment("loop", "[for each action in plan.downloads]")
q.message(engine, api, "download(id)")
q.message(api, files, "GET /files/:id/content")
q.ret(files, api, "bytes")
q.ret(api, engine)
q.self_message(engine, "write file; utimes(\nmtime = updatedAt)")
q.end_fragment()   # loop over the downloads

q.gap(2)           # keep the 3-line return label clear of the loop frame border
q.note(engine, "a transfer that throws is caught\nper action: report.failed += 1,\nthe message goes to report.errors\nand the run continues", w=175)
q.ret(engine, panel, "SyncReport\n{uploaded, downloaded,\nskipped, failed, errors}")
q.ret(panel, user, "show report")
q.deactivate(user)

# ---- automatic tracking (UC14a, desktop only) -----------------------------
q.gap(2)
q.fragment("opt", "[automatic tracking enabled]")
q.message(watcher, engine, "onChange(path)  (debounced 2 s)", kind="async")
q.self_message(engine, "synchronize()")
q.deactivate(engine)
q.deactivate(watcher)
q.end_fragment()   # opt

# ---- layout workaround (same as 08_sequence_login.py) ----------------------
# The library draws fragment frames only 20 px left of the first lifeline box, so the
# "loop"/"alt"/"opt" tabs and the guard texts land on the User lifeline and activation bar.
# Build the cells explicitly, then widen every frame to the left and move the guard labels
# just right of the User column.  Only cell geometry is touched.
q._build()
SHIFT = 60                                    # extra frame width on the left
GUARD_X = q.left + q.spacing / 2 + 12         # right of the User activation bar
for c in q.cells:
    if c.vertex and "shape=umlFrame" in c.style:
        c.x -= SHIFT
        c.w += SHIFT
    elif c.vertex and c.style.startswith("text;html=1;align=left;verticalAlign=middle;fontSize=10;"):
        c.x = GUARD_X                         # fragment guard text
    elif (not c.vertex and c.source is None and c.target is None and c.source_point
          and "endArrow=none" in c.style):
        c.source_point = (c.source_point[0] - SHIFT, c.source_point[1])   # "else" separator

q.save(OUT("10-sequence-sync"))
