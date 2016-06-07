from troposphere import (
    Output,
    GetAtt,
)

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
        DeletionPolicy="Retain",
    )
)


# Output S3 asset bucket name
template.add_output(Output(
    "AssetsBucketDomainName",
    Description="Assets bucket domain name",
    Value=GetAtt(assets_bucket, "DomainName")
))
