from troposphere.ec2 import (
    VPC,
)

from .template import template


vpc = VPC(
    "Vpc",
    template=template,
    CidrBlock="10.0.0.0/16",
)
