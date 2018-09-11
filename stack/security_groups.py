import os
from itertools import product

from troposphere import Ref
from troposphere.ec2 import SecurityGroup, SecurityGroupRule

from .template import template
from .vpc import loadbalancer_a_subnet_cidr, loadbalancer_b_subnet_cidr, vpc

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
)

# allow traffic from the load balancer subnets to the web workers
if os.environ.get('USE_ECS') == 'on' or os.environ.get('USE_EC2') == 'on':
    # if using ECS or EC2, allow traffic to the configured WebWorkerPort
    web_worker_ports = [Ref("WebWorkerPort")]
elif os.environ.get('USE_GOVCLOUD') == 'on':
    # if using GovCloud (real EC2 instances), allow traffic to the configured
    # WebWorkerPort and port 443
    web_worker_ports = [Ref("WebWorkerPort"), "443"]
else:
    # otherwise, if using Elastic Beanstalk, allow traffic only to EB's default
    # web worker port (80)
    web_worker_ports = ["80"]

cidrs = [loadbalancer_a_subnet_cidr, loadbalancer_b_subnet_cidr]

# HTTP from web public subnets
ingress_rules = [SecurityGroupRule(
    IpProtocol="tcp",
    FromPort=port,
    ToPort=port,
    CidrIp=cidr,
) for port, cidr in product(*[web_worker_ports, cidrs])]

# Health check
ingress_rules.append(SecurityGroupRule(
    IpProtocol=Ref("WebWorkerHealthCheckProtocol"),
    FromPort=Ref("WebWorkerHealthCheckPort"),
    ToPort=Ref("WebWorkerHealthCheckPort"),
    SourceSecurityGroupId=Ref(load_balancer_security_group),
))

container_security_group = SecurityGroup(
    'ContainerSecurityGroup',
    template=template,
    GroupDescription="Container security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=ingress_rules,
)
