"""08 — Sequence diagram: Sign up (UC1) and Log in (UC2).

Participants follow §3.2 / §3.4 of the design spec verbatim:
LoginPage (web page /login), ApiClient (fetch wrapper), AuthController, AuthService,
UsersService, PrismaService.  Server-side participants are grey (infrastructure group).
"""
from _common import *  # noqa: F401,F403

q = SequenceDiagram("Sequence diagram — Sign up and log in (UC1, UC2)", spacing=175, step=38)

# ---- participants ----------------------------------------------------------
u = q.participant("User", "actor")
page = q.participant("LoginPage", "boundary")
api = q.participant("ApiClient", "control")
ctl = q.participant("AuthController", "participant", INFRA)
auth = q.participant("AuthService", "participant", INFRA)
users = q.participant("UsersService", "participant", INFRA)
prisma = q.participant("PrismaService", "participant", INFRA)

# ---- Part 1: sign up (UC1) -------------------------------------------------
q.fragment("opt", "[new user]")
q.gap(2)                       # keep the guard clear of the first two-line message label
q.message(u, page, "enter username, password;\nclick Sign up")
q.message(page, api, "register(username, password)")
q.message(api, ctl, "POST /auth/register")
q.message(ctl, auth, "register(dto)")
q.message(auth, users, "findByUsername(username)")
q.message(users, prisma, "user.findUnique()")
q.ret(prisma, users, "null | User")
q.ret(users, auth)

q.fragment("alt", "[username taken]")
q.gap(1)
q.ret(auth, ctl, "409 ConflictException")
q.fragment_else("[else]")
q.gap(1)                       # two-line label must clear the separator
q.activate(auth)
q.message(auth, users, "create(username,\nhash(password))")
q.message(users, prisma, "user.create()")
q.ret(prisma, users, "User")
q.ret(users, auth)
q.self_message(auth, "signJwt(user)")
q.ret(auth, ctl, "AuthResponseDto")
q.end_fragment()
q.gap(1)                       # keep the next label off the alt frame border

q.ret(ctl, api, "201 AuthResponseDto")
q.ret(api, page)
q.ret(page, u, "account created")   # closes the LoginPage activation before UC2 starts
q.end_fragment()
q.deactivate(u)
q.gap(2)

# ---- Part 2: log in (UC2) --------------------------------------------------
q.message(u, page, "enter credentials;\nclick Log in")
q.message(page, api, "login(username, password)")
q.message(api, ctl, "POST /auth/login")
q.message(ctl, auth, "validateUser(username,\npassword)")
q.message(auth, users, "findByUsername(username)")
q.message(users, prisma, "user.findUnique()")
q.ret(prisma, users, "User | null")
q.ret(users, auth, "user")
q.message(auth, users, "verify(password,\npasswordHash)")
q.ret(users, auth, "boolean")

q.fragment("alt", "[valid]")
q.self_message(auth, "signJwt(user)")
q.ret(auth, ctl, "AuthResponseDto\n{accessToken, user}")
q.ret(ctl, api, "200 AuthResponseDto")
q.self_message(api, "SessionStore.set(token)")
q.note(api, "JWT HS256, 24 h,\nsent as\nAuthorization: Bearer", w=140)
q.ret(api, page, "session")
q.ret(page, u, "navigate to /drive (cabinet)")
q.fragment_else("[invalid]")
q.gap(1)
q.activate(auth)
q.activate(ctl)
q.activate(api)
q.activate(page)
q.ret(auth, ctl, "UnauthorizedException")
q.ret(ctl, api, "401")
q.ret(api, page, "error")
q.ret(page, u, "show «Invalid credentials»")
q.deactivate(u)
q.end_fragment()

# ---- layout workaround (cell geometry / style only, drawio.py untouched) ---
# 1. The library draws fragment frames only 20 px left of the first lifeline, so the
#    "opt"/"alt" tabs and guard texts land on the User lifeline: widen every frame to the
#    left and move the guard labels just right of the User activation bar.
# 2. The library insets frames by their *index* (not nesting depth), so the second,
#    top-level "alt" would look nested: recompute the inset from y-range containment.
# 3. The "else" separator lines must follow the frame they belong to.
# 4. Lifeline heads of actor/boundary/control kind draw the dashed line through their
#    name: give those labels a white background.
q._build()
SHIFT = 60                                    # extra frame width on the left
GUARD_X = q.left + q.spacing / 2 + 12         # right of the User activation bar
X0 = min(p.x for p in q._parts) - 20          # library's frame extent
X1 = max(p.x + p.w for p in q._parts) + 20
frames = [c for c in q.cells if c.vertex and "shape=umlFrame" in c.style]


def nesting(f):
    return sum(1 for g in frames if g is not f and g.y <= f.y and f.y + f.h <= g.y + g.h)


current = None
for c in q.cells:
    if c.vertex and "shape=umlFrame" in c.style:
        depth = nesting(c)
        c.x = X0 - SHIFT + 10 * depth
        c.w = (X1 - X0) + SHIFT - 20 * depth
        current = c
    elif c.vertex and c.style.startswith("text;html=1;align=left;verticalAlign=middle;fontSize=10;"):
        c.x = GUARD_X                         # fragment guard / else-guard text
    elif (not c.vertex and c.source is None and c.target is None and c.source_point
          and "endArrow=none" in c.style and current is not None):
        c.source_point = (current.x, c.source_point[1])            # "else" separator
        c.target_point = (current.x + current.w, c.target_point[1])
    elif c.vertex and "shape=umlLifeline" in c.style and "participant=uml" in c.style:
        c.style += "labelBackgroundColor=#ffffff;"

q.save(OUT("08-sequence-login"))
