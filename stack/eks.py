from troposphere import (
    And,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    NoValue,
    Output,
    Ref,
    Tags,
    ec2,
    eks,
    iam
)

from .common import cmk_arn
from .containers import (
    container_instance_role,
    container_instance_type,
    container_volume_size,
    desired_container_instances,
    max_container_instances
)
from .template import template
from .utils import ParameterWithDefaults as Parameter
from .vpc import (
    private_subnet_a,
    private_subnet_b,
    public_subnet_a,
    public_subnet_b,
    vpc
)

eks_service_role = iam.Role(
    # an IAM role that Kubernetes can assume to create AWS resources
    "EksServiceRole",
    template=template,
    AssumeRolePolicyDocument=dict(
        Statement=[
            dict(
                Effect="Allow",
                Principal=dict(Service=["eks.amazonaws.com"]),
                Action=["sts:AssumeRole"],
            )
        ]
    ),
    Path="/",
    ManagedPolicyArns=[
        "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
        "arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
    ],
)


eks_security_group = ec2.SecurityGroup(
    "EksClusterSecurityGroup",
    template=template,
    GroupDescription="EKS control plane security group.",
    VpcId=Ref(vpc),
    Tags=Tags(Name=Join("-", [Ref("AWS::StackName"), "eks-cluster"]),),
)

use_eks_encryption_config = Ref(template.add_parameter(
    Parameter(
        "EnableEksEncryptionConfig",
        Description="Use AWS Key Management Service (KMS) keys to provide envelope encryption of Kubernetes secrets. Depends on Customer managed key ARN.",  # noqa
        Type="String",
        AllowedValues=["true", "false"],
        Default="false",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Enable EKS EncryptionConfig",
))
use_eks_encryption_config_cond = "EnableEksEncryptionConfigCond"
template.add_condition(use_eks_encryption_config_cond, And(
    Equals(use_eks_encryption_config, "true"),
    Not(Equals(Ref(cmk_arn), ""))
))

# https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access
public_access_cidrs = Ref(template.add_parameter(
    Parameter(
        "EksPublicAccessCidrs",
        Description="The CIDR blocks that are allowed access to your cluster's public Kubernetes API server endpoint.",  # noqa
        Type="CommaDelimitedList",
        Default="",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Kubernetes API public access CIDRs",
))
restrict_eks_api_access_cond = "RestrictEksApiAccessCond"
template.add_condition(restrict_eks_api_access_cond, Not(Equals(Join("", public_access_cidrs), "")))

# Unlike most other resources in the stack, we specify the cluster name
# via a stack parameter so it's easy to find and so it cannot be accidentally
# recreated (for example if the ResourcesVpcConfig is changed).
cluster_name = Ref(template.add_parameter(
    Parameter(
        "EksClusterName",
        Description="The unique name to give to your cluster.",  # noqa
        Type="String",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Cluster name",
))

cluster = eks.Cluster(
    "EksCluster",
    template=template,
    Name=cluster_name,
    ResourcesVpcConfig=eks.ResourcesVpcConfig(
        SubnetIds=[
            # For load balancers
            Ref(public_subnet_a),
            Ref(public_subnet_b),
            # For worker nodes
            Ref(private_subnet_a),
            Ref(private_subnet_b),
        ],
        SecurityGroupIds=[Ref(eks_security_group)],
        EndpointPrivateAccess=If(restrict_eks_api_access_cond, True, False),
        EndpointPublicAccess=True,
        PublicAccessCidrs=If(restrict_eks_api_access_cond, public_access_cidrs, NoValue),
    ),
    EncryptionConfig=If(
        use_eks_encryption_config_cond,
        [eks.EncryptionConfig(Provider=eks.Provider(KeyArn=Ref(cmk_arn)), Resources=['secrets'])],
        NoValue
    ),
    RoleArn=GetAtt(eks_service_role, "Arn"),
)

eks.Nodegroup(
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-eks-nodegroup.html
    "Nodegroup",
    template=template,
    # For some reason, CloudFormation doesn't figure out that it needs to create
    # the cluster before the nodegroup that uses it.
    DependsOn=[cluster],
    # Required parameters:
    ClusterName=Ref(cluster),
    # The NodeRole must be specified as an ARN.
    NodeRole=GetAtt(container_instance_role, "Arn"),
    # The rest are optional.
    DiskSize=container_volume_size,
    InstanceTypes=[container_instance_type],
    ScalingConfig=eks.ScalingConfig(
        DesiredSize=desired_container_instances,
        MaxSize=max_container_instances,
        MinSize=2,
    ),
    Subnets=[Ref(private_subnet_a), Ref(private_subnet_b)],
)

# OUTPUTS
template.add_output(
    [
        Output(
            "ClusterEndpoint",
            Description="The connection endpoint for the EKS cluster API.",
            Value=GetAtt(cluster, "Endpoint"),
        ),
    ]
)
