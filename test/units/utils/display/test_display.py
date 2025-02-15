# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


from ansible.utils.display import Display


def test_display_basic_message(capsys, mocker):
    # Disable logging
    mocker.patch("ansible.utils.display.logger", return_value=None)

    d = Display()
    d.display("Some displayed message")
    out, err = capsys.readouterr()
    assert out == "Some displayed message\n"
    assert err == ""
