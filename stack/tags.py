from troposphere import AWS_STACK_NAME, Ref, Tags, autoscaling

from .template import template

common_tags = {"aws-web-stacks:stack-name": Ref(AWS_STACK_NAME)}


def tags_types_of_resource(resource):
    """
    return an iterable of the acceptable types for
    the Tags property on this resource.
    """
    tags_type = resource.props["Tags"][0]
    if isinstance(tags_type, tuple):
        return tags_type
    return [tags_type]


def tags_type_of_resource(resource):
    """
    Return the type that this resource expects its Tags
    property to be.  E.g. list, Tags, autoscaling.Tags.
    If there are multiple possibilities, returns the first.
    """
    return tags_types_of_resource(resource)[0]


def add_empty_tags(resource):
    # Put an empty tags prop on this resource, of the right type.
    tags_type = tags_type_of_resource(resource)
    resource.Tags = tags_type()


def add_common_tags(template):
    for resource in template.resources.values():
        if "Tags" not in resource.propnames:
            continue

        # WARNING: adding two Tags() objects together modifies and returns
        # the second object, giving it the concatenation of the
        # tags from the first and second objects, in that order.

        if not hasattr(resource, "Tags"):
            add_empty_tags(resource)

        if isinstance(resource.Tags, Tags):
            resource.Tags = Tags(**common_tags) + resource.Tags
        elif isinstance(resource.Tags, autoscaling.Tags):
            resource.Tags = autoscaling.Tags(**common_tags) + resource.Tags
        elif isinstance(resource.Tags, dict):
            tags = common_tags.copy()
            tags.update(**resource.Tags)  # override with any tags from this resource.
            resource.Tags = Tags(**tags)  # and set the result on the resource again.

        elif isinstance(resource.Tags, list):
            tags = tags_type_of_resource(resource)()
            tags.tags = resource.Tags
            resource.Tags = Tags(**common_tags) + tags
        else:
            raise TypeError("Unknown type %s for Tags on %s" % (type(resource.Tags), resource))


add_common_tags(template)
