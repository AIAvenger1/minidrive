"""04 — Class diagram: API server (NestJS) — modules, controllers, services, entities, DTOs.

Source of truth: docs/superpowers/specs/2026-09-07-minidrive-design.md §3.2.

Layout: Graphviz TB with one package (cluster) per Nest module plus "DTOs" and
"Entities (Prisma models)".  Rows follow the call chain
controller -> service -> infrastructure service (Users / Storage / Prisma); the
DTOs hang under the controllers that use them, the entities sit next to FilesService.
Edges are routed by Graphviz around the boxes; the «guard» edge is a flat
(constraint=False) edge so that JwtAuthGuard stays on the controller row.
"""
from _common import *

d = GraphDiagram("Class diagram — API server (NestJS)", routing=ORTHO)

USES = "«uses»"

# ---------------------------------------------------------------------------
# Packages — declaration order is the preferred left-to-right order
# ---------------------------------------------------------------------------
g_auth = d.group("AuthModule", color=INFRA)
g_users = d.group("UsersModule", color=INFRA)
g_dtos = d.group("DTOs", color=INFRA)
g_files = d.group("FilesModule", color=INFRA)
g_prisma = d.group("PrismaModule", color=INFRA)
g_storage = d.group("StorageModule", color=INFRA)
g_entities = d.group("Entities (Prisma models)", color=INFRA)

# ---------------------------------------------------------------------------
# AuthModule
# ---------------------------------------------------------------------------
auth_ctl = d.klass(
    "AuthController",
    methods=[
        "+ register(dto: RegisterDto): AuthResponseDto",
        "+ login(dto: LoginDto): AuthResponseDto",
        "+ me(user: UserDto): UserDto",
    ],
    color=INFRA, group=g_auth,
)
jwt_guard = d.klass("JwtAuthGuard", color=INFRA, group=g_auth)
auth_svc = d.klass(
    "AuthService",
    attrs=["- jwt: JwtService"],
    methods=[
        "+ register(dto): AuthResponseDto",
        "+ validateUser(username, password): User",
        "+ login(user: User): AuthResponseDto",
    ],
    color=INFRA, group=g_auth,
)
jwt_strategy = d.klass("JwtStrategy", methods=["+ validate(payload): UserDto"], color=INFRA, group=g_auth)

# ---------------------------------------------------------------------------
# UsersModule
# ---------------------------------------------------------------------------
users_svc = d.klass(
    "UsersService",
    methods=[
        "+ findByUsername(username): User",
        "+ create(username, passwordHash): User",
        "+ hash(password): string",
        "+ verify(password, hash): boolean",
    ],
    color=INFRA, group=g_users,
)

# ---------------------------------------------------------------------------
# DTOs (white)
# ---------------------------------------------------------------------------
register_dto = d.klass("RegisterDto", attrs=["+ username: string", "+ password: string"],
                       color="white", group=g_dtos)
login_dto = d.klass("LoginDto", attrs=["+ username: string", "+ password: string"],
                    color="white", group=g_dtos)
auth_resp_dto = d.klass("AuthResponseDto", attrs=["+ accessToken: string", "+ user: UserDto"],
                        color="white", group=g_dtos)
user_dto = d.klass("UserDto", attrs=["+ id: string", "+ username: string"], color="white", group=g_dtos)
file_dto = d.klass(
    "FileDto",
    attrs=[
        "+ id: string",
        "+ name: string",
        "+ extension: string",
        "+ size: number",
        "+ createdAt: Date",
        "+ updatedAt: Date",
        "+ uploadedBy: string",
        "+ modifiedBy: string",
    ],
    color="white", group=g_dtos,
)

# ---------------------------------------------------------------------------
# FilesModule
# ---------------------------------------------------------------------------
files_ctl = d.klass(
    "FilesController",
    methods=[
        "+ list(user): FileDto[]",
        "+ upload(user, file: Multipart): FileDto",
        "+ download(user, id): StreamableFile",
        "+ remove(user, id): void",
    ],
    color=INFRA, group=g_files,
)
files_svc = d.klass(
    "FilesService",
    methods=[
        "+ listFor(ownerId): FileDto[]",
        "+ upsert(owner: User, file): FileDto",
        "+ getContent(ownerId, id): Readable",
        "+ delete(ownerId, id): void",
        "- toDto(entry: FileEntry): FileDto",
    ],
    color=INFRA, group=g_files,
)

# ---------------------------------------------------------------------------
# PrismaModule / StorageModule
# ---------------------------------------------------------------------------
prisma_svc = d.klass(
    "PrismaService",
    stereotype="extends PrismaClient",
    attrs=["+ user", "+ fileEntry"],
    methods=["+ onModuleInit(): void"],
    color=INFRA, group=g_prisma,
)
storage_svc = d.klass(
    "StorageService",
    attrs=["- s3: S3Client", "- bucket: string"],
    methods=[
        "+ putObject(key, body, mimeType): void",
        "+ getObject(key): Readable",
        "+ deleteObject(key): void",
    ],
    color=INFRA, group=g_storage,
)

# ---------------------------------------------------------------------------
# Entities (Prisma models) — yellow
# ---------------------------------------------------------------------------
user_ent = d.klass(
    "User",
    attrs=["+ id: string", "+ username: string", "+ passwordHash: string", "+ createdAt: Date"],
    color=OPS, group=g_entities,
)
file_entry = d.klass(
    "FileEntry",
    attrs=[
        "+ id: string",
        "+ ownerId: string",
        "+ name: string",
        "+ extension: string",
        "+ size: number",
        "+ storageKey: string",
        "+ createdAt: Date",
        "+ updatedAt: Date",
        "+ uploadedById: string",
        "+ modifiedById: string",
    ],
    color=OPS, group=g_entities,
)

# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------
# Auth call chain (weighted so it stays a straight column inside AuthModule)
d.dependency(auth_ctl, auth_svc, weight=6)
d.dependency(auth_svc, jwt_strategy, "«configures»", weight=6)
d.dependency(auth_svc, users_svc)
# DTO usage
d.dependency(auth_ctl, register_dto, USES)
d.dependency(auth_ctl, login_dto, USES)
d.dependency(auth_ctl, auth_resp_dto, USES)
# AuthResponseDto.user: UserDto — flat edge so all DTOs share one row (the edge is short, so
# no multiplicity label: "1" would sit on the arrowhead)
d.directed(auth_resp_dto, user_dto, "user", constraint=False)
d.dependency(files_ctl, file_dto, USES)
# Files call chain
d.dependency(files_ctl, files_svc, weight=6)
# JwtAuthGuard protects /files: flat edge so the guard stays on the controller row
d.dependency(files_ctl, jwt_guard, "«guard»", constraint=False)
d.dependency(files_svc, storage_svc)
d.dependency(files_svc, prisma_svc)
# flat edge: UsersService and PrismaService share the infrastructure row
d.dependency(users_svc, prisma_svc, constraint=False)
d.dependency(files_svc, file_entry, "«maps»")
# Entity association: one User owns many FileEntry rows
d.assoc(user_ent, file_entry, "owner", mult_a="1", mult_b="0..*", weight=6)

# ranksep is generous so the AuthController -> DTO edges descend steeply instead of
# hugging the top border of the DTOs package
d.layout(rankdir="TB", nodesep=0.5, ranksep=1.2)


# ---------------------------------------------------------------------------
# Post-layout label tweak: Graphviz centres «maps» exactly where the edge crosses the
# Entities package border; slide it towards FilesService (rel -1..1 along the edge).
# ---------------------------------------------------------------------------
def move_label(a, b, rel, dx=0.0, dy=0.0):
    c = next(c for c in d.cells if not c.vertex and c.source == a and c.target == b)
    c.offset = (rel, 0.0)
    c.abs_offset = (dx, dy)


move_label(files_svc, file_entry, -0.45, 0, -10)
# the first «uses» label lands on the AuthModule border: slide it onto the diagonal that
# enters the DTOs package (right-hand side of the line)
# (the long first segment dominates the polyline length, so rel 0.7 is ~2/3 down the diagonal)
move_label(auth_ctl, register_dto, 0.7, 26, 0)

d.save(OUT("04-class-server"))
