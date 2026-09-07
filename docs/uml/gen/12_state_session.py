"""12 — State diagram: client session (spec §5, "Client session").

initial -> LoggedOut -> Authenticating -> composite LoggedIn { initial -> Browsing;
Browsing <-> Previewing | Uploading | Downloading | Deleting | Syncing };
LoggedIn --(Log out | any 401)--> LoggedOut;  LoggedOut --(close app)--> final.

Layout (TB): rank 0 = initial + final pseudo-states, rank 1 = LoggedOut | Authenticating,
below them the LoggedIn composite.  Inside the composite Previewing / initial / Syncing sit
above Browsing and the three yellow file operations below it.  The three transitions that
touch the composite border are drawn by draw.io with fixed ports (Graphviz only ranks the
composite below the top row through an invisible edge).
"""
from _common import *  # noqa: F401,F403

d = GraphDiagram("State diagram — client session", routing=STRAIGHT)

# transition style = library E_FLOW + smaller font (labels are event / action strings)
TR = E_FLOW + "fontSize=10;"


def tr(a, b, label="", **kw):
    return d.edge(a, b, TR, label, **kw)


# ---- top level ---------------------------------------------------------------------------------
start = d.initial()
fin = d.final()
logged_out = d.state("LoggedOut", color=ACCESS)
auth = d.state("Authenticating", color=ACCESS)

# ---- composite state LoggedIn ------------------------------------------------------------------
# Declaration order seeds the left-to-right order of the row above Browsing:
# Previewing | initial | Syncing (with layout(ordering="in") Browsing's in-edges keep it).
li = d.composite_state("LoggedIn")
previewing = d.state("Previewing", ["do / TextPreview | ImagePreview"], color=LIST, group=li)
li_start = d.initial(group=li)
syncing = d.state("Syncing", ["do / SyncEngine.synchronize()"], color=SYNC, group=li)
browsing = d.state("Browsing", ["entry / loadFiles()", "do / render FileTable (sort, filter, columns)"],
                   color=LIST, group=li)
uploading = d.state("Uploading", ["do / POST /files"], color=OPS, group=li)
downloading = d.state("Downloading", color=OPS, group=li)
deleting = d.state("Deleting", color=OPS, group=li)

# ---- transitions: session ----------------------------------------------------------------------
tr(start, logged_out)
# final sits on the top rank next to the initial; "close app" points back up (dot_reverse keeps
# the ranking initial/final -> LoggedOut)
tr(logged_out, fin, "close app", dot_reverse=True)
tr(logged_out, auth, "submit credentials / POST /auth/login")
tr(auth, logged_out, "401 / show error", dot_reverse=True)

# Edges that touch the composite border are drawn by draw.io only (skip_dot) and get fixed
# ports after layout (see below); Graphviz ranks the composite through the invisible edge.
e_enter = tr(auth, li, "200 / SessionStore.set(token)")
e_enter.skip_dot = True
e_logout = tr(li, logged_out, "Log out / SessionStore.clear()")
e_logout.skip_dot = True
e_401 = tr(li, logged_out, "any 401 / clear token")
e_401.skip_dot = True

# ---- transitions: inside LoggedIn --------------------------------------------------------------
tr(browsing, previewing, "click row", dot_reverse=True)
tr(previewing, browsing, "close")
tr(li_start, browsing)
tr(browsing, syncing, "Synchronize", dot_reverse=True)
tr(syncing, browsing, "SyncReport")
tr(browsing, uploading, "drop files | select files")
tr(uploading, browsing, "FileDto received / refresh")
tr(browsing, downloading, "download | drag out")
tr(downloading, browsing, "saved")
tr(browsing, deleting, "delete")
tr(deleting, browsing, "204 / refresh")

d.same_rank(start, fin)
d.same_rank(logged_out, auth)

d.legend(
    "Notation\n"
    "filled circle = initial pseudo-state;  bull's-eye = final state\n"
    "rounded rectangle = state (entry / do activities listed inside)\n"
    "large rounded frame «LoggedIn» = composite state with its own initial pseudo-state and sub-states\n"
    "arrow = transition, label:  event [guard] / action\n"
    "colours: blue = session, green = file list and preview, yellow = upload / download / delete, "
    "purple = synchronization",
    w=600,
)

# Invisible dot-only edge (through the public extra_graph_attrs hook of layout()):
# LoggedOut -> Browsing keeps the LoggedIn composite below the top row (minlen=3 leaves a rank
# of air for the exit labels).  weight=0: the edge only constrains ranks and does not drag
# Browsing sideways towards LoggedOut (the top row is centred afterwards anyway).
INVIS = f'"{logged_out}" -> "{browsing}" [style=invis, minlen=3, weight=0];'
d.layout(rankdir="TB", nodesep=0.9, ranksep=1.0, ordering="in", extra_graph_attrs=INVIS)

# ---- post-layout 1: centre the top row over the composite ------------------------------------
# Graphviz places the outer nodes relative to Browsing, which is right of the composite's middle,
# so the whole top row ends up right-heavy.  The top row is self-contained (its Graphviz-routed
# edges only connect nodes of the row; the three edges to the composite have fixed ports and no
# waypoints), so it can be shifted as a block after layout.
cells = {c.id: c for c in d.cells}
box = cells[li]
TOP = {start, fin, logged_out, auth}
top_cells = [cells[i] for i in TOP]
top_cx = (min(c.x for c in top_cells) + max(c.x + c.w for c in top_cells)) / 2
shift = (box.x + box.w / 2) - top_cx
shift = max(shift, 20 - min(c.x for c in top_cells))          # never leave the page on the left
for c in d.cells:
    if c.vertex and c.id in TOP:
        c.x += shift
    elif not c.vertex and c.source in TOP and c.target in TOP and c.points:
        c.points = [(px + shift, py) for (px, py) in c.points]

# ---- post-layout 2: fixed ports for the three edges that touch the composite border ------------
lo, au = cells[logged_out], cells[auth]
lo_cx = lo.x + lo.w / 2
au_cx = au.x + au.w / 2
EXIT_DX = 48                      # half distance between the two parallel exits under LoggedOut


def rel_x(px: float) -> float:
    """x inside the composite as a 0..1 port coordinate (kept 40 px away from the corners)."""
    px = min(max(px, box.x + 40), box.x + box.w - 40)
    return (px - box.x) / box.w


for c in d.cells:
    if c.vertex:
        continue
    c_style = c.style.replace("curved=1;", "")
    if c.source == li and c.target == logged_out:
        # two parallel vertical exits leaving the top border right under LoggedOut;
        # labels are pushed to the outer side of each line
        left = "Log out" in c.value
        sx = lo_cx + (-EXIT_DX if left else EXIT_DX)
        c.points = None
        c.style = c_style + (f"exitX={rel_x(sx):.3f};exitY=0;exitDx=0;exitDy=0;"
                             f"entryX={(sx - lo.x) / lo.w:.3f};entryY=1;entryDx=0;entryDy=0;")
        c.offset = (0.0, 0.0)
        c.abs_offset = (-92, 0) if left else (72, 0)
    elif c.source == auth and c.target == li:
        # entry from Authenticating's bottom straight down into the composite's top border
        # (diagonal only if Authenticating stands outside the composite's x-span)
        c.points = None
        c.style = c_style + (f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                             f"entryX={rel_x(au_cx):.3f};entryY=0;entryDx=0;entryDy=0;")
        c.offset = (0.0, 0.0)
        c.abs_offset = (100, 0)

# ---- post-layout 3: draw.io renders labels a little wider than Graphviz reserved for them;
# nudge the "close app" label off its (diagonal) line
for c in d.cells:
    if not c.vertex and c.source == logged_out and c.target == fin:
        ox, oy = c.abs_offset or (0.0, 0.0)
        c.abs_offset = (ox + 26, oy)

d.save(OUT("12-state-session"))
