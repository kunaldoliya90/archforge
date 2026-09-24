# Writing diagrams

Diagrams are Python files in `architecture/` that use the [`diagrams`](https://diagrams.mingrammer.com/) library. Every file renders to a PNG with the same name in `docs/assets/`.

## Anatomy of a diagram

```python
from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.database import PostgreSQL
from diagrams.programming.framework import FastAPI

from _style import ASYNC, DATA, DIAGRAM_DEFAULTS, SYNC, output

with Diagram("Orders service", filename=output("orders"), direction="LR", **DIAGRAM_DEFAULTS):
    with Cluster("API"):
        api = FastAPI("orders-api")
    db = PostgreSQL("orders DB")

    api >> Edge(color=DATA, label="writes") >> db
```

Two lines matter for ArchForge:

- `filename=output("orders")` writes the PNG to `docs/assets/orders.png`.
- `**DIAGRAM_DEFAULTS` applies the shared fonts, spacing and PNG settings, so every diagram looks consistent.

The icon catalogue covers AWS, GCP, Azure, Kubernetes, on-prem, SaaS and programming icons. Browse it at [diagrams.mingrammer.com](https://diagrams.mingrammer.com/docs/nodes/onprem).

## Shared styles

`architecture/_style.py` holds everything diagrams share. Files whose names start with `_` are helpers, not diagrams, and saving one re-renders every diagram.

| Constant | Colour | Use it for |
|---|---|---|
| `SYNC` | Blue | Request/response calls |
| `ASYNC` | Orange | Events and queues |
| `STREAM` | Green | Real-time streams (WebSocket, pub/sub) |
| `DATA` | Purple | Reads and writes to storage |

Using the same colours everywhere means one legend explains every diagram.

## Show it on a page

Embed the PNG from any Markdown page:

```markdown
![Orders service](../assets/orders.png)
```

The image becomes a card that readers can click to zoom and pan, with a badge naming its source file. It also appears in the home page gallery automatically.

## Conventions

- Keep node labels to at most 3 lines, about 22 characters per line. Use `\n` for line breaks.
- Use `direction="LR"` for flows and `"TB"` for layered stacks.
- Group with `Cluster` by deployment boundary (tier, VPC, service) rather than by technology.
- When a diagram's meaning changes, update the text on its page in the same pull request.

!!! note "Commit the PNG"
    The deployed site uses the PNGs committed in `docs/assets/`. Vercel doesn't have Graphviz, so it can't render diagrams. Always commit the `.py` and its `.png` together.
