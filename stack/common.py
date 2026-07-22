from troposphere import AWS_REGION, Equals, If, Not, Or, Ref

from .template import template
from .utils import ParameterWithDefaults as Parameter

dont_create_value = "(none)"

instance_role = "ContainerInstanceRole"

in_govcloud_region = "InGovCloudRegion"
template.add_condition(in_govcloud_region, Or(
    Equals(Ref(AWS_REGION), "us-gov-west-1"),
    Equals(Ref(AWS_REGION), "us-gov-east-1"),
))
arn_prefix = If(in_govcloud_region, "arn:aws-us-gov", "arn:aws")

use_aes256_encryption = Ref(template.add_parameter(
    Parameter(
        "UseAES256Encryption",
        Description="Enable encryption (S3, EBS, RDS).",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="Global",
    label="Enable Encryption",
))
use_aes256_encryption_cond = "UseAES256EncryptionCond"
template.add_condition(use_aes256_encryption_cond, Equals(use_aes256_encryption, "true"))

cmk_arn = template.add_parameter(
    Parameter(
        "CustomerManagedCmkArn",
        Description="KMS CMK ARN for encryption (excludes public buckets).",
        Type="String",
        Default="",
    ),
    group="Global",
    label="Customer managed key ARN",
)

use_cmk_arn = "CmkArnCondition"
template.add_condition(use_cmk_arn, Not(Equals(Ref(cmk_arn), "")))
