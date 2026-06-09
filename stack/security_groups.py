from troposphere import Join, Ref, Sub, Tag, Tags
from troposphere.ec2 import SecurityGroup

from .template import template
from .vpc import vpc

container_security_group = SecurityGroup(
    # NOTE: If creating an EKS cluster, eks.py will modify this security group.
    'ContainerSecurityGroup',
    template=template,
    GroupDescription="Container security group.",
    VpcId=Ref(vpc),
    Tags=Tags(
        Tag("Name", Join("-", [Ref("AWS::StackName"), "container"])),
        Tag(Sub("kubernetes.io/cluster/${EksCluster}"), "owned"),
    ),
)
