from troposphere import (
    Ref
)
from troposphere.ec2 import (
    SecurityGroup,
    SecurityGroupRule,
)

from .vpc import (
    vpc,
    loadbalancer_a_subnet_cidr,
    loadbalancer_b_subnet_cidr,
)
from .template import template


load_balancer_security_group = SecurityGroup(
    "LoadBalancerSecurityGroup",
    template=template,
    GroupDescription="Web load balancer security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="443",
            ToPort="443",
            CidrIp='0.0.0.0/0',
        ),
    ],
)

web_worker_port = 80

container_security_group = SecurityGroup(
    'ContainerSecurityGroup',
    template=template,
    GroupDescription="Container security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        # HTTP from web public subnets
        SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=web_worker_port,
            ToPort=web_worker_port,
            CidrIp=loadbalancer_a_subnet_cidr,
        ),
        SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=web_worker_port,
            ToPort=web_worker_port,
            CidrIp=loadbalancer_b_subnet_cidr,
        ),
    ],
)
