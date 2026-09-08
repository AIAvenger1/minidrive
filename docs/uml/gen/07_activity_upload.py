"""07 — Activity diagram: Upload / update a file (UC9, UC10).

The size limit is checked twice: the client drops oversized files before sending them
(splitBySize / MAX_UPLOAD_MB in packages/shared) and the API enforces the same limit again in
the FileInterceptor, so a hand-made request is rejected with 413.  The API also rejects an
unsafe file name with 400 before it touches the database.

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
validate = a.action("splitBySize(files):\nsize ≤ MAX_UPLOAD_MB (50)", C, 4, OPS, dx=MAIN)
valid = a.decision("[all accepted?]", C, 5, dx=MAIN)
show_error = a.action("Show «file too\nlarge» error", C, 6, "red", w=110, dx=SIDE)
end_error = a.end(C, 7, dx=SIDE)
post = a.action("POST /files (multipart,\nBearer JWT) — once per\naccepted file", C, 6, OPS, h=56, dx=MAIN)

# API lane: authentication and upsert
guard = a.action("JwtAuthGuard: verify token", A, 6, ACCESS, dx=MAIN)
authorized = a.decision("[authorized?]", A, 7, dx=MAIN)
e401 = a.action("401 Unauthorized", A, 8, "red", w=120, dx=SIDE)
show_login = a.action("Show login screen", C, 8, ACCESS, w=135, dx=SIDE)
end_401 = a.end(C, 9, dx=SIDE)
limits = a.action("FileInterceptor limits:\nsize ≤ maxFileBytes", A, 8, ACCESS, w=160, dx=MAIN)
within = a.decision("[within limit?]", A, 9, dx=MAIN)
e413 = a.action("413 Payload\nToo Large", A, 10, "red", w=110, dx=SIDE)
end_413 = a.end(A, 11, dx=SIDE)
upsert = a.action("FilesService.upsert\n(owner, file)", A, 10, OPS, w=150, dx=MAIN)
# row 11 of the main column stays empty: it is the row where the 413 branch ends, and the
# guard flow of [safe file name?] must not run through that final node.
safe = a.decision("[safe file name?]", A, 12, dx=MAIN)
e400 = a.action("400 Bad Request\n(unsafe name)", A, 13, "red", w=120, dx=SIDE)
end_400 = a.end(A, 14, dx=SIDE)
exists = decision_label_left("[name exists\nin space?]", A, 13, dx=MAIN)
uc10_note = a.note("UC10 Update a file =\nupload with an\nexisting name", A, 15, w=140, dx=SIDE)

# Storage & DB lane: overwrite (UC10) or create (UC9)
overwrite = a.action("Overwrite object\n(StorageService.putObject)", S, 14, INFRA)
update = a.action("Update FileEntry:\nsize, updatedAt = now,\nmodifiedBy = user", S, 15, INFRA)
create = a.action("Create FileEntry\n(uploadedBy = modifiedBy = user)", S, 16, INFRA)
put = a.action("Put object users/{ownerId}/{id},\nthen store storageKey\n(row + object rolled back on error)", S, 17, INFRA, h=60)
m_done = a.merge(S, 18)

# Response
ret = a.action("Return FileDto", A, 19, OPS, w=120, dx=MAIN)
refresh = a.action("Refresh FileTable", C, 19, LIST, w=140, dx=MAIN)
end_ok = a.end(C, 20, dx=MAIN)

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
down(authorized, limits, "[yes]")
down(limits, within)
a.flow(within, e413, "[no]", points=[(X(A, SIDE), Y(9))], exit_=(0, 0.5), entry=(0.5, 0))
down(e413, end_413)
down(within, upsert, "[yes]")
down(upsert, safe)
a.flow(safe, e400, "[no]", points=[(X(A, SIDE), Y(12))], exit_=(0, 0.5), entry=(0.5, 0))
down(e400, end_400)
down(safe, exists, "[yes]")

# guards are added after _build() (see below) so that they sit next to the diamond
f_yes = a.flow(exists, overwrite, points=[(X(S), Y(13))], exit_=(1, 0.5), entry=(0.5, 0))
f_no = a.flow(exists, create, points=[(X(A, MAIN), Y(16))], exit_=(0.5, 1), entry=(0, 0.5))
down(overwrite, update)
# overwrite branch joins the merge along the right edge of the lane (bypasses create/put)
a.flow(update, m_done, points=[(X(S, 150), Y(15)), (X(S, 150), Y(18))], exit_=(1, 0.5), entry=(1, 0.5))
down(create, put)
down(put, m_done)
a.flow(m_done, ret, points=[(X(S), Y(19))], exit_=(0.5, 1), entry=(1, 0.5))
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
