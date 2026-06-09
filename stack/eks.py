from troposphere import (
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

cluster_name = Ref(template.add_parameter(
    Parameter("EksClusterName", Description="The unique name to give to your cluster.", Type="String"),
    group="Elastic Kubernetes Service (EKS)",
    label="Cluster name",
))

# Construct cluster ARN manually (GetAtt(cluster, "Arn") unreliable in trust policies)
cluster_arn = Join(
    ":",
    [arn_prefix, "eks", Ref("AWS::Region"), Ref("AWS::AccountId"), "cluster", cluster_name],
)

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
)

# ---------------------------------------------------------------------------
# EKS add-ons: EBS CSI driver and Pod Identity Agent
# ---------------------------------------------------------------------------

# EBS CSI driver add-on for persistent volume support
ebs_csi_addon = eks.Addon(
    "EBSCSIAddon",
    template=template,
    AddonName="aws-ebs-csi-driver",
    ClusterName=Ref(cluster),
    ResolveConflicts="OVERWRITE",
)

# Pod Identity Agent add-on for workload identity (replaces IRSA)
pod_identity_addon = eks.Addon(
    "PodIdentityAddon",
    template=template,
    AddonName="eks-pod-identity-agent",
    ClusterName=Ref(cluster),
    ResolveConflicts="OVERWRITE",
)

# ---------------------------------------------------------------------------
# EBS CSI driver IAM role (Pod Identity)
# ---------------------------------------------------------------------------

ebs_csi_driver_role = iam.Role(
    "EBSCSIDriverRole",
    template=template,
    DependsOn=["EksCluster"],
    AssumeRolePolicyDocument=dict(
        Version="2012-10-17",
        Statement=[
            dict(
                Effect="Allow",
                Principal=dict(Service="pods.eks.amazonaws.com"),
                Action="sts:AssumeRole",
                Condition=dict(
                    ArnEquals={"aws:PrincipalArn": cluster_arn},
                ),
            ),
        ],
    ),
    Path="/",
    ManagedPolicyArns=[
        Join("", [arn_prefix, ":iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"]),
    ],
)

# ---------------------------------------------------------------------------
# EBS CSI driver pod identity association
# ---------------------------------------------------------------------------

ebs_csi_pod_identity = eks.PodIdentityAssociation(
    "EBSCSIPodIdentity",
    template=template,
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
        ImageId=Ref("AWS::NoValue"),
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
