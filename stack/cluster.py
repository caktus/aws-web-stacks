from troposphere import (
    Parameter,
    Ref,
)

from troposphere.ecs import (
    Cluster,
)

from .template import template


container_instance_type = Ref(template.add_parameter(Parameter(
    "ContainerInstanceType",
    Description="The container instance type",
    Type="String",
    Default="t2.micro",
    AllowedValues=["t2.micro", "t2.small", "t2.medium"]
)))


# ECS cluster
cluster = Cluster(
    "Cluster",
    template=template,
)
