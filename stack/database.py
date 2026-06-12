from collections import OrderedDict

from troposphere import (
    And,
    Condition,
    Equals,
    FindInMap,
    GetAtt,
    If,
    Join,
    Not,
    Output,
    Ref,
    Tags,
    ec2,
    rds
)

from .common import cmk_arn, use_aes256_encryption, use_cmk_arn
from .constants import dont_create_value
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import (
    private_subnet_a,
    private_subnet_a_cidr,
    private_subnet_b,
    private_subnet_b_cidr,
    vpc
)

rds_engine_map = OrderedDict([
    ("mysql", {"Port": "3306"}),
    ("postgres", {"Port": "5432"}),
])
template.add_mapping('RdsEngineMap', rds_engine_map)

# No AllowedValues - users can specify any RDS instance class directly.
# This avoids the need to update the template when new instance classes are released.
db_class = template.add_parameter(
    Parameter(
        "DatabaseClass",
        Default="db.t3.micro",
        Description="Database instance class. Use '(none)' to skip.",
        Type="String",
    ),
    group="Database",
    label="Instance Type",
)

db_condition = "DatabaseCondition"
template.add_condition(db_condition, Not(Equals(Ref(db_class), dont_create_value)))

db_replication = template.add_parameter(
    Parameter(
        "DatabaseReplication",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
        Description="Create a DB replica (fails if backup retention is 0).",
    ),
    group="Database",
    label="Database replication"
)
db_replication_condition = "DatabaseReplicationCondition"
template.add_condition(
    db_replication_condition,
    And(
        Condition(db_condition),
        Equals(Ref(db_replication), "true")
    )
)

db_engine = template.add_parameter(
    Parameter(
        "DatabaseEngine",
        Default="postgres",
        Description="Database engine.",
        Type="String",
        AllowedValues=list(rds_engine_map.keys()),
        ConstraintDescription="must select a valid database engine.",
    ),
    group="Database",
    label="Engine",
)

db_engine_version = template.add_parameter(
    Parameter(
        "DatabaseEngineVersion",
        Default="",
        Description="Database version.",
        Type="String",
    ),
    group="Database",
    label="Engine Version",
)

db_parameter_group_family = template.add_parameter(
    Parameter(
        "DatabaseParameterGroupFamily",
        Description="Parameter group family matching engine and version.",
        Type="String",
    ),
    group="Database",
    label="Parameter Group Family",
)

db_parameter_group = rds.DBParameterGroup(
    "DatabaseParameterGroup",
    template=template,
    Condition=db_condition,
    Description="Database parameter group.",
    Family=Ref(db_parameter_group_family),
    Parameters={},
)

db_name = template.add_parameter(
    Parameter(
        "DatabaseName",
        Default="app",
        Description="Database name.",
        Type="String",
        MinLength="1",
        MaxLength="64",
        AllowedPattern="[a-zA-Z][a-zA-Z0-9_]*",
        ConstraintDescription="must begin with a letter and contain only alphanumeric characters.",
    ),
    group="Database",
    label="Database Name",
)

db_user = template.add_parameter(
    Parameter(
        "DatabaseUser",
        Default="app",
        Description="DB admin username.",
        Type="String",
        MinLength="1",
        MaxLength="63",
        AllowedPattern="[a-zA-Z][a-zA-Z0-9_]*",
        ConstraintDescription="must begin with a letter and contain only alphanumeric characters and underscores.",
    ),
    group="Database",
    label="Username",
)

db_password = template.add_parameter(
    Parameter(
        "DatabasePassword",
        NoEcho=True,
        Description="Database password: 10-41 printable ASCII characters except /, \", or @.",
        Type="String",
        MinLength="10",
        MaxLength="41",
        AllowedPattern="[ !#-.0-?A-~]*",
        ConstraintDescription="10-41 printable ASCII characters except /, \", or @.",
    ),
    group="Database",
    label="Password",
)

db_allocated_storage = template.add_parameter(
    Parameter(
        "DatabaseAllocatedStorage",
        Default="20",
        Description="Storage size (Gb).",
        Type="Number",
        MinValue="5",
        MaxValue="1024",
        ConstraintDescription="must be between 5 and 1024 Gb.",
    ),
    group="Database",
    label="Storage (GB)",
)

db_multi_az = template.add_parameter(
    Parameter(
        "DatabaseMultiAZ",
        Default="false",
        Description="Enable MultiAZ.",
        Type="String",
        AllowedValues=["true", "false"],
        ConstraintDescription="must be true or false.",
    ),
    group="Database",
    label="Enable MultiAZ"
)

db_backup_retention_days = template.add_parameter(
    Parameter(
        "DatabaseBackupRetentionDays",
        Default="30",
        Description="Days to retain automated backups. 0 = backups disabled.",
        Type="Number",
        MinValue="0",
        MaxValue="35",
    ),
    group="Database",
    label="Backup Retention Days",
)

db_logging = template.add_parameter(
    Parameter(
        "DatabaseCloudWatchLogTypes",
        Default="",
        Description="RDS log types for CloudWatch.",
        Type="CommaDelimitedList",
    ),
    group="Database",
    label="Database Log Types",
)

db_logging_condition = "DatabaseLoggingCondition"
template.add_condition(db_logging_condition, Not(Equals(Join(",", Ref(db_logging)), "")))


db_security_group = ec2.SecurityGroup(
    'DatabaseSecurityGroup',
    template=template,
    GroupDescription="Database security group.",
    Condition=db_condition,
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            ToPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            CidrIp=Ref(private_subnet_a_cidr),
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            ToPort=FindInMap("RdsEngineMap", Ref(db_engine), "Port"),
            CidrIp=Ref(private_subnet_b_cidr),
        ),
    ],
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "rds"]),
    ),
)

db_subnet_group = rds.DBSubnetGroup(
    "DatabaseSubnetGroup",
    template=template,
    Condition=db_condition,
    DBSubnetGroupDescription="DB subnet group",
    SubnetIds=[Ref(private_subnet_a), Ref(private_subnet_b)],
)

db_instance = rds.DBInstance(
    "DatabaseInstance",
    template=template,
    DBName=Ref(db_name),
    Condition=db_condition,
    AllocatedStorage=Ref(db_allocated_storage),
    DBInstanceClass=Ref(db_class),
    Engine=Ref(db_engine),
    EngineVersion=Ref(db_engine_version),
    MultiAZ=Ref(db_multi_az),
    StorageEncrypted=use_aes256_encryption,
    StorageType="gp2",
    MasterUsername=Ref(db_user),
    MasterUserPassword=Ref(db_password),
    DBParameterGroupName=Ref(db_parameter_group),
    DBSubnetGroupName=Ref(db_subnet_group),
    VPCSecurityGroups=[Ref(db_security_group)],
    BackupRetentionPeriod=Ref(db_backup_retention_days),
    EnableCloudwatchLogsExports=If(db_logging_condition, Ref(db_logging), Ref("AWS::NoValue")),
    DeletionPolicy="Snapshot",
    UpdateReplacePolicy="Snapshot",
    KmsKeyId=If(use_cmk_arn, Ref(cmk_arn), Ref("AWS::NoValue")),
)

db_replica = rds.DBInstance(
    "DatabaseReplica",
    template=template,
    Condition=db_replication_condition,
    SourceDBInstanceIdentifier=Ref(db_instance),
    DBInstanceClass=Ref(db_class),
    Engine=Ref(db_engine),
    VPCSecurityGroups=[Ref(db_security_group)],
    DeletionPolicy="Snapshot",
    UpdateReplacePolicy="Snapshot",
)

db_url = If(
    db_condition,
    Join("", [
        Ref(db_engine),
        "://",
        Ref(db_user),
        ":_PASSWORD_@",
        GetAtt(db_instance, 'Endpoint.Address'),
        ":",
        GetAtt(db_instance, 'Endpoint.Port'),
        "/",
        Ref(db_name),
    ]),
    "",
)

db_replica_url = If(
    db_replication_condition,
    Join("", [
        Ref(db_engine),
        "://",
        Ref(db_user),
        ":_PASSWORD_@",
        GetAtt(db_replica, 'Endpoint.Address'),
        ":",
        GetAtt(db_replica, 'Endpoint.Port'),
        "/",
        Ref(db_name),
    ]),
    "",
)

template.add_output([
    Output(
        "DatabaseURL",
        Description="DB connection URL (no password).",
        Value=db_url,
        Condition=db_condition,
    ),
])

template.add_output([
    Output(
        "DatabaseReplicaURL",
        Description="DB replica URL (no password).",
        Value=db_replica_url,
        Condition=db_replication_condition,
    ),
])

template.add_output([
    Output(
        "DatabasePort",
        Description="DB port.",
        Value=GetAtt(db_instance, 'Endpoint.Port'),
        Condition=db_condition,
    ),
])

template.add_output([
    Output(
        "DatabaseAddress",
        Description="DB endpoint.",
        Value=GetAtt(db_instance, 'Endpoint.Address'),
        Condition=db_condition,
    ),
])

template.add_output([
    Output(
        "DatabaseReplicaAddress",
        Description="DB replica endpoint.",
        Value=GetAtt(db_replica, "Endpoint.Address"),
        Condition=db_replication_condition
    ),
])
