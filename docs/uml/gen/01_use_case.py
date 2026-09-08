"""01 — Use case diagram for MiniDrive (cascade style, no system-boundary box).

Actor «User» on the far left, four root use cases in the first column (blue). Everything else
hangs as a tree: «include» from the root, «extend» toward the base use cases, and parameter
leaves on plain solid association lines.

There is no «Resolve version conflicts» use case: synchronization never asks the user which
version to keep — the newest side wins and deletions are never propagated (spec §4.2).

Colour groups: blue = access / session, green = file list (view / sort / filter / columns /
preview), yellow = file operations (upload / update / download / delete), purple = sync.
"""
from _common import *  # noqa: F401,F403

d = GraphDiagram("Use case diagram", routing=STRAIGHT)

# ---------------------------------------------------------------------------
# Nodes — declaration order (top to bottom, column by column) seeds Graphviz's
# vertical ordering, so keep it in the order the diagram should read.
# ---------------------------------------------------------------------------
user = d.actor("User")

# Column 1 — root use cases connected straight to the actor (blue).
# «Log in» sits directly above the root so the root → login «include» is a short flat edge.
login = d.usecase("Log in to the system", ACCESS)
root = d.usecase("Work with the\nfile storage", ACCESS)
signup = d.usecase("Sign up", ACCESS)
logout = d.usecase("Log out from the system", ACCESS)

# Column 2 — included / extending use cases of the root
view = d.usecase("View the list of files\nand their attributes", LIST)
upload = d.usecase("Upload file(s)\nto the storage", OPS)
update = d.usecase("Update a file\n(new version)", OPS)
download = d.usecase("Download file(s)", OPS)
delete = d.usecase("Delete file(s)", OPS)
bind = d.usecase("Bind / change\nlocal folder", SYNC)
sync = d.usecase("Synchronize with\nthe local folder", SYNC)

# Column 3 — extensions of the column-2 use cases
sort = d.usecase("Sort by name", LIST)
filt = d.usecase("Filter by type", LIST)
columns = d.usecase("Show / hide\ntable columns", LIST)
contents = d.usecase("View the file contents", LIST)
select_upload = d.usecase("Select and upload", OPS)
dnd = d.usecase("Drag-and-drop", OPS)
drag_out = d.usecase("Drag out of the window", OPS)
auto_track = d.usecase("Automatic tracking\nof folder changes", SYNC)
refresh = d.usecase("Refresh the list", LIST)
server_addr = d.usecase("Change the API server\naddress (desktop only)", ACCESS)

# Column 4 — parameter leaves (narrower ellipses, green)
LEAF_W = 130
asc = d.usecase("Ascending", LIST, w=LEAF_W)
desc = d.usecase("Descending", LIST, w=LEAF_W)
all_files = d.usecase("All files", LIST, w=LEAF_W)
only_cpp = d.usecase("Only .cpp", LIST, w=LEAF_W)
only_png = d.usecase("Only .png", LIST, w=LEAF_W)
col_created = d.usecase("Creation date", LIST, w=LEAF_W)
col_modified = d.usecase("Modification date", LIST, w=LEAF_W)
col_uploaded = d.usecase("Uploaded by", LIST, w=LEAF_W)
col_edited = d.usecase("Edited by", LIST, w=LEAF_W)
col_size = d.usecase("Size", LIST, w=LEAF_W)
col_type = d.usecase("File type", LIST, w=LEAF_W)
cs_text = d.usecase(".cs as text", LIST, w=LEAF_W)
jpg_image = d.usecase(".jpg as image", LIST, w=LEAF_W)

# Notes
n_login = d.note("Log in / sign up.\nFurther interaction with the system\nrequires an authorized user")
n_update = d.note("Updates «modification date»\nand «edited by»")
n_drag_out = d.note("Desktop client only")
n_sync = d.note("Requires a previously\nbound folder")
n_auto_track = d.note("Desktop client only")
n_sync_rule = d.note("The newest version always wins;\ndeletions are never propagated")

# ---------------------------------------------------------------------------
# Edges — per-node out-edge order = top-to-bottom order of the children
# ---------------------------------------------------------------------------
# Actor — root use cases (plain association lines), all in one column
d.assoc(user, login)
d.assoc(user, root)
d.assoc(user, signup)
d.assoc(user, logout)
d.same_rank(login, root, signup, logout)

# «include» (arrow: root → included use case).  dot_reverse only keeps «Log in» ranked above
# the root inside column 1; the drawn arrow direction is unchanged.
d.include(root, login, dot_reverse=True)
d.include(root, view)

# «extend» off «View the list of files ...» (arrow: extension → base) + parameter leaves
d.extend(sort, view)
d.assoc(sort, asc)
d.assoc(sort, desc)
d.extend(filt, view)
d.assoc(filt, all_files)
d.assoc(filt, only_cpp)
d.assoc(filt, only_png)
d.extend(columns, view)
d.assoc(columns, col_created)
d.assoc(columns, col_modified)
d.assoc(columns, col_uploaded)
d.assoc(columns, col_edited)
d.assoc(columns, col_size)
d.assoc(columns, col_type)
d.extend(refresh, view)
d.extend(contents, view)
d.assoc(contents, cs_text)
d.assoc(contents, jpg_image)

# «extend» off the root — file operations (yellow)
d.extend(upload, root)
d.extend(select_upload, upload)
d.extend(dnd, upload)
d.extend(update, root)
d.extend(download, root)
d.extend(drag_out, download)
d.extend(delete, root)

# «extend» off the root — synchronization (purple)
d.extend(bind, root)
d.extend(sync, root)
d.extend(auto_track, sync)

# «extend» off «Log in» — the desktop login screen lets the user point the client at another API
d.extend(server_addr, login)

# Notes — Graphviz places each one as a leaf hanging off its target.  The login note is pinned
# above «Log in» instead: as an auto leaf it lands in column 2 and bends the Sort / Filter edges.
d.note_link(n_login, login, place="above")
d.note_link(n_update, update, place="auto")
d.note_link(n_drag_out, drag_out, place="auto")
d.note_link(n_sync, sync, place="auto")
d.note_link(n_auto_track, auto_track, place="auto")
d.note_link(n_sync_rule, sync, place="below")

# ---------------------------------------------------------------------------
d.layout(rankdir="LR", nodesep=0.3, ranksep=0.9)
d.save(OUT("01-use-case"))
