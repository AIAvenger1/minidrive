"""11 — Communication (collaboration) diagram: Sort and filter the file list (UC5, UC6).

Objects and messages mirror the VOPC diagram 03 (boundary / control / entity roles):
  actor              :User
  boundary  (blue)   :DriveWorkspace, :FileTable, :SortControl, :FilterControl
  control   (yellow) :useDrive, :DriveViewModel, :ApiClient, fileList (module of pure functions)
  entity    (green)  files : FileDto[]
Sequence numbers: 1 = load, 2 = sort by name (asc/desc), 3 = filter all / only .cpp / only .png, 4 = redraw.

The list is loaded by the useDrive hook, not by the view model: the hook owns the API call and
the 401 handling and hands the result to DriveViewModel.setFiles (packages/ui/src/useDrive.ts).

Layout notes
  * Graphviz routes every message (route_edges=True), so opposite-direction pairs are drawn as
    two separate polylines with their own reserved label space — the library's `bend=` waypoint
    only applies when draw.io routes the edges itself.
  * Ranks (LR): User | boundaries | useDrive | DriveViewModel + files | ApiClient + fileList.
"""
from _common import *

d = GraphDiagram("Communication diagram — Sort and filter the file list (UC5, UC6)", routing=STRAIGHT)

UNDERLINE = "fontStyle=4;"          # object names are underlined in communication diagrams
BOUNDARY, CONTROL, ENTITY = "blue", "yellow", "green"

# ---- objects (declaration order = top-to-bottom order inside a rank) --------------
user = d.actor(":User")
# boundary objects
workspace = d.simple_box(":DriveWorkspace", BOUNDARY, extra=UNDERLINE)
table = d.simple_box(":FileTable", BOUNDARY, extra=UNDERLINE)
sort_ctl = d.simple_box(":SortControl", BOUNDARY, extra=UNDERLINE)
filter_ctl = d.simple_box(":FilterControl", BOUNDARY, extra=UNDERLINE)
# control objects
hook = d.simple_box(":useDrive", CONTROL, extra=UNDERLINE)
vm = d.simple_box(":DriveViewModel", CONTROL, extra=UNDERLINE)
api = d.simple_box(":ApiClient", CONTROL, extra=UNDERLINE)
utils = d.simple_box("fileList\n(packages/shared)", CONTROL)
# entity object
files = d.simple_box("files : FileDto[]", ENTITY, extra=UNDERLINE)

# ---- messages (numbered, chronological) --------------------------------------------
# 1 — load the file list when the cabinet page opens
d.directed(user, workspace, "1: open /drive")
d.directed(workspace, hook, "1.1: refresh()")
d.directed(hook, api, "1.2: listFiles()")
d.directed(hook, vm, "1.4: setFiles(files)")         # 1.3 is the GET note on ApiClient
# 2 — sort by name (ascending / descending)
d.directed(user, sort_ctl, "2: toggle order")
d.directed(sort_ctl, vm, "2.1: setOrder(order)")
d.directed(vm, utils, "2.2: sortByName(files, order)")   # lazily, from the visibleFiles getter
# 3 — filter: all files / only .cpp / only .png
d.directed(user, filter_ctl, "3: onChange('png')")
d.directed(filter_ctl, vm, "3.1: setFilter(filter)")
d.directed(vm, utils, "3.2: filterByType(sorted, filter)")
# 4 — redraw the table with the visible (sorted + filtered) list
d.directed(vm, table, "4: render(visibleFiles)")
# structural link: the view model holds the loaded list
d.assoc(vm, files, "holds")

# ---- notes -------------------------------------------------------------------------
n_get = d.note("1.3: GET /files", "yellow")
d.note_link(n_get, api, place="right")

n_seq = d.note("Sequence numbers: 1 = load, 2 = sort by name (asc/desc),\n"
               "3 = filter all / only .cpp / only .png, 4 = redraw", "yellow", w=360)
# Free-standing note under the content: the library only exposes this placement through
# legend() (a text box), so reuse the same anchor for a real UML note shape.
d._nodes[n_seq].anchor = "__content__"
d._nodes[n_seq].place = "bottom"

# ---- layout ------------------------------------------------------------------------
d.same_rank(workspace, table, sort_ctl, filter_ctl)   # boundary column
d.same_rank(vm, files)                                # the entity hangs below the view model
d.same_rank(api, utils)                               # control helpers column
d.layout(rankdir="LR", nodesep=1.0, ranksep=1.2)
d.save(OUT("11-communication-sort-filter"))
