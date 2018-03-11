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
    """
    Helper timer class
    """

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
    """
    Clear import_module related data

    :return: None
    """
    if os.path.exists(_MODULES_PATH):
        # noinspection PyProtectedMember
        ImportModule._remove_tree(_MODULES_PATH)
        os.rmdir(_MODULES_PATH)


def import_module(module, package=None):
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module, package)


def check_import_module(module, module_name, checker_handler):
    """
    Set of checks for testing if a module is being imported

    :param module: module identifier, similar to github.com/user/module_name
    :param module_name: name of module to be imported
    :param checker_handler: handler to assure the module was imported
    :return: None
    """
    # Assure there is no cached data
    clear_modules_path()

    # Since it is the first time importing, the repo should be cloned
    timer.start()
    with ImportModule(module):
        m1 = import_module(module_name)
    t1 = timer.stop()

    # Check behavior of imported module
    checker_handler(m1)

    # Since it is the second time importing and reload=False
    # the repo should NOT be cloned
    timer.start()
    with ImportModule(module, reload_module=False):
        m2 = import_module(module_name)
    t2 = timer.stop()

    # Check behavior of imported module
    checker_handler(m2)

    # Although it is the third time importing, reload is True so
    # the repo should be cloned
    timer.start()
    with ImportModule(module, reload_module=True):
        m3 = import_module(module_name)
    t3 = timer.stop()

    # Check behavior of imported module
    checker_handler(m3)

    # Import the module using a different path - the repo should be cloned
    timer.start()
    with ImportModule(module, path="different_path"):
        m4 = import_module(module_name)
    t4 = timer.stop()

    # Check behavior of imported module
    checker_handler(m4)

    # Check if times match: when reload=False, the time should be minimal
    assert t2 < t1
    assert t2 < t3
    assert t2 < t4

    # Test ImportModule with array
    with ImportModule([module, module]):
        m4 = import_module(module_name)

    # Check behavior of imported module
    checker_handler(m4)

    # Test ImportModule with tuple
    with ImportModule((module, module)):
        m5 = import_module(module_name)

    # Check behavior of imported module
    checker_handler(m5)


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


def test_import_pypi():
    def check_six_1_0_0(module):
        assert module.__version__ == "1.0.0"

    check_import_module(
        "pypi.python.org/pypi/six/1.0.0", "six", check_six_1_0_0)

    def check_six_latest(module):
        assert module.__version__ > "1.0.0"

    check_import_module(
        "pypi.python.org/pypi/six", "six", check_six_latest)


if __name__ == "__main__":
    pytest.main(sys.argv)
