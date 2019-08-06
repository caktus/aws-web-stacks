from troposphere import AWS_STACK_NAME, Ref, Tags
from .template import template

common_tags = Tags({'aws-web-stacks:stack-name': Ref(AWS_STACK_NAME)})


def add_common_tags(template):
    for resource in template.resources.values():
        if 'Tags' not in resource.propnames:
            continue
        if not hasattr(resource, 'Tags'):
            resource.Tags = Tags()
        if isinstance(resource.Tags, Tags):
            tags = Tags() + common_tags
            tags += resource.Tags
            resource.Tags = tags


add_common_tags(template)
