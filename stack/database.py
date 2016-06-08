from troposphere import (
    rds,
    Ref,
    AWS_STACK_NAME,
)

from .template import template
from .vpc import (
    container_a_subnet,
    container_b_subnet,
)


db_subnet_group = rds.DBSubnetGroup(
    "DatabaseSubnetGroup",
    template=template,
    DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
    SubnetIds=[Ref(container_a_subnet), Ref(container_b_subnet)],
)


db_instance = rds.DBInstance(
    "PostgreSQL",
    template=template,
    DBInstanceIdentifier=Ref(AWS_STACK_NAME),
    Engine="postgres",
    EngineVersion="9.4.5",
    MultiAZ=True,
    StorageType="gp2",
    DBSubnetGroupName=Ref(db_subnet_group),
    BackupRetentionPeriod="7",
)
