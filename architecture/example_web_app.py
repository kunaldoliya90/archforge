"""Example — a typical web application, high level.

Replace this file with your own system. Anything you save in architecture/
re-renders its PNG into docs/assets/ while `python watch.py --serve` runs.
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import Kafka
from diagrams.programming.framework import FastAPI, React

from _style import ASYNC, DATA, DIAGRAM_DEFAULTS, SYNC, output

with Diagram("Web application — high level", filename=output("example_web_app"), direction="LR", **DIAGRAM_DEFAULTS):
    users = Users("Users")
    spa = React("Web app\n(SPA)")
    lb = Nginx("Load balancer")

    with Cluster("API tier (stateless)"):
        api = [FastAPI("api-1"), FastAPI("api-2")]

    with Cluster("Async work"):
        queue = Kafka("jobs")
        worker = Server("worker")

    with Cluster("Data"):
        db = PostgreSQL("Postgres")
        cache = Redis("Redis cache")
        files = Storage("Object storage")

    users >> Edge(color=SYNC) >> spa >> Edge(color=SYNC, label="HTTPS") >> lb >> Edge(color=SYNC) >> api
    api >> Edge(color=DATA) >> db
    api >> Edge(color=DATA, style="dashed") >> cache
    api >> Edge(color=ASYNC, label="enqueue") >> queue >> Edge(color=ASYNC) >> worker
    worker >> Edge(color=DATA) >> [db, files]
