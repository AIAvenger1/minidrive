"""02 — Domain class diagram (conceptual model, spec §3.1).

    cd <repo root> && python3 docs/uml/gen/02_class_domain.py

Rank structure (rankdir=TB, Graphviz routes the edges). Node declaration order = left-to-right
order inside a rank (file / access cluster on the left, synchronization cluster on the right):

    R0   User                                              SyncEngine
    R1   Space   Session                    LocalFolder SyncPlan SyncReport   («reads» SyncEngine -> Space)
    R2   FileEntry <- -«use»- - FilePreview - -> PreviewKind   SyncAction - -> SyncActionKind
    R3   FileContent   TextPreview ImagePreview   SortOrder FileFilter

Multiplicities at the "whole" end of a composition are placed at 35 % of the edge so they do not
sit on top of the 22 px diamond; flat (same-rank) edges use draw.io mid-point labels instead of
Graphviz labels, because a labelled flat edge makes dot insert an extra label rank and the edge arcs.
Edge weights keep the two vertical spines (User -> Space -> FileEntry -> FileContent and
SyncEngine -> SyncPlan -> SyncAction) straight.

Colour groups: blue = access/session, green = file list / preview, yellow = file metadata + bytes,
purple = synchronization, grey = enumerations (infrastructure).

This is the analysis-level model: Space, Session, LocalFolder and FileContent are concepts, not
classes of the implementation — the legend lists what each of them became in the code.
"""
from _common import *

d = GraphDiagram("Domain class diagram", routing=ORTHO)

# ---------------------------------------------------------------------------
# R0 — account (blue) and sync engine (purple)
# ---------------------------------------------------------------------------
user = d.klass(
    "User",
    attrs=["- id: string", "- username: string", "- passwordHash: string", "- createdAt: Date"],
    methods=["+ register(username: string, password: string): User",
             "+ authenticate(username: string, password: string): Session"],
    color=ACCESS,
)
engine = d.klass(
    "SyncEngine",
    attrs=["- localFolder: LocalFolder"],
    methods=["+ scan(dir): LocalFileInfo[]", "+ synchronize(dir): SyncReport"],
    color=SYNC,
)

# ---------------------------------------------------------------------------
# R1 — virtual disk (green), session (blue), sync parts (purple)
# ---------------------------------------------------------------------------
space = d.klass(
    "Space",
    stereotype="virtual disk",
    attrs=["- id: string", "- owner: User", "- files: FileEntry[]"],
    methods=["+ getFiles(): FileEntry[]", "+ addFile(f: FileEntry): void", "+ removeFile(id: string): void"],
    color=LIST,
)
session = d.klass(
    "Session",
    attrs=["- token: string", "- user: User", "- expiresAt: Date"],
    methods=["+ isValid(): boolean", "+ revoke(): void"],
    color=ACCESS,
)
folder = d.klass(
    "LocalFolder",
    attrs=["- path: string", "- boundAt: Date"],
    methods=["+ listFiles(): LocalFileInfo[]", "+ isBound(): boolean"],
    color=SYNC,
)
plan = d.klass(
    "SyncPlan",
    attrs=["- uploads: SyncAction[]", "- downloads: SyncAction[]", "- skipped: SyncAction[]"],
    color=SYNC,
)
report = d.klass(
    "SyncReport",
    attrs=["- uploaded: number", "- downloaded: number", "- skipped: number",
           "- failed: number", "- errors: string[]"],
    color=SYNC,
)

# ---------------------------------------------------------------------------
# R2 — file metadata (yellow), abstract preview (green), sync action (purple), enumerations (grey)
# ---------------------------------------------------------------------------
entry = d.klass(
    "FileEntry",
    attrs=["- id: string", "- name: string", "- extension: string", "- size: number",
           "- createdAt: Date", "- updatedAt: Date", "- uploadedBy: User", "- modifiedBy: User",
           "- storageKey: string"],
    methods=["+ isNewerThan(other: FileEntry): boolean"],
    color=OPS,
)
preview = d.klass(
    "FilePreview",
    stereotype="abstract",
    italic_name=True,
    attrs=["# entry: FileEntry"],
    methods=["+ canRender(ext: string): boolean", "+ render(): PreviewResult"],
    color=LIST,
)
preview_kind = d.enum("PreviewKind", ["text", "image", "none"], color=INFRA)
action = d.klass(
    "SyncAction",
    attrs=["- kind: SyncActionKind", "- name: string", "- reason: string"],
    color=SYNC,
)
action_kind = d.enum("SyncActionKind", ["upload", "download", "skip"], color=INFRA)

# ---------------------------------------------------------------------------
# R3 — file bytes (yellow), concrete previews (green), remaining enumerations (grey)
# ---------------------------------------------------------------------------
content = d.klass(
    "FileContent",
    attrs=["- storageKey: string", "- mimeType: string", "- bytes: Buffer"],
    methods=["+ getStream(): ReadableStream"],
    color=OPS,
)
text_preview = d.klass(
    "TextPreview",
    stereotype=".cs, text",
    attrs=["- encoding: string"],
    methods=["+ canRender(ext: string): boolean", "+ render(): PreviewResult"],
    color=LIST,
)
image_preview = d.klass(
    "ImagePreview",
    stereotype=".jpg, image",
    attrs=["- width: number", "- height: number"],
    methods=["+ canRender(ext: string): boolean", "+ render(): PreviewResult"],
    color=LIST,
)
sort_order = d.enum("SortOrder", ["asc", "desc"], color=INFRA)
file_filter = d.enum("FileFilter", ["all", "cpp", "png"], color=INFRA)


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------
def comp(whole, part, mult_whole, mult_part, **kw):
    """Composition whose whole-end multiplicity is placed clear of the diamond (-0.3 = 35 % along)."""
    return d.edge(whole, part, E_COMPOSITION, labels=[(mult_whole, -0.3), (mult_part, 0.8)], **kw)


# account / virtual disk (out-edges of User are ordered left -> right as declared: Space, FileEntry, Session)
comp(user, space, "1", "1", weight=3)
# many entries reference one user as uploader / last editor (drawn upwards; dot ranks User first)
d.assoc(entry, user, "uploadedBy / modifiedBy", mult_a="0..*", mult_b="1", dot_reverse=True)
d.assoc(user, session, mult_a="1", mult_b="0..*")
comp(space, entry, "1", "0..*", weight=3)
comp(entry, content, "1", "1", weight=3)

# preview hierarchy (flat edges on R2: FileEntry <- FilePreview -> PreviewKind)
d.edge(preview, entry, E_DEPENDENCY, labels=[("«use»", 0)], dot_reverse=True)
d.dependency(preview, preview_kind)
d.generalization(text_preview, preview)
d.generalization(image_preview, preview)

# synchronization (SyncEngine -> SyncPlan -> SyncAction is a weighted vertical spine)
d.dependency(engine, space, "«reads»")
comp(engine, folder, "1", "1")
d.edge(engine, plan, E_DEPENDENCY, "«creates»", weight=4)   # the plan is a local variable of synchronize()
d.dependency(engine, report, "«creates»")
comp(plan, action, "1", "0..*", weight=6)
d.dependency(action, action_kind)

# ---------------------------------------------------------------------------
# Ranks
# ---------------------------------------------------------------------------
d.same_rank(user, engine)
d.same_rank(space, session, folder, plan, report)
d.same_rank(entry, preview, preview_kind, action, action_kind)
d.same_rank(content, text_preview, image_preview, sort_order, file_filter)

d.legend(
    "Notation\n"
    "◆──  composition: the whole owns its parts (User ◆── Space, Space ◆── FileEntry, ...)\n"
    "◇──  aggregation: shared part, independent lifetime (not used in the domain model)\n"
    "──▷  generalization: TextPreview / ImagePreview are kinds of FilePreview\n"
    "───  association with multiplicities (1, 0..1, 0..*) and role names\n"
    "- - ▷  dependency: «use», «reads», «creates» — the source needs the target\n"
    "\n"
    "Conceptual classes without a direct counterpart in the implementation:  Space (ownership is the\n"
    "FileEntry.ownerId column),  Session (the session is a stateless JWT, so no row is stored),\n"
    "LocalFolder (the bound folder is a path in the desktop settings),  FileContent (an object in MinIO\n"
    "reached through StorageService) and FileEntry.isNewerThan() (inlined in computeSyncPlan).\n"
    "User.register() / User.authenticate() are realised by AuthService and UsersService.\n"
    "Enumerations carry the literal values of the TypeScript union types (packages/shared/src/types.ts).",
    w=700,
)

d.layout(rankdir="TB", nodesep=0.55, ranksep=1.0)
d.save(OUT("02-class-domain"))
