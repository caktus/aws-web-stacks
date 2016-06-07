from troposphere import (
    Ref,
)

from troposphere.ec2 import (
    InternetGateway,
    Route,
    RouteTable,
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
