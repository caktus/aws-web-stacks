import os

from troposphere import AWS_REGION, Equals, If, Not, Ref

from .template import template
from .utils import ParameterWithDefaults as Parameter

dont_create_value = "(none)"

in_govcloud_region = "InGovCloudRegion"
template.add_condition(in_govcloud_region, Equals(Ref(AWS_REGION), "us-gov-west-1"))
arn_prefix = If(in_govcloud_region, "arn:aws-us-gov", "arn:aws")

administrator_ip_address = Ref(
    template.add_parameter(
        Parameter(
            "AdministratorIPAddress",
            Description="The IP address allowed to access containers. "
            "Defaults to TEST-NET-1 (ie, no valid IP)",
            Type="String",
            # RFC5737 - TEST-NET-1 reserved for documentation
            Default="192.0.2.0/24",
        ),
        group="Application Server",
        label="Admin IP Address",
    )
)

if "on" in set([os.getenv("USE_DOKKU"), os.getenv("USE_EB"), os.getenv("USE_ECS")]):
    secret_key = Ref(
        template.add_parameter(
            Parameter(
                "SecretKey",
                Description="Application secret key for this stack (optional)",
                Type="String",
                NoEcho=True,
            ),
            group="Application Server",
            label="Secret Key",
        )
    )

use_aes256_encryption = Ref(
    template.add_parameter(
        Parameter(
            "UseAES256Encryption",
            Description="Whether or not to use server side encryption for S3, EBS, and RDS. "
            "When true, encryption is enabled for all resources.",
            Type="String",
            AllowedValues=["true", "false"],
            Default="false",
        ),
        group="Global",
        label="Enable Encryption",
    )
)
use_aes256_encryption_cond = "UseAES256EncryptionCond"
template.add_condition(
    use_aes256_encryption_cond, Equals(use_aes256_encryption, "true")
)

cmk_arn = template.add_parameter(
    Parameter(
        "CustomerManagedCmkArn",
        Description="KMS CMK ARN to encrypt stack resources (except for public buckets).",
        Type="String",
        Default="",
    ),
    group="Global",
    label="Customer managed key ARN",
)

use_cmk_arn = "CmkArnCondition"
template.add_condition(use_cmk_arn, Not(Equals(Ref(cmk_arn), "")))
