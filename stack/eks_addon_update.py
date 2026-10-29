# Scheduled EKS addon updates using a custom SSM Automation document (no
# AWS-managed runbook exists for this) paired with an SSM Association.
#
# For each addon installed on the cluster (discovered via list_addons) the
# document:
#   1. DescribeAddonVersions (paginated, filtered by name + cluster K8s
#      version) -> compatible versions
#   2. never downgrades: highest compatible version above current wins
#   3. vpc-cni is limited to at most one minor version ahead (AWS guidance)
#   4. no-op if already at the target, else UpdateAddon (carrying the
#      existing service account role) and wait on the update id until
#      Successful/Failed/Cancelled
#
# Schedule expressions are UTC.
#
# Runs as SSMNodegroupUpdateServiceRole (the shared EKS-update role
# from eks_nodegroup_update.py).
#
# Generated as part of the separate "eks-*-updates" template (see stack/eks_updates.py);
# the cluster is referenced by name via the EksClusterName parameter.
from troposphere import GetAtt, Join, Ref, ssm

from .eks_nodegroup_update import ssm_nodegroup_update_role
from .eks_updates import eks_cluster_name
from .template import updates_template
from .utils import ParameterWithDefaults as Parameter

update_schedule = Ref(updates_template.add_parameter(
    Parameter(
        "EksAddonUpdateSchedule",
        Description="SSM cron (UTC) for EKS addon updates; keep separate from the nodegroup schedule.",
        Type="String",
        Default="cron(0 10 ? * TUE#1 *)",
    ),
    group="Elastic Kubernetes Service (EKS)",
    label="Addon update schedule (UTC cron)",
))

# ---------------------------------------------------------------------------
# Automation document: the update script and the document content that
# embeds it (consumed by the EKSAddonUpdateDocument resource below).
# ---------------------------------------------------------------------------

script = """import json, re, time, boto3
import botocore.config
from botocore.exceptions import ClientError

_VERSION_RE = re.compile(r"^v?(\\d+)\\.(\\d+)\\.(\\d+)(?:-(?:eksbuild\\.(\\d+)|(\\d{8})))?$")

eks = boto3.client("eks", config=botocore.config.Config(
    retries={"max_attempts": 3, "mode": "standard"}))


def parse_version(raw_version):
    # Version parsing
    # Return (major, minor, patch, build, raw) or None if unrecognized.
    match = _VERSION_RE.match(raw_version or "")
    if not match:
        return None
    major, minor, patch, build, date = match.groups()
    return (int(major), int(minor), int(patch), int(build or date or 0), raw_version)


def version_key(version):
    # Ordering key; the Version dataclass orders on major/minor/patch/build.
    return version[:4]


def get_cluster_k8s_version(cluster):
    # Fetch EKS
    return eks.describe_cluster(name=cluster)["cluster"]["version"]


def list_addon_names(cluster):
    addon_names = []
    for addons_page in eks.get_paginator("list_addons").paginate(clusterName=cluster):
        addon_names.extend(addons_page["addons"])
    return addon_names


def get_addon(cluster, addon_name):
    # Return the addon descriptor, or None if not installed on the cluster.
    try:
        return eks.describe_addon(clusterName=cluster, addonName=addon_name)["addon"]
    except ClientError as api_error:
        if api_error.response["Error"]["Code"] == "ResourceNotFoundException":
            return None
        raise


def collect_compatible_versions(addon_name, k8s_version):
    # Return (parsed_versions, rejected_versions) for the addon + cluster version.
    #
    # VersionCandidates.from_addon_versions, paginated and name-filtered.
    #
    parsed_versions, rejected_versions = [], []
    for versions_page in eks.get_paginator("describe_addon_versions").paginate(
            addonName=addon_name, kubernetesVersion=k8s_version):
        for addon_group in versions_page["addons"]:
            if addon_group.get("addonName", addon_name) != addon_name:
                continue
            for version_entry in addon_group["addonVersions"]:
                parsed_version = parse_version(version_entry["addonVersion"])
                if parsed_version is None:
                    rejected_versions.append(version_entry["addonVersion"])
                else:
                    parsed_versions.append(parsed_version)
    return parsed_versions, rejected_versions


def within_one_minor_step(candidate, current_parsed):
    # AWS vpc-cni constraint: at most one minor version ahead.
    return (candidate[0], candidate[1]) <= (current_parsed[0], current_parsed[1] + 1)


def filter_one_minor_step(candidate_versions, current_parsed):
    return [candidate for candidate in candidate_versions
            if within_one_minor_step(candidate, current_parsed)]


def decide_update(addon_name, current_version, candidate_versions, k8s_version):
    # Pick the target version.
    #
    # Return (target_version, summary_entry). summary_entry is the final result
    # dict for no-op/skip cases; on an actual update it is None and the caller
    # performs the update.
    #
    current_parsed = parse_version(current_version)
    if addon_name == "vpc-cni" and current_parsed is not None:
        candidate_versions = filter_one_minor_step(candidate_versions, current_parsed)
    if not candidate_versions:
        return None, {"skipped": "no available version for %s" % k8s_version}
    target_version = max(candidate_versions, key=version_key)
    if target_version[4] == current_version:
        return None, {"no-op": current_version, "reason": "already at target"}
    if current_parsed is None:
        return None, {"skipped": "cannot compare %r to %r" % (current_version, target_version[4])}
    if version_key(target_version) <= version_key(current_parsed):
        return None, {"no-op": current_version, "reason": "already at or past target"}
    return target_version, None


# ---------------------------------------------------------------------------
# Addon Update Execution
# ---------------------------------------------------------------------------

def wait_for_update(cluster, update_id, addon_name, timeout=1800, delay=15):
    # eks_aws.wait_for_update; UpdateFailed becomes a plain Exception here.
    deadline = time.monotonic() + timeout
    while True:
        try:
            update_info = eks.describe_update(
                name=cluster, addonName=addon_name, updateId=update_id)["update"]
        except ClientError as api_error:
            if api_error.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
            # The update record may not be queryable immediately after
            # UpdateAddon returns; keep polling until the deadline.
            update_info = None
        if update_info is not None:
            if update_info["status"] == "Successful":
                return update_info
            if update_info["status"] in ("Failed", "Cancelled"):
                error_details = "; ".join(
                    "%s: %s" % (error_entry.get("errorCode"), error_entry.get("errorMessage"))
                    for error_entry in update_info.get("errors", [])
                )
                raise Exception("addon %s update %s %s: %s"
                                % (addon_name, update_id, update_info["status"].lower(), error_details))
        if time.monotonic() >= deadline:
            raise Exception("timed out after %ss waiting for addon %s update %s"
                            % (timeout, addon_name, update_id))
        time.sleep(delay)


def perform_update(cluster, addon_name, addon, target_version):
    # Call UpdateAddon and wait for the update to complete.
    update_kwargs = {"clusterName": cluster, "addonName": addon_name,
                     "addonVersion": target_version[4]}
    # No resolveConflicts: UpdateAddon rejects the parameter here;
    # carry the addon's existing service account role if it has one.
    if addon.get("serviceAccountRoleArn"):
        update_kwargs["serviceAccountRoleArn"] = addon["serviceAccountRoleArn"]
    update_info = eks.update_addon(**update_kwargs)["update"]
    wait_for_update(cluster, update_info["id"], addon_name)
    return {"updated": "%s -> %s" % (addon["addonVersion"], target_version[4]),
            "update_id": update_info["id"]}


def process_addon(cluster, addon_name, k8s_version):
    # Handle one addon update at a time.
    #
    # Return (summary_entry, rejected_versions).
    #
    addon = get_addon(cluster, addon_name)
    if addon is None:
        return {"skipped": "not installed on this cluster"}, []
    if addon["status"] != "ACTIVE":
        return {"skipped": "addon status is %s" % addon["status"]}, []
    candidate_versions, rejected_versions = collect_compatible_versions(addon_name, k8s_version)
    target_version, summary_entry = decide_update(
        addon_name, addon["addonVersion"], candidate_versions, k8s_version)
    if summary_entry is not None:
        return summary_entry, rejected_versions
    return perform_update(cluster, addon_name, addon, target_version), rejected_versions


def updateAddons(events, context):
    cluster = events["ClusterName"]
    k8s_version = get_cluster_k8s_version(cluster)
    results, unparseable_versions = {}, {}
    for addon_name in list_addon_names(cluster):
        try:
            summary_entry, rejected_versions = process_addon(cluster, addon_name, k8s_version)
            results[addon_name] = summary_entry
            if rejected_versions:
                unparseable_versions[addon_name] = rejected_versions
        except Exception as error:
            results[addon_name] = {"error": str(error)[:400]}
    addon_errors = {name: result for name, result in results.items() if "error" in result}
    summary = {"addons": results}
    if unparseable_versions:
        summary["unparseable_versions"] = unparseable_versions
    if addon_errors:
        raise Exception("addon update errors: %s" % json.dumps(addon_errors))
    return json.dumps(summary)

"""

document_content = dict(
    schemaVersion="0.3",
    assumeRole="{{ AutomationAssumeRole }}",
    description=(
        "## What does this document do?\n"
        "  Automation document to update all EKS cluster addons to their latest available versions.\n\n"
        "## Input Parameters\n"
        "  * ClusterName: (Required) The name of the cluster.\n"
        "  * AutomationAssumeRole: (Optional) The ARN of the role that allows the document to execute.\n"
    ),
    parameters=dict(
        ClusterName=dict(
            type="String",
            description="(Required) The name of the cluster.",
            allowedPattern=r"^[0-9A-Za-z][A-Za-z0-9\-_]*",
        ),
        AutomationAssumeRole=dict(
            type="AWS::IAM::Role::Arn",
            description="(Optional) The ARN of the role that allows the "
                        "document to execute.",
            default="",
            allowedPattern=r'^$|arn:(aws[a-zA-Z-]*)?:iam::\d{12}:role\/?[a-zA-Z_0-9+=,.@\-\_\/]+',
        ),
    ),
    mainSteps=[dict(
        name="updateAddons",
        action="aws:executeScript",
        maxAttempts=1,
        timeoutSeconds=3600,
        inputs=dict(
            Handler="updateAddons",
            Runtime="python3.12",
            Script=script,
            InputPayload={
                "ClusterName": "{{ ClusterName }}",
            },
        ),
    )],
)

# ---------------------------------------------------------------------------
# Custom automation document
# ---------------------------------------------------------------------------

addon_update_document = ssm.Document(
    "EKSAddonUpdateDocument",
    template=updates_template,
    DocumentType="Automation",
    Content=document_content,
)

# ---------------------------------------------------------------------------
# Scheduled automation association
# ---------------------------------------------------------------------------

ssm.Association(
    "EKSAddonUpdateAssociation",
    template=updates_template,
    Name=Ref(addon_update_document),
    AssociationName=Join("", ["EKS-AddonUpdate-", Ref("AWS::StackName")]),
    Parameters=dict(
        ClusterName=[eks_cluster_name],
        AutomationAssumeRole=[GetAtt(ssm_nodegroup_update_role, "Arn")],
    ),
    ScheduleExpression=update_schedule,
    # Don't fire immediately on association creation/update - only at the
    # scheduled cron slots, so a template deploy never triggers a live
    # addon upgrade.
    ApplyOnlyAtCronInterval=True,
)
