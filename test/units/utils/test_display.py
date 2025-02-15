# -*- coding: utf-8 -*-
# (c) 2020 Matt Martz <matt@sivel.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import locale
import sys
import unicodedata
from unittest.mock import MagicMock

import pytest

from ansible.utils.display import _LIBC, _MAX_INT, Display, get_text_width
from ansible.utils.multiprocessing import context as multiprocessing_context


@pytest.fixture
def problematic_wcswidth_chars():
    locale.setlocale(locale.LC_ALL, "C.UTF-8")

    candidates = set(
        chr(c) for c in range(sys.maxunicode) if unicodedata.category(chr(c)) == "Cf"
    )
    problematic = [
        candidate
        for candidate in candidates
        if _LIBC.wcswidth(candidate, _MAX_INT) == -1
    ]

    if not problematic:
        # Newer distributions (Ubuntu 22.04, Fedora 38) include a libc which does not report problematic characters.
        pytest.skip("no problematic wcswidth chars found")  # pragma: nocover

    return problematic


def test_get_text_width():
    locale.setlocale(locale.LC_ALL, "")
    assert get_text_width("コンニチハ") == 10
    assert get_text_width("abコcd") == 6
    assert get_text_width("café") == 4
    assert get_text_width("four") == 4
    assert get_text_width("\u001B") == 0
    assert get_text_width("ab\u0000") == 2
    assert get_text_width("abコ\u0000") == 4
    assert get_text_width("🚀🐮") == 4
    assert get_text_width("\x08") == 0
    assert get_text_width("\x08\x08") == 0
    assert get_text_width("ab\x08cd") == 3
    assert get_text_width("ab\x1bcd") == 3
    assert get_text_width("ab\x7fcd") == 3
    assert get_text_width("ab\x94cd") == 3

    pytest.raises(TypeError, get_text_width, 1)
    pytest.raises(TypeError, get_text_width, b"four")


def test_get_text_width_no_locale(problematic_wcswidth_chars):
    pytest.raises(EnvironmentError, get_text_width, problematic_wcswidth_chars[0])


def test_Display_banner_get_text_width(monkeypatch):
    locale.setlocale(locale.LC_ALL, "")
    display = Display()
    display_mock = MagicMock()
    monkeypatch.setattr(display, "display", display_mock)

    display.banner("🚀🐮", color=False, cows=False)
    args, kwargs = display_mock.call_args
    msg = args[0]
    stars = " %s" % (75 * "*")
    assert msg.endswith(stars)


def test_Display_banner_get_text_width_fallback(monkeypatch):
    locale.setlocale(locale.LC_ALL, "C.UTF-8")
    display = Display()
    display_mock = MagicMock()
    monkeypatch.setattr(display, "display", display_mock)

    display.banner("\U000110cd", color=False, cows=False)
    args, kwargs = display_mock.call_args
    msg = args[0]
    stars = " %s" % (78 * "*")
    assert msg.endswith(stars)


def test_Display_set_queue_parent():
    display = Display()
    pytest.raises(RuntimeError, display.set_queue, "foo")


def test_Display_set_queue_fork():
    def test():
        display = Display()
        display.set_queue("foo")
        assert display._final_q == "foo"

    p = multiprocessing_context.Process(target=test)
    p.start()
    p.join()
    assert p.exitcode == 0


def test_Display_display_fork():
    def test():
        queue = MagicMock()
        display = Display()
        display.set_queue(queue)
        display.display("foo")
        queue.send_display.assert_called_once_with("display", "foo")

    p = multiprocessing_context.Process(target=test)
    p.start()
    p.join()
    assert p.exitcode == 0


def test_Display_display_warn_fork():
    def test():
        queue = MagicMock()
        display = Display()
        display.set_queue(queue)
        display.warning("foo")
        queue.send_display.assert_called_once_with("warning", "foo")

    p = multiprocessing_context.Process(target=test)
    p.start()
    p.join()
    assert p.exitcode == 0


def test_Display_display_lock(monkeypatch):
    lock = MagicMock()
    display = Display()
    monkeypatch.setattr(display, "_lock", lock)
    display.display("foo")
    lock.__enter__.assert_called_once_with()


def test_Display_display_lock_fork(monkeypatch):
    lock = MagicMock()
    display = Display()
    monkeypatch.setattr(display, "_lock", lock)
    monkeypatch.setattr(display, "_final_q", MagicMock())
    display.display("foo")
    lock.__enter__.assert_not_called()
