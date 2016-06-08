from troposphere import (
    Parameter,
    Ref,
)

from .template import template


domain_name = Ref(template.add_parameter(Parameter(
    "DomainName",
    Description="The domain name",
    Type="String",
)))
