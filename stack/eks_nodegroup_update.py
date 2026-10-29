# Scheduled EKS managed nodegroup updates (AMI / K8s version) using an SSM
# Association and the AWS-UpdateEKSManagedNodeGroup runbook.
#
# Generated as part of the separate "eks-*-updates" template (see stack/eks_updates.py);
# the cluster and nodegroup are referenced by name via parameters.
from troposphere import GetAtt, Join, Ref, iam, ssm

from .eks_updates import arn_prefix, eks_cluster_name, eks_nodegroup_name
from .template import updates_template
from .utils import ParameterWithDefaults as Parameter

update_schedule = Ref(updates_template.add_parameter(
    Parameter(
        "EksNodegroupUpdateSchedule",
        Description="SSM cron schedule (UTC) for the nodegroup upgrade.",
        Type="String",
        Default="cron(30 10 ? * TUE#1 *)",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Upgrade schedule (UTC cron)",
))

# ---------------------------------------------------------------------------
# SSM Automation service role
# ---------------------------------------------------------------------------

ssm_nodegroup_update_role = iam.Role(
    "SSMNodegroupUpdateServiceRole",
    template=updates_template,
    AssumeRolePolicyDocument=dict(
        Statement=[dict(
            Effect="Allow",
            Principal=dict(Service="ssm.amazonaws.com"),
            Action=["sts:AssumeRole"],
        )]
    ),
    Path="/",
    ManagedPolicyArns=[
        Join("", [arn_prefix, ":iam::aws:policy/service-role/AmazonSSMAutomationRole"]),
    ],
    Policies=[
        iam.Policy(
            PolicyName="EKSNodegroupUpdatePolicy",
            PolicyDocument=dict(
                Statement=[
                    dict(
                        Effect="Allow",
                        Action=[
                            "eks:DescribeCluster",
                            "eks:DescribeNodegroup",
                            "eks:UpdateNodegroupVersion",
                            "eks:UpdateNodegroupConfig",
                            "eks:DescribeUpdate",
                            "eks:DescribeAddon",
                            "eks:DescribeAddonVersions",
                            "eks:ListAddons",
                            "eks:UpdateAddon",
                        ],
                        Resource="*",
                    ),
                    dict(
                        Effect="Allow",
                        Action=[
                            "ec2:DescribeLaunchTemplates",
                            "ec2:DescribeLaunchTemplateVersions",
                            "ec2:CreateLaunchTemplateVersion",
                            "ec2:RunInstances",
                        ],
                        Resource="*",
                    ),
                    dict(
                        # UpdateAddon requires iam:PassRole on an addon's
                        # service account role when it is carried through
                        # (the addon-update script does this). Scoped to
                        # EKS addon roles, which are currently named AmazonEKS*;
                        # can be widened to "*" if an addon uses another name.
                        Effect="Allow",
                        Action=["iam:PassRole"],
                        Resource=Join("", [arn_prefix, ":iam::", Ref("AWS::AccountId"), ":role/AmazonEKS*"]),
                    ),
                    dict(
                        Effect="Allow",
                        Action=[
                            "ssm:StartAutomationExecution",
                            "ssm:GetAutomationExecution",
                            "ssm:DescribeAutomationExecutions",
                            "ssm:DescribeAutomationStepExecutions",
                        ],
                        Resource="*",
                    ),
                ],
            ),
        ),
    ],
)

# ---------------------------------------------------------------------------
# Scheduled automation association
# ---------------------------------------------------------------------------

ssm.Association(
    "EKSNodegroupUpdateAssociation",
    template=updates_template,
    Name="AWS-UpdateEKSManagedNodeGroup",
    AssociationName=Join("", ["EKS-NodegroupUpdate-", Ref("AWS::StackName")]),
    Parameters=dict(
        ClusterName=[eks_cluster_name],
        NodeGroupName=[eks_nodegroup_name],
        UpdateType=["Update Node Group Version"],
        ForceUpdate=["false"],
        AutomationAssumeRole=[GetAtt(ssm_nodegroup_update_role, "Arn")],
    ),
    ScheduleExpression=update_schedule,
    # Don't fire immediately on association creation/update - only at the
    # scheduled cron slots, so a template deploy never triggers a live
    # nodegroup upgrade.
    ApplyOnlyAtCronInterval=True,
)
