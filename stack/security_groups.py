from troposphere import Join, Ref, Sub, Tag, Tags
from troposphere.ec2 import SecurityGroup, SecurityGroupRule

from . import (
    USE_DOKKU,
    USE_EB,
    USE_EC2,
    USE_ECS,
    USE_EKS,
    USE_GOVCLOUD,
    USE_NAT_GATEWAY
)
from .common import administrator_ip_address
from .template import template
from .vpc import vpc

if not USE_EKS:
    # EKS manages its own ELBs, so this stack doesn't have one
    load_balancer_security_group = SecurityGroup(
        "LoadBalancerSecurityGroup",
        template=template,
        GroupDescription="Web load balancer security group.",
        VpcId=Ref(vpc),
        SecurityGroupIngress=[
            # allow incoming traffic from the public internet to the load balancer
            # on ports 80 and 443
            SecurityGroupRule(
                IpProtocol="tcp",
                FromPort=port,
                ToPort=port,
                CidrIp="0.0.0.0/0",
            ) for port in ["80", "443"]
        ],
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "elb"]),
        ),
    )

    # allow traffic from the load balancer subnets to the web workers
    if USE_ECS or USE_EC2:
        # if using ECS or EC2, allow traffic to the configured WebWorkerPort
        web_worker_ports = [Ref("WebWorkerPort")]
    elif USE_GOVCLOUD:
        # if using GovCloud (real EC2 instances), allow traffic to the configured
        # WebWorkerPort and port 443
        web_worker_ports = [Ref("WebWorkerPort"), "443"]
    else:
        # otherwise, if using Elastic Beanstalk, allow traffic only to EB's default
        # web worker port (80)
        web_worker_ports = ["80"]

    # HTTP from web load balancer
    ingress_rules = [SecurityGroupRule(
        IpProtocol="tcp",
        FromPort=port,
        ToPort=port,
        SourceSecurityGroupId=Ref(load_balancer_security_group),
    ) for port in web_worker_ports]

    # Health check
    if not USE_EB and not USE_DOKKU:
        ingress_rules.append(SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=Ref("WebWorkerHealthCheckPort"),
            ToPort=Ref("WebWorkerHealthCheckPort"),
            Description="ELB Health Check",  # SecurityGroupRule doesn't support a Description attribute
            SourceSecurityGroupId=Ref(load_balancer_security_group),
        ))

    if not USE_NAT_GATEWAY:
        # Allow direct administrator access via SSH.
        ingress_rules.append(SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            Description="Administrator SSH Access",
            CidrIp=administrator_ip_address,
        ))
else:
    ingress_rules = []

container_security_group = SecurityGroup(
    # NOTE: If creating an EKS cluster, eks.py will modify this security group.
    'ContainerSecurityGroup',
    template=template,
    GroupDescription="Container security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=ingress_rules,
    Tags=Tags(
        Tag("Name", Join("-", [Ref("AWS::StackName"), "container"])),
        *(
            [Tag(Sub("kubernetes.io/cluster/${EksCluster}"), "owned")]
            if USE_EKS
            else []
        ),
    ),
)
