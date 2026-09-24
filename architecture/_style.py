"""Shared output location and styling for every diagram.

Files prefixed with "_" are helpers, not diagrams: watch.py never renders them
directly, but saving one re-renders every diagram.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "docs" / "assets"


def output(name: str) -> str:
    """Absolute output path (without extension) inside docs/assets/."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return str(ASSETS_DIR / name)


GRAPH_ATTR = {
    "pad": "0.6",
    "nodesep": "0.7",
    "ranksep": "1.0",
    "splines": "spline",
    "fontname": "DejaVu Sans",
    "fontsize": "22",
    "bgcolor": "white",
}
NODE_ATTR = {"fontname": "DejaVu Sans", "fontsize": "12"}
EDGE_ATTR = {"fontname": "DejaVu Sans", "fontsize": "10", "color": "#5b6573"}

DIAGRAM_DEFAULTS = {
    "outformat": "png",
    "show": False,
    "graph_attr": GRAPH_ATTR,
    "node_attr": NODE_ATTR,
    "edge_attr": EDGE_ATTR,
}

# Edge colours used consistently across diagrams (legend lives in the docs).
SYNC = "#2f6fdb"      # request/response
ASYNC = "#d9822b"     # Kafka events
STREAM = "#2e9e5b"    # real-time output (WebSocket / pub-sub)
DATA = "#7a5cc2"      # persistence
