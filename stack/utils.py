"""
Implement a way to override the parameter defaults in the .py files
at stack template creation time by reading in a JSON file.

At the end of this file, we look for an environment variable DEFAULTS_FILE
and if it exists, read it in to initialize the defaults we want to override.
"""

import json
import os

from troposphere import Parameter as TroposphereParameter

__ALL__ = [
    'ParameterWithDefaults',
    'set_defaults_from_dictionary',
]

parameter_defaults = {}


class ParameterWithDefaults(TroposphereParameter):
    """
    Like a parameter, but you can change its default value by
    loading different values in this module.
    """
    def __init__(self, title, **kwargs):
        # If the parameter can accept a 'Default' parameter, and
        # we have one configured, use that, overriding whatever was
        # passed in.
        if 'Default' in self.props and title in parameter_defaults:
            kwargs['Default'] = parameter_defaults[title]
        super().__init__(title, **kwargs)


def set_defaults_from_dictionary(d):
    """
    Update parameter default values from the given dictionary.
    Dictionary should map parameter names to default values.

    Example:

        {
            "AMI": "ami-078c57a94e9bdc6e0",
            "AssetsUseCloudFront": "false",
            "CacheNodeType": "(none)",
            "ContainerInstanceType": "t2.medium",
            "DatabaseClass": "db.t2.medium",
            "DatabaseEngineVersion": "10.3",
            "DatabaseStorageEncrypted": "true",
            "DomainName": "example.caktus-built.com",
            "KeyName": "id_example",
            "MaxScale": "2",
            "PrimaryAZ": "us-west-2a",
            "SecondaryAZ": "us-west-2b"
        }
    """
    parameter_defaults.update(d)


if os.environ.get('DEFAULTS_FILE'):
    set_defaults_from_dictionary(json.load(open(os.environ.get('DEFAULTS_FILE'))))
