"""07 — Activity diagram: Upload / update a file (UC9, UC10).

Swimlanes: User | Client (web / desktop) | API (FilesController / FilesService)
| Storage (MinIO) & DB (PostgreSQL).  Layout is a (lane, row) grid: the main flow
runs in one column per lane (dx=MAIN in the Client/API lanes), error exits live in
a second column (dx=SIDE), the Storage lane stacks the overwrite branch above the
create branch and routes the overwrite branch to the merge along the lane's right
edge so no flow crosses another node.  Waypoints are absolute page coordinates
computed with X()/Y() (mirrors ActivityDiagram._place).
"""
from _common import *

LANES = [
    "User",
    "Client (web / desktop)",
    "API (FilesController / FilesService)",
    "Storage (MinIO) & DB (PostgreSQL)",
]
LW, RH, HH = 380, 90, 30          # lane width, row height, header height
U, C, A, S = 0, 1, 2, 3           # lane indices
MAIN, SIDE = 60, -100             # x-offsets of the main / error columns (Client, API lanes)

a = ActivityDiagram("Activity diagram — Upload / update a file (UC9, UC10)", lanes=LANES,
                    lane_w=LW, row_h=RH, header_h=HH, lane_colors=["blue", "yellow", "grey", "grey"])


def X(lane: int, dx: float = 0) -> float:
    """Absolute x of a cell centre (waypoints are page coordinates)."""
    return lane * LW + LW / 2 + dx


def Y(row: int, dy: float = 0) -> float:
    """Absolute y of a cell centre."""
    return HH + 20 + row * RH + RH / 2 + dy


# ActivityDiagram.decision() always puts the guard text to the RIGHT of the diamond,
# which would collide with a flow leaving the right corner.  These two variants place
# the text below / left of the diamond instead (same rhombus, different label position).
_RHOMBUS = "rhombus;whiteSpace=wrap;html=1;fontSize=10;"


def decision_label_below(label: str, lane: int, row: int, **kw) -> str:
    style = _RHOMBUS + "labelPosition=center;verticalLabelPosition=bottom;align=center;verticalAlign=top;spacingTop=4;"
    return a._add(lane, row, 60, 60, label, style, **kw)


def decision_label_left(label: str, lane: int, row: int, **kw) -> str:
    style = _RHOMBUS + "labelPosition=left;verticalLabelPosition=middle;align=right;verticalAlign=middle;spacingRight=4;"
    return a._add(lane, row, 60, 60, label, style, **kw)


def down(src: str, dst: str, label: str = "") -> None:
    a.flow(src, dst, label, exit_=(0.5, 1), entry=(0.5, 0))


def right(src: str, dst: str, label: str = "") -> None:
    a.flow(src, dst, label, exit_=(1, 0.5), entry=(0, 0.5))


def left(src: str, dst: str, label: str = "") -> None:
    a.flow(src, dst, label, exit_=(0, 0.5), entry=(1, 0.5))


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
# User lane: how the files are picked (UC9a button dialog / UC9b drag-and-drop)
start = a.start(U, 0)
how = decision_label_below("[how?]", U, 1)
select = a.action("Select file(s)\nin the dialog", U, 2, OPS, w=140, dx=-85, dy=10)
drop = a.action("Drop file(s)\nonto the window", U, 2, OPS, w=140, dx=85, dy=10)
m_pick = a.merge(U, 3)

# Client lane: validation and request
validate = a.action("Validate: size ≤ 50 MB", C, 4, OPS, dx=MAIN)
valid = a.decision("[valid?]", C, 5, dx=MAIN)
show_error = a.action("Show error", C, 6, "red", w=100, dx=SIDE)
end_error = a.end(C, 7, dx=SIDE)
post = a.action("POST /files\n(multipart, Bearer JWT)", C, 6, OPS, dx=MAIN)

# API lane: authentication and upsert
guard = a.action("JwtAuthGuard: verify token", A, 6, ACCESS, dx=MAIN)
authorized = a.decision("[authorized?]", A, 7, dx=MAIN)
e401 = a.action("401 Unauthorized", A, 8, "red", w=120, dx=SIDE)
show_login = a.action("Show login screen", C, 8, ACCESS, w=135, dx=SIDE)
end_401 = a.end(C, 9, dx=SIDE)
upsert = a.action("FilesService.upsert\n(owner, file)", A, 8, OPS, w=150, dx=MAIN)
exists = decision_label_left("[name exists\nin space?]", A, 9, dx=MAIN)
uc10_note = a.note("UC10 Update a file =\nupload with an\nexisting name", A, 10, w=140, dx=SIDE)

# Storage & DB lane: overwrite (UC10) or create (UC9)
overwrite = a.action("Overwrite object\n(StorageService.putObject)", S, 10, INFRA)
update = a.action("Update FileEntry:\nupdatedAt = now,\nmodifiedBy = user", S, 11, INFRA)
create = a.action("Create FileEntry\n(uploadedBy = modifiedBy = user)", S, 12, INFRA)
put = a.action("Put object\nusers/{ownerId}/{id}", S, 13, INFRA)
m_done = a.merge(S, 14)

# Response
ret = a.action("Return FileDto", A, 15, OPS, w=120, dx=MAIN)
refresh = a.action("Refresh FileTable", C, 15, LIST, w=140, dx=MAIN)
end_ok = a.end(C, 16, dx=MAIN)

# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------
down(start, how)
a.flow(how, select, "[button]", points=[(X(U, -85), Y(1))], exit_=(0, 0.5), entry=(0.5, 0))
a.flow(how, drop, "[drag-and-drop]", points=[(X(U, 85), Y(1))], exit_=(1, 0.5), entry=(0.5, 0))
a.flow(select, m_pick, points=[(X(U, -85), Y(3))], exit_=(0.5, 1), entry=(0, 0.5))
a.flow(drop, m_pick, points=[(X(U, 85), Y(3))], exit_=(0.5, 1), entry=(1, 0.5))
# leave the merge downwards (its right corner is taken by the drop flow) and enter Validate from the left
a.flow(m_pick, validate, points=[(X(U), Y(4))], exit_=(0.5, 1), entry=(0, 0.5))

down(validate, valid)
a.flow(valid, show_error, "[no]", points=[(X(C, SIDE), Y(5))], exit_=(0, 0.5), entry=(0.5, 0))
down(show_error, end_error)
down(valid, post, "[yes]")
right(post, guard)

down(guard, authorized)
a.flow(authorized, e401, "[no]", points=[(X(A, SIDE), Y(7))], exit_=(0, 0.5), entry=(0.5, 0))
left(e401, show_login)
down(show_login, end_401)
down(authorized, upsert, "[yes]")
down(upsert, exists)

# guards are added after _build() (see below) so that they sit next to the diamond
f_yes = a.flow(exists, overwrite, points=[(X(S), Y(9))], exit_=(1, 0.5), entry=(0.5, 0))
f_no = a.flow(exists, create, points=[(X(A, MAIN), Y(12))], exit_=(0.5, 1), entry=(0, 0.5))
down(overwrite, update)
# overwrite branch joins the merge along the right edge of the lane (bypasses create/put)
a.flow(update, m_done, points=[(X(S, 150), Y(11)), (X(S, 150), Y(14))], exit_=(1, 0.5), entry=(1, 0.5))
down(create, put)
down(put, m_done)
a.flow(m_done, ret, points=[(X(S), Y(15))], exit_=(0.5, 1), entry=(1, 0.5))
left(ret, refresh)
down(refresh, end_ok)

a.note_link(uc10_note, exists)

# Both guards of [name exists in space?] ride on long L-shaped flows whose midpoint lies
# far from the diamond, so they are attached as positioned edge labels near the source
# end.  The edges only exist after _build(); save() skips the rebuild once lanes exist.
a._build()
a.add_edge_label(f_yes, "[yes]", pos=-0.75)
a.add_edge_label(f_no, "[no]", pos=-0.75)

a.save(OUT("07-activity-upload"))
