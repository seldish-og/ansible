# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

#############################################
#                WARNING                    #
#############################################
#
# This file is auto generated by the resource
#   module builder playbook.
#
# Do not edit this file manually.
#
# Changes to this file will be over written
#   by the resource module builder.
#
# Changes should be made in the model used to
#   generate this file or in the resource module
#   builder template.
#
#############################################
"""
The arg spec for the vyos_interfaces module
"""

from __future__ import annotations


class InterfacesArgs(object):  # pylint: disable=R0903
    """The arg spec for the vyos_interfaces module"""

    def __init__(self, **kwargs):
        pass

    argument_spec = {
        "config": {
            "elements": "dict",
            "options": {
                "description": {"type": "str"},
                "duplex": {"choices": ["full", "half", "auto"]},
                "enabled": {"default": True, "type": "bool"},
                "mtu": {"type": "int"},
                "name": {"required": True, "type": "str"},
                "speed": {
                    "choices": ["auto", "10", "100", "1000", "2500", "10000"],
                    "type": "str",
                },
                "vifs": {
                    "elements": "dict",
                    "options": {
                        "vlan_id": {"type": "int"},
                        "description": {"type": "str"},
                        "enabled": {"default": True, "type": "bool"},
                        "mtu": {"type": "int"},
                    },
                    "type": "list",
                },
            },
            "type": "list",
        },
        "state": {
            "choices": ["merged", "replaced", "overridden", "deleted"],
            "default": "merged",
            "type": "str",
        },
    }  # pylint: disable=C0301
