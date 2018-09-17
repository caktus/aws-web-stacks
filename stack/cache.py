from troposphere import Equals, If, Not, Ref, ec2, elasticache

from .common import dont_create_value
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import (
    container_a_subnet,
    container_a_subnet_cidr,
    container_b_subnet,
    container_b_subnet_cidr,
    vpc
)

cache_node_type = template.add_parameter(
    Parameter(
        "CacheNodeType",
        Default="cache.t2.micro",
        Description="Cache instance type",
        Type="String",
        AllowedValues=[
            dont_create_value,
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
            'cache.r4.large',
            'cache.r4.xlarge',
            'cache.r4.2xlarge',
            'cache.r4.4xlarge',
            'cache.r4.8xlarge',
            'cache.r4.16xlarge',
            'cache.r3.large',
            'cache.r3.xlarge',
            'cache.r3.2xlarge',
            'cache.r3.4xlarge',
            'cache.r3.8xlarge',
        ],
        ConstraintDescription="must select a valid cache node type.",
    ),
    group="Cache",
    label="Instance Type",
)

cache_engine = template.add_parameter(
    Parameter(
        "CacheEngine",
        Default="redis",
        Description="Cache engine (redis or memcached)",
        Type="String",
        AllowedValues=[
            'redis',
            'memcached',
        ],
        ConstraintDescription="must select a valid cache engine.",
    ),
    group="Cache",
    label="Engine",
)

cache_condition = "CacheCondition"
template.add_condition(cache_condition, Not(Equals(Ref(cache_node_type), dont_create_value)))

using_redis_condition = "UsingRedis"
template.add_condition(
    using_redis_condition,
    Equals(Ref(cache_engine), "redis"),
)

cache_security_group = ec2.SecurityGroup(
    'CacheSecurityGroup',
    template=template,
    GroupDescription="Cache security group.",
    Condition=cache_condition,
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        # Redis in from web clusters
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=If(using_redis_condition, "6379", "11211"),
            ToPort=If(using_redis_condition, "6379", "11211"),
            CidrIp=container_a_subnet_cidr,
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=If(using_redis_condition, "6379", "11211"),
            ToPort=If(using_redis_condition, "6379", "11211"),
            CidrIp=container_b_subnet_cidr,
        ),
    ],
)

cache_subnet_group = elasticache.SubnetGroup(
    "CacheSubnetGroup",
    template=template,
    Description="Subnets available for the cache instance",
    Condition=cache_condition,
    SubnetIds=[Ref(container_a_subnet), Ref(container_b_subnet)],
)

cache_cluster = elasticache.CacheCluster(
    "CacheCluster",
    template=template,
    Engine=Ref(cache_engine),
    CacheNodeType=Ref(cache_node_type),
    Condition=cache_condition,
    NumCacheNodes=1,  # Must be 1 for redis, but still required
    Port=If(using_redis_condition, 6379, 11211),
    VpcSecurityGroupIds=[Ref(cache_security_group)],
    CacheSubnetGroupName=Ref(cache_subnet_group),
)
