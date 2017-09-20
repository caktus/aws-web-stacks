import troposphere.cloudformation as cloudformation
import troposphere.ec2 as ec2
import troposphere.iam as iam
from troposphere import Base64, FindInMap, Join, Output, Parameter, Ref, Tags
from troposphere.policies import CreationPolicy, ResourceSignal

from .assets import assets_management_policy
from .common import container_instance_type
from .domain import domain_name
from .environment import environment_variables
from .logs import logging_policy
from .template import template
from .vpc import container_a_subnet, vpc

key_name = template.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH access to "
                "the AWS EC2 instances",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair."
))

dokku_version = template.add_parameter(Parameter(
    "DokkuVersion",
    Description="Dokku version to install, e.g., \"v0.10.4\" (see https://github.com/dokku/dokku/releases).",
    Type="String",
    Default="v0.10.4",
))

dokku_web_config = template.add_parameter(Parameter(
    "DokkuWebConfig",
    Description="Whether or not to enable the Dokku web config (defaults to false for security reasons).",
    Type="String",
    AllowedValues=["true", "false"],
    Default="false",
))

dokku_vhost_enable = template.add_parameter(Parameter(
    "DokkuVhostEnable",
    Description="Whether or not to use vhost-based deployments (e.g., foo.domain.name).",
    Type="String",
    AllowedValues=["true", "false"],
    Default="true",
))

root_size = template.add_parameter(Parameter(
    "RootVolumeSize",
    Description="The size of the root volumne (in GB).",
    Type="Number",
    Default="30",
))

ssh_cidr = template.add_parameter(Parameter(
    "SshCidr",
    Description="CIDR block from which to allow SSH access. Restrict this to your IP, if possible.",
    Type="String",
    Default="0.0.0.0/0",
))

# "16.04 hvm ssd" AMIs from https://cloud-images.ubuntu.com/locator/ec2/
template.add_mapping('RegionMap', {
    "ap-northeast-1": {"AMI": "ami-0417e362"},
    "ap-northeast-2": {"AMI": "ami-536ab33d"},
    "ap-south-1": {"AMI": "ami-df413bb0"},
    "ap-southeast-1": {"AMI": "ami-9f28b3fc"},
    "ap-southeast-2": {"AMI": "ami-bb1901d8"},
    "ca-central-1": {"AMI": "ami-a9c27ccd"},
    "eu-central-1": {"AMI": "ami-958128fa"},
    "eu-west-1": {"AMI": "ami-674cbc1e"},
    "eu-west-2": {"AMI": "ami-03998867"},
    "sa-east-1": {"AMI": "ami-a41869c8"},
    "us-east-1": {"AMI": "ami-1d4e7a66"},
    "us-east-2": {"AMI": "ami-dbbd9dbe"},
    "us-west-1": {"AMI": "ami-969ab1f6"},
    "us-west-2": {"AMI": "ami-8803e0f0"},
})

# EC2 instance role
instance_role = iam.Role(
    "ContainerInstanceRole",
    template=template,
    AssumeRolePolicyDocument=dict(Statement=[dict(
        Effect="Allow",
        Principal=dict(Service=["ec2.amazonaws.com"]),
        Action=["sts:AssumeRole"],
    )]),
    Path="/",
    Policies=[
        assets_management_policy,
        logging_policy,
    ]
)

# EC2 instance profile
instance_profile = iam.InstanceProfile(
    "ContainerInstanceProfile",
    template=template,
    Path="/",
    Roles=[Ref(instance_role)],
)

# EC2 security group
security_group = template.add_resource(ec2.SecurityGroup(
    'SecurityGroup',
    GroupDescription='Allows SSH access from SshCidr and HTTP/HTTPS access from anywhere.',
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=22,
            ToPort=22,
            CidrIp=Ref(ssh_cidr),
        ),
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=80,
            ToPort=80,
            CidrIp='0.0.0.0/0',
        ),
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=443,
            ToPort=443,
            CidrIp='0.0.0.0/0',
        ),
    ]
))

# Elastic IP for EC2 instance
eip = template.add_resource(ec2.EIP("Eip"))


# The Dokku EC2 instance
ec2_instance_name = 'Ec2Instance'
ec2_instance = template.add_resource(ec2.Instance(
    ec2_instance_name,
    ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
    InstanceType=container_instance_type,
    KeyName=Ref(key_name),
    SecurityGroupIds=[Ref(security_group)],
    IamInstanceProfile=Ref(instance_profile),
    SubnetId=Ref(container_a_subnet),
    BlockDeviceMappings=[
        ec2.BlockDeviceMapping(
            DeviceName="/dev/sda1",
            Ebs=ec2.EBSBlockDevice(
                VolumeSize=Ref(root_size),
            )
        ),
    ],
    CreationPolicy=CreationPolicy(
        ResourceSignal=ResourceSignal(
            Timeout='PT10M',  # 10 minutes
        ),
    ),
    UserData=Base64(Join('', [
        '#!/bin/bash\n',
        # install cfn helper scripts; modified from:
        # http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-helper-scripts-reference.html
        'sudo apt-get update\n',
        'apt-get -y install python-pip\n',
        'pip install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz\n',
        'cp /usr/local/init/ubuntu/cfn-hup /etc/init.d/cfn-hup\n',
        'chmod +x /etc/init.d/cfn-hup\n',
        # don't start cfn-hup yet, since we need to install cfn-hup.conf first
        'update-rc.d cfn-hup defaults\n',
        # call our "on_first_boot" configset (defined below):
        'cfn-init --stack="', Ref('AWS::StackName'), '" --region=', Ref('AWS::Region'),
        ' -r %s -c on_first_boot\n' % ec2_instance_name,
        # send the exit code from cfn-init to our CreationPolicy:
        'cfn-signal -e $? --stack="', Ref('AWS::StackName'), '" --region=', Ref('AWS::Region'),
        ' --resource %s\n' % ec2_instance_name,
    ])),
    Metadata=cloudformation.Metadata(
        cloudformation.Init(
            cloudformation.InitConfigSets(
                on_first_boot=['install_dokku', 'set_dokku_env', 'start_cfn_hup'],
                on_metadata_update=['set_dokku_env'],
            ),
            # TODO: figure out how to reinstall Dokku if the version is changed (?)
            install_dokku=cloudformation.InitConfig(
                commands={
                    '01_fetch': {
                        'command': Join('', [
                            'wget https://raw.githubusercontent.com/dokku/dokku/',
                            Ref(dokku_version),
                            '/bootstrap.sh',
                        ]),
                        'cwd': '~',
                    },
                    '02_install': {
                        # docker-ce fails to install with this error if bootstrap.sh is run without sudo:
                        # "debconf: delaying package configuration, since apt-utils is not installed"
                        'command': 'sudo -E bash bootstrap.sh',  # use -E to make sure bash gets our env
                        'env': {
                            'DOKKU_TAG': Ref(dokku_version),
                            'DOKKU_VHOST_ENABLE': Ref(dokku_vhost_enable),
                            'DOKKU_WEB_CONFIG': Ref(dokku_web_config),
                            'DOKKU_HOSTNAME': domain_name,
                            'DOKKU_KEY_FILE': '/home/ubuntu/.ssh/authorized_keys',  # use the key configured by key_name
                        },
                        'cwd': '~',
                    },
                },
            ),
            set_dokku_env=cloudformation.InitConfig(
                commands={
                    '01_set_env': {
                        # redirect output to /dev/null so we don't write environment variables to log file
                        'command': 'dokku config:set --global {} >/dev/null'.format(
                            ' '.join(['=$'.join([k, k]) for k in dict(environment_variables).keys()]),
                        ),
                        'env': dict(environment_variables),
                    },
                },
            ),
            start_cfn_hup=cloudformation.InitConfig(
                commands={
                    '01_start': {
                        'command': 'service cfn-hup start',
                    },
                },
                files={
                    '/etc/cfn/cfn-hup.conf': {
                        'content': Join('', [
                            '[main]\n',
                            'stack=', Ref('AWS::StackName'), '\n',
                            'region=', Ref('AWS::Region'), '\n',
                            'umask=022\n',
                            'interval=1\n',  # check for changes every minute
                            'verbose=true\n',
                        ]),
                        'mode': '000400',
                        'owner': 'root',
                        'group': 'root',
                    },
                    '/etc/cfn/hooks.d/cfn-auto-reloader.conf': {
                        'content': Join('', [
                            # trigger the on_metadata_update configset on any changes to Ec2Instance metadata
                            '[cfn-auto-reloader-hook]\n',
                            'triggers=post.update\n',
                            'path=Resources.%s.Metadata\n' % ec2_instance_name,
                            'action=/usr/local/bin/cfn-init',
                            ' --stack=', Ref('AWS::StackName'),
                            ' --resource=%s' % ec2_instance_name,
                            ' --configsets=on_metadata_update',
                            ' --region=', Ref('AWS::Region'), '\n',
                            'runas=root\n',
                        ]),
                        'mode': '000400',
                        'owner': 'root',
                        'group': 'root',
                    },
                },
            ),
        ),
    ),
    Tags=Tags(
        Name=Ref("AWS::StackName"),
    ),
))

# Associate the Elastic IP separately, so it doesn't change when the instance changes.
eip_assoc = template.add_resource(ec2.EIPAssociation(
    "EipAssociation",
    InstanceId=Ref(ec2_instance),
    EIP=Ref(eip),
))

template.add_output([
    Output(
        "PublicIP",
        Description="Public IP address of Elastic IP associated with the Dokku instance",
        Value=Ref(eip),
    ),
])
