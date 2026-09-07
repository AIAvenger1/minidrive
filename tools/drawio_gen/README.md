# drawio_gen — API cheat-sheet

Generates **native, editable draw.io** files (`.drawio`) plus PNG (2x) and SVG exports.
Import in a generator script (see `docs/uml/gen/_common.py`):

```python
from _common import *          # brings in drawio API, OUT(), DRAWIO_DIR, IMG_DIR, colour names
d = GraphDiagram("Use case diagram", routing=STRAIGHT)
...
d.layout(rankdir="LR", nodesep=0.3, ranksep=0.9)
d.save(OUT("01-use-case"))     # -> docs/uml/drawio/01-use-case.drawio + docs/uml/img/01-use-case.{png,svg}
```

Run from the repo root: `python3 docs/uml/gen/01_use_case.py`, then **Read the PNG** in
`docs/uml/img/` and fix overlaps or bad ordering before returning. Never edit `drawio.py` from a
diagram script; if the library cannot do something, work around it and report it.

Colours (`color=` argument): `blue` access/session · `green` file list, sort, filter, preview ·
`yellow` upload/update/download/delete · `purple` synchronization · `grey` infrastructure ·
`orange`, `red` (errors/conflicts) · `white` default · `none` transparent.
Text is plain; use `\n` for line breaks; stereotypes as «...» (guillemets) — `<`, `>`, `&` are escaped
automatically.

## 1. GraphDiagram — Graphviz-laid-out diagrams (use case, class, VOPC, component, deployment, state, communication)

Constructor: `GraphDiagram(name, routing=ORTHO | STRAIGHT)` — `STRAIGHT` for use case / state /
communication, `ORTHO` (default) for class / component / deployment.

Nodes (all return an id string; optional `group=<group id>` puts the node inside a container):

| call | shape |
|---|---|
| `actor(name)` | stick figure |
| `usecase(text, color, w=None, h=60)` | ellipse |
| `note(text, color)` | note; attach with `note_link(note, target, place="auto")` (`auto` = Graphviz places it as a leaf; or `above/below/left/right`) |
| `klass(name, attrs=[...], methods=[...], stereotype=None, color, italic_name=False)` | class box with attribute / method rows, e.g. `"- id: string"`, `"+ isNewerThan(other: FileEntry): boolean"` |
| `enum(name, values, color)` / `interface(name, methods, color)` | «enumeration» / «interface» boxes |
| `component(name, color, stereotype=None)` | UML component |
| `lollipop(name)` | provided-interface circle (connect provider with `assoc`, consumers with `dependency`) |
| `database(name, color)` | cylinder |
| `artifact(name, color)` | «artifact» note shape |
| `simple_box(label, color, w, h, rounded=False, extra="")` | plain rectangle (objects in communication diagrams: label like `":FileTable"`, add `extra="fontStyle=4;"` for underline) |
| `state(name, internals=["do / ..."], color)` | rounded state |
| `initial(group=None)` / `final(group=None)` | pseudo-states |
| `text(label, w, boxed=True)` | free text box (participates in layout) |
| `legend(text, w=420)` | boxed legend placed under the content after layout |

Containers (groups become draw.io containers; nodes inside move with them):

| call | use |
|---|---|
| `group(label, color, parent=None, pad=20, title_h=30)` | package / subsystem rectangle |
| `composite_state(name, parent=None)` | composite state (rounded) |
| `node3d(label, parent=None, color)` | deployment node (3-D box); nest with `parent=` |

Edges (source, target; optional `label=`; returned object can be ignored):

| call | notation |
|---|---|
| `assoc(a, b, label, mult_a, mult_b)` | plain line (+ multiplicities at the ends) |
| `directed(a, b, label, mult_a, mult_b)` | navigable association / communication message |
| `include(base, included)` / `extend(extension, base)` | dashed «include» / «extend» |
| `generalization(child, parent)` / `realization(impl, iface)` | hollow triangle (solid / dashed) |
| `composition(whole, part, mult_whole="1", mult_part="*")` / `aggregation(...)` | diamond at the whole end |
| `dependency(a, b, label)` | dashed open arrow (`label="«use»"`) |
| `transition(a, b, label)` | state transition / flow arrow |
| `edge(a, b, style, label, constraint, minlen, weight, dot_reverse, label_offset=(rel, px), bend=px)` | low-level |

**Edges may start or end at a group id** (`dependency(web_pkg, shared_pkg, "«import»")`): one edge is
drawn from/to the whole container, clipped at its border — use this instead of many parallel edges
from every class inside a package to the same target.

Layout: `layout(rankdir="TB"|"LR", nodesep, ranksep, margin=20, route_edges=True)`; edges follow
Graphviz's node-avoiding polylines and labels sit where Graphviz reserved room for them. `same_rank(a, b, ...)` forces
nodes onto one rank (same column in LR / same row in TB). Opposite-direction edge pairs are bent
apart automatically. `extend`, `generalization`, `realization` rank the *base/parent first* so
trees flow root → leaves (cascade) and parents sit above children.

## 2. ActivityDiagram — swimlanes + (lane, row) grid

```python
a = ActivityDiagram("Synchronize", lanes=["User", "Desktop client", "API"], lane_w=260, row_h=90,
                    lane_colors=["blue", "purple", "grey"])
s = a.start(lane=0, row=0);  x = a.action("Click «Synchronize»", 0, 1)
q = a.decision("[folder bound?]", 1, 2)            # diamond, label drawn beside it
y = a.action("Open folder picker", 1, 3, dx=-60)   # dx/dy nudge inside the cell
f = a.bar(1, 4, w=220)                             # fork / join bar
m = a.merge(1, 6);  e = a.end(1, 7);  n = a.note("text", 2, 1)
a.flow(q, y, "[no]");  a.flow(q, z, "[yes]", points=[(x_px, y_px)], exit_=(1, 0.5), entry=(1, 0.5))
a.note_link(n, x);  a.save(OUT("06-activity-sync"))
```
Cell centre: `x = lane*lane_w + lane_w/2`, `y = 50 + row*row_h + row_h/2`. Keep one node per
cell; never route a flow straight through another node — use a different row/`dx` or `points=`.

## 3. SequenceDiagram — messages in order, activations computed

```python
q = SequenceDiagram("Log in", spacing=190, step=40)
u = q.participant("User", "actor");  page = q.participant("LoginPage", "boundary")
api = q.participant("ApiClient", "control");  ctl = q.participant("AuthController", "participant", "grey")
q.message(u, page, "enter credentials")          # sync call, activates target
q.message(page, api, "login(username, password)")
q.fragment("alt", "[valid]");  q.self_message(ctl, "signJwt()");  q.ret(ctl, api, "AuthResponseDto")
q.fragment_else("[invalid]");  q.ret(ctl, api, "401");  q.end_fragment()
q.note(page, "token stored in SessionStore");  q.gap();  q.ret(page, u, "show cabinet")
q.save(OUT("08-sequence-login"))
```
Kinds: `actor`, `boundary`, `control`, `entity`, `participant` (box; `color=`). `message(..., kind="async")`
for asynchronous. `activate(p)` / `deactivate(p)` for manual control. Fragments: `alt`, `opt`, `loop`, `ref`.

## 4. Checklist before returning a diagram

1. Script runs without error from the repo root; `.drawio`, `.png`, `.svg` exist.
2. Read the PNG: no overlapping nodes or labels, arrows point the right way, every element from the
   brief is present, names match the spec verbatim, colours follow the groups above.
3. Fix layout with `same_rank`, `minlen`, `nodesep/ranksep`, node order, `bend`, or manual note
   placement — then re-run and re-check. Up to 4 iterations.
