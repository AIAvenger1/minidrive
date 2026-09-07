"""10 — Sequence diagram: Synchronize with the local folder (UC14).

Desktop flow: the user presses «Synchronize» in SyncPanel (renderer), the request crosses the
Electron IPC boundary into SyncEngine (main process), which scans the bound folder with
LocalFolderScanner, fetches the remote list through ApiClient → FilesController, computes the
SyncPlan (computeSyncPlan from packages/shared) and executes it action by action.  The trailing
`opt` shows the automatic tracking (UC14a): FolderWatcher re-triggers synchronize() after a
debounced file-system change.

Participants and messages follow §3.2, §3.5 and §4.2 of the design spec verbatim.
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
q.message(panel, engine, "synchronize()")
q.note(panel, "via Electron IPC\n(PreloadBridge →\nIpcHandlers)", w=130)

q.message(engine, scanner, "scan(path)")
q.ret(scanner, engine, "LocalFileInfo[]")

q.message(engine, api, "listFiles()")
q.message(api, files, "GET /files")
q.ret(files, api, "FileDto[]")
q.ret(api, engine)

q.self_message(engine, "plan = computeSyncPlan(\nlocal, remote)")
q.note(engine, "conflict = both sides\nchanged → newest\nwins (UC14b)", w=130)

q.fragment("loop", "[for each action in plan]")
q.fragment("alt", "[upload]")
q.message(engine, api, "upload(file)")
q.message(api, files, "POST /files")
q.ret(files, api, "FileDto")
q.ret(api, engine)

q.fragment_else("[download]")
q.message(engine, api, "download(id)")
q.message(api, files, "GET /files/:id/content")
q.ret(files, api, "bytes")
q.ret(api, engine)
q.self_message(engine, "write file; utimes(\nmtime = updatedAt)")

q.fragment_else("[skip]")
q.self_message(engine, "record skipped")
q.end_fragment()   # alt
q.end_fragment()   # loop

q.gap(2)           # keep the 3-line return label clear of the loop frame border
q.ret(engine, panel, "SyncReport\n{uploaded, downloaded,\nskipped, failed}")
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
