from troposphere import (
    Equals,
    Join,
    Parameter,
    Ref,
    Tags,
    transfer,
)

from .template import template

use_transfer_server = template.add_parameter(
    Parameter(
        "UseTransferServer",
        Description="Whether or not to create a AWS Transfer Server.",
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="SFTP",
    label="Enable SFTP Server",
)
use_transfer_server_condition = "UseTransferServer"
template.add_condition(use_transfer_server_condition, Equals(Ref(use_transfer_server), "true"))


transfer_server = transfer.Server(
    "TransferServer",
    template=template,
    Condition=use_transfer_server_condition,
    IdentityProviderType="SERVICE_MANAGED",
    EndpointType="PUBLIC",
    Tags=Tags(
        Name=Join("-", [Ref("AWS::StackName"), "sftp"]),
    ),
)
