from troposphere import (
    And,
    Condition,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Or,
    Output,
    Ref,
    Tags,
    constants,
    ec2,
    elasticache
)

from .common import (
    cmk_arn,
    dont_create_value,
    use_aes256_encryption,
    use_aes256_encryption_cond,
    use_cmk_arn
)
from .security_groups import container_security_group
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import (
    primary_az,
    private_subnet_a,
    private_subnet_b,
    secondary_az,
    vpc
)

NODE_TYPES = [
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
]

cache_node_type = template.add_parameter(
    Parameter(
        "CacheNodeType",
        Default=dont_create_value,
        Description="Cache instance type",
        Type="String",
        AllowedValues=NODE_TYPES,
        ConstraintDescription="must select a valid cache node type.",
    ),
    group="Memcached",
    label="Instance Type",
)

using_memcached_condition = "UsingMemcached"
template.add_condition(using_memcached_condition, Not(Equals(Ref(cache_node_type), dont_create_value)))

redis_node_type = template.add_parameter(
    Parameter(
        "RedisNodeType",
        Default=dont_create_value,
        Description="Redis instance type",
        Type="String",
        AllowedValues=NODE_TYPES,
        ConstraintDescription="must select a valid cache node type.",
    ),
    group="Redis",
    label="Instance Type",
)

using_redis_condition = "UsingRedis"
template.add_condition(using_redis_condition, Not(Equals(Ref(redis_node_type), dont_create_value)))

# Parameter constraints (MinLength, AllowedPattern, etc.) don't allow a blank value,
# so we use a special "blank" do-not-create value
auth_token_dont_create_value = 'DO_NOT_CREATE_AUTH_TOKEN'

redis_auth_token = template.add_parameter(
    Parameter(
        "RedisAuthToken",
        NoEcho=True,
        Default=auth_token_dont_create_value,
        Description="The password used to access a Redis ReplicationGroup (required for HIPAA).",
        Type="String",
        MinLength="16",
        MaxLength="128",
        AllowedPattern="[ !#-.0-?A-~]*",  # see http://www.catonmat.net/blog/my-favorite-regex/
        ConstraintDescription="must consist of 16-128 printable ASCII "
                              "characters except \"/\", \"\"\", or \"@\"."
    ),
    group="Redis",
    label="AuthToken",
)

using_auth_token_condition = "AuthTokenCondition"
template.add_condition(using_auth_token_condition,
                       Not(Equals(Ref(redis_auth_token), auth_token_dont_create_value)))

redis_version = template.add_parameter(
    Parameter(
        "RedisVersion",
        Default="",
        Description="Redis version to use. See available versions: aws elasticache describe-cache-engine-versions",
        Type="String",
    ),
    group="Redis",
    label="Redis Version",
)

redis_num_cache_clusters = Ref(template.add_parameter(
    Parameter(
        "RedisNumCacheClusters",
        Description="The number of clusters this replication group initially has.",
        Type="Number",
        Default="1",
    ),
    group="Redis",
    label="Number of node groups",
))

redis_snapshot_retention_limit = Ref(template.add_parameter(
    Parameter(
        "RedisSnapshotRetentionLimit",
        Default="0",
        Description="The number of days for which ElastiCache retains automatic snapshots before deleting them."
                    "For example, if you set SnapshotRetentionLimit to 5, a snapshot that was taken today is "
                    "retained for 5 days before being deleted. 0 = automatic backups are disabled for this cluster.",
        Type="Number",
    ),
    group="Redis",
    label="Snapshow retention limit",
))

redis_automatic_failover = template.add_parameter(
    Parameter(
        "RedisAutomaticFailover",
        Description="Specifies whether a read-only replica is automatically promoted to read/write primary if "
                    "the existing primary fails.",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="Redis",
    label="Enable automatic failover",
)
redis_uses_automatic_failover = "RedisAutomaticFailoverCondition"
template.add_condition(redis_uses_automatic_failover, Equals(Ref(redis_automatic_failover), "true"))

secure_redis_condition = "SecureRedisCondition"
template.add_condition(secure_redis_condition,
                       And(Condition(using_redis_condition), Condition(use_aes256_encryption_cond)))

using_either_cache_condition = "EitherCacheCondition"
template.add_condition(using_either_cache_condition,
                       Or(Condition(using_memcached_condition), Condition(using_redis_condition)))

# Subnet and security group shared by both clusters

cache_subnet_group = elasticache.SubnetGroup(
    "CacheSubnetGroup",
    template=template,
    Description="Subnets available for the cache instance",
    Condition=using_either_cache_condition,
    SubnetIds=[Ref(private_subnet_a), Ref(private_subnet_b)],
)

cache_security_group = ec2.SecurityGroup(
    'CacheSecurityGroup',
    template=template,
    GroupDescription="Cache security group.",
    Condition=using_either_cache_condition,
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        If(
            using_memcached_condition,
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort=constants.MEMCACHED_PORT,
                ToPort=constants.MEMCACHED_PORT,
                SourceSecurityGroupId=Ref(container_security_group),
            ),
            Ref("AWS::NoValue"),
        ),
        If(
            using_redis_condition,
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort=constants.REDIS_PORT,
                ToPort=constants.REDIS_PORT,
                SourceSecurityGroupId=Ref(container_security_group),
            ),
            Ref("AWS::NoValue"),
        ),
    ],
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "cache"]),
    ),
)

cache_cluster = elasticache.CacheCluster(
    "CacheCluster",
    template=template,
    Engine="memcached",
    CacheNodeType=Ref(cache_node_type),
    Condition=using_memcached_condition,
    NumCacheNodes=1,
    Port=constants.MEMCACHED_PORT,
    VpcSecurityGroupIds=[Ref(cache_security_group)],
    CacheSubnetGroupName=Ref(cache_subnet_group),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "cache"]),
    ),
)

redis_replication_group = elasticache.ReplicationGroup(
    "RedisReplicationGroup",
    template=template,
    AtRestEncryptionEnabled=use_aes256_encryption,
    AutomaticFailoverEnabled=Ref(redis_automatic_failover),
    AuthToken=If(using_auth_token_condition, Ref(redis_auth_token), Ref("AWS::NoValue")),
    Engine="redis",
    EngineVersion=Ref(redis_version),
    CacheNodeType=Ref(redis_node_type),
    CacheSubnetGroupName=Ref(cache_subnet_group),
    Condition=using_redis_condition,
    NumCacheClusters=redis_num_cache_clusters,
    Port=constants.REDIS_PORT,
    PreferredCacheClusterAZs=If(redis_uses_automatic_failover,
                                [Ref(primary_az), Ref(secondary_az)],
                                Ref("AWS::NoValue")),
    ReplicationGroupDescription="Redis ReplicationGroup",
    SecurityGroupIds=[Ref(cache_security_group)],
    SnapshotRetentionLimit=redis_snapshot_retention_limit,
    TransitEncryptionEnabled=use_aes256_encryption,
    KmsKeyId=If(use_cmk_arn, Ref(cmk_arn), Ref("AWS::NoValue")),
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "redis"]),
    ),
)

cache_address = If(
    using_memcached_condition,
    GetAtt(cache_cluster, 'ConfigurationEndpoint.Address'),
    "",
)

cache_port = If(
    using_memcached_condition,
    GetAtt(cache_cluster, 'ConfigurationEndpoint.Port'),
    "",
)

cache_url = If(
    using_memcached_condition,
    Join("", [
        "memcached://",
        cache_address,
        ":",
        cache_port,
    ]),
    "",
)

template.add_output([
    Output(
        "CacheAddress",
        Description="The DNS address for the cache node/cluster.",
        Value=cache_address,
        Condition=using_memcached_condition,
    ),
    Output(
        "CachePort",
        Description="The port number for the cache node/cluster.",
        Value=GetAtt(cache_cluster, 'ConfigurationEndpoint.Port'),
        Condition=using_memcached_condition,
    ),
    Output(
        "CacheURL",
        Description="URL to connect to the cache node/cluster.",
        Value=cache_url,
        Condition=using_memcached_condition,
    ),
])

redis_address = If(
    using_redis_condition,
    GetAtt(redis_replication_group, 'PrimaryEndPoint.Address'),
    "",
)

redis_port = If(
    using_redis_condition,
    GetAtt(redis_replication_group, 'PrimaryEndPoint.Port'),
    "",
)

redis_url = If(
    using_redis_condition,
    Join("", [
        "redis",
        If(secure_redis_condition, "s", ""),
        "://",
        If(using_auth_token_condition, ":_PASSWORD_@", ""),
        redis_address,
        ":",
        redis_port,
    ]),
    "",
)

template.add_output([
    Output(
        "RedisAddress",
        Description="The DNS address for the Redis node/cluster.",
        Value=redis_address,
        Condition=using_redis_condition,
    ),
    Output(
        "RedisPort",
        Description="The port number for the Redis node/cluster.",
        Value=redis_port,
        Condition=using_redis_condition,
    ),
    Output(
        "RedisURL",
        Description="URL to connect to the Redis node/cluster.",
        Value=redis_url,
        Condition=using_redis_condition,
    ),
])
