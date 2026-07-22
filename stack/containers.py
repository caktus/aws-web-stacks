from troposphere import Join, Ref, iam

from .assets import assets_management_policy
from .common import arn_prefix
from .logs import logging_policy
from .template import template
from .utils import ParameterWithDefaults as Parameter

desired_container_instances = Ref(
    template.add_parameter(
        Parameter(
            "DesiredScale",
            Description="Desired count",
            Type="Number",
            Default="2",
        ),
        group="Application Server",
        label="Desired Instance Count",
    )
)
max_container_instances = Ref(
    template.add_parameter(
        Parameter(
            "MaxScale",
            Description="Max count",
            Type="Number",
            Default="4",
        ),
        group="Application Server",
        label="Maximum Instance Count",
    )
)

container_volume_size = Ref(
    template.add_parameter(
        Parameter(
            "ContainerVolumeSize",
            Description="EBS volume size (GB).",
            Type="Number",
            Default="20",
        ),
        group="Application Server",
        label="Root Volume Size",
    )
)

container_policies = [assets_management_policy, logging_policy]

container_instance_role = iam.Role(
    "ContainerInstanceRole",
    template=template,
    AssumeRolePolicyDocument=dict(
        Statement=[
            dict(
                Effect="Allow",
                Principal=dict(Service=["ec2.amazonaws.com"]),
                Action=["sts:AssumeRole"],
            )
        ]
    ),
    Path="/",
    Policies=container_policies,
    ManagedPolicyArns=[
        Join("", [arn_prefix, ":iam::aws:policy/AmazonEKSWorkerNodePolicy"]),
        Join("", [arn_prefix, ":iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"]),
        Join("", [arn_prefix, ":iam::aws:policy/AmazonEKS_CNI_Policy"]),
    ],
)

container_instance_profile = iam.InstanceProfile(
    "ContainerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(container_instance_role)],
)

# No AllowedValues - users can specify any EC2 instance type directly.
# This avoids the need to update the template when new instance types are released.
container_instance_type = Ref(
    template.add_parameter(
        Parameter(
            "ContainerInstanceType",
            Description="Instance type",
            Type="String",
            Default="t3a.micro",
        ),
        group="Application Server",
        label="Instance Type",
    )
)
