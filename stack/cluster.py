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


template.add_mapping("ECSRegionMap", {
    "eu-west-1": {"AMI": "ami-4e6ffe3d"},
    "us-east-1": {"AMI": "ami-8f7687e2"},
    "us-west-2": {"AMI": "ami-84b44de4"},
})


# ECS cluster
cluster = Cluster(
    "Cluster",
    template=template,
)
