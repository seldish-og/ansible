# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import json

import pytest

from ansible.module_utils.common import warnings


@pytest.mark.parametrize("stdin", [{}], indirect=["stdin"])
def test_warn(am, capfd):

    am.warn("warning1")

    with pytest.raises(SystemExit):
        am.exit_json(warnings=["warning2"])
    out, err = capfd.readouterr()
    assert json.loads(out)["warnings"] == ["warning1", "warning2"]


@pytest.mark.parametrize("stdin", [{}], indirect=["stdin"])
def test_deprecate(am, capfd, monkeypatch):
    monkeypatch.setattr(warnings, "_global_deprecations", [])

    am.deprecate("deprecation1")
    am.deprecate(
        "deprecation2", "2.3"
    )  # pylint: disable=ansible-deprecated-no-collection-name
    am.deprecate(
        "deprecation3", version="2.4"
    )  # pylint: disable=ansible-deprecated-no-collection-name
    am.deprecate(
        "deprecation4", date="2020-03-10"
    )  # pylint: disable=ansible-deprecated-no-collection-name
    am.deprecate("deprecation5", collection_name="ansible.builtin")
    am.deprecate("deprecation6", "2.3", collection_name="ansible.builtin")
    am.deprecate("deprecation7", version="2.4", collection_name="ansible.builtin")
    am.deprecate("deprecation8", date="2020-03-10", collection_name="ansible.builtin")

    with pytest.raises(SystemExit):
        am.exit_json(deprecations=["deprecation9", ("deprecation10", "2.4")])

    out, err = capfd.readouterr()
    output = json.loads(out)
    assert "warnings" not in output or output["warnings"] == []
    assert output["deprecations"] == [
        {"msg": "deprecation1", "version": None, "collection_name": None},
        {"msg": "deprecation2", "version": "2.3", "collection_name": None},
        {"msg": "deprecation3", "version": "2.4", "collection_name": None},
        {"msg": "deprecation4", "date": "2020-03-10", "collection_name": None},
        {"msg": "deprecation5", "version": None, "collection_name": "ansible.builtin"},
        {"msg": "deprecation6", "version": "2.3", "collection_name": "ansible.builtin"},
        {"msg": "deprecation7", "version": "2.4", "collection_name": "ansible.builtin"},
        {
            "msg": "deprecation8",
            "date": "2020-03-10",
            "collection_name": "ansible.builtin",
        },
        {"msg": "deprecation9", "version": None, "collection_name": None},
        {"msg": "deprecation10", "version": "2.4", "collection_name": None},
    ]


@pytest.mark.parametrize("stdin", [{}], indirect=["stdin"])
def test_deprecate_without_list(am, capfd):
    with pytest.raises(SystemExit):
        am.exit_json(deprecations="Simple deprecation warning")

    out, err = capfd.readouterr()
    output = json.loads(out)
    assert "warnings" not in output or output["warnings"] == []
    assert output["deprecations"] == [
        {"msg": "Simple deprecation warning", "version": None, "collection_name": None},
    ]


@pytest.mark.parametrize("stdin", [{}], indirect=["stdin"])
def test_deprecate_without_list_version_date_not_set(am, capfd):
    with pytest.raises(AssertionError) as ctx:
        am.deprecate("Simple deprecation warning", date="", version="")
    assert (
        ctx.value.args[0]
        == "implementation error -- version and date must not both be set"
    )
