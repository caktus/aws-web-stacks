from troposphere import (
    And,
    Condition,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Parameter,
    Ref,
    Tags,
    iam,
    transfer,
)

from .common import arn_prefix, cmk_arn, use_aes256_encryption_cond, use_cmk_arn
from .template import template

use_sftp_server = template.add_parameter(
    Parameter(
        "UseSFTPServer",
        Description="Whether or not to set up an SFTP service.  If 'true', this will set up a transfer server and "
        "add an S3 bucket for its use, along with a role and policies for use when adding users.",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="SFTP",
    label="Enable SFTP Server",
)

use_sftp_condition = "UseSFTPServerCondition"
use_sftp_with_kms_condition = "UseSFTPWithKMSCondition"
use_sftp_without_kms_condition = "UseSFTPWithoutKMSCondition"

template.add_condition(use_sftp_condition, Equals(Ref(use_sftp_server), "true"))
template.add_condition(
    # If this condition is true, we need to create policies and roles that give
    # access to the customer KMS.
    use_sftp_with_kms_condition,
    And(
        Equals(Ref(use_sftp_server), "true"),
        Condition(use_aes256_encryption_cond),
        Condition(use_cmk_arn),
    ),
)
template.add_condition(
    # If this condition is true, we need to create policies and roles,
    # but they should not give access to customer KMS.
    use_sftp_without_kms_condition,
    And(Equals(Ref(use_sftp_server), "true"), Not(Condition(use_cmk_arn))),
)


transfer_server = transfer.Server(
    "TransferServer",
    template=template,
    Condition=use_sftp_condition,
    IdentityProviderType="SERVICE_MANAGED",
    EndpointType="PUBLIC",
    Tags=Tags(Name=Join("-", [Ref("AWS::StackName"), "sftp"])),
)
