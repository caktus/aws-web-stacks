from troposphere import (
    AWS_REGION,
    GetAtt,
    Join,
    Ref,
)

from troposphere.ec2 import (
    EIP,
    InternetGateway,
    NatGateway,
    Route,
    RouteTable,
    Subnet,
    SubnetRouteTableAssociation,
    VPC,
    VPCGatewayAttachment,
)

from .template import template


vpc = VPC(
    "Vpc",
    template=template,
    CidrBlock="10.0.0.0/16",
)


# Allow outgoing to outside VPC
internet_gateway = InternetGateway(
    "InternetGateway",
    template=template,
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
)


public_route = Route(
    "PublicRoute",
    template=template,
    GatewayId=Ref(internet_gateway),
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref(public_route_table),
)


# Holds public instances
public_subnet_cidr = "10.0.1.0/24"

public_subnet = Subnet(
    "PublicSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=public_subnet_cidr,
)


SubnetRouteTableAssociation(
    "PublicSubnetRouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(public_subnet),
)


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
)


# Holds load balancer
loadbalancer_a_subnet_cidr = "10.0.2.0/24"
loadbalancer_a_subnet = Subnet(
    "LoadbalancerASubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=loadbalancer_a_subnet_cidr,
    AvailabilityZone=Join("", [Ref(AWS_REGION), "a"]),
)


SubnetRouteTableAssociation(
    "LoadbalancerASubnetRouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(loadbalancer_a_subnet),
)


loadbalancer_b_subnet_cidr = "10.0.3.0/24"
loadbalancer_b_subnet = Subnet(
    "LoadbalancerBSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=loadbalancer_b_subnet_cidr,
    AvailabilityZone=Join("", [Ref(AWS_REGION), "b"]),
)


SubnetRouteTableAssociation(
    "LoadbalancerBSubnetRouteTableAssociation",
    template=template,
    RouteTableId=Ref(public_route_table),
    SubnetId=Ref(loadbalancer_b_subnet),
)


# Private route table
private_route_table = RouteTable(
    "PrivateRouteTable",
    template=template,
    VpcId=Ref(vpc),
)


private_nat_route = Route(
    "PrivateNatRoute",
    template=template,
    RouteTableId=Ref(private_route_table),
    DestinationCidrBlock="0.0.0.0/0",
    NatGatewayId=Ref(nat_gateway),
)


# Holds containers instances
container_a_subnet_cidr = "10.0.10.0/24"
container_a_subnet = Subnet(
    "ContainerASubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=container_a_subnet_cidr,
    AvailabilityZone=Join("", [Ref(AWS_REGION), "a"]),
)


SubnetRouteTableAssociation(
    "ContainerARouteTableAssociation",
    template=template,
    SubnetId=Ref(container_a_subnet),
    RouteTableId=Ref(private_route_table),
)


container_b_subnet_cidr = "10.0.11.0/24"
container_b_subnet = Subnet(
    "ContainerBSubnet",
    template=template,
    VpcId=Ref(vpc),
    CidrBlock=container_b_subnet_cidr,
    AvailabilityZone=Join("", [Ref(AWS_REGION), "b"]),
)


SubnetRouteTableAssociation(
    "ContainerBRouteTableAssociation",
    template=template,
    SubnetId=Ref(container_b_subnet),
    RouteTableId=Ref(private_route_table),
)
