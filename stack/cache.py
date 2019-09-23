from troposphere import (
    And,
    Condition,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Output,
    Ref,
    Tags,
    ec2,
    elasticache
)

from .common import dont_create_value, use_aes256_encryption, use_aes256_encryption_cond
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import (
    private_subnet_a,
    private_subnet_a_cidr,
    private_subnet_b,
    private_subnet_b_cidr,
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

using_memcached_condition = "UsingMemcached"
template.add_condition(
    using_memcached_condition,
    Equals(Ref(cache_engine), "memcached"),
)

cache_auth_token = template.add_parameter(
    Parameter(
        "CacheAuthToken",
        NoEcho=True,
        Description="The password used to access a Redis ReplicationGroup (required for HIPAA).",
        Type="String",
        MinLength="16",
        MaxLength="128",
        AllowedPattern="[ !#-.0-?A-~]*",  # see http://www.catonmat.net/blog/my-favorite-regex/
        ConstraintDescription="must consist of 16-128 printable ASCII "
                              "characters except \"/\", \"\"\", or \"@\"."
    ),
    group="Cache",
    label="AuthToken",
)

cache_auth_token_condition = "CacheAuthTokenCondition"
template.add_condition(cache_auth_token_condition, Not(Equals(Ref(cache_auth_token), "")))

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
            CidrIp=Ref(private_subnet_a_cidr),
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=If(using_redis_condition, "6379", "11211"),
            ToPort=If(using_redis_condition, "6379", "11211"),
            CidrIp=Ref(private_subnet_b_cidr),
        ),
    ],
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "cache"]),
    ),
)

cache_subnet_group = elasticache.SubnetGroup(
    "CacheSubnetGroup",
    template=template,
    Description="Subnets available for the cache instance",
    Condition=cache_condition,
    SubnetIds=[Ref(private_subnet_a), Ref(private_subnet_b)],
)

cache_cluster = elasticache.CacheCluster(
    "CacheCluster",
    ClusterName=Join("-", [Ref("AWS::StackName"), "cache"]),
    template=template,
    Engine=Ref(cache_engine),
    CacheNodeType=Ref(cache_node_type),
    Condition=cache_condition,
    NumCacheNodes=1,  # Must be 1 for redis, but still required
    Port=If(using_redis_condition, 6379, 11211),
    VpcSecurityGroupIds=[Ref(cache_security_group)],
    CacheSubnetGroupName=Ref(cache_subnet_group),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "cache"]),
    ),
)

replication_group = elasticache.ReplicationGroup(
    "CacheReplicationGroup",
    template=template,
    AtRestEncryptionEnabled=use_aes256_encryption,
    AutomaticFailoverEnabled=False,
    AuthToken=If(cache_auth_token_condition, Ref(cache_auth_token), ""),
    Engine=Ref(cache_engine),
    CacheNodeType=Ref(cache_node_type),
    CacheSubnetGroupName=Ref(cache_subnet_group),
    Condition=using_redis_condition,
    NumNodeGroups=1,
    Port=6379,
    ReplicationGroupId=Join("-", [Ref("AWS::StackName"), "cache"]),
    ReplicationGroupDescription="Redis ReplicationGroup",
    SecurityGroupIds=[Ref(cache_security_group)],
    TransitEncryptionEnabled=use_aes256_encryption,
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "cache"]),
    ),
)

secure_redis_condition = "SecureRedisCondition"
template.add_condition(secure_redis_condition,
                       And(Condition(using_redis_condition), Condition(use_aes256_encryption_cond)))

cache_address = If(
    cache_condition,
    If(
        using_redis_condition,
        GetAtt(replication_group, 'PrimaryEndPoint.Address'),
        GetAtt(cache_cluster, 'ConfigurationEndpoint.Address')
    ),
    "",  # defaults to empty string if no cache was created
)

cache_port = If(
    cache_condition,
    If(
        using_redis_condition,
        GetAtt(replication_group, 'PrimaryEndPoint.Port'),
        GetAtt(cache_cluster, 'ConfigurationEndpoint.Port')
    ),
    "",  # defaults to empty string if no cache was created
)

cache_url = If(
    cache_condition,
    Join("", [
        Ref(cache_engine),
        If(secure_redis_condition, "s", ""),
        "://",
        If(cache_auth_token_condition, ":_PASSWORD_@", ""),
        cache_address,
        ":",
        cache_port
    ]),
    "",  # defaults to empty string if no cache was created
)

template.add_output([
    Output(
        "CacheURL",
        Description="URL to connect to the cache node/cluster.",
        Value=cache_url,
        Condition=cache_condition,
    ),
])

template.add_output([
    Output(
        "CacheAddress",
        Description="The DNS address for the cache node/cluster.",
        Value=cache_address,
        Condition=cache_condition,
    ),
])

template.add_output([
    Output(
        "CachePort",
        Description="The port number for the cache node/cluster.",
        Value=cache_port,
        Condition=cache_condition,
    ),
])
