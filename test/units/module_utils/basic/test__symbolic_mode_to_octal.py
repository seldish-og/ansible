# -*- coding: utf-8 -*-
# Copyright:
#   (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#   (c) 2016-2017 Ansible Project
# License: GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import pytest

from ansible.module_utils.basic import AnsibleModule


#
# Info helpful for making new test cases:
#
# base_mode = {'dir no perms': 0o040000,
# 'file no perms': 0o100000,
# 'dir all perms': 0o400000 | 0o777,
# 'file all perms': 0o100000, | 0o777}
#
# perm_bits = {'x': 0b001,
# 'w': 0b010,
# 'r': 0b100}
#
# role_shift = {'u': 6,
# 'g': 3,
# 'o': 0}

DATA = (  # Going from no permissions to setting all for user, group, and/or other
    (0o040000, "a+rwx", 0o0777),
    (0o040000, "u+rwx,g+rwx,o+rwx", 0o0777),
    (0o040000, "o+rwx", 0o0007),
    (0o040000, "g+rwx", 0o0070),
    (0o040000, "u+rwx", 0o0700),
    # Going from all permissions to none for user, group, and/or other
    (0o040777, "a-rwx", 0o0000),
    (0o040777, "u-rwx,g-rwx,o-rwx", 0o0000),
    (0o040777, "o-rwx", 0o0770),
    (0o040777, "g-rwx", 0o0707),
    (0o040777, "u-rwx", 0o0077),
    # now using absolute assignment from None to a set of perms
    (0o040000, "a=rwx", 0o0777),
    (0o040000, "u=rwx,g=rwx,o=rwx", 0o0777),
    (0o040000, "o=rwx", 0o0007),
    (0o040000, "g=rwx", 0o0070),
    (0o040000, "u=rwx", 0o0700),
    # X effect on files and dirs
    (0o040000, "a+X", 0o0111),
    (0o100000, "a+X", 0),
    (0o040000, "a=X", 0o0111),
    (0o100000, "a=X", 0),
    (0o040777, "a-X", 0o0666),
    # Same as chmod but is it a bug?
    # chmod a-X statfile <== removes execute from statfile
    (0o100777, "a-X", 0o0666),
    # Multiple permissions
    (0o040000, "u=rw-x+X,g=r-x+X,o=r-x+X", 0o0755),
    (0o100000, "u=rw-x+X,g=r-x+X,o=r-x+X", 0o0644),
    (0o040000, "ug=rx,o=", 0o0550),
    (0o100000, "ug=rx,o=", 0o0550),
    (0o040000, "u=rx,g=r", 0o0540),
    (0o100000, "u=rx,g=r", 0o0540),
    (0o040777, "ug=rx,o=", 0o0550),
    (0o100777, "ug=rx,o=", 0o0550),
    (0o040777, "u=rx,g=r", 0o0547),
    (0o100777, "u=rx,g=r", 0o0547),
)

UMASK_DATA = (
    (0o100000, "+rwx", 0o770),
    (0o100777, "-rwx", 0o007),
)

INVALID_DATA = (
    (0o040000, "a=foo", "bad symbolic permission for mode: a=foo"),
    (0o040000, "f=rwx", "bad symbolic permission for mode: f=rwx"),
)


@pytest.mark.parametrize("stat_info, mode_string, expected", DATA)
def test_good_symbolic_modes(mocker, stat_info, mode_string, expected):
    mock_stat = mocker.MagicMock()
    mock_stat.st_mode = stat_info
    assert AnsibleModule._symbolic_mode_to_octal(mock_stat, mode_string) == expected


@pytest.mark.parametrize("stat_info, mode_string, expected", UMASK_DATA)
def test_umask_with_symbolic_modes(mocker, stat_info, mode_string, expected):
    mock_umask = mocker.patch("os.umask")
    mock_umask.return_value = 0o7

    mock_stat = mocker.MagicMock()
    mock_stat.st_mode = stat_info

    assert AnsibleModule._symbolic_mode_to_octal(mock_stat, mode_string) == expected


@pytest.mark.parametrize("stat_info, mode_string, expected", INVALID_DATA)
def test_invalid_symbolic_modes(mocker, stat_info, mode_string, expected):
    mock_stat = mocker.MagicMock()
    mock_stat.st_mode = stat_info
    with pytest.raises(ValueError) as exc:
        assert AnsibleModule._symbolic_mode_to_octal(mock_stat, mode_string) == "blah"
    assert exc.match(expected)
