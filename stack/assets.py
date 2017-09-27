import os

from troposphere import GetAtt, If, Join, Output, Ref, Split, iam
from troposphere.cloudfront import (
    DefaultCacheBehavior,
    Distribution,
    DistributionConfig,
    ForwardedValues,
    Origin,
    S3Origin
)
from troposphere.s3 import (
    Bucket,
    CorsConfiguration,
    CorsRules,
    Private,
    PublicRead,
    VersioningConfiguration
)

from .common import arn_prefix
from .domain import domain_name, domain_name_alternates, no_alt_domains
from .template import template

common_bucket_conf = dict(
    VersioningConfiguration=VersioningConfiguration(
        Status="Enabled"
    ),
    DeletionPolicy="Retain",
    CorsConfiguration=CorsConfiguration(
        CorsRules=[CorsRules(
            AllowedOrigins=Split(";", Join("", [
                "https://", domain_name,
                If(
                    no_alt_domains,
                    # if we don't have any alternate domains, return an empty string
                    "",
                    # otherwise, return the ';https://' that will be needed by the first domain
                    ";https://",
                ),
                # then, add all the alternate domains, joined together with ';https://'
                Join(";https://", domain_name_alternates),
                # now that we have a string of origins separated by ';', Split() is used to make it into a list again
            ])),
            AllowedMethods=[
                "POST",
                "PUT",
                "HEAD",
                "GET",
            ],
            AllowedHeaders=[
                "*",
            ],
        )],
    ),
)

# Create an S3 bucket that holds statics and media
assets_bucket = template.add_resource(
    Bucket(
        "AssetsBucket",
        AccessControl=PublicRead,
        **common_bucket_conf,
    )
)


# Output S3 asset bucket name
template.add_output(Output(
    "AssetsBucketDomainName",
    Description="Assets bucket domain name",
    Value=GetAtt(assets_bucket, "DomainName")
))


# Create an S3 bucket that holds user uploads or other non-public files
private_assets_bucket = template.add_resource(
    Bucket(
        "PrivateAssetsBucket",
        AccessControl=Private,
        **common_bucket_conf,
    )
)


# Output S3 asset bucket name
template.add_output(Output(
    "PrivateAssetsBucketDomainName",
    Description="Private assets bucket domain name",
    Value=GetAtt(private_assets_bucket, "DomainName")
))


# central asset management policy for use in instance roles
assets_management_policy = iam.Policy(
    PolicyName="AssetsManagementPolicy",
    PolicyDocument=dict(
        Statement=[
            dict(
                Effect="Allow",
                Action=["s3:ListBucket"],
                Resource=Join("", [arn_prefix, ":s3:::", Ref(assets_bucket)]),
            ),
            dict(
                Effect="Allow",
                Action=["s3:*"],
                Resource=Join("", [arn_prefix, ":s3:::", Ref(assets_bucket), "/*"]),
            ),
            dict(
                Effect="Allow",
                Action=["s3:ListBucket"],
                Resource=Join("", [arn_prefix, ":s3:::", Ref(private_assets_bucket)]),
            ),
            dict(
                Effect="Allow",
                Action=["s3:*"],
                Resource=Join("", [arn_prefix, ":s3:::", Ref(private_assets_bucket), "/*"]),
            ),
        ],
    ),
)


if os.environ.get('USE_GOVCLOUD') != 'on':
    # Create a CloudFront CDN distribution
    distribution = template.add_resource(
        Distribution(
            'AssetsDistribution',
            DistributionConfig=DistributionConfig(
                Origins=[Origin(
                    Id="Assets",
                    DomainName=GetAtt(assets_bucket, "DomainName"),
                    S3OriginConfig=S3Origin(
                        OriginAccessIdentity="",
                    ),
                )],
                DefaultCacheBehavior=DefaultCacheBehavior(
                    TargetOriginId="Assets",
                    ForwardedValues=ForwardedValues(
                        # Cache results *should* vary based on querystring (e.g., 'style.css?v=3')
                        QueryString=True,
                        # make sure headers needed by CORS policy above get through to S3
                        # http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/header-caching.html#header-caching-web-cors
                        Headers=[
                            'Origin',
                            'Access-Control-Request-Headers',
                            'Access-Control-Request-Method',
                        ],
                    ),
                    ViewerProtocolPolicy="allow-all",
                ),
                Enabled=True
            ),
        )
    )

    # Output CloudFront url
    template.add_output(Output(
        "AssetsDistributionDomainName",
        Description="The assest CDN domain name",
        Value=GetAtt(distribution, "DomainName")
    ))
else:
    distribution = None
