"""09 — Sequence diagram: Upload a file, then view its contents (UC9, UC8).

The client side is the shared React layer of packages/ui: DriveWorkspace is the boundary that
owns the seven controls (a page only mounts it), the useDrive hook holds the DriveViewModel and
does the list refresh, and PreviewPanel loads and renders the selected file on its own.  There is
no upload() or preview() on the view model: DriveWorkspace talks to ApiClient directly and
PreviewPanel calls createPreview(entry) itself.

Part 1 (UC9b, drag-and-drop upload) shows the client-side size check (splitBySize, 50 MB) and the
overwrite-vs-create alternative of FilesService.upsert (UC10 semantics, spec §3.2) followed by the
list refresh; part 2 (UC8) shows the click-to-preview flow for report.cs via createPreview(entry)
→ TextPreview and GET /files/:id/content.
"""
import re

from _common import *  # noqa: F401,F403

q = SequenceDiagram("Sequence diagram — Upload a file, then view its contents (UC9, UC8)",
                    spacing=170, step=38)

# ---- participants ------------------------------------------------------------
user = q.participant("User", "actor")
page = q.participant("DriveWorkspace", "boundary")
hook = q.participant("useDrive", "control")
preview = q.participant("PreviewPanel", "boundary")
api = q.participant("ApiClient", "control")
ctl = q.participant("FilesController", "participant", INFRA)
svc = q.participant("FilesService", "participant", INFRA)
sto = q.participant("StorageService", "participant", INFRA)
db = q.participant("PrismaService", "participant", INFRA)

# narrow note: fits between the DriveWorkspace and useDrive lifelines
q.note(page, "DriveWorkspace\n(packages/ui) owns\nUploadDropzone,\nFileTable and\nPreviewPanel;\na page only\nmounts it", w=112)

# ---- Part 1 — UC9 / UC9b: upload by drag-and-drop ---------------------------
q.message(user, page, "drop report.cs onto the window\n(drag-and-drop)")
q.self_message(page, "splitBySize(files):\nsize ≤ 50 MB")
q.message(page, api, "upload(name, file, mimeType)")
q.message(api, ctl, "POST /files\n(multipart, Bearer)")
q.message(ctl, svc, "upsert(owner, file)")
q.message(svc, db, "fileEntry.findUnique(\n{ownerId, name})")
q.ret(db, svc, "null | FileEntry")

q.fragment("alt", "[exists] — overwrite (UC10)")
q.message(svc, sto, "putObject(storageKey, bytes)")
q.ret(sto, svc)
q.message(svc, db, "fileEntry.update(\n{size, updatedAt, modifiedById})")
q.ret(db, svc)
q.fragment_else("[new] — create")
q.message(svc, db, "fileEntry.create(...)")
q.ret(db, svc, "FileEntry")
q.message(svc, sto, "putObject(\nusers/{ownerId}/{id}, bytes)")
q.ret(sto, svc)
q.end_fragment()
q.gap(1)  # keep the next return label off the fragment border

q.ret(svc, ctl, "FileDto")
q.ret(ctl, api, "201 FileDto")
q.ret(api, page, "FileDto")

# refresh the list after the upload — the hook owns the call, not the view model
q.message(page, hook, "refresh()")
q.message(hook, api, "listFiles()")
q.message(api, ctl, "GET /files")
q.ret(ctl, api, "FileDto[]")
q.ret(api, hook, "FileDto[]")
q.self_message(hook, "vm.setFiles(files);\nrerender()")
q.ret(hook, page, "re-render from vm.visibleFiles")
q.ret(page, user, "report.cs appears in FileTable")
q.deactivate(user)          # part 1 is over: close the User's activation
q.gap(2)

# ---- Part 2 — UC8: view the file contents -----------------------------------
q.message(user, page, "click row report.cs")
q.message(page, hook, "update(vm => vm.select(file))")
q.ret(hook, page)
q.message(page, preview, "file (React prop)")
q.self_message(preview, "createPreview(entry)\n→ TextPreview")
q.message(preview, api, "download(id)")
q.message(api, ctl, "GET /files/:id/content")
q.message(ctl, svc, "getContent(ownerId, id)")
q.message(svc, sto, "getObject(storageKey)")
q.ret(sto, svc, "Readable")
q.ret(svc, ctl, "Readable")
q.ret(ctl, api, "200 text/plain stream")
# note sits right of the (now idle) FilesController, in the gap before FilesService
q.note(ctl, "for .jpg the same call\nreturns image/jpeg and\nPreviewPanel renders\n<img> (ImagePreview)", w=140)
q.ret(api, preview, "Blob")
q.self_message(preview, "setResult({kind: 'text', text})")
q.ret(preview, user, "contents shown in <pre>")

# ---- layout post-processing (library cells only; drawio.py is untouched) -----
q._build()
u = q._p(user)

# 1) The alt frame normally starts 20 px left of the first lifeline, so its "alt" tab and the
#    operand guards are crossed by the User's activation bar. Extend the frame further left and
#    move the guards to the right of that bar.
frame = next(c for c in q.cells if c.vertex and "shape=umlFrame" in c.style)
new_x0 = u.x - 55
frame.w += frame.x - new_x0
frame.x = new_x0
guard_x = u.x + u.w / 2 + 15                    # just right of the User activation bar
for c in q.cells:
    if c.vertex and c.style.startswith("text;html=1;align=left;verticalAlign=middle;fontSize=10"):
        c.x = guard_x
    elif not c.vertex and c.style.startswith("endArrow=none;dashed=1") and c.source_point:
        c.source_point = (new_x0, c.source_point[1])   # else-separator now spans the wider frame

# 2) deactivate() closes an activation at the *next* row, so the User's first bar would overhang
#    the "report.cs appears in FileTable" return by one step. Trim it to end just below that arrow.
user_bars = [c for c in q.cells if c.vertex and c.parent == user and "orthogonalPerimeter" in c.style]
user_bars.sort(key=lambda c: c.y)
bar = user_bars[0]
old_h, bar.h = bar.h, bar.h - (q.step - 6)
# message end points are stored as fractions of the bar height: rescale them so the arrows keep
# their absolute y (otherwise the last return would turn diagonal)
for c in q.cells:
    if c.vertex or bar.id not in (c.source, c.target):
        continue
    key = "exitY" if c.source == bar.id else "entryY"
    c.style = re.sub(rf"{key}=([\d.]+)",
                     lambda m: f"{key}={float(m.group(1)) * old_h / bar.h:.3f}", c.style)

q.save(OUT("09-sequence-upload-preview"))
