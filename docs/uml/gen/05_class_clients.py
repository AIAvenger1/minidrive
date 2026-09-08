"""05 — Class diagram: shared packages, web client and desktop client (spec §3.3–§3.5).

Four packages, left to right: packages/shared (types and pure modules), packages/ui (the React
screens both clients render), apps/web and apps/desktop.

The screens are *not* duplicated per client: DriveWorkspace composes the seven controls once in
packages/ui, and each app only mounts it — the web through its /drive page, the desktop through
its App shell, which additionally wraps SyncPanel with the platform callbacks (Electron IPC on
the desktop, the File System Access API in the browser).  packages/shared exports modules of free
functions rather than utility classes, so they are drawn as «module» boxes.

Graphviz LR layout with routed edges; cross-package «import» is drawn once per package.
"""
from _common import *

d = GraphDiagram("Class diagram — shared packages, web client and desktop client", routing=ORTHO)

USE = "«use»"
OVERRIDES = ["+ canRender(ext): boolean", "+ render(): PreviewResult"]


def dep(a, b, label="", back=False, **kw):
    kw.setdefault("dot_reverse", back)
    return d.edge(a, b, E_DEPENDENCY, label, **kw)


def gen(child, parent):
    return d.generalization(child, parent)


def comp(whole, part, back=False):
    return d.edge(whole, part, E_COMPOSITION, "", dot_reverse=back)


# =============================================================================
# packages/shared — types and modules of pure functions
# =============================================================================
shared = d.group("packages/shared", color=LIST)

file_dto = d.klass("FileDto",
                   attrs=["id: string", "name: string", "extension: string", "size: number",
                          "createdAt: string (ISO)", "updatedAt: string (ISO)",
                          "uploadedBy: string", "modifiedBy: string"],
                   stereotype="type", color=LIST, group=shared, min_w=170)
column_visibility = d.klass("ColumnVisibility",
                            attrs=["Record<ColumnKey, boolean>", "name is always true"],
                            stereotype="type", color=LIST, group=shared)
local_file_info = d.klass("LocalFileInfo",
                          attrs=["name: string", "size: number", "mtime: number (epoch ms)"],
                          stereotype="type", color=SYNC, group=shared, min_w=170)
sync_action = d.klass("SyncAction", attrs=["kind: 'upload' | 'download' | 'skip'",
                                           "name: string", "reason: string"],
                      stereotype="type", color=SYNC, group=shared, min_w=170)
sync_plan = d.klass("SyncPlan",
                    attrs=["uploads: SyncAction[]", "downloads: SyncAction[]", "skipped: SyncAction[]"],
                    stereotype="type", color=SYNC, group=shared, min_w=170)
sync_report = d.klass("SyncReport",
                      attrs=["uploaded: number", "downloaded: number", "skipped: number",
                             "failed: number", "errors: string[]"],
                      stereotype="type", color=SYNC, group=shared, min_w=170)

file_list = d.klass("fileList", methods=[
    "+ extensionOf(name): string",
    "+ sortByName(files, order): FileDto[]",
    "+ filterByType(files, filter): FileDto[]",
    "+ isSafeFileName(name): boolean",
    "+ isSyncableName(name): boolean",
], stereotype="module", color=LIST, group=shared)
columns_mod = d.klass("columns", methods=[
    "+ COLUMN_KEYS / DEFAULT_COLUMNS",
    "+ toggleColumn(visibility, key): ColumnVisibility",
], stereotype="module", color=LIST, group=shared)
limits_mod = d.klass("limits", methods=[
    "+ MAX_UPLOAD_MB = 50",
    "+ splitBySize(files): {accepted, rejected}",
], stereotype="module", color=OPS, group=shared)
preview_mod = d.klass("preview", methods=[
    "+ previewKindOf(name): PreviewKind",
    "+ createPreview(entry: FileDto): FilePreview",
], stereotype="module", color=LIST, group=shared)
sync_mod = d.klass("sync", methods=[
    "+ SKEW_MS = 2000",
    "+ computeSyncPlan(local, remote): SyncPlan",
    "+ runSyncPlan(plan, remote, transfers): SyncReport",
    "+ emptySyncReport() / failedSyncReport()",
], stereotype="module", color=SYNC, group=shared)
ledger_mod = d.klass("syncLedger", methods=[
    "+ SyncLedger = Record<name, entry>",
    "+ reconcileWithLedger(local, ledger): LocalFileInfo[]",
    "+ recordTransfer(ledger, name, entry): SyncLedger",
    "+ pruneLedger(ledger, present): SyncLedger",
], stereotype="module", color=SYNC, group=shared)

file_preview = d.klass("FilePreview", attrs=["# entry: FileDto"], methods=OVERRIDES,
                       stereotype="abstract", color=LIST, group=shared, italic_name=True)
text_preview = d.klass("TextPreview", methods=OVERRIDES, stereotype=".cs, text", color=LIST, group=shared)
image_preview = d.klass("ImagePreview", methods=OVERRIDES, stereotype=".jpg, image", color=LIST, group=shared)

view_model = d.klass("DriveViewModel",
                     attrs=["files / order / filter", "columns / selected"],
                     methods=["+ setFiles / setOrder / setFilter",
                              "+ toggleColumn / select",
                              "+ get visibleFiles(): FileDto[]"],
                     color=LIST, group=shared, min_w=190)
api_client = d.klass("ApiClient",
                     attrs=["- baseUrl: string", "- token: string | null"],
                     methods=["+ register() / login() / me()", "+ listFiles(): FileDto[]",
                              "+ upload(name, body, mimeType): FileDto",
                              "+ download(id): Blob", "+ remove(id): void",
                              "throws ApiError {status}"],
                     color=ACCESS, group=shared, min_w=190)

comp(sync_plan, sync_action, back=True)
dep(sync_mod, sync_plan, "«create»", back=True)
dep(sync_mod, local_file_info, back=True)
dep(sync_mod, sync_report, back=True)
dep(ledger_mod, local_file_info, back=True)
dep(file_list, file_dto, back=True)
dep(columns_mod, column_visibility, back=True)
dep(preview_mod, file_preview, "«create»", back=True)
gen(text_preview, file_preview)
gen(image_preview, file_preview)
dep(view_model, file_list, USE, back=True)
dep(view_model, columns_mod, USE, back=True)

# =============================================================================
# packages/ui — the React layer both clients render
# =============================================================================
ui = d.group("packages/ui — shared React layer", color=LIST)


def component(name: str, color: str, group: str, **kw) -> str:
    return d.klass(name, stereotype="component", color=color, group=group, min_w=150, **kw)


login_form = component("LoginForm", ACCESS, ui,
                       attrs=["baseUrl field (desktop)", "sign up / log in modes"])
drive_workspace = component("DriveWorkspace", LIST, ui,
                            attrs=["composes the seven controls",
                                   "+ uploadFiles / downloadSelected", "+ deleteSelected / logout"])
u_upload = component("UploadDropzone", OPS, ui)
u_sort = component("SortControl", LIST, ui)
u_filter = component("FilterControl", LIST, ui)
u_columns = component("ColumnToggle", LIST, ui)
u_table = component("FileTable", LIST, ui)
u_preview = component("PreviewPanel", LIST, ui)
u_sync_panel = component("SyncPanel", SYNC, ui,
                         attrs=["props: pickFolder, synchronize,", "watch, progress, boundFolder",
                                "renders SyncReportSummary"])
use_drive = d.klass("useDrive", stereotype="hook", color=LIST, group=ui,
                    methods=["+ refresh()   (401 → onUnauthorized)",
                             "+ update(fn): void", "+ vm / busy / error"], min_w=190)
api_registry = d.klass("apiRegistry", stereotype="module", color=ACCESS, group=ui,
                       methods=["+ configureApi(baseUrl, token)", "+ getApi(): ApiClient"],
                       min_w=190)

for c in (u_upload, u_sort, u_filter, u_columns, u_table, u_preview):
    comp(drive_workspace, c)
dep(drive_workspace, use_drive, USE)
dep(drive_workspace, limits_mod, "«use» splitBySize", back=True)
dep(drive_workspace, api_registry, "«use» getApi")
dep(login_form, api_registry, "«use» configureApi")
dep(u_preview, preview_mod, "«use» createPreview", back=True)
dep(use_drive, view_model, back=True)
dep(api_registry, api_client, back=True)

# =============================================================================
# apps/web (Next.js)
# =============================================================================
web = d.group("apps/web (Next.js)", color=ACCESS)

login_page = d.klass("LoginPage", stereotype="page /login", color=ACCESS, group=web, min_w=150)
drive_page = d.klass("DrivePage", stereotype="page /drive", color=LIST, group=web, min_w=150)
session_store = d.klass("SessionStore", attrs=["token in localStorage"],
                        methods=["+ load() / save(token) / clear()",
                                 "restored by useSession (GET /auth/me)"],
                        color=ACCESS, group=web)
browser_sync = d.klass("BrowserSyncEngine",
                       attrs=["- api: SyncApi", "- ledgers: LedgerStore"],
                       methods=["+ scan(dir): LocalFileInfo[]",
                                "+ synchronize(dir, onProgress): SyncReport",
                                "module: supportsFolderSync / pickFolder"],
                       color=SYNC, group=web, min_w=200)
ledger_store = d.klass("localLedgerStore", stereotype="module", color=SYNC, group=web,
                       methods=["+ load(folder) / save(folder, ledger)   (localStorage)"], min_w=190)
web_note = d.note("File System Access API (Chrome / Edge only);\nno automatic watching — every run is manual;\n"
                  "the mtime of a written file is kept in a\nlocalStorage ledger so the next run sees it as Synced",
                  group=web, w=300)

comp(drive_page, drive_workspace)
comp(drive_page, u_sync_panel)
comp(login_page, login_form)
dep(login_page, session_store)
dep(drive_page, browser_sync)
dep(browser_sync, sync_mod, "«use» computeSyncPlan,\nrunSyncPlan", back=True)
dep(browser_sync, ledger_mod, "«use»", back=True)
dep(browser_sync, ledger_store)
d.note_link(web_note, browser_sync)

# =============================================================================
# apps/desktop (Electron)
# =============================================================================
desktop = d.group("apps/desktop (Electron)", color=SYNC)
renderer_g = d.group("Renderer (React)", parent=desktop, color="white")
preload_g = d.group("Preload", parent=desktop, color="white")
main_g = d.group("Main process", parent=desktop, color="white")

r_app = d.klass("App", stereotype="shell", color=ACCESS, group=renderer_g,
                methods=["+ mounts LoginForm | DriveWorkspace"], min_w=170)
r_sync_panel = d.klass("SyncPanel", stereotype="wrapper", color=SYNC, group=renderer_g,
                       methods=["+ binds SyncPanel to window.minidrive"], min_w=170)
r_session = d.klass("SessionStore", attrs=["token via IPC"],
                    methods=["+ load() / save(token) / clear()"], color=ACCESS, group=renderer_g)

preload_bridge = d.klass("PreloadBridge", attrs=["+ window.minidrive: contextBridge API"],
                         color=INFRA, group=preload_g, min_w=190)

main_window = d.klass("createWindow", stereotype="function", color=INFRA, group=main_g, min_w=150)
ipc_handlers = d.klass("registerIpc", stereotype="function", color=INFRA, group=main_g,
                       methods=["+ sync:run / sync:watch / sync:pick",
                                "+ session:* / file:drag"], min_w=190)
settings = d.klass("settings", stereotype="module", color=INFRA, group=main_g,
                   methods=["+ baseUrl / boundFolder / autoWatch",
                            "+ token encrypted (safeStorage)"], min_w=190)
drag_out_handler = d.klass("dragOutHandler", stereotype="module", color=OPS, group=main_g,
                           methods=["+ startDrag(sender, api, file)"], min_w=190)
local_folder_scanner = d.klass("LocalFolderScanner", stereotype="module", color=SYNC, group=main_g,
                               methods=["+ scan(dir): LocalFileInfo[]"], min_w=190)
sync_engine = d.klass("SyncEngine",
                      attrs=["- api: SyncApi", "- scanner"],
                      methods=["+ scan(dir): LocalFileInfo[]",
                               "+ synchronize(dir, onProgress): SyncReport"],
                      color=SYNC, group=main_g, min_w=190)
folder_watcher = d.klass("FolderWatcher",
                         methods=["+ start(dir, onChange) / stop()", "+ pause() / resume()",
                                  "+ get active(): boolean"],
                         color=SYNC, group=main_g, min_w=190)

comp(r_app, drive_workspace)
dep(r_app, login_form)
comp(r_sync_panel, u_sync_panel)
dep(r_app, r_session)
dep(r_sync_panel, preload_bridge)
dep(r_session, preload_bridge)
dep(preload_bridge, ipc_handlers, "«ipc» invoke / on")
dep(ipc_handlers, sync_engine, USE)
dep(ipc_handlers, folder_watcher, USE)
dep(ipc_handlers, drag_out_handler, USE)
dep(ipc_handlers, settings, USE)
dep(sync_engine, local_folder_scanner, USE)
dep(sync_engine, sync_mod, "«use» computeSyncPlan,\nrunSyncPlan", back=True)
dep(drag_out_handler, main_window, "«use» startDrag")

d.legend("Colours: blue = access / session, green = file list, sort, filter, preview, "
         "yellow = upload / download, purple = synchronization, grey = infrastructure.\n"
         "Dashed open arrow = dependency («use», «create», «import»), hollow triangle = generalization, "
         "filled diamond = composition.\n"
         "«module» = a TypeScript module of exported functions and constants (there are no utility "
         "classes); «component» / «hook» = React.\n"
         "packages/ui holds every screen: both clients mount the same LoginForm, DriveWorkspace and "
         "SyncPanel and differ only in the platform callbacks.", w=760)

d.layout(rankdir="LR", nodesep=0.35, ranksep=0.5)

d.save(OUT("05-class-clients"))
