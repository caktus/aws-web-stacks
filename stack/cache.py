from troposphere import (
    ec2,
    Parameter,
    elasticache,
    Ref,
)

from .template import template
from .vpc import (
    vpc,
    container_a_subnet,
    container_a_subnet_cidr,
    container_b_subnet,
    container_b_subnet_cidr,
)


cache_node_type = template.add_parameter(Parameter(
    "CacheNodeType",
    Default="cache.t2.micro",
    Description="Cache instance class",
    Type="String",
    AllowedValues=[
        'cache.t2.micro',
        'cache.t2.small',
        'cache.t2.medium',
        'cache.m3.medium',
        'cache.m3.large',
        'cache.m3.xlarge',
        'cache.m3.2xlarge',
        'cache.m4.large',
        'cache.m4.xlarge',
        'cache.m4.2xlarge',
        'cache.m4.4xlarge',
        'cache.m4.10xlarge',
        'cache.r3.large',
        'cache.r3.xlarge',
        'cache.r3.2xlarge',
        'cache.r3.4xlarge',
        'cache.r3.8xlarge',
    ],
    ConstraintDescription="must select a valid cache node type.",
))


cache_security_group = ec2.SecurityGroup(
    'CacheSecurityGroup',
    template=template,
    GroupDescription="Cache security group.",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        # Redis in from web clusters
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="6379",
            ToPort="6379",
            CidrIp=container_a_subnet_cidr,
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="6379",
            ToPort="6379",
            CidrIp=container_b_subnet_cidr,
        ),
    ],
)


cache_subnet_group = elasticache.SubnetGroup(
    "CacheSubnetGroup",
    template=template,
    Description="Subnets available for the cache instance",
    SubnetIds=[Ref(container_a_subnet), Ref(container_b_subnet)],
)


redis_instance = elasticache.CacheCluster(
    "Redis",
    template=template,
    Engine="redis",
    CacheNodeType=Ref(cache_node_type),
    NumCacheNodes=1,  # Must be 1 for redis, but still required
    Port=6379,
    VpcSecurityGroupIds=[Ref(cache_security_group)],
    CacheSubnetGroupName=Ref(cache_subnet_group),
)
