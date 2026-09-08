"""15 — Component diagram with interfaces.

Source of truth: docs/superpowers/specs/2026-09-07-minidrive-design.md §3 (architecture).
Left → right: shared packages + bound local folder | web / desktop clients | REST interface |
API modules | provided storage interfaces (SQL, S3) | infrastructure (PostgreSQL, MinIO).
Both clients import the same two workspace packages: @minidrive/shared (types and pure logic)
and @minidrive/ui (the React screens and controls), so the UI components belong to neither app.
Colours: blue = web client (access), purple = desktop client + bound folder (synchronization),
green = @minidrive/shared and @minidrive/ui (file-list logic and screens), grey = infrastructure.
"""
from _common import *  # noqa: F401,F403

d = GraphDiagram("Component diagram", routing=ORTHO)

# Graphviz ejects cluster members from a root-level rank=same, so nodes INSIDE a subsystem cannot
# be same_rank()ed.  Instead every intra-subsystem edge gets minlen=0: dot treats it as a flat edge
# and keeps the subsystem's components stacked in ONE column.  In LR mode the head of a flat edge
# is drawn ABOVE its tail, hence dot_reverse=True wherever the arrow must point downwards.
FLAT = dict(minlen=0, weight=4)
DOWN = dict(dot_reverse=True, **FLAT)


def ports(exit_x, exit_y, entry_x, entry_y):
    """draw.io connection points: the edge leaves / enters on the side facing the other end
    (without them draw.io may attach a diagonal edge to the top or bottom of a box)."""
    return (f"exitX={exit_x};exitY={exit_y};exitDx=0;exitDy=0;"
            f"entryX={entry_x};entryY={entry_y};entryDx=0;entryDy=0;")


RIGHTWARDS = ports(1, 0.5, 0, 0.5)   # source right side -> target left side
LEFTWARDS = ports(0, 0.5, 1, 0.5)    # source left side  -> target right side


def requires(consumer, target, label="", p=RIGHTWARDS, **kw):
    """Dependency (dashed open arrow) from a consumer to an interface / package / artifact."""
    return d.edge(consumer, target, E_DEPENDENCY + p, label, **kw)


def provides(provider, iface, **kw):
    """Provider —— lollipop.  The lollipop is ranked BEFORE its provider (dot_reverse) so it sits
    to the left of the provider, facing the consumers."""
    return d.edge(provider, iface, E_ASSOC + LEFTWARDS, "", dot_reverse=True, **kw)


# ---------------------------------------------------------------------------
# Subsystems (draw.io containers).  Declaration order seeds the top-to-bottom order in LR mode.
# ---------------------------------------------------------------------------
g_web = d.group("Web client — Next.js (apps/web)", color=ACCESS)
g_desktop = d.group("Desktop client — Electron (apps/desktop)", color=SYNC)
g_api = d.group("API — NestJS (apps/api)", color=INFRA)

# ---------------------------------------------------------------------------
# Column 0: shared package (tall: four «import» ports on its right side) + bound local folder
# ---------------------------------------------------------------------------
shared = d.component("@minidrive/shared\n(packages/shared)", LIST, h=110)
folder = d.artifact("Bound local folder", SYNC)

# Column 0b: the shared React layer — both clients render the very same screens and controls
ui_pkg = d.component("@minidrive/ui (packages/ui)\nLoginForm, DriveWorkspace,\nSyncPanel, FileTable, PreviewPanel,\nUploadDropzone, SortControl,\nFilterControl, ColumnToggle,\napiRegistry, useDrive", LIST, w=280, h=120)

# ---------------------------------------------------------------------------
# Column 1: client components.  One width for all six boxes so the edges leaving them to the
# right jog at the same x.
# ---------------------------------------------------------------------------
CW = 260
pages = d.component("Pages (/login, /drive)", ACCESS, group=g_web, w=CW)
bsync = d.component("BrowserSyncEngine", ACCESS, group=g_web, w=CW)

renderer = d.component("Renderer UI (React)", SYNC, group=g_desktop, w=CW)
preload = d.component("Preload bridge", SYNC, group=g_desktop, w=CW)
main_proc = d.component("Main process\n(SyncEngine, FolderWatcher,\nIpcHandlers, DragOutHandler)", SYNC,
                        group=g_desktop, w=CW)

# ---------------------------------------------------------------------------
# Column 2: the REST interface provided by the API
# ---------------------------------------------------------------------------
# three short lines: a narrow label leaves room for the consumer edges arriving from below-left
rest = d.lollipop("REST API\n(/auth, /files,\n/health, /docs)\nHTTPS/JSON")
n_rest = d.note("In the cloud deployment both clients reach this\ninterface through the caddy reverse proxy (HTTPS :443);\nthe web app itself is served by the web container\n(Next.js standalone, :3000).  /docs (Swagger) is\npublished locally only (SWAGGER_ENABLED).", w=330)

# ---------------------------------------------------------------------------
# Column 3: API modules — one column, internal dependencies drawn as vertical arrows.
# Declared as the chain Auth → Users → Prisma ← Files → Storage so that every flat edge joins two
# vertically adjacent boxes.
# ---------------------------------------------------------------------------
auth_mod = d.component("AuthModule", INFRA, group=g_api)
users_mod = d.component("UsersModule", INFRA, group=g_api)
prisma_mod = d.component("PrismaModule", INFRA, group=g_api)
files_mod = d.component("FilesModule", INFRA, group=g_api)
storage_mod = d.component("StorageModule", INFRA, group=g_api)

# ---------------------------------------------------------------------------
# Columns 4–5: storage interfaces and the infrastructure that provides them
# ---------------------------------------------------------------------------
sql = d.lollipop("SQL (Prisma)")
s3 = d.lollipop("S3 API")
postgres = d.database("PostgreSQL", INFRA)
minio = d.database("MinIO\n(S3 object storage)", INFRA)

# ---------------------------------------------------------------------------
# REST API: provided by AuthModule + FilesModule, required by the client UIs
# ---------------------------------------------------------------------------
provides(auth_mod, rest)
provides(files_mod, rest)
requires(pages, rest)
requires(bsync, rest)
# weight pulls the lollipop down towards the desktop client so this edge arrives almost horizontally
# and does not cut through the lollipop label hanging under the circle
requires(renderer, rest, weight=3)
d.note_link(n_rest, rest, place="auto")

# ---------------------------------------------------------------------------
# Storage interfaces: SQL provided by PostgreSQL, S3 API provided by MinIO
# ---------------------------------------------------------------------------
requires(prisma_mod, sql)
provides(postgres, sql)
requires(storage_mod, s3)
provides(minio, s3)

# ---------------------------------------------------------------------------
# Desktop internals: Renderer —IPC— Preload —— Main process; Main process → bound folder
# ---------------------------------------------------------------------------
d.assoc(renderer, preload, "IPC (contextBridge)", **DOWN)
d.assoc(preload, main_proc, **DOWN)
# leaves Main below its centre so the edge does not share a segment with the «import» edge above;
# the folder is ranked before Main (dot_reverse) so it sits to the left, next to the desktop group.
requires(main_proc, folder, "Node fs / chokidar", p=ports(0, 0.75, 1, 0.8), dot_reverse=True)

# ---------------------------------------------------------------------------
# «import» of the shared package (arrows point left, towards column 0).  The four edges fan out
# into four ports on the right side of the package: top source → top port.
# ---------------------------------------------------------------------------
requires(ui_pkg, shared, "«import»", p=ports(0, 0.5, 1, 0.2), dot_reverse=True)
requires(bsync, shared, "«import»", p=ports(0, 0.5, 1, 0.4), dot_reverse=True)
requires(renderer, shared, "«import»", p=ports(0, 0.5, 1, 0.6), dot_reverse=True)
requires(main_proc, shared, "«import»", p=ports(0, 0.25, 1, 0.8), dot_reverse=True)

# Both clients render the very same screens: they «import» @minidrive/ui instead of owning
# a private copy of the components (apps/web/src/app/drive/page.tsx, apps/desktop/.../App.tsx).
requires(pages, ui_pkg, "«import»", p=ports(0, 0.5, 1, 0.3), dot_reverse=True)
requires(renderer, ui_pkg, "«import»", p=ports(0, 0.5, 1, 0.7), dot_reverse=True)

# ---------------------------------------------------------------------------
# API internal dependencies (spec §3.2): Auth → Users → Prisma, Files → Storage, Files → Prisma
# ---------------------------------------------------------------------------
d.dependency(auth_mod, users_mod, **DOWN)
d.dependency(users_mod, prisma_mod, **DOWN)
d.dependency(files_mod, prisma_mod, **FLAT)          # arrow points up: Prisma sits above Files
d.dependency(files_mod, storage_mod, **DOWN)

# ---------------------------------------------------------------------------
# Layout: line up the three top-level columns (package + folder | interfaces | data stores);
# the client / API columns are clusters and are aligned by dot itself.
# ---------------------------------------------------------------------------
d.same_rank(shared, folder)
d.same_rank(ui_pkg, folder)
d.same_rank(sql, s3)
d.same_rank(postgres, minio)

d.legend(
    "○ — provided interface (lollipop);  dashed open arrow — dependency / required interface\n"
    "solid line — assembly / IPC link;  «artifact» — folder on the local file system;  "
    "cylinder — database / object store\n"
    "colours: blue = web client (access);  purple = desktop client + local folder (synchronization);\n"
    "green = shared workspace packages (@minidrive/shared logic, @minidrive/ui screens);  "
    "grey = infrastructure",
    w=600,
)

d.layout(rankdir="LR", nodesep=0.5, ranksep=0.9)
d.save(OUT("15-component"))
