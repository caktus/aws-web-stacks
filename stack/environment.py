from troposphere import GetAtt, Join, Ref

from .assets import (
    assets_bucket,
    distribution,
    private_assets_bucket,
)
from .cache import (
    redis_instance,
)
from .common import (
    secret_key,
)
from .database import (
    db_instance,
    db_name,
    db_user,
    db_password,
)
from .domain import domain_name


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
