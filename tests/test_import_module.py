#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
# noinspection PyPackageRequirements
import pytest
import importlib
# noinspection PyProtectedMember
from import_module import ImportModule, _MODULES_PATH


class Timer:
    def __init__(self):
        self.__start = None

    def start(self):
        self.__start = time.time()

    def stop(self):
        time_passed = time.time() - self.__start
        self.__start = None
        return time_passed


timer = Timer()


def clear_modules_path():
    if os.path.exists(_MODULES_PATH):
        # noinspection PyProtectedMember
        ImportModule._remove_tree(_MODULES_PATH)
        os.rmdir(_MODULES_PATH)


def check_import_module(module, module_name, checker_handler):
    clear_modules_path()

    timer.start()
    with ImportModule(module):
        m1 = importlib.import_module(module_name)
    t1 = timer.stop()

    checker_handler(m1)

    timer.start()
    with ImportModule(module, reload=False):
        m2 = importlib.import_module(module_name)
    t2 = timer.stop()

    checker_handler(m2)

    timer.start()
    with ImportModule(module, reload=True):
        m3 = importlib.import_module(module_name)
    t3 = timer.stop()

    checker_handler(m3)

    assert t1 < t3
    assert t2 < t3


def test_import_github():
    def check_dummy_module(module):
        attributes = []
        for a in dir(module):
            if not a.startswith("_"):
                attributes.append(a)

        assert attributes == ["call"]
        assert module.call() == "call"

    check_import_module(
        "github.com/i96751414/py-dummy", "dummy", check_dummy_module)


if __name__ == "__main__":
    pytest.main(sys.argv)
