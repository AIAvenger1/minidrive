"""16 — Deployment diagram: local development (Stage 2) and cloud (Stage 3 bonus).

Source of truth: docs/superpowers/specs/2026-09-07-minidrive-design.md §3 (architecture) and §6
(deployment).  Three «device» nodes: the end-user workstation, the cloud VM and the developer
workstation; execution environments are nested 3-D nodes, Docker containers are components,
databases / object stores are cylinders, deployed programs are «artifact»s.  Communication paths
are plain associations labelled with protocol and port.
"""
from _common import *

d = GraphDiagram("Deployment diagram — local development and cloud", routing=ORTHO)


def ports(exit_y=0.5, entry_y=0.5, backwards=False):
    """Fixed connection points: every path leaves the right-hand side of its source and enters the
    left-hand side of its target (or the reverse for `backwards`), so the picture reads left -> right
    and the jog of each edge lies in the gap between two columns, never through a neighbour.
    `exit_y` / `entry_y` (0..1) pick the height of the port on that side so that several paths
    reaching the same node land at distinct points instead of converging into one."""
    ex, nx = (0, 1) if backwards else (1, 0)
    return (f"exitX={ex};exitY={exit_y};exitDx=0;exitDy=0;"
            f"entryX={nx};entryY={entry_y};entryDx=0;entryDy=0;")


def path(a, b, label, exit_y=0.5, entry_y=0.5, backwards=False, **kw):
    """Communication path: plain line with a protocol / port label."""
    return d.edge(a, b, E_ASSOC + ports(exit_y, entry_y, backwards), label, **kw)


# ---------------------------------------------------------------------------
# Device 1 — user workstation (desktop client + browser)
# ---------------------------------------------------------------------------
g_user = d.node3d("«device»\nUser workstation (macOS / Windows)", color=INFRA)
bound_folder = d.artifact("Bound local folder", color=SYNC, group=g_user)
desktop_app = d.artifact("MiniDrive desktop app (Electron)", color="white", group=g_user)
g_browser = d.node3d("«executionEnvironment»\nChrome / Edge browser", parent=g_user, color="white")
web_client = d.artifact("MiniDrive web client (Next.js pages)", color="white", group=g_browser)

# ---------------------------------------------------------------------------
# Device 2 — cloud VM running Docker Compose (Stage 3 bonus)
# ---------------------------------------------------------------------------
g_cloud = d.node3d("«device»\nCloud VM — Ubuntu (Docker host)", color=INFRA)
g_compose = d.node3d("«executionEnvironment»\nDocker Compose", parent=g_cloud, color="white")
caddy = d.component("caddy (TLS reverse proxy :443)", color=INFRA, group=g_compose)
api = d.component("api — NestJS (:3000)", color=INFRA, group=g_compose)
web = d.component("web — Next.js standalone (:3000)", color=INFRA, group=g_compose)
postgres = d.database("postgres\n(:5432, volume pgdata)", color=INFRA, group=g_compose)
minio = d.database("minio\n(:9000, volume miniodata)", color=INFRA, group=g_compose)
n_swagger = d.note("SWAGGER_ENABLED=false:\nthe /docs page is served\nlocally only", group=g_compose)

# ---------------------------------------------------------------------------
# Device 3 — developer workstation (Stage 2, everything local)
# ---------------------------------------------------------------------------
g_dev = d.node3d("«device»\nDeveloper workstation (Stage 2, local)", color=INFRA)
electron_dev = d.artifact("Electron app (yarn dev)", color="white", group=g_dev)
g_compose_local = d.node3d("«executionEnvironment»\nDocker Compose (local)", parent=g_dev, color="white")
api_local = d.component("api (:3000)", color=INFRA, group=g_compose_local)
pg_local = d.database("postgres", color=INFRA, group=g_compose_local)
minio_local = d.database("minio\n(:9000, console :9001)", color=INFRA, group=g_compose_local)
# The note lives inside the local compose node, stacked above the api container (flat note
# link, minlen=0) — placing it outside would land it in caddy's column and stretch the device box.
n_same = d.note("same images as in the cloud", group=g_compose_local)

# ---------------------------------------------------------------------------
# Device 4 — GitHub Actions runner (continuous integration)
# ---------------------------------------------------------------------------
g_ci = d.node3d("«device»\nGitHub Actions runner (ubuntu-latest)", color=INFRA)
ci_job = d.artifact("ci.yml — yarn build + yarn test", color="white", group=g_ci)

# ---------------------------------------------------------------------------
# Communication paths
# ---------------------------------------------------------------------------
# The bound folder is ranked *before* the desktop app (dot_reverse) so it sits to the left of it
# and the whole picture flows: local folder | clients | reverse proxy | services | stores.
# weight=10 keeps the folder level with the desktop app (straight "fs" line).
path(desktop_app, bound_folder, "fs", backwards=True, dot_reverse=True, weight=10)
# minlen=2 widens the gap between the two device boxes so the labels sit in the open space.
# The browser sits above caddy and the desktop app below it, so the two paths enter caddy's left
# side at different heights (upper / lower third) instead of converging into one point.
path(web_client, caddy, "HTTPS :443", entry_y=0.3, minlen=2)
path(desktop_app, caddy, "HTTPS/JSON :443", entry_y=0.7, minlen=2)
# Fan-outs: with ordering=out and rankdir=LR dot stacks the *first* declared target at the bottom,
# so "api" / "postgres" are declared first (bottom, exit port at 0.7) and "web" / "minio" second
# (top, exit port at 0.3) — the fixed ports then match the node positions and no lines cross.
path(caddy, api, "HTTP :3000", exit_y=0.7)
path(caddy, web, "HTTP :3000", exit_y=0.3)
path(api, postgres, "TCP :5432 (Prisma)", exit_y=0.7)
path(api, minio, "S3 API :9000", exit_y=0.3)
# Local stack: the same wiring as in the cloud, minus caddy / web
path(electron_dev, api_local, "HTTP :3000")
path(api_local, pg_local, "TCP :5432", exit_y=0.7)
path(api_local, minio_local, "S3 API :9000", exit_y=0.3)
d.note_link(n_same, api_local, place="auto", minlen=0)
d.note_link(n_swagger, api, place="auto", minlen=0)

# NOTE: same_rank() cannot be used across clusters — Graphviz drops such nodes from their
# cluster ("was already in a rankset, deleted from cluster").  The two workstations are
# left-aligned anyway: the bound folder and the Electron dev app have no predecessors, so dot
# puts both in rank 0 (the leftmost column).  Two invisible dot-only edges (injected through
# the public extra_graph_attrs hook, not drawn) fine-tune the picture:
#   * bound folder -> web client: moves the browser into the desktop app's column, so both
#     client -> caddy paths leave the user workstation from the same x;
#   * desktop app -> Electron dev app (constraint=false, no rank effect): joins the otherwise
#     disconnected developer workstation to the main component so that dot's crossing
#     minimisation places it *below* the user workstation / cloud pair (flat invisible edges
#     across clusters are ignored by dot, so this non-flat edge is used instead).
INVIS = (f'node [shape=box, fixedsize=true, label=""]; '
         f'"{bound_folder}" -> "{web_client}" [style=invis, minlen=1]; '
         f'"{desktop_app}" -> "{electron_dev}" [style=invis, constraint=false];'
         f'"{electron_dev}" -> "{ci_job}" [style=invis, constraint=false];')

d.legend(
    "«device» / «executionEnvironment» — 3-D nodes (hardware / runtime)\n"
    "component — Docker container;  cylinder — database / object store\n"
    "«artifact» — deployed program or folder;  solid line — communication path (protocol :port)\n"
    "colours: purple = local folder synchronized with the space;  grey = infrastructure",
    w=470,
)

d.layout(rankdir="LR", nodesep=0.45, ranksep=0.8, extra_graph_attrs=INVIS)
d.save(OUT("16-deployment"))
