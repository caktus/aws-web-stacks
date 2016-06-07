from troposphere.s3 import (
    Bucket,
    PublicRead,
    VersioningConfiguration,
)

from .template import template


# Create an S3 bucket that holds statics and media
assets_bucket = template.add_resource(
    Bucket(
        "AssetsBucket",
        AccessControl=PublicRead,
        VersioningConfiguration=VersioningConfiguration(
            Status="Enabled"
        ),
    )
)
