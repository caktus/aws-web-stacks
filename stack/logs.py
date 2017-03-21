from troposphere import logs

from .template import template


container_log_group = logs.LogGroup(
    "ContainerLogs",
    template=template,
    RetentionInDays=365,
    DeletionPolicy="Retain",
)
