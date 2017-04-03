from troposphere import (
    GetAtt, Join,
    Parameter, Ref
)
from .assets import (
    assets_bucket,
    distribution,
    private_assets_bucket,
)
from .cache import (
    redis_instance,
)
from .database import (
    db_instance,
    db_name,
    db_user,
    db_password,
)
from .domain import domain_name
from .template import template


container_instance_type = Ref(template.add_parameter(Parameter(
    "ContainerInstanceType",
    Description="The container instance type",
    Type="String",
    Default="t2.micro",
    AllowedValues=[
        't2.nano',
        't2.micro',
        't2.small',
        't2.medium',
        't2.large',
        't2.xlarge',
        't2.2xlarge',
        'm4.large',
        'm4.xlarge',
        'm4.2xlarge',
        'm4.4xlarge',
        'm4.10xlarge',
        'm4.16xlarge',
        'm3.medium',
        'm3.large',
        'm3.xlarge',
        'm3.2xlarge',
        'c4.large',
        'c4.xlarge',
        'c4.2xlarge',
        'c4.4xlarge',
        'c4.8xlarge',
        'c3.large',
        'c3.xlarge',
        'c3.2xlarge',
        'c3.4xlarge',
        'c3.8xlarge',
        'p2.xlarge',
        'p2.8xlarge',
        'p2.16xlarge',
        'g2.2xlarge',
        'g2.8xlarge',
        'x1.16large',
        'x1.32xlarge',
        'r4.large',
        'r4.xlarge',
        'r4.2xlarge',
        'r4.4xlarge',
        'r4.8xlarge',
        'r4.16xlarge',
        'r3.large',
        'r3.xlarge',
        'r3.2xlarge',
        'r3.4xlarge',
        'r3.8xlarge',
        'i3.large',
        'i3.xlarge',
        'i3.2xlarge',
        'i3.4xlarge',
        'i3.8xlarge',
        'i3.16large',
        'd2.xlarge',
        'd2.2xlarge',
        'd2.4xlarge',
        'd2.8xlarge',
        'f1.2xlarge',
        'f1.16xlarge',
    ]
)))

secret_key = Ref(template.add_parameter(Parameter(
    "SecretKey",
    Description="Application secret key",
    Type="String",
)))

environment_variables = [
    ("AWS_STORAGE_BUCKET_NAME", Ref(assets_bucket)),
    ("AWS_PRIVATE_STORAGE_BUCKET_NAME", Ref(private_assets_bucket)),
    ("DOMAIN_NAME", domain_name),
    ("SECRET_KEY", secret_key),
    ("DATABASE_URL", Join("", [
        "postgres://",
        Ref(db_user),
        ":",
        Ref(db_password),
        "@",
        GetAtt(db_instance, 'Endpoint.Address'),
        "/",
        Ref(db_name),
    ])),
    ("REDIS_URL", Join("", [
        "redis://",
        GetAtt(redis_instance, 'RedisEndpoint.Address'),
        ":",
        GetAtt(redis_instance, 'RedisEndpoint.Port'),
    ])),
]

if distribution:
    # not supported by GovCloud, so add it only if it was created
    environment_variables.append(
        ("CDN_DOMAIN_NAME", GetAtt(distribution, "DomainName"))
    )
