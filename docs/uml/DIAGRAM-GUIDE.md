# Reproducing the UML diagram pipeline in another project

This is a hand-over guide for a student who wants the same diagram workflow in their own course
project. Everything here was checked against the code in this repository: the library lives in
`tools/drawio_gen/drawio.py`, the generators in `docs/uml/gen/`, the outputs in
`docs/uml/drawio/` (editable sources) and `docs/uml/img/` (PNG + SVG).

Paths are written relative to the repository root; `<repo>` means the root of *your* repository.

---

## 1. What you get and why

Each diagram is a short Python script. Running it produces three files:

| file | what it is |
|---|---|
| `docs/uml/drawio/NN-name.drawio` | a **native, editable draw.io document** — open it in draw.io / diagrams.net and every box is a real UML shape you can drag |
| `docs/uml/img/NN-name.png` | PNG exported at scale 2 (retina), for the report |
| `docs/uml/img/NN-name.svg` | SVG export, for slides or the web |

Why generate instead of drawing:

1. **The diagram is a diff.** Renaming a class is a one-line edit and a re-run, not twenty minutes
   of dragging. When the code changes, the diagram changes with it.
2. **Layout is not your problem.** `GraphDiagram` hands the node/edge graph to Graphviz `dot`,
   reads the coordinates and edge polylines back, and writes them into the `.drawio` file. Boxes do
   not overlap and edges route around them.
3. **You still keep an editable file.** The `.drawio` is not a picture — the lecturer can open it,
   and you can hand-fix one label if you ever need to (see §6).
4. **The report is reproducible.** `tools/build-report.sh` runs pandoc over a Markdown report that
   embeds the PNGs; regenerate the diagrams, rebuild the report, and the DOCX/PDF is current.

The library has **no third-party Python dependencies** — it imports only
`html, json, os, shutil, subprocess, sys, xml.etree.ElementTree, dataclasses, typing`. The two
external tools are Graphviz (`dot`) and the draw.io desktop CLI.

---

## 2. Prerequisites

### macOS (Homebrew) — this is the setup this repo was built on

```bash
brew install python3 graphviz
brew install --cask drawio
```

Check:

```bash
python3 -V          # 3.9+ is enough (3.14 here)
dot -V              # graphviz version ...
ls /Applications/draw.io.app/Contents/MacOS/draw.io    # the CLI binary the library calls
```

The cask also installs a `drawio` wrapper on `PATH` (`/opt/homebrew/bin/drawio` on Apple Silicon,
`/usr/local/bin/drawio` on Intel).

**No `pip install` is needed.** Nothing in `drawio.py` imports a third-party package.

### Where the library looks for the draw.io binary

`tools/drawio_gen/drawio.py` starts with:

```python
DRAWIO_BIN = os.environ.get("DRAWIO_BIN", "/Applications/draw.io.app/Contents/MacOS/draw.io")
```

So the default path is the macOS app bundle, and you override it with an environment variable:

```bash
DRAWIO_BIN=/opt/homebrew/bin/drawio python3 docs/uml/gen/01_use_case.py
```

If the binary is missing the script still writes the `.drawio` file and prints
`[drawio] CLI not found at ...; wrote ... only` — it does not crash. That is the fast path while
you iterate on the graph structure.

### Linux

```bash
sudo apt install python3 graphviz          # or: dnf install python3 graphviz
# draw.io desktop: download the .deb / .rpm / AppImage from
#   https://github.com/jgraph/drawio-desktop/releases
sudo apt install ./drawio-amd64-*.deb
export DRAWIO_BIN=$(command -v drawio)
```

draw.io desktop is an Electron app and wants a display. On a headless box wrap the run:

```bash
xvfb-run -a python3 docs/uml/gen/01_use_case.py
```

### Windows

```powershell
winget install Python.Python.3
winget install Graphviz.Graphviz
winget install JGraph.Draw
$env:DRAWIO_BIN = "C:\Program Files\draw.io\draw.io.exe"
```

Make sure the Graphviz `bin` folder is on `PATH` (the installer offers a checkbox for it), because
the library calls `shutil.which("dot")` and raises `Graphviz 'dot' not found on PATH` otherwise.

---

## 3. Copying the tooling into your repository

### 3.1 What to copy

| from this repo | to `<repo>` | change it? |
|---|---|---|
| `tools/drawio_gen/drawio.py` | `tools/drawio_gen/drawio.py` | **no** — treat it as a vendored library |
| `tools/drawio_gen/README.md` | `tools/drawio_gen/README.md` | no (it is the API cheat-sheet) |
| `docs/uml/gen/_common.py` | `docs/uml/gen/_common.py` | **yes** — the colour aliases (see below) |
| any `docs/uml/gen/NN_*.py` | `docs/uml/gen/` | yes — they are your starting templates |
| `tools/build-report.sh` | `tools/build-report.sh` | only if you also want the pandoc report |

Do **not** copy `docs/uml/drawio/` or `docs/uml/img/` — those are generated.

### 3.2 Expected folder layout

```
<repo>/
├── tools/
│   ├── drawio_gen/
│   │   ├── drawio.py          # the library (do not edit from a generator)
│   │   └── README.md          # API cheat-sheet
│   └── build-report.sh        # optional: pandoc DOCX/PDF
└── docs/
    └── uml/
        ├── gen/               # one Python script per diagram
        │   ├── _common.py
        │   ├── 01_use_case.py
        │   └── ...
        ├── drawio/            # generated .drawio (commit these)
        └── img/               # generated .png / .svg (commit these)
```

The layout is **load-bearing**: `_common.py` computes the repository root as three levels up from
itself (`docs/uml/gen/../../..`) and then hard-codes `tools/drawio_gen`, `docs/uml/drawio` and
`docs/uml/img`. Keep the same depth, or edit those three joins.

### 3.3 What to change in `_common.py`

The whole file is 29 lines. The parts you touch:

```python
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "drawio_gen"))

from drawio import *
from drawio import COLORS, ORTHO, STRAIGHT, GraphDiagram, ActivityDiagram, SequenceDiagram

DRAWIO_DIR = os.path.join(ROOT, "docs", "uml", "drawio")
IMG_DIR = os.path.join(ROOT, "docs", "uml", "img")

# Semantic colour groups — rename these for YOUR subject area
ACCESS, LIST, OPS, SYNC, INFRA = "blue", "green", "yellow", "purple", "grey"


def OUT(name: str) -> str:
    return os.path.join(DRAWIO_DIR, name + ".drawio")
```

`ACCESS / LIST / OPS / SYNC / INFRA` are this project's semantic groups (access & session, file
list, file operations, synchronization, infrastructure). Replace them with names that fit your
system — e.g. `AUTH, CATALOG, ORDERS, PAYMENT, INFRA` — and keep using the aliases instead of raw
colour strings, so a colour change is a one-line edit in `_common.py`.

`from _common import *` re-exports exactly what `drawio.py` declares in `__all__`:

```
Diagram, GraphDiagram, ActivityDiagram, SequenceDiagram, COLORS, ORTHO, STRAIGHT, export,
E_ASSOC, E_DIRECTED, E_INCLUDE, E_EXTEND, E_GENERALIZATION, E_REALIZATION,
E_COMPOSITION, E_AGGREGATION, E_DEPENDENCY, E_NOTE, E_FLOW
```

plus `OUT`, `DRAWIO_DIR`, `IMG_DIR` and your colour aliases from `_common.py`. The `E_*` constants
are draw.io style strings you concatenate when you need a variant of a standard edge (see §5.3).

The nine colour names accepted by every `color=` argument are fixed in `drawio.py`:
`blue, green, yellow, purple, orange, red, grey, white, none`. Each is a (fill, stroke) pair from
the draw.io default palette; `none` is transparent.

### 3.4 Naming convention

Script `docs/uml/gen/NN_snake_name.py` writes `NN-kebab-name.drawio` / `.png` / `.svg`. Keep the
two-digit prefix: it fixes the order the diagrams appear in the report and makes `ls` readable.

---

## 4. Anatomy of a generator script (minimal working example)

Every generator has the same five parts:

1. a module docstring saying what the diagram shows and why the layout is what it is;
2. `from _common import *`;
3. a diagram object (`GraphDiagram`, `ActivityDiagram` or `SequenceDiagram`);
4. nodes, then edges, then notes/legend — **declaration order matters**, it seeds Graphviz's
   ordering inside a rank;
5. `layout(...)` and `save(OUT("NN-name"))`.

### 4.1 The script

Save as `docs/uml/gen/00_demo_class.py`:

```python
"""00 — Minimal class diagram: three classes, one generalization, one association, one note."""
from _common import *

d = GraphDiagram("Demo class diagram", routing=ORTHO)

account = d.klass(
    "Account",
    attrs=["- id: string", "- email: string"],
    methods=["+ rename(name: string): void"],
    color=ACCESS,
)
admin = d.klass(
    "AdminAccount",
    attrs=["- scopes: string[]"],
    methods=["+ grant(scope: string): void"],
    color=ACCESS,
)
order = d.klass(
    "Order",
    attrs=["- id: string", "- total: number"],
    methods=["+ submit(): void"],
    color=OPS,
)

d.generalization(admin, account)
d.assoc(account, order, "places", mult_a="1", mult_b="0..*")

n = d.note("An AdminAccount may place orders\non behalf of another account.")
d.note_link(n, order, place="right")

d.same_rank(admin, order)
d.layout(rankdir="TB", nodesep=0.6, ranksep=0.9)
d.save(OUT("00-demo-class"))
```

### 4.2 The command

From the repository root:

```bash
python3 docs/uml/gen/00_demo_class.py
```

Output (verified):

```
[drawio] wrote <repo>/docs/uml/drawio/00-demo-class.drawio
```

and three files:

```
docs/uml/drawio/00-demo-class.drawio
docs/uml/img/00-demo-class.png      # 2x PNG
docs/uml/img/00-demo-class.svg
```

The rendered picture: `Account` on top; `AdminAccount` below it joined by a hollow-triangle
generalization; `Order` beside `AdminAccount`, joined to `Account` by a plain association labelled
`places` with `1` at the `Account` end and `0..*` at the `Order` end; the note attached to `Order`
by a dashed line on its right.

### 4.3 Reading the example

* `klass(name, attrs=[...], methods=[...], stereotype=None, color=..., min_w=170, italic_name=False)`
  — write attributes and operations as plain UML strings (`"- id: string"`,
  `"+ submit(): void"`). `min_w` widens narrow boxes so a column lines up.
* `generalization(child, parent)` — note the argument order (child first); the library ranks the
  **parent above the child** automatically.
* `assoc(a, b, label, mult_a, mult_b)` — `mult_a` is drawn near `a`, `mult_b` near `b`.
* `note(text, color="yellow", w=None)` + `note_link(note, target, place=...)`. `place="auto"` lets
  Graphviz hang the note off the target as a leaf (never overlaps, but consumes a rank);
  `above/below/left/right` pins it next to the target after layout, trying the other three spots if
  the first one collides.
* `same_rank(a, b, ...)` forces nodes onto one Graphviz rank — same row with `rankdir="TB"`, same
  column with `rankdir="LR"`.
* `save()` calls `layout()` for you if you forgot; calling it explicitly is how you pass
  `rankdir/nodesep/ranksep`.

---

## 5. One section per diagram type

Common vocabulary used below:

* `routing=ORTHO` — right-angle edges (class, component, deployment diagrams).
* `routing=STRAIGHT` — straight lines (use case, state, communication diagrams).
* `layout(rankdir, nodesep, ranksep, margin=20, ordering="out", extra_graph_attrs="", route_edges=True, splines="polyline")`
  — `nodesep` is the gap *within* a rank, `ranksep` the gap *between* ranks, both in Graphviz
  inches. With `route_edges=True` (default) the drawn edges follow Graphviz's node-avoiding
  polylines and each label sits where Graphviz reserved room for it.
* `legend(text, w=420)` — a boxed text block placed under the bottom-left corner of the content.
* `edge(a, b, style, label, constraint, minlen, weight, dot_reverse, label_offset=(rel, px), bend=px)`
  — the low-level escape hatch; the named helpers all funnel into it.
* `dot_reverse=True` — tells Graphviz to rank the *target* before the source without flipping the
  drawn arrowhead. This is how "arrows that point up the tree" keep the tree flowing root → leaves.

### 5.1 Use case diagram — template `01_use_case.py`

Calls: `GraphDiagram(..., routing=STRAIGHT)`, `actor`, `usecase(text, color, w=None, h=60)`,
`assoc`, `include(base, included)`, `extend(extension, base)`, `note` + `note_link`, `same_rank`,
`layout(rankdir="LR", ...)`.

Conventions the lecturer accepted here:

* **Cascade style, no system-boundary box.** The actor sits on the far left; a handful of *root*
  use cases form column 1; everything else hangs off them as an include/extend tree flowing left to
  right.
* Actor → root use cases are plain `assoc` lines. Refinements are `«include»` / `«extend»`.
* **Parameter leaves on solid association lines** — the concrete choices of a use case (Ascending /
  Descending, All files / Only .cpp / Only .png) are narrow ellipses joined with `assoc`, not with
  `«extend»`.
* All text in English; colours carry the semantic group.

Pattern:

```python
d = GraphDiagram("Use case diagram", routing=STRAIGHT)
user = d.actor("User")
login = d.usecase("Log in to the system", ACCESS)
root  = d.usecase("Work with the\nfile storage", ACCESS)
d.assoc(user, login)
d.assoc(user, root)
d.same_rank(login, root, signup, logout)          # column 1
d.include(root, login, dot_reverse=True)
d.extend(sort, view)                              # arrow: extension -> base
LEAF_W = 130
asc = d.usecase("Ascending", LIST, w=LEAF_W)
d.assoc(sort, asc)                                # parameter leaf, solid line
d.note_link(n_login, login, place="above")
d.layout(rankdir="LR", nodesep=0.3, ranksep=0.9)
```

Layout knobs: `same_rank` to keep the root column together; `w=` on leaf ellipses so the last column
stays narrow; `nodesep` around 0.3 (many short ellipses); `place="above"/"below"` for notes that
would otherwise land in the middle of a column and bend the edges around them.

### 5.2 Domain class diagram — template `02_class_domain.py`

Calls: `klass`, `enum(name, values, color)`, `composition(whole, part, mult_whole, mult_part)`,
`aggregation(...)`, `generalization`, `assoc`, `dependency(a, b, label)`, `same_rank`, `legend`,
`layout(rankdir="TB", ...)`.

Conventions: conceptual classes only (things in the problem domain, not implementation classes);
`stereotype=` for concepts that need one; a `legend()` that explains the notation **and** lists
which conceptual classes have no direct counterpart in the code.

```python
d = GraphDiagram("Domain class diagram", routing=ORTHO)
user = d.klass("User", attrs=[...], methods=[...], color=ACCESS)
space = d.klass("Space", stereotype="virtual disk", attrs=[...], color=LIST)
comp(user, space, "1", "1")            # composition, multiplicities at both ends
d.dependency(action, action_kind)      # dashed «use»
d.same_rank(space, session, folder, plan, report)
d.legend("Notation\n◆──  composition ...", w=700)
d.layout(rankdir="TB", nodesep=0.55, ranksep=1.0)
```

Layout knobs: one `same_rank(...)` per row (`R0…R3`) is the whole layout strategy; `weight=` on the
edges of a vertical spine keeps that chain straight; put a multiplicity at ~0.35 of the edge
(`labels=[("1", -0.7)]` via `edge`) when it collides with the 22 px composition diamond; a labelled
*flat* (same-rank) edge makes `dot` insert an extra rank and arc the line — drop the Graphviz label
and let draw.io centre it instead.

### 5.3 VOPC (View Of Participating Classes) — template `03_class_vopc_sort_filter.py`

This is the one the assignment requires for *your* variant use case.

Calls: `klass(..., stereotype="boundary"|"control"|"entity"|"utility")`, `enum`, `actor`, `assoc`,
`edge(..., E_DIRECTED + ports(...))`, `edge(..., E_DEPENDENCY + ports(...))`, `note_link`,
`legend`, `same_rank`, `layout(rankdir="LR", ...)`.

Conventions: RUP stereotypes in guillemets, coloured by role — `«boundary»` blue, `«control»` /
`«utility»` yellow, `«entity»` / `«enumeration»` green — plus a `legend()` that spells the colour
code out. The actor is on the left, then boundary → control → entity columns.

The local helper that makes VOPCs readable is worth copying verbatim:

```python
def ports(ex, ey, nx, ny) -> str:
    """draw.io style fragment pinning the exit (source) and entry (target) ports of an edge."""
    return f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;"

d.assoc(user, workspace, routing=STRAIGHT)                     # fan from the actor
d.edge(sort_ctl, vm, E_DIRECTED + ports(1, 0.5, 0, 0.2), label="setOrder")
d.edge(vm, file_table, E_DIRECTED + ports(0, 0.85, 1, 0.5), label="renders", dot_reverse=True)
d.edge(vm, utils, E_DEPENDENCY + ports(1, 0.5, 0, 0.5), label="«use»")
d.same_rank(workspace, sort_ctl, filter_ctl, file_table)       # boundary column
d.layout(rankdir="LR", nodesep=0.55, ranksep=1.0)
```

Layout knobs: **pinned ports** are the fix for arrows that all converge on one point — give each
incoming edge a different `entryY` (0.2 / 0.5 / 0.85). Use `routing=STRAIGHT` on the actor fan,
otherwise orthogonal routing buses all four lines through one neighbour. `dot_reverse=True` on an
edge that must be drawn back toward an earlier column.

### 5.4 Implementation class diagrams (server / clients) — templates `04_class_server.py`, `05_class_clients.py`

Calls: `group(label, color, parent=None, pad=20, title_h=30)` for packages/modules, `klass`,
`interface(name, methods)`, `enum`, `generalization`, `realization(impl, iface)`, `composition`,
`dependency`, `legend`, `layout`.

Conventions: one `group()` per package/module (NestJS module, workspace package); rows follow the
call chain (controller → service → infrastructure service); DTOs and entities get their own groups.

Two things worth stealing:

* **Edges may start or end at a group id.** `d.dependency(web_pkg, shared_pkg, "«import»")` draws
  *one* arrow from the whole container instead of eight parallel arrows out of every class inside it.
* Same-rank inside a cluster does not work — Graphviz ejects cluster members from a root-level
  `rank=same`. Use `minlen=0` on the intra-package edges instead so `dot` treats them as flat edges
  and keeps the package in one column:

```python
FLAT = dict(minlen=0, weight=4)
DOWN = dict(dot_reverse=True, **FLAT)
d.dependency(auth_mod, users_mod, **DOWN)
```

Layout knobs: `constraint=False` for an edge that must not influence ranking (e.g. a `«guard»`
that should stay on the controller row); `label_offset=(rel, px)` or a direct `c.offset` /
`c.abs_offset` fix-up after `layout()` for a label that lands on a package border; drop `ranksep`
to 0.5 when the diagram gets wide (see the 7000 px limit in §6).

### 5.5 Activity diagram with swimlanes — template `06_activity_sync.py`

`ActivityDiagram` does **not** use Graphviz. You place everything on a (lane, row) grid, which is
exactly what you want for swimlanes.

```python
a = ActivityDiagram("Activity diagram — Synchronize (UC14)",
                    lanes=["User", "Desktop client", "API"],
                    lane_w=250, row_h=90, header_h=30,
                    lane_colors=["blue", "purple", "grey"])
s   = a.start(0, 0)
act = a.action("Click «Synchronize»", 0, 1, color=SYNC)
q   = a.decision("[folder bound?]", 1, 2)
f   = a.bar(1, 4, w=220)            # fork / join bar
m   = a.merge(1, 6)
n   = a.note("FolderWatcher can trigger this", 1, 0, w=210)
e   = a.end(1, 7)
a.flow(s, act, exit_=(0.5, 1), entry=(0.5, 0))
a.flow(q, act, "[no]", points=[(x_px, y_px)], exit_=(0, 0.5), entry=(1, 0.5))
a.note_link(n, act)
a.save(OUT("06-activity-sync"))
```

Nodes: `start`, `end`, `flow_final`, `action(label, lane, row, color, w=170, h=50)`,
`decision(label, lane, row)`, `merge`, `bar` (fork/join), `note(text, lane, row, w, color)`.
All of them take `dx=` / `dy=` to nudge inside the cell.

Cell centre (page coordinates, needed for `points=`):

```python
x = lane * lane_w + lane_w / 2
y = header_h + 20 + row * row_h + row_h / 2
```

Define `X(lane, dx=0)` and `Y(row, dy=0)` helpers at the top of the script — every bent flow in
`06_activity_sync.py` uses them.

Conventions: one node per cell; loops as merge-above-decision with the back-edge running up a free
outer channel; guards `[yes]` / `[no]` on the flows.

Layout knobs: never let a flow run straight through another node — give it explicit `points=` or
move the node to another row/`dx`. `exit_=(0.5, 1)` / `entry=(0.5, 0)` (bottom → top) for a
downward flow, `(1, 0.5)` / `(0, 0.5)` for a rightward one. `decision()` always draws its question
to the right; if that corner is taken, add the node with `a._add(lane, row, 60, 60, label,
"rhombus;html=1;fontSize=10;" + label_position_style)` — `06_activity_sync.py` has a ready
`_LABEL_POS` dict for above / below / upper-left. For a guard on an L-shaped flow, call `a._build()`
once and then `a.add_edge_label(flow_id, "[no]", pos=-0.85)` to pin the label near the source end.

### 5.6 Sequence diagram — template `08_sequence_login.py`

Geometry is computed by the library: activations, connection points, fragment frames, notes.

```python
q = SequenceDiagram("Sequence diagram — Sign up and log in", spacing=175, step=38)
u    = q.participant("User", "actor")
page = q.participant("LoginPage", "boundary")
api  = q.participant("ApiClient", "control")
ctl  = q.participant("AuthController", "participant", INFRA)   # third arg = colour

q.note(page, "the /login route\nonly mounts LoginForm", w=112)
q.fragment("opt", "[new user]")
q.gap(2)
q.message(u, page, "enter credentials; click Log in")
q.message(page, api, "login(username, password)")
q.self_message(auth, "issue(user): jwt.sign({sub})")
q.ret(auth, ctl, "AuthResponseDto")
q.fragment_else("[invalid]")
q.ret(ctl, api, "401")
q.end_fragment()
q.deactivate(u)
q.save(OUT("08-sequence-login"))
```

Participant kinds: `actor`, `boundary`, `control`, `entity`, `participant` (plain box). Use the RUP
kinds so the sequence diagram matches the VOPC. `message(a, b, text, kind="sync"|"async")`,
`ret(a, b, text)` (dashed return), `self_message(a, text)`, `activate(p)` / `deactivate(p)` for
manual activation control, `fragment(kind, guard)` / `fragment_else(guard)` / `end_fragment()` with
`kind` in `alt, opt, loop, ref`.

Conventions: server-side participants are grey (`INFRA`); one fragment per alternative flow of the
use case; a `note()` for anything the arrows cannot say.

Layout knobs: `spacing=` is the horizontal distance between lifelines — lower it (170–190) when you
have seven participants; `step=` is the vertical distance between messages. `q.gap(n)` inserts blank
steps — use it after `fragment(...)` so a two-line message label clears the frame border, and before
a message whose label would otherwise sit on the `else` separator. Break long labels with `\n`.

### 5.7 Communication diagram — template `11_communication_sort_filter.py`

A `GraphDiagram` with `routing=STRAIGHT`, objects as `simple_box`, messages as `directed`.

```python
d = GraphDiagram("Communication diagram — Sort and filter", routing=STRAIGHT)
UNDERLINE = "fontStyle=4;"          # object names are underlined
user  = d.actor(":User")
table = d.simple_box(":FileTable", BOUNDARY, extra=UNDERLINE)
utils = d.simple_box("fileList\n(packages/shared)", CONTROL)

d.directed(user, workspace, "1: open /drive")
d.directed(workspace, hook,  "1.1: refresh()")
d.directed(hook, api,        "1.2: listFiles()")
d.directed(vm, table,        "4: render(visibleFiles)")
d.assoc(vm, files, "holds")         # structural link, not a message

n_seq = d.note("Sequence numbers: 1 = load, 2 = sort by name (asc/desc),\n"
               "3 = filter all / only .cpp / only .png, 4 = redraw", "yellow", w=360)
d._nodes[n_seq].anchor = "__content__"      # free-standing note under the content
d._nodes[n_seq].place = "bottom"

d.same_rank(workspace, table, sort_ctl, filter_ctl)
d.layout(rankdir="LR", nodesep=1.0, ranksep=1.2)
```

Conventions:

* Object names are `:ClassName` (or `name : Class`) and **underlined** — pass
  `extra="fontStyle=4;"` to `simple_box`. A module of free functions is not an object, so it gets no
  underline.
* Objects and their colours mirror the VOPC of the same use case, so the lecturer can line the two
  diagrams up.
* Messages are **hierarchically numbered** (`1`, `1.1`, `1.2`, `2`, `2.1`, …).
* **Add a note explaining the numbering scheme** — a free-standing one under the diagram. The
  library only exposes that placement through `legend()` (a text box), so set `anchor`/`place`
  directly to get a real UML note shape, as above.

Layout knobs: generous `nodesep` (≈1.0) and `ranksep` (≈1.2) — the message labels are long and need
the room. `same_rank` per role column. Note that `bend=` only applies when draw.io routes the edges
itself; with the default `route_edges=True` Graphviz already separates opposite-direction pairs into
two polylines with their own label space.

### 5.8 State machine diagram — template `12_state_session.py`

```python
d = GraphDiagram("State diagram — client session", routing=STRAIGHT)
TR = E_FLOW + "fontSize=10;"
def tr(a, b, label="", **kw):
    return d.edge(a, b, TR, label, **kw)

start = d.initial()
fin   = d.final()
out   = d.state("LoggedOut", color=ACCESS)
li    = d.composite_state("LoggedIn")                       # container
browsing = d.state("Browsing",
                   ["entry / useDrive.refresh()", "do / render FileTable"],
                   color=LIST, group=li)
li_start = d.initial(group=li)

tr(start, out)
tr(out, fin, "close app", dot_reverse=True)
tr(out, auth, "submit credentials / POST /auth/login")
```

Calls: `initial(group=None)`, `final(group=None)`, `state(name, internals=[...], color, group, w)`,
`composite_state(name, parent=None)`, `transition(a, b, label)` (or your own `tr` helper on
`E_FLOW`).

Conventions: internal activities as `entry / …`, `do / …`, `exit / …` strings in `internals=`;
transition labels as `event / action` or `event [guard]`; a composite state for the "logged in"
region with its own `initial()` inside.

Layout knobs: `dot_reverse=True` on a transition that points back up a rank; `group=li` puts a state
inside the composite; declaration order inside the composite seeds the left-to-right order of a row.
Transitions that touch a *composite border* need fixed ports — after `layout()`, find the cell and
set `c.points = None` plus `exitX/exitY/entryX/entryY` on `c.style` (there is a worked example at the
end of `12_state_session.py`).

### 5.9 Component diagram — template `15_component.py`

```python
d = GraphDiagram("Component diagram", routing=ORTHO)
g_api  = d.group("API — NestJS (apps/api)", color=INFRA)
shared = d.component("@minidrive/shared\n(packages/shared)", LIST, h=110)
files  = d.component("FilesModule", INFRA, group=g_api)
rest   = d.lollipop("REST /files")          # provided interface
folder = d.artifact("Bound local folder", color=SYNC)
pg     = d.database("postgres", color=INFRA)

d.edge(files, rest, E_ASSOC + LEFTWARDS, "", dot_reverse=True)     # provides
d.edge(web, rest, E_DEPENDENCY + RIGHTWARDS, "")                   # requires
d.dependency(web_pkg, shared, "«import»")
d.legend("○ — provided interface (lollipop); dashed open arrow — dependency ...", w=600)
d.layout(rankdir="LR", nodesep=0.5, ranksep=0.9)
```

Calls: `component(name, color, group=None, stereotype=None, w=None, h=60)`, `lollipop(name)`,
`database(name, color)`, `artifact(name, color)`, `group(...)` for subsystems, `dependency`,
`assoc`, `legend`.

Conventions: a provided interface is a lollipop connected to its provider with a plain `assoc`
(ranked *before* the provider via `dot_reverse=True`, so it faces the consumers) and to every
consumer with a dashed `dependency`. Colour by subsystem; a `legend()` decodes the notation and the
colours.

Layout knobs: `ports(exit_x, exit_y, entry_x, entry_y)` helper (same shape as in §5.3) so every edge
leaves the side facing its target; `minlen=0` for intra-cluster edges (see §5.4); `h=` on a component
that needs room for several ports on one side.

### 5.10 Deployment diagram — template `16_deployment.py`

```python
d = GraphDiagram("Deployment diagram", routing=ORTHO)
g_user    = d.node3d("«device»\nUser workstation (macOS / Windows)", color=INFRA)
g_browser = d.node3d("«executionEnvironment»\nChrome / Edge browser", parent=g_user, color="white")
web       = d.artifact("MiniDrive web client (Next.js pages)", color="white", group=g_browser)
g_cloud   = d.node3d("«device»\nCloud VM — Ubuntu (Docker host)", color=INFRA)
api       = d.component("api — NestJS (:3000)", color=INFRA, group=g_compose)
pg        = d.database("postgres\n(:5432, volume pgdata)", color=INFRA, group=g_compose)

d.edge(web, caddy, E_ASSOC + ports(0.5, 0.5), "HTTPS :443")
d.layout(rankdir="LR", nodesep=0.45, ranksep=0.8, extra_graph_attrs=INVIS)
```

Calls: `node3d(label, parent=None, color, pad=24)` — a 3-D box that is also a container, nest with
`parent=`; `component`, `database`, `artifact` with `group=<node id>`; communication paths as plain
`assoc`/`edge` with a `"protocol :port"` label.

Conventions: `«device»` and `«executionEnvironment»` stereotypes in the node label; Docker
containers as components; databases/object stores as cylinders; deployed programs and folders as
`«artifact»`; every path labelled with protocol and port; a `legend()` decoding the shapes.

Layout knobs: `extra_graph_attrs=` is the public hook for raw Graphviz — inject **invisible** edges
to line clusters up or to attach an otherwise disconnected node so `dot` puts it where you want:

```python
INVIS = (f'"{bound_folder}" -> "{web_client}" [style=invis, minlen=1]; '
         f'"{desktop_app}" -> "{electron_dev}" [style=invis, constraint=false];')
d.layout(rankdir="LR", nodesep=0.45, ranksep=0.8, extra_graph_attrs=INVIS)
```

Also give each incoming path a different `entry_y` so several paths reaching one node land at
distinct points instead of converging.

---

## 6. Running, exporting and checking

### 6.1 Run one diagram

```bash
python3 docs/uml/gen/03_class_vopc_sort_filter.py
```

### 6.2 Run all of them

```bash
for f in docs/uml/gen/[0-9][0-9]_*.py; do python3 "$f"; done
```

### 6.3 Always look at the PNG

Open `docs/uml/img/NN-name.png` and check, in this order:

1. no overlapping nodes and **no overlapping labels**;
2. arrowheads point the right way (`extend`: extension → base; `generalization`: child → parent);
3. every element the assignment asks for is present, spelled exactly as in your spec;
4. colours match your semantic groups and the legend says so.

Fix with `same_rank`, `minlen`, `nodesep` / `ranksep`, declaration order, `label_offset`, `bend`, or
manual note placement — then re-run and look again. Two to four iterations is normal.

### 6.4 The draw.io CLI clipping limit

The library exports PNG at `scale=2.0` (`export(src, dst, "png", scale=2.0, border=12)`). **A 2x PNG
wider than roughly 7000 px is silently clipped by the draw.io CLI** — no error, no non-zero exit
code, just a truncated picture. The widest diagram in this repo is `05-class-clients.png` at
6963 px, deliberately just under the line.

Check every export:

```bash
python3 - <<'PY'
import glob, struct
for f in sorted(glob.glob("docs/uml/img/*.png")):
    d = open(f, "rb").read(24)
    print(f, struct.unpack(">II", d[16:24]))
PY
```

If a diagram goes over: reduce `ranksep` / `nodesep`, shorten labels, split the diagram in two, or
move detail into a `legend()` under the picture instead of onto the nodes.

### 6.5 Regeneration and hand-edited `.drawio` files

The generator is the source of truth. Re-running it **overwrites** the `.drawio` and both images.

If somebody hand-edits `docs/uml/drawio/NN-name.drawio` in the draw.io app:

1. Do not re-run the generator yet — you would lose the edit.
2. Open the edited file, work out what changed, and **port the change back into the generator
   script** (a renamed class, a moved note, a new edge).
3. Re-run the generator and compare the new PNG with the hand-edited one.
4. If the change genuinely cannot be expressed through the library, do it as a post-`layout()`
   fix-up in the script — the diagram objects expose `d.cells`, and each cell has `x, y, w, h,
   style, value, points, offset, abs_offset`, exactly as `04_class_server.py` and
   `12_state_session.py` do at the end. **Never edit `drawio.py` from a generator script.**

To export an existing `.drawio` by hand (same call the library makes):

```bash
/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -b 12 -s 2 \
  -o docs/uml/img/00-demo-class.png docs/uml/drawio/00-demo-class.drawio
```

---

## 7. Embedding in a pandoc report

In the Markdown report (`docs/reports/stage1-uml.md` here), an image on its own paragraph becomes a
numbered figure:

```markdown
![Рис. 1. Діаграма компонентів](../uml/img/15-component.png){width=16cm}
```

* The path is relative to the report file (`docs/reports/` → `../uml/img/`).
* `{width=16cm}` scales to the text block of an A4 page with 2 cm margins. Use 15 cm for a tall
  diagram, 12–14 cm for very tall activity/sequence diagrams so they fit one page.
* The alt text becomes the caption **only** with the `implicit_figures` extension, and only when the
  image is the entire paragraph — leave a blank line above and below it.

The build script (`tools/build-report.sh`) already passes both:

```bash
COMMON=(--from markdown+smart+implicit_figures --toc --toc-depth=2 --number-sections \
        -V lang=uk --resource-path=".:..:../uml/img")

pandoc "$BASE.md" "${COMMON[@]}" -o "$BASE.docx"
pandoc "$BASE.md" "${COMMON[@]}" --pdf-engine=xelatex --include-in-header ../../tools/titlepage.tex \
  -V mainfont="Times New Roman" -V fontsize=12pt -V geometry:margin=2cm -o "$BASE.pdf"
```

`--resource-path` lets pandoc find the images even if you shorten the link, and the script `cd`s
into the report directory first so relative links resolve. Run it as:

```bash
tools/build-report.sh docs/reports/stage1-uml.md
```

Prerequisites for the report step: `brew install pandoc` and a TeX distribution with `xelatex`
(`brew install --cask mactex-no-gui`, or `basictex` plus the packages xelatex asks for).

---

## 8. Assignment checklist → which template to start from

| requirement | minimum | template to copy | output name |
|---|---|---|---|
| Use case diagram | 1+ | `01_use_case.py` | `01-use-case` |
| Class diagram — domain model | 1 | `02_class_domain.py` | `02-class-domain` |
| Class diagram — **VOPC for your variant use case** | 1 | `03_class_vopc_sort_filter.py` | `03-class-vopc-…` |
| Class diagram — implementation (server) | optional, counts toward "2+" | `04_class_server.py` | `04-class-server` |
| Class diagram — implementation (clients) | optional | `05_class_clients.py` | `05-class-clients` |
| Activity diagram (swimlanes, fork/join, decision) | 1+ | `06_activity_sync.py`, `07_activity_upload.py` | `06-activity-…` |
| Interaction — sequence | part of "2+" | `08_sequence_login.py`, `09`, `10` | `08-sequence-…` |
| Interaction — communication (numbered messages) | part of "2+" | `11_communication_sort_filter.py` | `11-communication-…` |
| State machine diagram | 1+ | `12_state_session.py`, `13`, `14` | `12-state-…` |
| Component diagram | 1+ | `15_component.py` | `15-component` |
| Deployment diagram | 1+ | `16_deployment.py` | `16-deployment` |

Class diagrams: **2 or more**, and one of them must be the VOPC for the use case of your variant.
Interaction diagrams: **2 or more**; the safe combination is one sequence + one communication for
the *same* use case, with the same participants and the same colours, so the two read as one story.

Suggested order of work: use case → domain classes → VOPC of the variant use case → sequence for
that use case → communication for that use case → activity → states → component → deployment.

---

## 9. Troubleshooting

**`RuntimeError: Graphviz 'dot' not found on PATH`**
`layout()` calls `shutil.which("dot")`. Install Graphviz (`brew install graphviz`) and make sure the
shell you run from sees it: `dot -V`. On Windows add the Graphviz `bin` folder to `PATH` and open a
new terminal.

**`[drawio] CLI not found at /Applications/draw.io.app/Contents/MacOS/draw.io; wrote … only`**
The `.drawio` was written but not exported. Point the library at your binary:

```bash
DRAWIO_BIN=$(command -v drawio) python3 docs/uml/gen/01_use_case.py
```

Export it once per shell with `export DRAWIO_BIN=...` if you run many scripts.

**`RuntimeError: draw.io export failed (…)`**
`export()` raises when the CLI exits non-zero or writes no file. Usual causes: no display (run under
`xvfb-run -a` on a headless Linux box), the app is mid-update, or a sandboxed/quarantined binary on
macOS (open the draw.io app once by hand and accept the Gatekeeper prompt).

**Boxes are drawn but the picture looks empty / all shapes are grey rectangles**
Your draw.io is much older than the shape names used here (`shape=umlLifeline`, `shape=cylinder3`,
`shape=cube`, `participant=umlBoundary`). Update draw.io desktop.

**Fonts look different in the PNG than in the app**
The exporter uses the fonts installed on the machine. The styles do not pin a font family, so
draw.io's default (Helvetica) is used; the width of a box is estimated by `_text_width()` for an
11 pt font. If a label overflows its box on your machine, pass an explicit `w=` (`usecase`,
`note`, `state`, `simple_box`, `component`, `text`, `legend` all take one) or `min_w=` on `klass`.

**Cyrillic (or any non-ASCII) in labels**
Fully supported — the XML is written as UTF-8 and `«»` guillemets are used for stereotypes
throughout. Two rules: (a) save your generator scripts as UTF-8, and (b) `<`, `>` and `&` are
HTML-escaped automatically, so write `List<FileDto>` literally and do not pre-escape it. If Cyrillic
comes out as boxes in the PNG, the machine is missing a font that covers it — install one (macOS and
Windows ship with several). This project keeps all **diagram** text in English and only the report
prose in Ukrainian, which also sidesteps the problem in xelatex.

**Overlapping labels**
In order of how often it works:
1. raise `nodesep` / `ranksep`;
2. `same_rank(...)` the nodes that should share a row/column;
3. reorder the node declarations — declaration order is the ordering hint inside a rank;
4. pin edge ports with an `exitX/exitY/entryX/entryY` fragment so incoming edges land at different
   heights;
5. `label_offset=(rel, px)` on the edge, or `bend=px`;
6. after `layout()`, walk `d.cells` and set `c.offset` (relative, −1…1) / `c.abs_offset` (pixels) on
   the one stubborn label.

**A note lands in the middle of the diagram and bends nearby edges**
`note_link(n, target, place="auto")` makes the note a Graphviz leaf, which occupies a rank. Switch to
`place="above"` / `"below"` / `"left"` / `"right"` — the note is then placed after layout and the
library tries the other three spots if the first one collides.

**An edge inside a package pushes its classes into different columns**
Do not `same_rank()` cluster members (Graphviz ejects them). Use `minlen=0` on the intra-package
edges, plus `dot_reverse=True` where the arrow must point the other way.

**The PNG is cut off on the right**
See §6.4 — the 2x export clips above roughly 7000 px. Check the width, then shrink `ranksep` or split
the diagram.
