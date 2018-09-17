from collections import OrderedDict

from troposphere import Template


class InterfaceTemplate(Template):
    """
    Custom Template class that allows us to optionally define groups and labels for
    CloudFormation Parameters at the time they're added to the template. Groups and
    labels specified, if any, will be added to a custom AWS::CloudFormation::Interface
    """

    def __init__(self, *args, **kwargs):
        super(InterfaceTemplate, self).__init__(*args, **kwargs)
        # use OrderedDict() so we can keep track of the order in which groups are added
        self.parameter_groups = OrderedDict()
        self.parameter_labels = {}
        self.group_order = []

    def add_parameter(self, parameter, group=None, label=None):
        """
        Save group and/or label, if specified, for later generation of
        'AWS::CloudFormation::Interface' in to_dict().
        """
        parameter = super(InterfaceTemplate, self).add_parameter(parameter)
        if group:
            if group not in self.parameter_groups:
                self.parameter_groups[group] = []
            self.parameter_groups[group].append(parameter.title)
        if label:
            self.parameter_labels[parameter.title] = label
        return parameter

    def set_group_order(self, group_order):
        """
        Set an ordered list of all known, possible parameter groups in this stack.
        If none is provided, groups will appear in the order they were first passed
        to add_parameter().
        """
        self.group_order = group_order

    def to_dict(self):
        """
        Overwrite 'AWS::CloudFormation::Interface' key in self.metadata (if any)
        with the groups and labels defined via add_parameter(), and then call
        super().to_dict().
        """
        # create an ordered list of parameter groups for our interface
        ordered_groups = list(self.group_order)
        groups_in_stack = list(self.parameter_groups.keys())
        # add any groups specified in the stack that we didn't know about in advance
        ordered_groups += [g for g in groups_in_stack if g not in ordered_groups]
        # remove any groups NOT specified in the stack
        ordered_groups = [g for g in ordered_groups if g in groups_in_stack]
        # update metadata with our interface
        self.metadata.update({
            'AWS::CloudFormation::Interface': {
                'ParameterGroups': [
                    {
                        'Label': {'default': group},
                        'Parameters': self.parameter_groups[group],
                    }
                    for group in ordered_groups
                ],
                'ParameterLabels': dict([
                    (parameter, {'default': label})
                    for parameter, label in self.parameter_labels.items()
                ]),
            }
        })
        return super(InterfaceTemplate, self).to_dict()


# The CloudFormation template
template = InterfaceTemplate()

# If you create a new group and care about the order in which it shows up in the
# CloudFormation interface, add it below.
template.set_group_order([
    'Global',
    'Application Server',
    'Load Balancer',
    'Static Media',
    'Database',
    'Cache',
    'Elasticsearch',
])
