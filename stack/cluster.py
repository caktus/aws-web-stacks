from troposphere.ecs import (
    Cluster,
)

from .template import template


# ECS cluster
cluster = Cluster(
    "Cluster",
    template=template,
)
