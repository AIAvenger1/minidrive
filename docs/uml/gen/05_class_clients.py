"""05 — Class diagram: shared package, web client and desktop client (spec §3.3–§3.5).

Graphviz LR layout with routed edges; cross-package dependencies are drawn once per package."""
from _common import *

d = GraphDiagram("Class diagram — shared package, web client and desktop client", routing=ORTHO)

USE = "«use»"
OVERRIDES = ["+ canRender(ext): boolean", "+ render(): PreviewResult"]
# fixed ports: FWD = leave on the right, enter on the left; BACK = the opposite (arrow points left)
FWD = "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
BACK = "exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
LBL = "labelBackgroundColor=#ffffff;"


def ports(ex, ey, nx, ny):
    return f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;"


def dep(a, b, label="", back=False, port=None, **kw):
    kw.setdefault("dot_reverse", back)
    kw.pop("port", None)
    return d.edge(a, b, E_DEPENDENCY, label, **kw)


def gen(child, parent):
    return d.generalization(child, parent)


def comp(whole, part, back=False):
    return d.edge(whole, part, E_COMPOSITION, "", dot_reverse=back)


# =============================================================================
# packages/shared
# =============================================================================
shared = d.group("packages/shared", color=LIST)

sync_report = d.klass("SyncReport",
                      attrs=["uploaded: number", "downloaded: number", "skipped: number",
                             "failed: number", "errors: string[]"],
                      stereotype="type", color=SYNC, group=shared, min_w=150)
sync_action = d.klass("SyncAction", attrs=["kind: SyncActionKind", "name: string", "reason: string"],
                      stereotype="type", color=SYNC, group=shared, min_w=150)
sync_plan = d.klass("SyncPlan",
                    attrs=["uploads: SyncAction[]", "downloads: SyncAction[]", "skipped: SyncAction[]"],
                    stereotype="type", color=SYNC, group=shared, min_w=150)
local_file_info = d.klass("LocalFileInfo", attrs=["name: string", "size: number", "mtime: Date"],
                          stereotype="type", color=SYNC, group=shared, min_w=150)
sync_ledger = d.klass("SyncLedger",
                      attrs=["- entries: Map<name, {size, mtime, updatedAt}>"],
                      methods=["+ reconcileWithLedger(local, ledger)",
                               "+ recordTransfer(ledger, name, entry)",
                               "+ pruneLedger(ledger, present)"],
                      color=SYNC, group=shared, min_w=210)
file_dto = d.klass("FileDto",
                   attrs=["id", "name", "extension", "size", "createdAt", "updatedAt",
                          "uploadedBy", "modifiedBy"],
                   stereotype="dto", color=LIST, group=shared, min_w=150)
column_visibility = d.klass("ColumnVisibility",
                            attrs=["Record<ColumnKey, boolean>", "name: always true"],
                            stereotype="type", color=LIST, group=shared)
file_preview = d.klass("FilePreview", attrs=["# entry: FileDto"], methods=OVERRIDES,
                       stereotype="abstract", color=LIST, group=shared, italic_name=True)
file_list_utils = d.klass("FileListUtils", methods=[
    "+ sortByName(files, order): FileDto[]",
    "+ filterByType(files, filter): FileDto[]",
    "+ previewKindOf(name): PreviewKind",
    "+ toggleColumn(visibility, key): ColumnVisibility",
    "+ computeSyncPlan(local: LocalFileInfo[], remote: FileDto[]): SyncPlan",
], stereotype="utility", color=LIST, group=shared)
preview_factory = d.klass("PreviewFactory", methods=["+ createPreview(entry: FileDto): FilePreview"],
                          stereotype="factory", color=LIST, group=shared)
text_preview = d.klass("TextPreview", methods=OVERRIDES, stereotype=".cs, text", color=LIST, group=shared)
image_preview = d.klass("ImagePreview", methods=OVERRIDES, stereotype=".jpg, image", color=LIST, group=shared)

comp(sync_plan, sync_action, back=True)
dep(file_list_utils, sync_plan, "«create»", back=True)
dep(file_list_utils, local_file_info, back=True)
dep(file_list_utils, file_dto, back=True)
dep(file_list_utils, column_visibility, back=True)
dep(preview_factory, file_preview, "«create»", back=True)
gen(text_preview, file_preview)
gen(image_preview, file_preview)

# =============================================================================
# apps/web (Next.js)
# =============================================================================
web = d.group("apps/web (Next.js)", color=ACCESS)


def component(name: str, color: str, group: str) -> str:
    return d.klass(name, stereotype="component", color=color, group=group, min_w=140)


# column 0 (bottom-to-top): BrowserSyncEngine, DrivePage, LoginPage
browser_sync = d.klass("BrowserSyncEngine",
                       attrs=["- dirHandle: FileSystemDirectoryHandle"],
                       methods=["+ pickFolder()", "+ scan(dir): LocalFileInfo[]",
                                "+ synchronize(dir): SyncReport"],
                       color=SYNC, group=web, min_w=220)
drive_page = d.klass("DrivePage", stereotype="page", color=LIST, group=web, min_w=140)
login_page = d.klass("LoginPage", stereotype="page", color=ACCESS, group=web, min_w=140)
# column 1 (bottom-to-top): ApiClient, SyncPanel ... FileTable
api_client = d.klass("ApiClient",
                     methods=["+ register()", "+ login()", "+ listFiles()", "+ upload(file)",
                              "+ download(id)", "+ remove(id)"],
                     color=ACCESS, group=web, min_w=150)
w_sync_panel = component("SyncPanel", SYNC, web)
w_upload_dropzone = component("UploadDropzone", OPS, web)
w_preview_panel = component("PreviewPanel", LIST, web)
w_filter_control = component("FilterControl", LIST, web)
w_sort_control = component("SortControl", LIST, web)
w_column_toggle = component("ColumnToggle", LIST, web)
w_file_table = component("FileTable", LIST, web)
drive_workspace = component("DriveWorkspace", LIST, web)
login_form = component("LoginForm", LIST, web)
session_store = d.klass("SessionStore", attrs=["- token (localStorage)"],
                        methods=["+ load()", "+ save(token)", "+ clear()"], color=ACCESS, group=web)
web_note = d.note("File System Access API (Chrome/Edge);\nno automatic watching;\n"
                  "mtime kept in a localStorage ledger", group=web)
ui_note = d.note("shared via packages/ui", group=web)

e_drive_utils = dep(drive_page, file_list_utils, "«use» sortByName, filterByType,\ntoggleColumn, previewKindOf", back=True)
e_drive_factory = dep(drive_page, preview_factory, "«use» createPreview", back=True)
e_bsync_utils = dep(browser_sync, file_list_utils, "«use» computeSyncPlan", back=True)
e_bsync_ledger = dep(browser_sync, sync_ledger, USE, back=True)
for c in (w_sync_panel, w_upload_dropzone, w_preview_panel, w_filter_control, w_sort_control,
          w_column_toggle, w_file_table):
    comp(drive_page, c)
e_drive_api = dep(drive_page, api_client, USE)
e_login_api = dep(login_page, api_client, USE)
e_bsync_api = dep(browser_sync, api_client, USE)
e_api_session = dep(api_client, session_store, USE)
e_syncpanel_bsync = dep(w_sync_panel, browser_sync, USE, back=True, port=ports(0, 0.8, 1, 0.8))
d.note_link(web_note, browser_sync)
d.note_link(ui_note, drive_workspace)
d.note_link(ui_note, login_form)

# =============================================================================
# apps/desktop (Electron)
# =============================================================================
desktop = d.group("apps/desktop (Electron)", color=SYNC)
renderer_g = d.group("Renderer (React) — same components as apps/web", parent=desktop, color="white")
preload_g = d.group("Preload", parent=desktop, color="white")
main_g = d.group("Main process", parent=desktop, color="white")

# renderer column 0 (bottom-to-top): ApiClient, SyncPanel ... FileTable; column 1: SessionStore
r_api_client = d.klass("ApiClient", color=ACCESS, group=renderer_g, min_w=140)
r_sync_panel = component("SyncPanel", SYNC, renderer_g)
r_upload_dropzone = component("UploadDropzone", OPS, renderer_g)
r_preview_panel = component("PreviewPanel", LIST, renderer_g)
r_filter_control = component("FilterControl", LIST, renderer_g)
r_sort_control = component("SortControl", LIST, renderer_g)
r_column_toggle = component("ColumnToggle", LIST, renderer_g)
r_file_table = component("FileTable", LIST, renderer_g)
r_session_store = d.klass("SessionStore", attrs=["- token (safeStorage)"], color=ACCESS, group=renderer_g)

preload_bridge = d.klass("PreloadBridge", attrs=["+ minidrive: window API"], color=INFRA, group=preload_g)

ipc_handlers = d.klass("IpcHandlers", color=INFRA, group=main_g, min_w=140)
drag_out_handler = d.klass("DragOutHandler", methods=["+ startDrag(fileId)"], color=OPS, group=main_g)
local_folder_scanner = d.klass("LocalFolderScanner", methods=["+ scan(path): LocalFileInfo[]"],
                               color=SYNC, group=main_g)
sync_engine = d.klass("SyncEngine", attrs=["- localFolder"],
                      methods=["+ scan()", "+ synchronize(): SyncReport", "+ startWatching()",
                               "+ stopWatching()"], color=SYNC, group=main_g)
main_window = d.klass("MainWindow", color=INFRA, group=main_g, min_w=140)
folder_watcher = d.klass("FolderWatcher", methods=["+ watch(path, onChange)"], color=SYNC, group=main_g)

# renderer -> shared
e_rtable_utils = dep(r_file_table, file_list_utils, "«use» sortByName, filterByType,\ntoggleColumn", back=True)
e_rpreview_factory = dep(r_preview_panel, preview_factory, "«use» createPreview", back=True)
# renderer -> preload -> main (dependency chain)
e_rsync_preload = dep(r_sync_panel, preload_bridge, USE)
e_rtable_preload = dep(r_file_table, preload_bridge, "«use» startDrag")
e_rapi_session = dep(r_api_client, r_session_store, USE)
e_preload_ipc = dep(preload_bridge, ipc_handlers, "«ipc» invoke")
# IpcHandlers -> SyncEngine, DragOutHandler, LocalFolderScanner (declared bottom-to-top)
e_ipc_drag = dep(ipc_handlers, drag_out_handler, USE)
e_ipc_scanner = dep(ipc_handlers, local_folder_scanner, USE)
e_ipc_sync = dep(ipc_handlers, sync_engine, USE)
# SyncEngine -> LocalFolderScanner (same column, vertical), FolderWatcher; DragOutHandler -> MainWindow
e_sync_scanner = dep(sync_engine, local_folder_scanner, USE, constraint=False, port=ports(0.5, 1, 0.5, 0))
e_sync_watcher = dep(sync_engine, folder_watcher, USE)
e_drag_window = dep(drag_out_handler, main_window, "«use» webContents.startDrag")
# main -> shared (routed around the main-process box after layout)
e_sync_utils = dep(sync_engine, file_list_utils, "«use» computeSyncPlan", back=True)

d.legend("Colours: blue = access / session, green = file list, sort, filter, preview, "
         "yellow = upload / download, purple = synchronization, grey = infrastructure.\n"
         "Dashed open arrow = dependency («use»), hollow triangle = generalization, "
         "filled diamond = composition.", w=560)

d.layout(rankdir="LR", nodesep=0.4, ranksep=1.0)

d.save(OUT("05-class-clients"))
