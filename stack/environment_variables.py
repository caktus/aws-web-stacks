from troposphere import (
    GetAtt, Join,
    Parameter, Ref
)
from .assets import (
    assets_bucket,
    distribution,
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


secret_key = Ref(template.add_parameter(Parameter(
    "SecretKey",
    Description="Application secret key",
    Type="String",
)))

environment_variables = [
    ("AWS_STORAGE_BUCKET_NAME", Ref(assets_bucket)),
    ("CDN_DOMAIN_NAME", GetAtt(distribution, "DomainName")),
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
