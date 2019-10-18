from troposphere import Ref, iam

from .assets import assets_management_policy
from .logs import logging_policy
from .template import template

# EKS instance role
instance_role = iam.Role(
    "ContainerInstanceRole",
    template=template,
    AssumeRolePolicyDocument=dict(Statement=[dict(
        Effect="Allow",
        Principal=dict(Service=["ec2.amazonaws.com"]),
        Action=["sts:AssumeRole"],
    )]),
    Path="/",
    Policies=[
        assets_management_policy,
        logging_policy,
    ],
    ManagedPolicyArns=[
        "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    ]
)

# EKS instance profile
instance_profile = iam.InstanceProfile(
    "ContainerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(instance_role)],
)
