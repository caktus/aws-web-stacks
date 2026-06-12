from troposphere import Equals, If, Join, Ref, Split

from .template import template
from .utils import ParameterWithDefaults as Parameter

domain_name = Ref(template.add_parameter(
    Parameter(
        "DomainName",
        Description="Domain name.",
        Type="String",
    ),
    group="Global",
    label="Domain Name",
))

domain_name_alternates = Ref(template.add_parameter(
    Parameter(
        "DomainNameAlternates",
        Description="Alternate FQDNs for the SSL certificate.",
        Type="CommaDelimitedList",
    ),
    group="Global",
    label="Alternate Domain Names",
))

no_alt_domains = "NoAlternateDomains"
template.add_condition(
    no_alt_domains,
    # Equals() only supports strings, so convert domain_name_alternates to one first
    Equals(Join("", domain_name_alternates), ""),
)

all_domains_list = Split(";", Join("", [
    domain_name,
    If(
        no_alt_domains,
        # if we don't have any alternate domains, return an empty string
        "",
        # otherwise, return the ';' that will be needed by the first domain
        ";",
    ),
    # then, add all the alternate domains, joined together with ';
    Join(";", domain_name_alternates),
    # now that we have a string of origins separated by ';', Split() is used to make it into a list again
]))
