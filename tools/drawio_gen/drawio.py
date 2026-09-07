"""
drawio.py — a small generator of native, editable draw.io (.drawio) UML diagrams.

Three diagram families:

* GraphDiagram   — use case, class, component, deployment, state diagrams.
                   Nodes/edges are declared, then `layout()` runs Graphviz `dot`
                   to place them (clusters become containers).
* ActivityDiagram — swimlanes + (lane, row) grid; no Graphviz.
* SequenceDiagram — participants + ordered messages; geometry is computed here
                   (activations, fixed connection points, fragments, notes).

Every diagram is saved with `save(path)` which writes the .drawio XML and, when
the draw.io desktop CLI is available, exports PNG (2x) and SVG next to it in the
directory given by `img_dir` (default: ../img relative to the .drawio file).

Label texts are plain strings; use "\n" for line breaks.  Stereotypes are written
with guillemets «...» (no HTML-escaping trap).  `<`/`>`/`&` in labels are escaped
automatically so html=1 labels render literally.
"""
from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DRAWIO_BIN = os.environ.get("DRAWIO_BIN", "/Applications/draw.io.app/Contents/MacOS/draw.io")

# Semantic colour pairs (fill, stroke) — draw.io default palette.
COLORS: Dict[str, Tuple[str, str]] = {
    "blue": ("#dae8fc", "#6c8ebf"),
    "green": ("#d5e8d4", "#82b366"),
    "yellow": ("#fff2cc", "#d6b656"),
    "purple": ("#e1d5e7", "#9673a6"),
    "orange": ("#ffe6cc", "#d79b00"),
    "red": ("#f8cecc", "#b85450"),
    "grey": ("#f5f5f5", "#666666"),
    "white": ("#ffffff", "#000000"),
    "none": ("none", "#000000"),
}

# Edge styles -----------------------------------------------------------------
ORTHO = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
STRAIGHT = "edgeStyle=none;"

E_ASSOC = "endArrow=none;html=1;labelBackgroundColor=#ffffff;"
E_DIRECTED = "endArrow=open;endSize=12;endFill=0;html=1;labelBackgroundColor=#ffffff;"
E_INCLUDE = "endArrow=open;endSize=12;dashed=1;html=1;labelBackgroundColor=#ffffff;"
E_EXTEND = "endArrow=open;endSize=12;dashed=1;html=1;labelBackgroundColor=#ffffff;"
E_GENERALIZATION = "endArrow=block;endSize=16;endFill=0;html=1;labelBackgroundColor=#ffffff;"
E_REALIZATION = "endArrow=block;endSize=16;endFill=0;dashed=1;html=1;labelBackgroundColor=#ffffff;"
E_COMPOSITION = "startArrow=diamondThin;startFill=1;startSize=22;endArrow=none;html=1;labelBackgroundColor=#ffffff;"
E_AGGREGATION = "startArrow=diamondThin;startFill=0;startSize=22;endArrow=none;html=1;labelBackgroundColor=#ffffff;"
E_DEPENDENCY = "endArrow=open;endSize=12;dashed=1;html=1;labelBackgroundColor=#ffffff;"
E_NOTE = "endArrow=none;dashed=1;html=1;labelBackgroundColor=#ffffff;"
E_FLOW = "endArrow=open;endSize=12;endFill=0;html=1;labelBackgroundColor=#ffffff;"
E_MSG_SYNC = "html=1;verticalAlign=bottom;endArrow=block;endFill=1;"
E_MSG_ASYNC = "html=1;verticalAlign=bottom;endArrow=open;endFill=0;endSize=12;"
E_MSG_RETURN = "html=1;verticalAlign=bottom;endArrow=open;endFill=0;endSize=10;dashed=1;"


def esc(text: str) -> str:
    """HTML-escape a label for html=1 cells; newlines become <br>."""
    return html.escape(text, quote=False).replace("\n", "<br>")


def _text_width(text: str, font: float = 11.0) -> float:
    longest = max((len(line) for line in text.split("\n")), default=0)
    return longest * font * 0.60 + 20


# =============================================================================
# Core model
# =============================================================================
@dataclass
class Cell:
    id: str
    value: str = ""
    style: str = ""
    vertex: bool = True
    parent: str = "1"
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    source: Optional[str] = None
    target: Optional[str] = None
    points: Optional[List[Tuple[float, float]]] = None
    source_point: Optional[Tuple[float, float]] = None
    target_point: Optional[Tuple[float, float]] = None
    relative: bool = False          # for edge labels
    offset: Optional[Tuple[float, float]] = None
    abs_offset: Optional[Tuple[float, float]] = None   # mxPoint as="offset" (px) for edge labels
    connectable: bool = True
    raw_value: bool = False         # value already HTML


class Diagram:
    """Bare draw.io page: a list of cells + serializer + exporter."""

    def __init__(self, name: str):
        self.name = name
        self.cells: List[Cell] = []
        self._n = 0

    # -- ids -----------------------------------------------------------------
    def _id(self, prefix: str = "c") -> str:
        self._n += 1
        return f"{prefix}{self._n}"

    # -- low-level cell helpers ---------------------------------------------
    def add_vertex(self, value: str, style: str, w: float, h: float, x: float = 0, y: float = 0,
                   parent: str = "1", cid: Optional[str] = None, raw: bool = False) -> str:
        cid = cid or self._id("v")
        self.cells.append(Cell(cid, value if raw else esc(value), style, True, parent, x, y, w, h,
                               raw_value=True))
        return cid

    def add_edge(self, source: Optional[str], target: Optional[str], style: str, value: str = "",
                 parent: str = "1", points: Optional[List[Tuple[float, float]]] = None,
                 source_point: Optional[Tuple[float, float]] = None,
                 target_point: Optional[Tuple[float, float]] = None, cid: Optional[str] = None,
                 label_offset: Tuple[float, float] = (0.0, 0.0),
                 label_abs_offset: Optional[Tuple[float, float]] = None) -> str:
        cid = cid or self._id("e")
        self.cells.append(Cell(cid, esc(value), style, False, parent, source=source, target=target,
                               points=points, source_point=source_point, target_point=target_point,
                               raw_value=True, offset=label_offset, abs_offset=label_abs_offset))
        return cid

    def add_edge_label(self, edge_id: str, text: str, pos: float = 0.0, align: str = "center",
                       valign: str = "middle", extra: str = "") -> str:
        """Label attached to an edge; pos in [-1, 1] (-1 = source end, 1 = target end)."""
        cid = self._id("l")
        style = (f"edgeLabel;html=1;align={align};verticalAlign={valign};resizable=0;points=[];"
                 f"labelBackgroundColor=#ffffff;{extra}")
        c = Cell(cid, esc(text), style, True, edge_id, x=pos, y=0, w=0, h=0, relative=True,
                 offset=(0, 0), connectable=False, raw_value=True)
        self.cells.append(c)
        return cid

    # -- serialisation ------------------------------------------------------
    def to_xml(self) -> str:
        mxfile = ET.Element("mxfile", host="Electron", type="device", version="24.7.17")
        diagram = ET.SubElement(mxfile, "diagram", name=self.name, id=self.name.lower().replace(" ", "-"))
        model = ET.SubElement(diagram, "mxGraphModel", dx="1200", dy="800", grid="1", gridSize="10",
                              guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1",
                              pageScale="1", pageWidth="1169", pageHeight="827", math="0", shadow="0")
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        for c in self.cells:
            attrs = {"id": c.id, "value": c.value, "style": c.style, "parent": c.parent}
            if c.vertex:
                attrs["vertex"] = "1"
                if not c.connectable:
                    attrs["connectable"] = "0"
            else:
                attrs["edge"] = "1"
                if c.source:
                    attrs["source"] = c.source
                if c.target:
                    attrs["target"] = c.target
            el = ET.SubElement(root, "mxCell", **attrs)
            if c.vertex:
                if c.relative:
                    g = ET.SubElement(el, "mxGeometry", x=_f(c.x), relative="1")
                    g.set("as", "geometry")
                    if c.offset is not None:
                        p = ET.SubElement(g, "mxPoint")
                        p.set("as", "offset")
                else:
                    g = ET.SubElement(el, "mxGeometry", x=_f(c.x), y=_f(c.y), width=_f(c.w), height=_f(c.h))
                    g.set("as", "geometry")
            else:
                g = ET.SubElement(el, "mxGeometry", relative="1")
                g.set("as", "geometry")
                if c.offset is not None and (c.offset[0] or c.offset[1]):
                    g.set("x", _f(c.offset[0]))
                    g.set("y", _f(c.offset[1]))
                if c.abs_offset is not None and (c.abs_offset[0] or c.abs_offset[1]):
                    op = ET.SubElement(g, "mxPoint", x=_f(c.abs_offset[0]), y=_f(c.abs_offset[1]))
                    op.set("as", "offset")
                if c.source_point:
                    p = ET.SubElement(g, "mxPoint", x=_f(c.source_point[0]), y=_f(c.source_point[1]))
                    p.set("as", "sourcePoint")
                if c.target_point:
                    p = ET.SubElement(g, "mxPoint", x=_f(c.target_point[0]), y=_f(c.target_point[1]))
                    p.set("as", "targetPoint")
                if c.points:
                    arr = ET.SubElement(g, "Array")
                    arr.set("as", "points")
                    for (px, py) in c.points:
                        ET.SubElement(arr, "mxPoint", x=_f(px), y=_f(py))
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(mxfile, encoding="unicode")

    def save(self, path: str, img_dir: Optional[str] = None, png: bool = True, svg: bool = True) -> str:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_xml())
        base = os.path.splitext(os.path.basename(path))[0]
        img_dir = os.path.abspath(img_dir or os.path.join(os.path.dirname(path), "..", "img"))
        os.makedirs(img_dir, exist_ok=True)
        if os.path.exists(DRAWIO_BIN):
            if png:
                export(path, os.path.join(img_dir, base + ".png"), "png")
            if svg:
                export(path, os.path.join(img_dir, base + ".svg"), "svg")
        else:
            print(f"[drawio] CLI not found at {DRAWIO_BIN}; wrote {path} only", file=sys.stderr)
        print(f"[drawio] wrote {path}")
        return path


def _f(v: float) -> str:
    return str(int(round(v))) if abs(v - round(v)) < 1e-6 else f"{v:.2f}"


def export(src: str, dst: str, fmt: str = "png", scale: float = 2.0, border: int = 12) -> None:
    args = [DRAWIO_BIN, "-x", "-f", fmt, "-b", str(border)]
    if fmt == "png":
        args += ["-s", str(scale)]
    args += ["-o", dst, src]
    r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError(f"draw.io export failed ({r.returncode}): {r.stdout} {r.stderr}")


# =============================================================================
# Graph diagrams (Graphviz layout)
# =============================================================================
@dataclass
class _Node:
    id: str
    w: float
    h: float
    group: Optional[str] = None
    # style builder is deferred so that layout can supply x/y
    make: object = None
    same_rank_with: Optional[str] = None
    anchor: Optional[str] = None       # manual placement relative to this node (notes)
    place: str = "above"


@dataclass
class _Group:
    id: str
    label: str
    style: str
    parent: Optional[str] = None
    pad: float = 20.0
    title_h: float = 30.0
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


@dataclass
class _GEdge:
    source: str
    target: str
    style: str
    label: str = ""
    labels: List[Tuple[str, float]] = field(default_factory=list)   # (text, pos)
    constraint: bool = True
    minlen: int = 1
    weight: int = 1
    dot_reverse: bool = False
    skip_dot: bool = False
    label_offset: Tuple[float, float] = (0.0, 0.0)   # (relative position along edge -1..1, px perpendicular)
    bend: float = 0.0                                 # perpendicular offset of a middle waypoint (px)
    route: Optional[List[Tuple[float, float]]] = None  # dot polyline (absolute px, source → target)
    lp: Optional[Tuple[float, float]] = None           # dot label position (absolute px)


class GraphDiagram(Diagram):
    def __init__(self, name: str, routing: str = ORTHO):
        super().__init__(name)
        self.routing = routing
        self._nodes: Dict[str, _Node] = {}
        self._groups: Dict[str, _Group] = {}
        self._edges: List[_GEdge] = []
        self._order: List[str] = []
        self._rank_groups: List[List[str]] = []
        self._laid_out = False

    # ---- generic node registration ---------------------------------------
    def _node(self, w: float, h: float, make, group: Optional[str] = None, nid: Optional[str] = None) -> str:
        nid = nid or self._id("n")
        self._nodes[nid] = _Node(nid, w, h, group, make)
        self._order.append(nid)
        return nid

    def group(self, label: str, style: Optional[str] = None, parent: Optional[str] = None,
              color: str = "none", pad: float = 20, title_h: float = 30) -> str:
        fill, stroke = COLORS[color]
        style = style or (f"rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;align=left;spacingLeft=8;"
                          f"fontStyle=1;fillColor={fill};strokeColor={stroke};dashed=0;container=1;")
        gid = self._id("g")
        self._groups[gid] = _Group(gid, label, style, parent, pad, title_h)
        return gid

    # ---- shapes -------------------------------------------------------------
    def actor(self, name: str, group: Optional[str] = None) -> str:
        style = "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;"
        w = max(60, _text_width(name))
        def make(d, x, y, parent, nid):
            d.add_vertex(name, style, 30, 60, x + (w - 30) / 2, y, parent, nid)
        return self._node(w, 80, make, group)

    def usecase(self, name: str, color: str = "white", group: Optional[str] = None,
                w: Optional[float] = None, h: float = 60) -> str:
        fill, stroke = COLORS[color]
        style = f"ellipse;whiteSpace=wrap;html=1;fontSize=11;fillColor={fill};strokeColor={stroke};"
        w = w or max(150, _text_width(name) * 1.15)
        def make(d, x, y, parent, nid):
            d.add_vertex(name, style, w, h, x, y, parent, nid)
        return self._node(w, h, make, group)

    def note(self, text: str, color: str = "yellow", group: Optional[str] = None, w: Optional[float] = None) -> str:
        fill, stroke = COLORS[color]
        style = (f"shape=note;whiteSpace=wrap;html=1;size=14;align=left;spacingLeft=6;spacingRight=10;"
                 f"fontSize=10;fillColor={fill};strokeColor={stroke};")
        lines = text.split("\n")
        w = w or min(260, max(140, _text_width(text, 10)))
        h = max(50, 18 * len(lines) + 16)
        def make(d, x, y, parent, nid):
            d.add_vertex(text, style, w, h, x, y, parent, nid)
        return self._node(w, h, make, group)

    def klass(self, name: str, attrs: Optional[List[str]] = None, methods: Optional[List[str]] = None,
              stereotype: Optional[str] = None, color: str = "white", group: Optional[str] = None,
              min_w: float = 170, italic_name: bool = False) -> str:
        """UML class box: header + attribute rows + separator + method rows (friend-style stack layout)."""
        attrs = attrs or []
        methods = methods or []
        fill, stroke = COLORS[color]
        row_h, sep_h = 22.0, 8.0
        head_h = 40.0 if stereotype else 30.0
        header = (f"«{stereotype}»<br>" if stereotype else "") + (f"<i>{esc(name)}</i>" if italic_name else esc(name))
        style = (f"swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize={int(head_h)};"
                 f"horizontalStack=0;resizeParent=1;resizeParentMax=0;html=1;whiteSpace=wrap;collapsible=0;"
                 f"marginBottom=0;fontSize=12;fillColor={fill};strokeColor={stroke};swimlaneFillColor=#ffffff;")
        rows = attrs + (["--"] if (attrs and methods) else []) + methods
        w = max(min_w, max((_text_width(r) for r in attrs + methods), default=0), _text_width(name, 12) + 10)
        h = head_h + row_h * (len(attrs) + len(methods)) + (sep_h if (attrs and methods) else 0)
        if not rows:
            h = head_h + 16
        row_style = ("text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;"
                     "overflow=hidden;html=1;fontSize=11;whiteSpace=wrap;")
        sep_style = "line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;html=1;"
        def make(d, x, y, parent, nid):
            d.add_vertex(header, style, w, h, x, y, parent, nid, raw=True)
            cy = head_h
            for r in rows:
                if r == "--":
                    d.add_vertex("", sep_style, w, sep_h, 0, cy, nid)
                    cy += sep_h
                else:
                    d.add_vertex(r, row_style, w, row_h, 0, cy, nid)
                    cy += row_h
        return self._node(w, h, make, group)

    def enum(self, name: str, values: List[str], color: str = "white", group: Optional[str] = None) -> str:
        return self.klass(name, attrs=values, methods=[], stereotype="enumeration", color=color, group=group)

    def interface(self, name: str, methods: List[str], color: str = "white", group: Optional[str] = None) -> str:
        return self.klass(name, attrs=[], methods=methods, stereotype="interface", color=color, group=group)

    def simple_box(self, label: str, color: str = "white", group: Optional[str] = None, w: float = 160,
                   h: float = 50, extra: str = "", rounded: bool = False) -> str:
        fill, stroke = COLORS[color]
        style = (f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;fontSize=11;fillColor={fill};"
                 f"strokeColor={stroke};{extra}")
        w = max(w, _text_width(label))
        def make(d, x, y, parent, nid):
            d.add_vertex(label, style, w, h, x, y, parent, nid)
        return self._node(w, h, make, group)

    def component(self, name: str, color: str = "white", group: Optional[str] = None,
                  stereotype: Optional[str] = None, w: Optional[float] = None, h: float = 60) -> str:
        fill, stroke = COLORS[color]
        style = (f"shape=component;align=left;spacingLeft=36;html=1;whiteSpace=wrap;fontSize=11;"
                 f"fillColor={fill};strokeColor={stroke};")
        label = (f"«{stereotype}»\n" if stereotype else "") + name
        w = w or max(170, _text_width(label) + 30)
        def make(d, x, y, parent, nid):
            d.add_vertex(label, style, w, h, x, y, parent, nid)
        return self._node(w, h, make, group)

    def artifact(self, name: str, color: str = "grey", group: Optional[str] = None, w: Optional[float] = None) -> str:
        fill, stroke = COLORS[color]
        style = (f"shape=note;whiteSpace=wrap;html=1;size=12;fontSize=11;align=center;"
                 f"fillColor={fill};strokeColor={stroke};")
        label = "«artifact»\n" + name
        w = w or max(150, _text_width(label))
        def make(d, x, y, parent, nid):
            d.add_vertex(label, style, w, 50, x, y, parent, nid)
        return self._node(w, 50, make, group)

    def database(self, name: str, color: str = "grey", group: Optional[str] = None) -> str:
        fill, stroke = COLORS[color]
        style = (f"shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;"
                 f"fontSize=11;fillColor={fill};strokeColor={stroke};")
        w = max(120, _text_width(name))
        def make(d, x, y, parent, nid):
            d.add_vertex(name, style, w, 70, x, y, parent, nid)
        return self._node(w, 70, make, group)

    def node3d(self, label: str, parent: Optional[str] = None, color: str = "white", pad: float = 24) -> str:
        """Deployment node (3D box) used as a container (group)."""
        fill, stroke = COLORS[color]
        style = (f"shape=cube;size=12;direction=south;boundedLbl=1;verticalAlign=top;align=left;spacingTop=6;"
                 f"spacingLeft=14;html=1;whiteSpace=wrap;fontStyle=1;fontSize=12;fillColor={fill};"
                 f"strokeColor={stroke};container=1;")
        return self.group(label, style=style, parent=parent, pad=pad, title_h=40)

    def lollipop(self, name: str, group: Optional[str] = None) -> str:
        style = ("ellipse;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;"
                 "fontSize=10;fillColor=#ffffff;strokeColor=#000000;")
        w = max(40, _text_width(name, 10))
        def make(d, x, y, parent, nid):
            d.add_vertex(name, style, 20, 20, x + (w - 20) / 2, y, parent, nid)
        return self._node(w, 44, make, group)

    def state(self, name: str, internals: Optional[List[str]] = None, color: str = "white",
              group: Optional[str] = None, w: Optional[float] = None) -> str:
        fill, stroke = COLORS[color]
        internals = internals or []
        style = (f"rounded=1;whiteSpace=wrap;html=1;arcSize=25;fontSize=11;fillColor={fill};"
                 f"strokeColor={stroke};verticalAlign=top;spacingTop=4;")
        if internals:
            value = f"<b>{esc(name)}</b><hr size='1'>" + "<br>".join(esc(i) for i in internals)
        else:
            value = f"<b>{esc(name)}</b>"
            style = style.replace("verticalAlign=top;spacingTop=4;", "")
        w = w or max(130, max(_text_width(t) for t in [name] + internals) + 10)
        h = 40 + 16 * len(internals) + (6 if internals else 0)
        def make(d, x, y, parent, nid):
            d.add_vertex(value, style, w, h, x, y, parent, nid, raw=True)
        return self._node(w, h, make, group)

    def composite_state(self, name: str, parent: Optional[str] = None, color: str = "none") -> str:
        fill, stroke = COLORS[color]
        style = (f"rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;arcSize=10;"
                 f"fillColor={fill};strokeColor={stroke};container=1;")
        return self.group(name, style=style, parent=parent, pad=26, title_h=30)

    def initial(self, group: Optional[str] = None) -> str:
        style = "ellipse;html=1;shape=startState;fillColor=#000000;strokeColor=#000000;"
        def make(d, x, y, parent, nid):
            d.add_vertex("", style, 30, 30, x, y, parent, nid)
        return self._node(30, 30, make, group)

    def final(self, group: Optional[str] = None) -> str:
        style = "ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;"
        def make(d, x, y, parent, nid):
            d.add_vertex("", style, 30, 30, x, y, parent, nid)
        return self._node(30, 30, make, group)

    def text(self, label: str, w: Optional[float] = None, group: Optional[str] = None, boxed: bool = True,
             font: float = 10) -> str:
        style = (f"text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;spacingLeft=6;spacingTop=4;"
                 f"fontSize={font};" + ("strokeColor=#8C97A3;fillColor=#ffffff;" if boxed else "strokeColor=none;fillColor=none;"))
        w = w or min(420, max(200, _text_width(label, font)))
        h = 16 * len(label.split("\n")) + 12
        def make(d, x, y, parent, nid):
            d.add_vertex(label, style, w, h, x, y, parent, nid)
        return self._node(w, h, make, group)

    # ---- edges -------------------------------------------------------------
    def edge(self, source: str, target: str, style: str = E_ASSOC, label: str = "", constraint: bool = True,
             minlen: int = 1, weight: int = 1, labels: Optional[List[Tuple[str, float]]] = None,
             routing: Optional[str] = None, dot_reverse: bool = False,
             label_offset: Tuple[float, float] = (0.0, 0.0), bend: float = 0.0) -> _GEdge:
        """Add an edge. `dot_reverse=True` makes Graphviz rank target before source (used for
        extend / generalization / realization, whose arrows point *up* the tree).
        `label_offset=(rel, px)` moves the edge label along (-1..1) / perpendicular (px) to the edge.
        `bend` (px) adds a curved middle waypoint offset perpendicular to the straight line."""
        r = self.routing if routing is None else routing
        e = _GEdge(source, target, r + style, label, labels or [], constraint, minlen, weight, dot_reverse,
                   label_offset=label_offset, bend=bend)
        self._edges.append(e)
        return e

    def assoc(self, a, b, label="", mult_a="", mult_b="", **kw):
        labels = []
        if mult_a:
            labels.append((mult_a, -0.8))
        if mult_b:
            labels.append((mult_b, 0.8))
        return self.edge(a, b, E_ASSOC, label, labels=labels, **kw)

    def directed(self, a, b, label="", mult_a="", mult_b="", **kw):
        labels = [(mult_a, -0.8)] if mult_a else []
        if mult_b:
            labels.append((mult_b, 0.8))
        return self.edge(a, b, E_DIRECTED, label, labels=labels, **kw)

    def include(self, base, included, **kw):
        return self.edge(base, included, E_INCLUDE, "«include»", **kw)

    def extend(self, extension, base, **kw):
        kw.setdefault("dot_reverse", True)
        return self.edge(extension, base, E_EXTEND, "«extend»", **kw)

    def generalization(self, child, parent, **kw):
        kw.setdefault("dot_reverse", True)
        return self.edge(child, parent, E_GENERALIZATION, "", **kw)

    def realization(self, impl, iface, **kw):
        kw.setdefault("dot_reverse", True)
        return self.edge(impl, iface, E_REALIZATION, "", **kw)

    def composition(self, whole, part, mult_whole="1", mult_part="*", label="", **kw):
        labels = []
        if mult_whole:
            labels.append((mult_whole, -0.8))
        if mult_part:
            labels.append((mult_part, 0.8))
        return self.edge(whole, part, E_COMPOSITION, label, labels=labels, **kw)

    def aggregation(self, whole, part, mult_whole="1", mult_part="*", label="", **kw):
        labels = []
        if mult_whole:
            labels.append((mult_whole, -0.8))
        if mult_part:
            labels.append((mult_part, 0.8))
        return self.edge(whole, part, E_AGGREGATION, label, labels=labels, **kw)

    def dependency(self, a, b, label="", **kw):
        return self.edge(a, b, E_DEPENDENCY, label, **kw)

    def note_link(self, note, target, place: str = "auto", **kw):
        """Attach a note to a node.
        place="auto": Graphviz places the note as a leaf hanging off the target (never overlaps).
        place=above|below|left|right: manual placement next to the target after layout; if that spot
        overlaps another node the other three spots are tried in turn."""
        if place == "auto":
            kw.setdefault("dot_reverse", True)
            kw.setdefault("weight", 1)
            return self.edge(note, target, E_NOTE, "", routing=STRAIGHT, **kw)
        kw.setdefault("constraint", False)
        e = self.edge(note, target, E_NOTE, "", routing=STRAIGHT, **kw)
        e.skip_dot = True
        self._nodes[note].anchor = target
        self._nodes[note].place = place
        return e

    def legend(self, text: str, w: float = 420) -> str:
        """Boxed notation legend placed under the bottom-left corner of the content after layout."""
        nid = self.text(text, w=w, boxed=True)
        self._nodes[nid].anchor = "__content__"
        self._nodes[nid].place = "bottom"
        return nid

    def same_rank(self, *nids: str) -> None:
        """Force nodes onto the same Graphviz rank (same column in LR, same row in TB)."""
        self._rank_groups.append(list(nids))

    def transition(self, a, b, label="", **kw):
        return self.edge(a, b, E_FLOW, label, **kw)

    # ---- group endpoints ------------------------------------------------------
    def _in_group(self, nid: str, gid: str) -> bool:
        g = self._nodes[nid].group
        while g:
            if g == gid:
                return True
            g = self._groups[g].parent
        return False

    def _rep(self, nid: str) -> str:
        """Representative Graphviz node for an endpoint that is a group id (compound edges)."""
        if nid in self._groups:
            for cand in self._order:
                n = self._nodes[cand]
                if n.anchor is None and self._in_group(cand, nid):
                    return cand
            raise ValueError(f"group {nid} contains no nodes; cannot connect an edge to it")
        return nid

    # ---- layout via Graphviz ----------------------------------------------
    def layout(self, rankdir: str = "TB", nodesep: float = 0.5, ranksep: float = 0.7, margin: float = 20,
               ordering: str = "out", extra_graph_attrs: str = "", route_edges: bool = True,
               splines: str = "polyline") -> None:
        """Run Graphviz. With route_edges=True (default) the edges follow Graphviz's node-avoiding
        polylines and edge labels sit where Graphviz reserved room for them; with False draw.io
        routes the edges itself (straight / orthogonal)."""
        dot = shutil.which("dot")
        if not dot:
            raise RuntimeError("Graphviz 'dot' not found on PATH")
        self._route = route_edges
        src = self._dot_source(rankdir, nodesep, ranksep, ordering, extra_graph_attrs,
                               splines if route_edges else "line")
        r = subprocess.run([dot, "-Tjson"], input=src, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("dot failed: " + r.stderr + "\n" + src)
        data = json.loads(r.stdout)
        bb = [float(v) for v in data["bb"].split(",")]
        llx, lly, urx, ury = bb
        positions: Dict[str, Tuple[float, float]] = {}

        def walk(obj):
            name = obj.get("name", "")
            if name.startswith("cluster_"):
                gid = name[len("cluster_"):]
                g = self._groups[gid]
                cb = [float(v) for v in obj["bb"].split(",")]
                g.x = cb[0] - llx + margin
                g.y = (ury - cb[3]) + margin
                g.w = cb[2] - cb[0]
                g.h = cb[3] - cb[1]
            elif "pos" in obj and name in self._nodes:
                px, py = (float(v) for v in obj["pos"].split(","))
                n = self._nodes[name]
                positions[name] = (px - llx + margin - n.w / 2, (ury - py) + margin - n.h / 2)

        for obj in data.get("objects", []):
            walk(obj)
        # edge routes + label positions from Graphviz
        if route_edges:
            dot_edges = [e for e in self._edges if not e.skip_dot]
            by_id = {}
            for je in data.get("edges", []):
                if "id" in je:
                    by_id[je["id"]] = je
            for i, e in enumerate(dot_edges):
                je = by_id.get(f"E{i}")
                if je is None and i < len(data.get("edges", [])) and not by_id:
                    je = data["edges"][i]
                if je is None or "pos" not in je:
                    continue
                pts = _parse_pos(je["pos"])
                pts = [(px - llx + margin, (ury - py) + margin) for (px, py) in pts]
                if e.dot_reverse:
                    pts = list(reversed(pts))
                e.route = pts
                if "lp" in je:
                    lx, ly = (float(v) for v in je["lp"].split(","))
                    e.lp = (lx - llx + margin, (ury - ly) + margin)
        # manual placement of anchored nodes (notes, legend) with collision avoidance
        def overlaps(rect, skip):
            x, y, w, h = rect
            for oid, (ox, oy) in positions.items():
                if oid == skip:
                    continue
                o = self._nodes[oid]
                if x < ox + o.w + 8 and x + w + 8 > ox and y < oy + o.h + 8 and y + h + 8 > oy:
                    return True
            return False

        for nid in self._order:
            n = self._nodes[nid]
            if n.anchor is None:
                continue
            if n.anchor == "__content__":
                xs = [p[0] for p in positions.values()] + [g.x for g in self._groups.values()]
                ys = [p[1] + self._nodes[k].h for k, p in positions.items()] + [g.y + g.h for g in self._groups.values()]
                positions[nid] = (min(xs) if xs else 0, (max(ys) if ys else 0) + 40)
                continue
            t = self._nodes[n.anchor]
            tx, ty = positions[n.anchor]
            gap = 36
            spots = {
                "above": (tx + (t.w - n.w) / 2, ty - n.h - gap),
                "below": (tx + (t.w - n.w) / 2, ty + t.h + gap),
                "left": (tx - n.w - gap, ty + (t.h - n.h) / 2),
                "right": (tx + t.w + gap, ty + (t.h - n.h) / 2),
            }
            order = [n.place] + [k for k in ("above", "right", "below", "left") if k != n.place]
            pos = spots[order[0]]
            for k in order:
                cand = spots[k]
                if not overlaps((cand[0], cand[1], n.w, n.h), nid):
                    pos = cand
                    break
            positions[nid] = pos
            # notes live in the same container as their anchor
            n.group = t.group
        # normalise: shift everything so the top-left content corner is at (margin, margin)
        xs = [p[0] for p in positions.values()] + [g.x for g in self._groups.values()]
        ys = [p[1] for p in positions.values()] + [g.y for g in self._groups.values()]
        if xs and ys:
            dx, dy = margin - min(xs), margin - min(ys)
            positions = {k: (v[0] + dx, v[1] + dy) for k, v in positions.items()}
            for g in self._groups.values():
                g.x += dx
                g.y += dy
            for e in self._edges:
                if e.route:
                    e.route = [(x + dx, y + dy) for (x, y) in e.route]
                if e.lp:
                    e.lp = (e.lp[0] + dx, e.lp[1] + dy)
        self._emit(positions)
        self._laid_out = True

    def _dot_source(self, rankdir, nodesep, ranksep, ordering, extra, splines="line") -> str:
        out = [f'digraph G {{ rankdir={rankdir}; nodesep={nodesep}; ranksep={ranksep}; ordering={ordering}; '
               f'splines={splines}; compound=true; {extra}',
               'node [shape=box, fixedsize=true, label="", fontsize=11];', 'edge [fontsize=10];']
        children: Dict[Optional[str], List[str]] = {}
        for gid, g in self._groups.items():
            children.setdefault(g.parent, []).append(gid)

        def emit_group(gid: str, indent: str):
            g = self._groups[gid]
            # uniform cluster margin = padding + title height (room for the container label)
            out.append(f'{indent}subgraph cluster_{gid} {{ margin={g.pad + g.title_h};')
            for nid in self._order:
                n = self._nodes[nid]
                if n.group == gid and n.anchor is None:
                    out.append(f'{indent}  "{nid}" [width={n.w / 72:.3f}, height={n.h / 72:.3f}];')
            for sub in children.get(gid, []):
                emit_group(sub, indent + "  ")
            out.append(f'{indent}}}')

        for nid in self._order:
            n = self._nodes[nid]
            if n.group is None and n.anchor is None:
                out.append(f'"{nid}" [width={n.w / 72:.3f}, height={n.h / 72:.3f}];')
        for gid in children.get(None, []):
            emit_group(gid, "  ")
        ei = 0
        for e in self._edges:
            if e.skip_dot:
                continue
            attrs = [f'id="E{ei}"', f'constraint={"true" if e.constraint else "false"}', f'minlen={e.minlen}',
                     f'weight={e.weight}']
            ei += 1
            if e.label:
                attrs.append(f'label="{_dot_esc(e.label)}"')
            s, t = (e.target, e.source) if e.dot_reverse else (e.source, e.target)
            if s in self._groups:
                attrs.append(f'ltail="cluster_{s}"')
            if t in self._groups:
                attrs.append(f'lhead="cluster_{t}"')
            out.append(f'"{self._rep(s)}" -> "{self._rep(t)}" [{", ".join(attrs)}];')
        for grp in self._rank_groups:
            out.append("{ rank=same; " + " ".join(f'"{n}";' for n in grp) + " }")
        out.append("}")
        return "\n".join(out)

    def _emit(self, positions: Dict[str, Tuple[float, float]]) -> None:
        # groups first (parents before children), absolute -> relative geometry
        def depth(gid):
            d, g = 0, self._groups[gid]
            while g.parent:
                d += 1
                g = self._groups[g.parent]
            return d
        for gid in sorted(self._groups, key=depth):
            g = self._groups[gid]
            px, py = (0.0, 0.0)
            parent_id = "1"
            if g.parent:
                pg = self._groups[g.parent]
                px, py, parent_id = pg.x, pg.y, g.parent
            self.add_vertex(g.label, g.style, g.w, g.h, g.x - px, g.y - py, parent_id, gid)
        for nid in self._order:
            n = self._nodes[nid]
            x, y = positions[nid]
            parent_id = "1"
            if n.group:
                g = self._groups[n.group]
                x, y, parent_id = x - g.x, y - g.y, n.group
            n.make(self, x, y, parent_id, nid)
        # detect opposite-direction pairs (by top-level container) and bend them apart
        def top(nid):
            g = self._nodes[nid].group if nid in self._nodes else nid
            while g and self._groups[g].parent:
                g = self._groups[g].parent
            return g or nid
        pairs = {(top(e.source), top(e.target)) for e in self._edges}
        exact = {(e.source, e.target) for e in self._edges}
        centers = {}
        for nid, (x, y) in positions.items():
            n = self._nodes[nid]
            centers[nid] = (x + n.w / 2, y + n.h / 2)
        for gid, g in self._groups.items():
            centers[gid] = (g.x + g.w / 2, g.y + g.h / 2)
        for e in self._edges:
            if e.route and len(e.route) >= 2:
                # Graphviz-routed edge: straight segments through the interior corners; label where
                # Graphviz reserved space for it (expressed as position along the edge + px offset).
                style = e.style.replace(ORTHO, "").replace(STRAIGHT, "") + "edgeStyle=none;"
                interior = e.route[1:-1]
                rel, abs_off = 0.0, None
                if e.lp and e.label:
                    rel, abs_off = _label_placement(e.route, e.lp)
                eid = self.add_edge(e.source, e.target, style, e.label, points=interior or None,
                                    label_offset=(rel, 0.0), label_abs_offset=abs_off)
                for (text, pos) in e.labels:
                    self.add_edge_label(eid, text, pos)
                continue
            bend = e.bend
            label_offset = e.label_offset
            reverse_exact = (e.target, e.source) in exact
            reverse_top = (top(e.target), top(e.source)) in pairs and top(e.source) != top(e.target)
            if not bend and (reverse_exact or reverse_top):
                bend = 28.0
            points = None
            style = e.style
            if bend:
                (x1, y1), (x2, y2) = centers[e.source], centers[e.target]
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                ln = (dx * dx + dy * dy) ** 0.5 or 1.0
                px, py = -dy / ln, dx / ln           # right-hand normal
                points = [(mx + px * bend, my + py * bend)]
                if "orthogonalEdgeStyle" not in style:
                    style += "curved=1;"
            eid = self.add_edge(e.source, e.target, style, e.label, points=points, label_offset=label_offset)
            for (text, pos) in e.labels:
                self.add_edge_label(eid, text, pos)

    def save(self, path: str, **kw) -> str:
        if not self._laid_out:
            self.layout()
        return super().save(path, **kw)


def _dot_esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _parse_pos(pos: str) -> List[Tuple[float, float]]:
    """Parse a Graphviz edge `pos` (B-spline with optional s,/e, end points) into a de-duplicated
    polyline ordered from tail to head."""
    start = end = None
    pts: List[Tuple[float, float]] = []
    for tok in pos.replace("\\\n", "").split():
        if tok.startswith("e,"):
            end = tuple(float(v) for v in tok[2:].split(","))
        elif tok.startswith("s,"):
            start = tuple(float(v) for v in tok[2:].split(","))
        else:
            pts.append(tuple(float(v) for v in tok.split(",")))
    if start:
        pts.insert(0, start)
    if end:
        pts.append(end)
    out: List[Tuple[float, float]] = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > 0.5 or abs(p[1] - out[-1][1]) > 0.5:
            out.append(p)
    # drop nearly collinear interior points (keep corners only)
    if len(out) > 2:
        keep = [out[0]]
        for a, b, c in zip(out, out[1:], out[2:]):
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(cross) > 1.0:
                keep.append(b)
        keep.append(out[-1])
        out = keep
    return out


def _label_placement(route: List[Tuple[float, float]], lp: Tuple[float, float]) -> Tuple[float, Optional[Tuple[float, float]]]:
    """Map an absolute label point to draw.io's (relative position along the edge in -1..1, px offset)."""
    seg_len, total = [], 0.0
    for a, b in zip(route, route[1:]):
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        seg_len.append(L)
        total += L
    if total <= 0:
        return 0.0, None
    best = (float("inf"), 0.0, route[0])
    acc = 0.0
    for (a, b), L in zip(zip(route, route[1:]), seg_len):
        if L == 0:
            continue
        t = ((lp[0] - a[0]) * (b[0] - a[0]) + (lp[1] - a[1]) * (b[1] - a[1])) / (L * L)
        t = max(0.0, min(1.0, t))
        px, py = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
        d = (lp[0] - px) ** 2 + (lp[1] - py) ** 2
        if d < best[0]:
            best = (d, (acc + t * L) / total, (px, py))
        acc += L
    frac, (px, py) = best[1], best[2]
    return 2 * frac - 1, (lp[0] - px, lp[1] - py)


# =============================================================================
# Activity diagram — swimlanes + grid
# =============================================================================
class ActivityDiagram(Diagram):
    def __init__(self, name: str, lanes: List[str], lane_w: float = 260, row_h: float = 90,
                 header_h: float = 30, lane_colors: Optional[List[str]] = None):
        super().__init__(name)
        self.lanes = lanes
        self.lane_w, self.row_h, self.header_h = lane_w, row_h, header_h
        self.lane_ids: List[str] = []
        self._max_row = 0
        self._pending: List[Tuple] = []
        self._lane_colors = lane_colors or ["white"] * len(lanes)

    # positions are resolved at save time (lane height depends on max row)
    def _place(self, lane: int, row: int, w: float, h: float, dx: float = 0, dy: float = 0):
        x = lane * self.lane_w + (self.lane_w - w) / 2 + dx
        y = self.header_h + 20 + row * self.row_h + (self.row_h - h) / 2 + dy
        self._max_row = max(self._max_row, row)
        return x, y

    def _add(self, lane, row, w, h, value, style, dx=0, dy=0, raw=False) -> str:
        nid = self._id("a")
        self._max_row = max(self._max_row, row)
        self._pending.append(("v", nid, lane, row, w, h, value, style, dx, dy, raw))
        return nid

    def start(self, lane: int, row: int, **kw) -> str:
        return self._add(lane, row, 30, 30, "", "ellipse;html=1;shape=startState;fillColor=#000000;strokeColor=#000000;", **kw)

    def end(self, lane: int, row: int, **kw) -> str:
        return self._add(lane, row, 30, 30, "", "ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;", **kw)

    def flow_final(self, lane: int, row: int, **kw) -> str:
        return self._add(lane, row, 30, 30, "", "ellipse;html=1;shape=umlDestroy;strokeWidth=2;", **kw)

    def action(self, label: str, lane: int, row: int, color: str = "white", w: float = 170, h: float = 50, **kw) -> str:
        fill, stroke = COLORS[color]
        style = f"rounded=1;whiteSpace=wrap;html=1;arcSize=30;fontSize=11;fillColor={fill};strokeColor={stroke};"
        w = max(w, min(220, _text_width(label)))
        return self._add(lane, row, w, h, label, style, **kw)

    def decision(self, label: str, lane: int, row: int, w: float = 60, h: float = 60, **kw) -> str:
        """Diamond; label is drawn beside it (UML puts the question in a note or on guards)."""
        style = "rhombus;whiteSpace=wrap;html=1;fontSize=10;labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=4;"
        return self._add(lane, row, w, h, label, style, **kw)

    def merge(self, lane: int, row: int, **kw) -> str:
        return self._add(lane, row, 40, 40, "", "rhombus;whiteSpace=wrap;html=1;", **kw)

    def bar(self, lane: int, row: int, w: float = 200, **kw) -> str:
        """Fork/join bar."""
        return self._add(lane, row, w, 8, "", "rounded=0;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=#000000;", **kw)

    def note(self, text: str, lane: int, row: int, w: float = 200, color: str = "yellow", **kw) -> str:
        fill, stroke = COLORS[color]
        h = max(44, 18 * len(text.split("\n")) + 14)
        style = f"shape=note;whiteSpace=wrap;html=1;size=12;align=left;spacingLeft=6;fontSize=10;fillColor={fill};strokeColor={stroke};"
        return self._add(lane, row, w, h, text, style, **kw)

    def flow(self, a: str, b: str, label: str = "", points: Optional[List[Tuple[float, float]]] = None,
             exit_: Optional[Tuple[float, float]] = None, entry: Optional[Tuple[float, float]] = None) -> str:
        style = ORTHO + E_FLOW + "fontSize=10;labelBackgroundColor=#ffffff;"
        if exit_:
            style += f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;"
        if entry:
            style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        eid = self._id("f")
        self._pending.append(("e", eid, a, b, style, label, points))
        return eid

    def note_link(self, note: str, target: str) -> str:
        eid = self._id("f")
        self._pending.append(("e", eid, note, target, STRAIGHT + E_NOTE, "", None))
        return eid

    def _build(self):
        total_h = self.header_h + 40 + (self._max_row + 1) * self.row_h
        for i, name in enumerate(self.lanes):
            fill, stroke = COLORS[self._lane_colors[i]]
            style = (f"swimlane;html=1;startSize={int(self.header_h)};fontStyle=1;fontSize=12;"
                     f"fillColor={fill};strokeColor={stroke};swimlaneFillColor=#ffffff;")
            lid = self.add_vertex(name, style, self.lane_w, total_h, i * self.lane_w, 0, "1")
            self.lane_ids.append(lid)
        for item in self._pending:
            if item[0] == "v":
                _, nid, lane, row, w, h, value, style, dx, dy, raw = item
                x, y = self._place(lane, row, w, h, dx, dy)
                # child of its lane, relative coordinates
                self.add_vertex(value, style, w, h, x - lane * self.lane_w, y, self.lane_ids[lane], nid, raw=raw)
            else:
                _, eid, a, b, style, label, points = item
                self.add_edge(a, b, style, label, "1", points=points, cid=eid)

    def save(self, path: str, **kw) -> str:
        if not self.lane_ids:
            self._build()
        return super().save(path, **kw)


# =============================================================================
# Sequence diagram — computed geometry
# =============================================================================
@dataclass
class _Participant:
    id: str
    name: str
    kind: str
    x: float = 0
    w: float = 0
    activations: List[List[float]] = field(default_factory=list)   # [y_start, y_end, cell_id]
    open_stack: List[int] = field(default_factory=list)


class SequenceDiagram(Diagram):
    KIND_STYLE = {
        "participant": ("shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;"
                        "dropTarget=0;collapsible=0;recursiveResize=0;outlineConnect=0;portConstraint=eastwest;"
                        "newEdgeStyle={\"curved\":0,\"rounded\":0};size=40;fontSize=11;", 130, 40),
        "actor": ("shape=umlLifeline;participant=umlActor;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;"
                  "container=1;dropTarget=0;collapsible=0;recursiveResize=0;outlineConnect=0;portConstraint=eastwest;"
                  "newEdgeStyle={\"curved\":0,\"rounded\":0};verticalAlign=top;spacingTop=36;size=40;fontSize=11;", 30, 40),
        "boundary": ("shape=umlLifeline;participant=umlBoundary;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;"
                     "container=1;dropTarget=0;collapsible=0;recursiveResize=0;outlineConnect=0;portConstraint=eastwest;"
                     "newEdgeStyle={\"curved\":0,\"rounded\":0};verticalAlign=top;spacingTop=36;size=40;fontSize=11;", 50, 40),
        "control": ("shape=umlLifeline;participant=umlControl;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;"
                    "container=1;dropTarget=0;collapsible=0;recursiveResize=0;outlineConnect=0;portConstraint=eastwest;"
                    "newEdgeStyle={\"curved\":0,\"rounded\":0};verticalAlign=top;spacingTop=36;size=40;fontSize=11;", 50, 40),
        "entity": ("shape=umlLifeline;participant=umlEntity;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;"
                   "container=1;dropTarget=0;collapsible=0;recursiveResize=0;outlineConnect=0;portConstraint=eastwest;"
                   "newEdgeStyle={\"curved\":0,\"rounded\":0};verticalAlign=top;spacingTop=36;size=40;fontSize=11;", 50, 40),
    }

    def __init__(self, name: str, spacing: float = 190, step: float = 40, top: float = 20, left: float = 40):
        super().__init__(name)
        self.spacing, self.step, self.top, self.left = spacing, step, top, left
        self._parts: List[_Participant] = []
        self._events: List[Tuple] = []
        self._y = 0.0

    # ---- declarations -------------------------------------------------------
    def participant(self, name: str, kind: str = "participant", color: str = "white") -> str:
        pid = self._id("p")
        self._parts.append(_Participant(pid, name, kind))
        self._parts[-1].color = color  # type: ignore[attr-defined]
        return pid

    def _p(self, pid: str) -> _Participant:
        return next(p for p in self._parts if p.id == pid)

    def message(self, a: str, b: str, text: str, kind: str = "sync", activate: bool = True) -> None:
        """kind: sync | async | return"""
        self._events.append(("msg", a, b, text, kind, activate))

    def ret(self, a: str, b: str, text: str = "") -> None:
        self._events.append(("msg", a, b, text, "return", False))

    def self_message(self, a: str, text: str) -> None:
        self._events.append(("self", a, text))

    def note(self, over: str, text: str, w: float = 180, side: str = "right") -> None:
        self._events.append(("note", over, text, w, side))

    def gap(self, n: int = 1) -> None:
        self._events.append(("gap", n))

    def fragment(self, kind: str, guard: str = "") -> None:
        self._events.append(("frag_begin", kind, guard))

    def fragment_else(self, guard: str = "") -> None:
        self._events.append(("frag_else", guard))

    def end_fragment(self) -> None:
        self._events.append(("frag_end",))

    def activate(self, a: str) -> None:
        self._events.append(("activate", a))

    def deactivate(self, a: str) -> None:
        self._events.append(("deactivate", a))

    # ---- build --------------------------------------------------------------
    def _build(self):
        # participant x positions
        x = self.left
        for p in self._parts:
            style, w, hh = self.KIND_STYLE[p.kind]
            if p.kind == "participant":
                w = max(w, _text_width(p.name, 11) + 10)
            p.w = w
            p.x = x + (self.spacing - w) / 2
            x += self.spacing
        head = 40
        y = self.top + head + 30
        acts: List[Tuple[str, float, float]] = []     # (pid, y0, y1)
        open_act: Dict[str, List[int]] = {p.id: [] for p in self._parts}
        msgs: List[Tuple] = []
        notes: List[Tuple] = []
        frags: List[List] = []
        frag_stack: List[List] = []

        def cx(p: _Participant) -> float:
            return p.x + p.w / 2

        def ensure_act(pid: str, y0: float) -> int:
            if open_act[pid]:
                return open_act[pid][-1]
            acts.append((pid, y0, y0))
            idx = len(acts) - 1
            open_act[pid].append(idx)
            return idx

        def close_act(pid: str, y1: float):
            if open_act[pid]:
                idx = open_act[pid].pop()
                p_, y0, _ = acts[idx]
                acts[idx] = (p_, y0, max(y1, y0 + 20))

        for ev in self._events:
            kind = ev[0]
            if kind == "gap":
                y += self.step * ev[1] * 0.5
            elif kind == "activate":
                ensure_act(ev[1], y)
            elif kind == "deactivate":
                close_act(ev[1], y)
            elif kind == "msg":
                _, a, b, text, mk, activate = ev
                if mk == "return":
                    src_idx = open_act[a][-1] if open_act[a] else ensure_act(a, y - 10)
                    close_act(a, y)
                    dst_idx = open_act[b][-1] if open_act[b] else ensure_act(b, y - 10)
                    msgs.append((a, b, text, mk, y, src_idx, dst_idx))
                else:
                    src_idx = ensure_act(a, y - 10) if not open_act[a] else open_act[a][-1]
                    if activate:
                        acts.append((b, y, y))
                        dst_idx = len(acts) - 1
                        open_act[b].append(dst_idx)
                    else:
                        dst_idx = ensure_act(b, y)
                    msgs.append((a, b, text, mk, y, src_idx, dst_idx))
                y += self.step
            elif kind == "self":
                _, a, text = ev
                idx = ensure_act(a, y - 10)
                msgs.append((a, a, text, "self", y, idx, idx))
                y += self.step + 10
            elif kind == "note":
                _, over, text, w, side = ev
                notes.append((over, text, w, side, y))
                y += max(self.step, 18 * len(text.split("\n")) + 20)
            elif kind == "frag_begin":
                fr = [ev[1], ev[2], y - 8, None, []]      # kind, guard, y0, y1, else-lines
                frags.append(fr)
                frag_stack.append(fr)
                y += 22
            elif kind == "frag_else":
                fr = frag_stack[-1]
                fr[4].append((ev[1], y))
                y += 22
            elif kind == "frag_end":
                fr = frag_stack.pop()
                fr[3] = y + 4
                y += 16
        y_end = y + 20
        # close all open activations at the end
        for pid, stack in open_act.items():
            while stack:
                close_act(pid, y_end - 30)
        total_h = y_end - self.top

        # ---- emit lifelines
        for p in self._parts:
            style, _, _ = self.KIND_STYLE[p.kind]
            fill, stroke = COLORS[getattr(p, "color", "white")]
            if p.kind == "participant":
                style += f"fillColor={fill};strokeColor={stroke};"
            self.add_vertex(p.name, style, p.w, total_h, p.x, self.top, "1", p.id)
        # ---- fragments (behind messages: emitted before them)
        if frags:
            x0 = min(p.x for p in self._parts) - 20
            x1 = max(p.x + p.w for p in self._parts) + 20
        for depth, fr in enumerate(frags):
            k, guard, y0, y1, elses = fr
            inset = 10 * depth
            fx, fw = x0 + inset, (x1 - x0) - 2 * inset
            fid = self.add_vertex(k, "shape=umlFrame;whiteSpace=wrap;html=1;pointerEvents=0;width=50;height=24;fontSize=11;fillColor=none;", fw, (y1 - y0), fx, y0, "1")
            if guard:
                self.add_vertex(guard, "text;html=1;align=left;verticalAlign=middle;fontSize=10;strokeColor=none;fillColor=none;", 200, 20, fx + 56, y0 + 2, "1")
            for (g, gy) in elses:
                self.add_edge(None, None, "endArrow=none;dashed=1;html=1;strokeColor=#000000;", "", "1",
                              source_point=(fx, gy), target_point=(fx + fw, gy))
                if g:
                    self.add_vertex(g, "text;html=1;align=left;verticalAlign=middle;fontSize=10;strokeColor=none;fillColor=none;", 200, 20, fx + 8, gy + 2, "1")
        # ---- activations
        act_ids: List[str] = []
        for (pid, y0, y1) in acts:
            p = self._p(pid)
            aid = self.add_vertex("", "html=1;points=[];perimeter=orthogonalPerimeter;fillColor=#ffffff;strokeColor=#000000;",
                                  10, y1 - y0, p.w / 2 - 5, y0 - self.top, pid)
            act_ids.append(aid)
        # ---- messages
        for (a, b, text, mk, my, si, di) in msgs:
            pa, pb = self._p(a), self._p(b)
            if mk == "self":
                xa = cx(pa) + 5
                self.add_edge(None, None, E_MSG_SYNC + "edgeStyle=orthogonalEdgeStyle;rounded=0;fontSize=10;align=left;",
                              text, "1", points=[(xa + 40, my), (xa + 40, my + 20)],
                              source_point=(xa, my), target_point=(xa, my + 20))
                continue
            style = {"sync": E_MSG_SYNC, "async": E_MSG_ASYNC, "return": E_MSG_RETURN}[mk] + "fontSize=10;"
            sa, sb = acts[si], acts[di]
            left_to_right = cx(pa) < cx(pb)
            # exit point on source activation
            ex = 1 if left_to_right else 0
            ey = _frac(my, sa[1], sa[2])
            en = 0 if left_to_right else 1
            eny = _frac(my, sb[1], sb[2])
            style += f"exitX={ex};exitY={ey:.3f};exitDx=0;exitDy=0;entryX={en};entryY={eny:.3f};entryDx=0;entryDy=0;"
            self.add_edge(act_ids[si], act_ids[di], style, text, "1")
        # ---- notes
        for (over, text, w, side, ny) in notes:
            p = self._p(over)
            nx = cx(p) + 20 if side == "right" else cx(p) - 20 - w
            h = 18 * len(text.split("\n")) + 14
            self.add_vertex(text, "shape=note;whiteSpace=wrap;html=1;size=12;align=left;spacingLeft=6;fontSize=10;fillColor=#fff2cc;strokeColor=#d6b656;",
                            w, h, nx, ny - 6, "1")

    def save(self, path: str, **kw) -> str:
        if not any(c.vertex for c in self.cells):
            self._build()
        return super().save(path, **kw)


def _frac(y: float, y0: float, y1: float) -> float:
    if y1 <= y0:
        return 0.0
    return min(1.0, max(0.0, (y - y0) / (y1 - y0)))


__all__ = ["Diagram", "GraphDiagram", "ActivityDiagram", "SequenceDiagram", "COLORS", "ORTHO", "STRAIGHT",
           "E_ASSOC", "E_DIRECTED", "E_INCLUDE", "E_EXTEND", "E_GENERALIZATION", "E_REALIZATION",
           "E_COMPOSITION", "E_AGGREGATION", "E_DEPENDENCY", "E_NOTE", "E_FLOW", "export"]
