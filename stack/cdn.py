from troposphere import (
    AWS_REGION,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Output,
    Parameter,
    Ref,
    iam
)
from troposphere.cloudfront import (
    CacheCookiesConfig,
    CacheHeadersConfig,
    CachePolicy,
    CachePolicyConfig,
    CacheQueryStringsConfig,
    CustomOriginConfig,
    DefaultCacheBehavior,
    Distribution,
    DistributionConfig,
    Origin,
    ParametersInCacheKeyAndForwardedToOrigin,
    ViewerCertificate
)

from .certificates import application as app_certificate
from .domain import all_domains_list
from .template import template

origin_domain_name = Ref(
    template.add_parameter(
        Parameter(
            "AppCloudFrontOriginDomainName",
            Description="Domain name of the origin server",
            Type="String",
            Default="",
        ),
        group="Application Server",
        label="CloudFront Origin Domain Name",
    )
)

instance_role = Ref(
    template.add_parameter(
        Parameter(
            "AppCloudFrontRoleArn",
            Description="ARN of the role to add IAM permissions for invalidating this distribution",
            Type="String",
            Default="",
        ),
        group="Application Server",
        label="CloudFront Role ARN",
    )
)

origin_request_policy_id = Ref(
    template.add_parameter(
        Parameter(
            "AppCloudFrontOriginRequestPolicyId",
            Description="The unique identifier of the origin request policy to attach to the app cache behavior",
            Type="String",
            # https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-origin-request-policies.html#managed-origin-request-policy-all-viewer
            # Recommended for custom origins
            Default="216adef6-5c7f-47e4-b989-5492eafa07d3",
        ),
        group="Application Server",
        label="Origin Request Policy ID",
    )
)

app_protocol_policy = template.add_parameter(
    Parameter(
        "AppCloudFrontProtocolPolicy",
        Description="The protocols allowed by the application server's CloudFront distribution. See: "
        "http://docs.aws.amazon.com/cloudfront/latest/APIReference/API_DefaultCacheBehavior.html",
        Type="String",
        AllowedValues=["redirect-to-https", "https-only", "allow-all"],
        Default="redirect-to-https",
    ),
    group="Application Server",
    label="CloudFront Protocol Policy",
)

app_forwarded_headers = template.add_parameter(
    Parameter(
        "AppCloudFrontForwardedHeaders",
        Description=(
            "The CachePolicy headers that will be forwarded to the origin and used in the cache key. "
            "The 'Host' header is required for SSL on an Elastic Load Balancer, but it "
            "should NOT be passed to a Lambda Function URL."
        ),
        Type="CommaDelimitedList",
        Default="",
    ),
    group="Application Server",
    label="CloudFront Forwarded Headers",
)
app_forwarded_headers_condition = "AppCloudFrontForwardedHeadersCondition"
template.add_condition(
    app_forwarded_headers_condition,
    Not(Equals(Join("", Ref(app_forwarded_headers)), "")),
)

# Currently, you can specify only certificates that are in the US East (N. Virginia) region.
# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distributionconfig-viewercertificate.html
us_east_1_condition = "UsEast1Condition"
template.add_condition(
    us_east_1_condition,
    Equals(Ref(AWS_REGION), "us-east-1"),
)

app_certificate_arn = template.add_parameter(
    Parameter(
        "AppCloudFrontCertArn",
        Description="If your stack is NOT in the us-east-1 you must manually create an ACM certificate for "
        "your application domain in the us-east-1 region and provide its ARN here.",
        Type="String",
    ),
    group="Application Server",
    label="CloudFront SSL Certificate ARN",
)
app_certificate_arn_condition = "AppCloudFrontCertArnCondition"
template.add_condition(
    app_certificate_arn_condition, Not(Equals(Ref(app_certificate_arn), ""))
)

cache_policy = template.add_resource(
    CachePolicy(
        "AppCloudFrontCachePolicy",
        CachePolicyConfig=CachePolicyConfig(
            Name="AppCachePolicy",
            DefaultTTL=86400,  # 1 day
            MaxTTL=31536000,  # 1 year
            MinTTL=0,
            ParametersInCacheKeyAndForwardedToOrigin=ParametersInCacheKeyAndForwardedToOrigin(
                CookiesConfig=CacheCookiesConfig(
                    CookieBehavior="none",
                ),
                EnableAcceptEncodingGzip=True,
                EnableAcceptEncodingBrotli=True,
                HeadersConfig=If(
                    app_forwarded_headers_condition,
                    CacheHeadersConfig(
                        # Determines whether any HTTP headers are included in the
                        # cache key and in requests that CloudFront sends to the
                        # origin
                        # * whitelist: Only the HTTP headers that are listed in the
                        #   Headers type are included in the cache key and in
                        #   requests that CloudFront sends to the origin.
                        HeaderBehavior="whitelist",
                        Headers=Ref(app_forwarded_headers),
                    ),
                    CacheHeadersConfig(
                        HeaderBehavior="none",
                    ),
                ),
                QueryStringsConfig=CacheQueryStringsConfig(
                    # Determines whether any URL query strings in viewer
                    # requests are included in the cache key and in requests
                    # that CloudFront sends to the origin
                    QueryStringBehavior="all",
                ),
            ),
        ),
    )
)

# Create a CloudFront CDN distribution
app_distribution = template.add_resource(
    Distribution(
        "AppCloudFrontDistribution",
        DistributionConfig=DistributionConfig(
            Aliases=all_domains_list,
            HttpVersion="http2",
            # If we're in us-east-1, use the application certificate tied to the load balancer, otherwise,
            # use the manually-created cert
            ViewerCertificate=If(
                us_east_1_condition,
                ViewerCertificate(
                    AcmCertificateArn=app_certificate,
                    SslSupportMethod="sni-only",
                    # Default/recommended on the AWS console, as of May, 2023
                    MinimumProtocolVersion="TLSv1.2_2021",
                ),
                If(
                    app_certificate_arn_condition,
                    ViewerCertificate(
                        AcmCertificateArn=Ref(app_certificate_arn),
                        SslSupportMethod="sni-only",
                        MinimumProtocolVersion="TLSv1.2_2021",
                    ),
                    Ref("AWS::NoValue"),
                ),
            ),
            Origins=[
                Origin(
                    Id="ApplicationServer",
                    DomainName=origin_domain_name,
                    CustomOriginConfig=CustomOriginConfig(
                        OriginProtocolPolicy="https-only",
                    ),
                )
            ],
            DefaultCacheBehavior=DefaultCacheBehavior(
                TargetOriginId="ApplicationServer",
                Compress="true",
                AllowedMethods=[
                    "DELETE",
                    "GET",
                    "HEAD",
                    "OPTIONS",
                    "PATCH",
                    "POST",
                    "PUT",
                ],
                CachePolicyId=Ref(cache_policy),
                CachedMethods=["HEAD", "GET"],
                OriginRequestPolicyId=origin_request_policy_id,
                ViewerProtocolPolicy=Ref(app_protocol_policy),
            ),
            Enabled=True,
        ),
    )
)

invalidation_policy = template.add_resource(
    iam.PolicyType(
        "AppCloudFrontInvalidationPolicy",
        PolicyName="AppCloudFrontInvalidationPolicy",
        PolicyDocument=dict(
            Statement=[
                dict(
                    Effect="Allow",
                    Action=[
                        "cloudfront:GetDistribution",
                        "cloudfront:GetDistributionConfig",
                        "cloudfront:ListDistributions",
                        "cloudfront:ListCloudFrontOriginAccessIdentities",
                        "cloudfront:CreateInvalidation",
                        "cloudfront:GetInvalidation",
                        "cloudfront:ListInvalidations",
                    ],
                    Resource="*",
                    # TODO: if/when CloudFront supports resource-level IAM permissions, enable them, e.g.:
                    # Resource=Join("", [arn_prefix, ":cloudfront:::distribution/", Ref(app_distribution)]),
                    # See: https://stackoverflow.com/a/29563986/166053
                ),
            ],
        ),
        Roles=[instance_role],
    )
)

# Output CloudFront url
template.add_output(
    Output(
        "AppCloudFrontDomainName",
        Description="The app CDN domain name",
        Value=GetAtt(app_distribution, "DomainName"),
    )
)
