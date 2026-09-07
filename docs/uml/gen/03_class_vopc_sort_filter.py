"""03 — VOPC (View Of Participating Classes) for UC5 "Sort by name" + UC6 "Filter by type".

RUP boundary / control / entity stereotypes, coloured by role:
    «boundary» blue · «control» / «utility» yellow · «entity» / «enumeration» green
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
sort_ctl = d.klass("SortControl", stereotype="boundary", color=BOUNDARY,
                   attrs=["- order: SortOrder"],
                   methods=["+ toggleOrder(): void"])
filter_ctl = d.klass("FilterControl", stereotype="boundary", color=BOUNDARY,
                     attrs=["- filter: FileFilter"],
                     methods=["+ select(filter: FileFilter): void"])
file_table = d.klass("FileTable", stereotype="boundary", color=BOUNDARY,
                     attrs=["- columns: ColumnVisibility", "- rows: FileDto[]"],
                     methods=["+ render(files: FileDto[]): void", "+ onRowClick(file: FileDto): void"])

# ---- control classes (columns 2-3) -----------------------------------------------
vm = d.klass("DriveViewModel", stereotype="control", color=CONTROL,
             attrs=["- files: FileDto[]", "- order: SortOrder = ASC", "- filter: FileFilter = ALL"],
             methods=["+ loadFiles(): Promise<void>", "+ setOrder(order: SortOrder): void",
                      "+ setFilter(filter: FileFilter): void", "+ get visibleFiles(): FileDto[]"])
api = d.klass("ApiClient", stereotype="control", color=CONTROL,
              attrs=["- baseUrl: string", "- token: string"],
              methods=["+ listFiles(): Promise<FileDto[]>"])
utils = d.klass("FileListUtils", stereotype="utility", color=CONTROL,
                methods=["+ sortByName(files: FileDto[], order: SortOrder): FileDto[]",
                         "+ filterByType(files: FileDto[], filter: FileFilter): FileDto[]"])

# ---- entity classes (columns 3-4) ------------------------------------------------
dto = d.klass("FileDto", stereotype="entity", color=ENTITY,
              attrs=["+ id: string", "+ name: string", "+ extension: string", "+ size: number",
                     "+ createdAt: Date", "+ updatedAt: Date", "+ uploadedBy: string", "+ modifiedBy: string"])
sort_order = d.enum("SortOrder", ["ASC", "DESC"], color=ENTITY)
file_filter = d.enum("FileFilter", ["ALL", "CPP_PNG"], color=ENTITY)

# ---- links ---------------------------------------------------------------------
# actor -> boundaries: straight fan lines (orthogonal routing would bus them through FilterControl)
d.assoc(user, sort_ctl, routing=STRAIGHT)
d.assoc(user, filter_ctl, routing=STRAIGHT)
d.assoc(user, file_table, routing=STRAIGHT)

# boundaries -> control (ports pinned so the three edges enter DriveViewModel at distinct heights)
d.edge(sort_ctl, vm, E_DIRECTED + ports(1, 0.5, 0, 0.2))
d.edge(filter_ctl, vm, E_DIRECTED + ports(1, 0.5, 0, 0.5))
d.edge(vm, file_table, E_DIRECTED + ports(0, 0.8, 1, 0.5), label="renders",
       dot_reverse=True)                                   # arrow points back to the boundary column

# control -> control / entity
d.edge(vm, api, E_DIRECTED + ports(1, 0.2, 0, 0.5))
d.edge(vm, utils, E_DEPENDENCY + ports(1, 0.5, 0, 0.5), label="«use»")
d.edge(vm, dto, E_ASSOC + ports(1, 0.85, 0, 0.5), labels=[("0..*", 0.7)])

# utility -> entities
d.edge(utils, dto, E_DEPENDENCY + ports(0.5, 1, 0.5, 0))
d.edge(utils, sort_order, E_DEPENDENCY + ports(1, 0.35, 0, 0.5))
d.edge(utils, file_filter, E_DEPENDENCY + ports(1, 0.65, 0, 0.5))

# ---- note ----------------------------------------------------------------------
note = d.note("visibleFiles = filterByType(sortByName(files, order), filter);\n"
              "computed client-side, unit-tested in packages/shared", w=300)
d.note_link(note, vm, place="below")

d.legend("«boundary» (blue) — UI controls the User interacts with\n"
         "«control» / «utility» (yellow) — client-side logic (view model, API access, pure functions)\n"
         "«entity» / «enumeration» (green) — data carried between the layers", w=560)

# ---- layout --------------------------------------------------------------------
d.same_rank(sort_ctl, filter_ctl, file_table)
d.same_rank(api, utils, dto)
d.same_rank(sort_order, file_filter)
d.layout(rankdir="LR", nodesep=0.55, ranksep=1.0)
d.save(OUT("03-class-vopc-sort-filter"))
