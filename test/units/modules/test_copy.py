# -*- coding: utf-8 -*-
# Copyright:
#   (c) 2018 Ansible Project
# License: GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import pytest

from ansible.modules.copy import AnsibleModuleError, split_pre_existing_dir

from ansible.module_utils.basic import AnsibleModule


THREE_DIRS_DATA = (
    (
        "/dir1/dir2",
        # 0 existing dirs: error (because / should always exist)
        None,
        # 1 existing dir:
        ("/", ["dir1", "dir2"]),
        # 2 existing dirs:
        ("/dir1", ["dir2"]),
        # 3 existing dirs:
        ("/dir1/dir2", []),
    ),
    (
        "/dir1/dir2/",
        # 0 existing dirs: error (because / should always exist)
        None,
        # 1 existing dir:
        ("/", ["dir1", "dir2"]),
        # 2 existing dirs:
        ("/dir1", ["dir2"]),
        # 3 existing dirs:
        ("/dir1/dir2", []),
    ),
)


TWO_DIRS_DATA = (
    (
        "dir1/dir2",
        # 0 existing dirs:
        (".", ["dir1", "dir2"]),
        # 1 existing dir:
        ("dir1", ["dir2"]),
        # 2 existing dirs:
        ("dir1/dir2", []),
        # 3 existing dirs: Same as 2 because we never get to the third
    ),
    (
        "dir1/dir2/",
        # 0 existing dirs:
        (".", ["dir1", "dir2"]),
        # 1 existing dir:
        ("dir1", ["dir2"]),
        # 2 existing dirs:
        ("dir1/dir2", []),
        # 3 existing dirs: Same as 2 because we never get to the third
    ),
    (
        "/dir1",
        # 0 existing dirs: error (because / should always exist)
        None,
        # 1 existing dir:
        ("/", ["dir1"]),
        # 2 existing dirs:
        ("/dir1", []),
        # 3 existing dirs: Same as 2 because we never get to the third
    ),
    (
        "/dir1/",
        # 0 existing dirs: error (because / should always exist)
        None,
        # 1 existing dir:
        ("/", ["dir1"]),
        # 2 existing dirs:
        ("/dir1", []),
        # 3 existing dirs: Same as 2 because we never get to the third
    ),
) + THREE_DIRS_DATA


ONE_DIR_DATA = (
    (
        "dir1",
        # 0 existing dirs:
        (".", ["dir1"]),
        # 1 existing dir:
        ("dir1", []),
        # 2 existing dirs: Same as 1 because we never get to the third
    ),
    (
        "dir1/",
        # 0 existing dirs:
        (".", ["dir1"]),
        # 1 existing dir:
        ("dir1", []),
        # 2 existing dirs: Same as 1 because we never get to the third
    ),
) + TWO_DIRS_DATA


@pytest.mark.parametrize("directory, expected", ((d[0], d[4]) for d in THREE_DIRS_DATA))
def test_split_pre_existing_dir_three_levels_exist(directory, expected, mocker):
    mocker.patch("os.path.exists", side_effect=[True, True, True])
    split_pre_existing_dir(directory) == expected


@pytest.mark.parametrize("directory, expected", ((d[0], d[3]) for d in TWO_DIRS_DATA))
def test_split_pre_existing_dir_two_levels_exist(directory, expected, mocker):
    mocker.patch("os.path.exists", side_effect=[True, True, False])
    split_pre_existing_dir(directory) == expected


@pytest.mark.parametrize("directory, expected", ((d[0], d[2]) for d in ONE_DIR_DATA))
def test_split_pre_existing_dir_one_level_exists(directory, expected, mocker):
    mocker.patch("os.path.exists", side_effect=[True, False, False])
    split_pre_existing_dir(directory) == expected


@pytest.mark.parametrize("directory", (d[0] for d in ONE_DIR_DATA if d[1] is None))
def test_split_pre_existing_dir_root_does_not_exist(directory, mocker):
    mocker.patch("os.path.exists", return_value=False)
    with pytest.raises(AnsibleModuleError) as excinfo:
        split_pre_existing_dir(directory)
    assert excinfo.value.results["msg"].startswith(
        "The '/' directory doesn't exist on this machine."
    )


@pytest.mark.parametrize(
    "directory, expected",
    ((d[0], d[1]) for d in ONE_DIR_DATA if not d[0].startswith("/")),
)
def test_split_pre_existing_dir_working_dir_exists(directory, expected, mocker):
    mocker.patch("os.path.exists", return_value=False)
    split_pre_existing_dir(directory) == expected


#
# Info helpful for making new test cases:
#
# base_mode = {
# 'dir no perms':   0o040000,
# 'file no perms':  0o100000,
# 'dir all perms':  0o040000 | 0o777,
# 'file all perms': 0o100000 | 0o777}
#
# perm_bits = {
# 'x': 0b001,
# 'w': 0b010,
# 'r': 0b100}
#
# role_shift = {
# 'u': 6,
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
    # Verify X uses computed not original mode
    (0o100777, "a=,u=rX", 0o0400),
    (0o040777, "a=,u=rX", 0o0500),
    # Multiple permissions
    (0o040000, "u=rw-x+X,g=r-x+X,o=r-x+X", 0o0755),
    (0o100000, "u=rw-x+X,g=r-x+X,o=r-x+X", 0o0644),
)

UMASK_DATA = (
    (0o100000, "+rwx", 0o770),
    (0o100777, "-rwx", 0o007),
)

INVALID_DATA = (
    (0o040000, "a=foo", "bad symbolic permission for mode: a=foo"),
    (0o040000, "f=rwx", "bad symbolic permission for mode: f=rwx"),
    (0o100777, "of=r", "bad symbolic permission for mode: of=r"),
    (0o100777, "ao=r", "bad symbolic permission for mode: ao=r"),
    (0o100777, "oa=r", "bad symbolic permission for mode: oa=r"),
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
