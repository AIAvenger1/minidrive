"""Shared bootstrap for the diagram generator scripts in this folder.

    from _common import *
    d = GraphDiagram("...")
    ...
    d.save(OUT("01-use-case"))
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "drawio_gen"))

from drawio import *  # noqa: E402,F401,F403
from drawio import COLORS, ORTHO, STRAIGHT, GraphDiagram, ActivityDiagram, SequenceDiagram  # noqa: E402

DRAWIO_DIR = os.path.join(ROOT, "docs", "uml", "drawio")
IMG_DIR = os.path.join(ROOT, "docs", "uml", "img")

# Semantic colour groups used across all MiniDrive diagrams
ACCESS, LIST, OPS, SYNC, INFRA = "blue", "green", "yellow", "purple", "grey"


def OUT(name: str) -> str:
    """Path of the .drawio file for a diagram name like '01-use-case'."""
    return os.path.join(DRAWIO_DIR, name + ".drawio")


__all__ = [n for n in dir() if not n.startswith("_")] + ["OUT"]
