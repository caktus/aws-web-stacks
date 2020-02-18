from troposphere import AWS_STACK_NAME, Ref, Tags

from .template import template

common_tags = Tags({'aws-web-stacks:stack-name': Ref(AWS_STACK_NAME)})


def add_common_tags(template):
    for resource in template.resources.values():
        if 'Tags' not in resource.propnames:
            continue
        if not hasattr(resource, "Tags"):
            # We need to create an empty tags prop for this resource.
            # Not all resources use the same type for their tags, sigh.
            # At least we can figure it out from the information that
            # troposphere puts on the class.
            tags_type = resource.props["Tags"][0]
            if isinstance(tags_type, tuple):
                tags_type = tags_type[0]
            resource.Tags = tags_type()

        if isinstance(resource.Tags, Tags):
            tags = Tags() + common_tags
            tags += resource.Tags
            resource.Tags = tags
        if isinstance(resource.Tags, dict):
            tags = common_tags.to_dict()  # actually returns a list. Sigh.
            tags = dict(tags)  # convert to a dict.
            tags.update(resource.Tags)  # override with any tags from this resource.
            resource.Tags = tags  # and set the result on the resource again.


add_common_tags(template)
