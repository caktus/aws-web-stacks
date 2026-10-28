# Shared definitions for the separate "eks-*-updates" CloudFormation template
# (stacks/eks-*-updates.yaml).
#
# The scheduled EKS update resources (SSM automation role, the custom addon
# update document, and both SSM associations) live in their own cloudformation stack.
# This stack is deployed after the main stack and references the cluster/nodegroup by name.
from troposphere import AWS_REGION, Equals, If, Or, Ref

from .template import updates_template
from .utils import ParameterWithDefaults as Parameter

in_govcloud_region = "InGovCloudRegion"
updates_template.add_condition(in_govcloud_region, Or(
    Equals(Ref(AWS_REGION), "us-gov-west-1"),
    Equals(Ref(AWS_REGION), "us-gov-east-1"),
))
arn_prefix = If(in_govcloud_region, "arn:aws-us-gov", "arn:aws")

# Name of the cluster created by the main stack (its EksClusterName parameter).
eks_cluster_name = Ref(updates_template.add_parameter(
    Parameter(
        "EksClusterName",
        Description="Name of the EKS cluster created by the main stack.",
        Type="String",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Cluster name",
))

# Name of the nodegroup created by the main stack (its NodegroupName output).
# This is dynamically determined and passed when running the deploy-cf-stack.yaml playbook
eks_nodegroup_name = Ref(updates_template.add_parameter(
    Parameter(
        "EksNodegroupName",
        Description="Name of the nodegroup created by the main stack.",
        Type="String",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Nodegroup name",
))
