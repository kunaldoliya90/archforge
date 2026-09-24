"""Example — a streaming event pipeline, low level.

Shows nested clusters and the shared edge colours from _style.py.
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.analytics import Flink
from diagrams.onprem.client import Client
from diagrams.onprem.compute import Server
from diagrams.onprem.database import ClickHouse
from diagrams.onprem.monitoring import Grafana
from diagrams.onprem.queue import Kafka

from _style import ASYNC, DATA, DIAGRAM_DEFAULTS, STREAM, SYNC, output

with Diagram("Event pipeline — low level", filename=output("example_event_pipeline"), direction="LR", **DIAGRAM_DEFAULTS):
    with Cluster("Producers"):
        producers = [Client("Web SDK"), Client("Mobile SDK"), Server("Backend\nservices")]

    collector = Server("Collector\nvalidate · enrich")

    with Cluster("Stream processing"):
        raw = Kafka("events.raw")
        with Cluster("Flink jobs"):
            sessionize = Flink("sessionize")
            aggregate = Flink("aggregate\n1-min windows")
        clean = Kafka("events.clean")

    with Cluster("Serving"):
        warehouse = ClickHouse("ClickHouse")
        dashboards = Grafana("Dashboards")
        alerts = Server("Alerting")

    producers >> Edge(color=SYNC, label="HTTPS batch") >> collector >> Edge(color=ASYNC) >> raw
    raw >> Edge(color=ASYNC) >> [sessionize, aggregate]
    sessionize >> Edge(color=ASYNC) >> clean
    aggregate >> Edge(color=STREAM, label="real-time") >> alerts
    clean >> Edge(color=DATA) >> warehouse >> Edge(color=SYNC) >> dashboards
