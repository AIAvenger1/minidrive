"""03 — VOPC (View Of Participating Classes) for UC5 "Sort by name" + UC6 "Filter by type".

RUP boundary / control / entity stereotypes, coloured by role:
    «boundary» blue · «control» / «utility» yellow · «entity» / «enumeration» green

The boundary classes are React components of packages/ui, so their "attributes" are props and
their "operations" are the callbacks they receive.  Loading the list is not a method of the view
model: the useDrive hook (packages/ui) calls ApiClient and hands the result to
DriveViewModel.setFiles, and sorting / filtering happen lazily inside the visibleFiles getter.
"""
from _common import *

BOUNDARY, CONTROL, ENTITY = "blue", "yellow", "green"


def ports(ex, ey, nx, ny) -> str:
    """draw.io style fragment pinning the exit (source) and entry (target) ports of an edge."""
    return f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;"


d = GraphDiagram("VOPC — Sort and filter the file list (UC5 + UC6)", routing=ORTHO)

# ---- actor -------------------------------------------------------------------
user = d.actor("User")

# ---- boundary classes (column 1) ----------------------------------------------
workspace = d.klass("DriveWorkspace", stereotype="boundary", color=BOUNDARY,
                    attrs=["- vm: DriveViewModel"],
                    methods=["+ useEffect(): refresh() on mount"])
sort_ctl = d.klass("SortControl", stereotype="boundary", color=BOUNDARY,
                   attrs=["+ order: SortOrder", "+ onToggle: () => void"])
filter_ctl = d.klass("FilterControl", stereotype="boundary", color=BOUNDARY,
                     attrs=["+ filter: FileFilter", "+ onChange: (f: FileFilter) => void"])
file_table = d.klass("FileTable", stereotype="boundary", color=BOUNDARY,
                     attrs=["+ files: FileDto[]", "+ columns: ColumnVisibility",
                            "+ selected: FileDto | null", "+ onSelect: (f: FileDto) => void"])

# ---- control classes (columns 2-3) -----------------------------------------------
hook = d.klass("useDrive", stereotype="control", color=CONTROL,
               attrs=["- vm: DriveViewModel", "- busy: boolean", "- error: string | null"],
               methods=["+ refresh(): Promise<void>", "+ update(fn: (vm) => void): void"])
vm = d.klass("DriveViewModel", stereotype="control", color=CONTROL,
             attrs=["- files: FileDto[]", "- order: SortOrder = 'asc'", "- filter: FileFilter = 'all'",
                    "- columns: ColumnVisibility", "- selected: FileDto | null"],
             methods=["+ setFiles(files: FileDto[]): void", "+ setOrder(order: SortOrder): void",
                      "+ setFilter(filter: FileFilter): void", "+ toggleColumn(key: ColumnKey): void",
                      "+ select(file: FileDto | null): void", "+ get visibleFiles(): FileDto[]"])
api = d.klass("ApiClient", stereotype="control", color=CONTROL,
              attrs=["- baseUrl: string", "- token: string"],
              methods=["+ listFiles(): Promise<FileDto[]>"])
utils = d.klass("fileList", stereotype="utility", color=CONTROL,
                methods=["+ sortByName(files: FileDto[], order: SortOrder): FileDto[]",
                         "+ filterByType(files: FileDto[], filter: FileFilter): FileDto[]"])

# ---- entity classes (columns 3-4) ------------------------------------------------
dto = d.klass("FileDto", stereotype="entity", color=ENTITY,
              attrs=["+ id: string", "+ name: string", "+ extension: string", "+ size: number",
                     "+ createdAt: string", "+ updatedAt: string", "+ uploadedBy: string",
                     "+ modifiedBy: string"])
sort_order = d.enum("SortOrder", ["asc", "desc"], color=ENTITY)
file_filter = d.enum("FileFilter", ["all", "cpp", "png"], color=ENTITY)

# ---- links ---------------------------------------------------------------------
# actor -> boundaries: straight fan lines (orthogonal routing would bus them through FilterControl)
d.assoc(user, workspace, routing=STRAIGHT)
d.assoc(user, sort_ctl, routing=STRAIGHT)
d.assoc(user, filter_ctl, routing=STRAIGHT)
d.assoc(user, file_table, routing=STRAIGHT)

# boundaries -> control (ports pinned so the edges enter their target at distinct heights)
d.edge(workspace, hook, E_DIRECTED + ports(1, 0.5, 0, 0.5), label="refresh()")
d.edge(sort_ctl, vm, E_DIRECTED + ports(1, 0.5, 0, 0.2), label="setOrder")
d.edge(filter_ctl, vm, E_DIRECTED + ports(1, 0.5, 0, 0.5), label="setFilter")
d.edge(vm, file_table, E_DIRECTED + ports(0, 0.85, 1, 0.5), label="renders",
       dot_reverse=True)                                   # arrow points back to the boundary column

# the hook owns the loading and feeds the view model (flat edge inside the control column)
d.edge(hook, vm, E_DIRECTED + ports(0.5, 1, 0.5, 0), label="setFiles(files)", constraint=False)
d.edge(hook, api, E_DIRECTED + ports(1, 0.5, 0, 0.5), label="listFiles()")

# control -> control / entity
d.edge(vm, utils, E_DEPENDENCY + ports(1, 0.5, 0, 0.5), label="«use»")
d.edge(vm, dto, E_ASSOC + ports(1, 0.85, 0, 0.5), labels=[("0..*", 0.7)])

# utility -> entities
d.edge(utils, dto, E_DEPENDENCY + ports(0.5, 1, 0.5, 0))
d.edge(utils, sort_order, E_DEPENDENCY + ports(1, 0.35, 0, 0.5))
d.edge(utils, file_filter, E_DEPENDENCY + ports(1, 0.65, 0, 0.5))

# ---- note ----------------------------------------------------------------------
note = d.note("visibleFiles = filterByType(sortByName(files, order), filter);\n"
              "evaluated lazily in the getter, unit-tested in packages/shared", w=320)
d.note_link(note, vm, place="below")

d.legend("«boundary» (blue) — React components of packages/ui; their attributes are props\n"
         "«control» (yellow) — client-side logic: the useDrive hook loads and re-renders, "
         "DriveViewModel holds the state, ApiClient talks to the server\n"
         "«utility» (yellow) — fileList, a module of pure functions in packages/shared\n"
         "«entity» / «enumeration» (green) — data carried between the layers "
         "(the enumerations are TypeScript union types)", w=680)

# ---- layout --------------------------------------------------------------------
d.same_rank(workspace, sort_ctl, filter_ctl, file_table)
d.same_rank(hook, vm)
d.same_rank(api, utils, dto)
d.same_rank(sort_order, file_filter)
d.layout(rankdir="LR", nodesep=0.55, ranksep=1.0)
d.save(OUT("03-class-vopc-sort-filter"))
