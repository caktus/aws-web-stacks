from troposphere import Join, iam, logs

from .common import arn_prefix
from .template import template

container_log_group = logs.LogGroup(
    "ContainerLogs",
    template=template,
    RetentionInDays=365,
    DeletionPolicy="Retain",
)


logging_policy = iam.Policy(
    PolicyName="LoggingPolicy",
    PolicyDocument=dict(
        Statement=[dict(
            Effect="Allow",
            Action=[
                "logs:Create*",
                "logs:PutLogEvents",
            ],
            Resource=Join("", [
                arn_prefix,
                ":logs:*:*:*",  # allow logging to any log group
            ]),
        )],
    ),
)
