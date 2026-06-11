from troposphere import (
    AWS_ACCOUNT_ID,
    AWS_REGION,
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

from .common import arn_prefix, cmk_arn, use_aes256_encryption, use_cmk_arn
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

# ---------------------------------------------------------------------------
# EKS service role
# ---------------------------------------------------------------------------

eks_service_role = iam.Role(
    "EksServiceRole",
    template=template,
    AssumeRolePolicyDocument=dict(
        Statement=[dict(Effect="Allow", Principal=dict(Service=["eks.amazonaws.com"]), Action=["sts:AssumeRole"])]
    ),
    Path="/",
    ManagedPolicyArns=[
        Join("", [arn_prefix, ":iam::aws:policy/AmazonEKSClusterPolicy"]),
        Join("", [arn_prefix, ":iam::aws:policy/AmazonEKSServicePolicy"]),
    ],
)

# ---------------------------------------------------------------------------
# EKS cluster security group
# ---------------------------------------------------------------------------

eks_security_group = ec2.SecurityGroup(
    "EksClusterSecurityGroup",
    template=template,
    GroupDescription="EKS control plane security group.",
    VpcId=Ref(vpc),
    Tags=Tags(Name=Join("-", [Ref("AWS::StackName"), "eks-cluster"])),
)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

public_access_cidrs = Ref(template.add_parameter(
    Parameter(
        "EksPublicAccessCidrs",
        Description="CIDR blocks allowed access to the public Kubernetes API endpoint.",
        Type="CommaDelimitedList",
        Default="",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Kubernetes API public access CIDRs",
))
restrict_eks_api_access_cond = "RestrictEksApiAccessCond"
template.add_condition(restrict_eks_api_access_cond, Not(Equals(Join("", public_access_cidrs), "")))

# Encryption config for Kubernetes secrets
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

cluster_name = Ref(template.add_parameter(
    Parameter("EksClusterName", Description="The unique name to give to your cluster.", Type="String"),
    group="Elastic Kubernetes Service (EKS)",
    label="Cluster name",
))

# Custom AMI support for the nodegroup
custom_eks_ami = Ref(template.add_parameter(
    Parameter(
        "CustomEKSAMI",
        Description="Custom AMI ID for the EKS node group. It is recommended not to set this value, as AWS will automatically select the most optimized image when CustomAMIImageType is specified.",  # noqa
        Type="String",
        Default="",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Custom EKS AMI",
))

use_custom_ami = "UseCustomAMI"
template.add_condition(use_custom_ami, Not(Equals(custom_eks_ami, "")))

custom_ami_image_type = Ref(template.add_parameter(
    Parameter(
        "CustomAMIImageType",
        Description="The image type to match the custom AMI. E.g., AL2023_x86_64_STANDARD, AL2_x86_64",
        Type="String",
        Default="",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Custom AMI Image Type",
))

use_custom_ami_type = "UseCustomAMIType"
template.add_condition(use_custom_ami_type, Not(Equals(custom_ami_image_type, "")))

cluster_version = Ref(template.add_parameter(
    Parameter("EksClusterVersion", Description="Kubernetes version for the EKS cluster.", Type="String", Default=""),
    group="Elastic Kubernetes Service (EKS)",
    label="Kubernetes Cluster Version",
))
use_cluster_version = "UseEksClusterVersion"
template.add_condition(use_cluster_version, Not(Equals(cluster_version, "")))

# ---------------------------------------------------------------------------
# EKS cluster
# ---------------------------------------------------------------------------

cluster = eks.Cluster(
    "EksCluster",
    template=template,
    Name=cluster_name,
    Version=If(use_cluster_version, cluster_version, Ref("AWS::NoValue")),
    # Use modern API authentication instead of the deprecated `aws-auth` ConfigMap
    AccessConfig=eks.AccessConfig(
        AuthenticationMode="API",
        BootstrapClusterCreatorAdminPermissions=True,
    ),
    Logging=eks.Logging(ClusterLogging=eks.ClusterLogging(EnabledTypes=[
        eks.LoggingTypeConfig(Type="api"),
        eks.LoggingTypeConfig(Type="audit"),
        eks.LoggingTypeConfig(Type="authenticator"),
    ])),
    ResourcesVpcConfig=eks.ResourcesVpcConfig(
        SubnetIds=[Ref(public_subnet_a), Ref(public_subnet_b), Ref(private_subnet_a), Ref(private_subnet_b)],
        SecurityGroupIds=[Ref(eks_security_group)],
        EndpointPrivateAccess=If(restrict_eks_api_access_cond, True, False),
        EndpointPublicAccess=True,
        PublicAccessCidrs=If(restrict_eks_api_access_cond, public_access_cidrs, NoValue),
    ),
    RoleArn=GetAtt(eks_service_role, "Arn"),
    EncryptionConfig=If(
        use_eks_encryption_config_cond,
        [eks.EncryptionConfig(Provider=eks.Provider(KeyArn=Ref(cmk_arn)), Resources=["secrets"])],
        NoValue,
    ),
)

# ---------------------------------------------------------------------------
# EKS add-ons: EBS CSI driver and Pod Identity Agent
# ---------------------------------------------------------------------------

# Pod Identity Agent add-on (must be installed before any associations)
pod_identity_addon = eks.Addon(
    "PodIdentityAddon",
    template=template,
    AddonName="eks-pod-identity-agent",
    ClusterName=Ref(cluster),
    ResolveConflicts="OVERWRITE",
)

# EBS CSI driver add-on for persistent volume support
ebs_csi_addon = eks.Addon(
    "EBSCSIAddon",
    template=template,
    AddonName="aws-ebs-csi-driver",
    ClusterName=Ref(cluster),
    ResolveConflicts="OVERWRITE",
)

# EBS CSI driver IAM role (Pod Identity)
# Trust policy must use StringEquals with a manually-constructed cluster ARN
# (GetAtt is unreliable in IAM trust policy documents)
ebs_csi_driver_role = iam.Role(
    "EBSCSIDriverRole",
    template=template,
    AssumeRolePolicyDocument=dict(
        Version="2012-10-17",
        Statement=[
            dict(
                Effect="Allow",
                Principal=dict(Service="pods.eks.amazonaws.com"),
                Action=["sts:AssumeRole", "sts:TagSession"],
                Condition=dict(
                    StringEquals={
                        "aws:SourceArn": Join("", [
                            arn_prefix, ":eks:", Ref(AWS_REGION), ":",
                            Ref(AWS_ACCOUNT_ID), ":cluster/", cluster_name,
                        ]),
                    },
                ),
            ),
        ],
    ),
    Path="/",
    ManagedPolicyArns=[
        Join("", [arn_prefix, ":iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"]),
    ],
)

# EBS CSI driver pod identity association
ebs_csi_pod_identity = eks.PodIdentityAssociation(
    "EBSCSIPodIdentity",
    template=template,
    DependsOn=["PodIdentityAddon", "EBSCSIAddon"],
    ClusterName=Ref(cluster),
    Namespace="kube-system",
    RoleArn=GetAtt(ebs_csi_driver_role, "Arn"),
    ServiceAccount="ebs-csi-controller-sa",
)

# ---------------------------------------------------------------------------
# Nodegroup launch template
# ---------------------------------------------------------------------------

nodegroup_launch_template = ec2.LaunchTemplate(
    "NodegroupLaunchTemplate",
    template=template,
    LaunchTemplateName=Join("-", [Ref("AWS::StackName"), "nodegroup-lt"]),
    LaunchTemplateData=ec2.LaunchTemplateData(
        ImageId=If(use_custom_ami, custom_eks_ami, Ref("AWS::NoValue")),
        BlockDeviceMappings=[
            ec2.LaunchTemplateBlockDeviceMapping(
                DeviceName="/dev/xvda",
                Ebs=ec2.EBSBlockDevice(
                    DeleteOnTermination=True,
                    Encrypted=use_aes256_encryption,
                    KmsKeyId=If(use_cmk_arn, Ref(cmk_arn), Ref("AWS::NoValue")),
                    VolumeType="gp3",
                    VolumeSize=container_volume_size,
                ),
            ),
        ],
        InstanceType=container_instance_type,
        MetadataOptions=ec2.MetadataOptions(HttpTokens="required", HttpPutResponseHopLimit=3),
        TagSpecifications=[
            ec2.TagSpecifications(
                ResourceType="instance",
                Tags=Tags(
                    Name=Join("-", [Ref("AWS::StackName"), "node"]),
                ),
            ),
        ],
    )
)

# ---------------------------------------------------------------------------
# Nodegroup
# ---------------------------------------------------------------------------

eks.Nodegroup(
    "Nodegroup",
    template=template,
    ClusterName=Ref(cluster),
    NodegroupName=Join("-", [Ref("AWS::StackName"), "nodegroup"]),
    NodeRole=GetAtt(container_instance_role, "Arn"),
    Version=If(use_cluster_version, cluster_version, Ref("AWS::NoValue")),
    LaunchTemplate=eks.LaunchTemplateSpecification(
        Id=Ref(nodegroup_launch_template),
        Version=GetAtt(nodegroup_launch_template, "LatestVersionNumber"),
    ),
    ScalingConfig=eks.ScalingConfig(
        DesiredSize=desired_container_instances,
        MaxSize=max_container_instances,
        MinSize=2,
    ),
    Subnets=[Ref(private_subnet_a), Ref(private_subnet_b)],
    # EKS Nodegroup Tags expects a dict, not the list format from Tags()
    Tags={
        "Name": Join("-", [Ref("AWS::StackName"), "nodegroup"]),
    },
    AmiType=If(use_custom_ami_type, custom_ami_image_type, Ref("AWS::NoValue")),
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

template.add_output(Output(
    "ClusterEndpoint",
    Description="EKS cluster API endpoint.",
    Value=GetAtt(cluster, "Endpoint"),
))
template.add_output(Output(
    "ClusterName",
    Description="EKS cluster name.",
    Value=cluster_name,
))
template.add_output(Output(
    "NodegroupName",
    Description="EKS managed nodegroup name.",
    Value=Join("-", [Ref("AWS::StackName"), "nodegroup"]),
))
template.add_output(Output(
    "ContainerInstanceRoleArn",
    Description="ARN of the IAM role assumed by EKS worker nodes.",
    Value=GetAtt(container_instance_role, "Arn"),
))
