from troposphere import AWS_REGION, Equals, If, Not, Ref

from .template import template
from .utils import ParameterWithDefaults as Parameter

dont_create_value = "(none)"

in_govcloud_region = "InGovCloudRegion"
template.add_condition(in_govcloud_region, Equals(Ref(AWS_REGION), "us-gov-west-1"))
arn_prefix = If(in_govcloud_region, "arn:aws-us-gov", "arn:aws")

administrator_ip_address = Ref(template.add_parameter(
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
))

container_instance_type = Ref(template.add_parameter(
    Parameter(
        "ContainerInstanceType",
        Description="The application server instance type",
        Type="String",
        Default="t2.micro",
        AllowedValues=[
            't3.nano',
            't3.micro',
            't3.small',
            't3.medium',
            't3.large',
            't3.xlarge',
            't3.2xlarge',
            't2.nano',
            't2.micro',
            't2.small',
            't2.medium',
            't2.large',
            't2.xlarge',
            't2.2xlarge',
            'm5.large',
            'm5.xlarge',
            'm5.2xlarge',
            'm5.4xlarge',
            'm5.12xlarge',
            'm5.24xlarge',
            'm5d.large',
            'm5d.xlarge',
            'm5d.2xlarge',
            'm5d.4xlarge',
            'm5d.12xlarge',
            'm5d.24xlarge',
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
            'c5.large',
            'c5.xlarge',
            'c5.2xlarge',
            'c5.4xlarge',
            'c5.9xlarge',
            'c5.18xlarge',
            'c5d.large',
            'c5d.xlarge',
            'c5d.2xlarge',
            'c5d.4xlarge',
            'c5d.9xlarge',
            'c5d.18xlarge',
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
            'r5.large',
            'r5.xlarge',
            'r5.2xlarge',
            'r5.4xlarge',
            'r5.12xlarge',
            'r5.24xlarge',
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
    ),
    group="Application Server",
    label="Instance Type",
))

secret_key = Ref(template.add_parameter(
    Parameter(
        "SecretKey",
        Description="Application secret key for this stack (optional)",
        Type="String",
        NoEcho=True,
    ),
    group="Application Server",
    label="Secret Key",
))

use_aes256_encryption = Ref(template.add_parameter(
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
))
use_aes256_encryption_cond = "UseAES256EncryptionCond"
template.add_condition(use_aes256_encryption_cond, Equals(use_aes256_encryption, "true"))

cmk_arn = template.add_parameter(
    Parameter(
        "CmkArn",
        Description="KMS CMK ARN to encrypt stack resources.",
        Type="String",
    ),
    group="Global",
    label="Customer managed key ARN",
)

use_cmk_arn = "CmkArnCondition"
template.add_condition(use_cmk_arn, Not(Equals(Ref(cmk_arn), "")))
