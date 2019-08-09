import os

from troposphere import GetAtt, Join, Ref, Tags
from troposphere.ec2 import (
    EIP,
    VPC,
    InternetGateway,
    NatGateway,
    Route,
    RouteTable,
    Subnet,
    SubnetRouteTableAssociation,
    VPCGatewayAttachment
)

from .template import template
from .utils import ParameterWithDefaults as Parameter

USE_NAT_GATEWAY = os.environ.get('USE_NAT_GATEWAY') == 'on'
USE_DOKKU = os.environ.get('USE_DOKKU') == 'on'

# Allows for private IPv4 ranges in the 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16
# address spaces, with block size between /16 and /28 as allowed by VPCs and subnets.
PRIVATE_IPV4_CIDR_REGEX = r"^((10\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)|(172\.(1[6-9]|2[0-9]|3[0-1])\.)|192\.168\.)(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(1[6-9]|2[0-8]))$"  # noqa: E501
PRIVATE_IPV4_CONSTRAINT = "Must be a private IPv4 range with size /16 and /28."

primary_az = template.add_parameter(
    Parameter(
        "PrimaryAZ",
        Description="The primary availability zone for creating resources.",
        Type="AWS::EC2::AvailabilityZone::Name",
    ),
    group="Global",
    label="Primary Availability Zone",
)


secondary_az = template.add_parameter(
    Parameter(
        "SecondaryAZ",
        Description="The secondary availability zone for creating resources. Must differ from primary zone.",
        Type="AWS::EC2::AvailabilityZone::Name",
    ),
    group="Global",
    label="Secondary Availability Zone",
)

vpc_cidr = template.add_parameter(
    Parameter(
        "VpcCidr",
        Description="The primary IPv4 CIDR block for the VPC.",
        Type="String",
        Default="10.0.0.0/16",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="VPC IPv4 CIDR Block",
)

public_subnet_cidr = template.add_parameter(
    Parameter(
        "PublicSubnetCidr",
        Description="IPv4 CIDR block for the public subnet.",
        Type="String",
        Default="10.0.1.0/24",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Public Subnet CIDR Block",
)

loadbalancer_a_subnet_cidr = template.add_parameter(
    Parameter(
        "LoadBalancerSubnetACidr",
        Description="IPv4 CIDR block for the load balancer subnet in the primary AZ.",
        Type="String",
        Default="10.0.2.0/24",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Load Balancer A CIDR Block",
)

loadbalancer_b_subnet_cidr = template.add_parameter(
    Parameter(
        "LoadBalancerSubnetBCidr",
        Description="IPv4 CIDR block for the load balancer subnet in the secondary AZ.",
        Type="String",
        Default="10.0.3.0/24",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Load Balancer B CIDR Block",
)

container_a_subnet_cidr = template.add_parameter(
    Parameter(
        "ContainerSubnetACidr",
        Description="IPv4 CIDR block for the container subnet in the primary AZ.",
        Type="String",
        Default="10.0.10.0/24",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Container A CIDR Block",
)

container_b_subnet_cidr = template.add_parameter(
    Parameter(
        "ContainerSubnetBCidr",
        Description="IPv4 CIDR block for the container subnet in the secondary AZ.",
        Type="String",
        Default="10.0.11.0/24",
        AllowedPattern=PRIVATE_IPV4_CIDR_REGEX,
        ConstraintDescription=PRIVATE_IPV4_CONSTRAINT,
    ),
    group="Global",
    label="Container B CIDR Block",
)


vpc = VPC(
    "Vpc",
    template=template,
    CidrBlock=Ref(vpc_cidr),
    EnableDnsSupport=True,
    EnableDnsHostnames=True,
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "vpc"]),
    ),
)


# Allow outgoing to outside VPC
internet_gateway = InternetGateway(
    "InternetGateway",
    template=template,
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "igw"]),
    ),
)


# Attach Gateway to VPC
VPCGatewayAttachment(
    "GatewayAttachement",
    template=template,
    VpcId=Ref(vpc),
    InternetGatewayId=Ref(internet_gateway),
)


# Public route table
public_route_table = RouteTable(
    "PublicRouteTable",
    template=template,
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "public"]),
    ),
)


public_route = Route(
    "PublicRoute",
    template=template,
    GatewayId=Ref(internet_gateway),
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref(public_route_table),
)


# Holds public instances
public_subnet = Subnet(
    "PublicSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(public_subnet_cidr),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "public"]),
    ),
)


SubnetRouteTableAssociation(
    "PublicSubnetRouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(public_subnet),
)

if USE_NAT_GATEWAY:
    # NAT
    nat_ip = EIP(
        "NatIp",
        template=template,
        Domain="vpc",
    )

    nat_gateway = NatGateway(
        "NatGateway",
        template=template,
        AllocationId=GetAtt(nat_ip, "AllocationId"),
        SubnetId=Ref(public_subnet),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "nat"]),
        ),
    )


if not USE_DOKKU:
    # Holds load balancer
    loadbalancer_a_subnet = Subnet(
        "LoadbalancerASubnet",
        template=template,
        VpcId=Ref(vpc),
        CidrBlock=Ref(loadbalancer_a_subnet_cidr),
        AvailabilityZone=Ref(primary_az),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "elb-a"]),
        ),
    )

    SubnetRouteTableAssociation(
        "LoadbalancerASubnetRouteTableAssociation",
        template=template,
        RouteTableId=Ref(public_route_table),
        SubnetId=Ref(loadbalancer_a_subnet),
    )

    loadbalancer_b_subnet = Subnet(
        "LoadbalancerBSubnet",
        template=template,
        VpcId=Ref(vpc),
        CidrBlock=Ref(loadbalancer_b_subnet_cidr),
        AvailabilityZone=Ref(secondary_az),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "elb-b"]),
        ),
    )

    SubnetRouteTableAssociation(
        "LoadbalancerBSubnetRouteTableAssociation",
        template=template,
        RouteTableId=Ref(public_route_table),
        SubnetId=Ref(loadbalancer_b_subnet),
    )


if USE_NAT_GATEWAY:
    # Private route table
    private_route_table = RouteTable(
        "PrivateRouteTable",
        template=template,
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("-", [Ref("AWS::StackName"), "private"]),
        ),
    )

    private_nat_route = Route(
        "PrivateNatRoute",
        template=template,
        RouteTableId=Ref(private_route_table),
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=Ref(nat_gateway),
    )


# Holds containers instances
container_a_subnet = Subnet(
    "ContainerASubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(container_a_subnet_cidr),
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(primary_az),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "container-a"]),
    ),
)


container_route_table = Ref(private_route_table) if USE_NAT_GATEWAY\
    else Ref(public_route_table)


SubnetRouteTableAssociation(
    "ContainerARouteTableAssociation",
    template=template,
    SubnetId=Ref(container_a_subnet),
    RouteTableId=container_route_table,
)


container_b_subnet = Subnet(
    "ContainerBSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=Ref(container_b_subnet_cidr),
    MapPublicIpOnLaunch=not USE_NAT_GATEWAY,
    AvailabilityZone=Ref(secondary_az),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "container-b"]),
    ),
)


SubnetRouteTableAssociation(
    "ContainerBRouteTableAssociation",
    template=template,
    SubnetId=Ref(container_b_subnet),
    RouteTableId=container_route_table,
)
