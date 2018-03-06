#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import git
import errno

_MODULES_PATH = os.path.abspath("__importmodule__")
_ERROR_INVALID_NAME = 123


class GitError(Exception):
    pass


class ImportModule(object):
    def __init__(self, module, path=None, reload=False):
        if not isinstance(module, (str, tuple, list)):
            raise AttributeError("module must be either str or tuple/list")
        if isinstance(module, (tuple, list)):
            for value in module:
                if not isinstance(value, str):
                    raise AttributeError("url must be composed of str values")
        if not (path is None or isinstance(path, str)):
            raise AttributeError("path must be either None or str")
        if not isinstance(reload, bool):
            raise AttributeError("reload must be True or False")

        self.module = module
        self.reload = reload
        self.path = path

    @staticmethod
    def _is_pathname_valid(pathname):
        try:
            if not isinstance(pathname, str) or not pathname:
                return False

            _, pathname = os.path.splitdrive(pathname)

            root_dir_name = os.environ.get("HOMEDRIVE", "C:") \
                if sys.platform == "win32" else os.path.sep

            if not os.path.isdir(root_dir_name):
                raise AssertionError

            root_dir_name = root_dir_name.rstrip(os.path.sep) + os.path.sep

            for pathname_part in pathname.split(os.path.sep):
                try:
                    os.lstat(root_dir_name + pathname_part)
                except OSError as exc:
                    if hasattr(exc, "winerror"):
                        if exc.winerror == _ERROR_INVALID_NAME:
                            return False
                    elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                        return False

        except TypeError:
            return False

        else:
            return True

    def _get_module(self, module, path):
        # TODO Add Bitbucket, GitHub, Google Code, and Launchpad
        if module.startswith("github.com/"):
            try:
                git.Repo.clone_from("https://{}".format(module), path)
            except Exception as e:
                raise GitError(e)
            self._chmod(path, 0o755)
        else:
            raise NotImplementedError("Type of module not supported")

    @staticmethod
    def _chmod(path, mode):
        for root, dirs, files in os.walk(path):
            for d in dirs:
                os.chmod(os.path.join(root, d), mode)
            for f in files:
                os.chmod(os.path.join(root, f), mode)

    @staticmethod
    def _remove_tree(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))

    def _load_module(self, module):
        _path = module if self.path is None else self.path
        module_path = os.path.join(_MODULES_PATH, _path)

        if not self._is_pathname_valid(module_path):
            raise ValueError("Invalid module path: '{}'".format(module_path))

        if self.reload and os.path.exists(module_path):
            self._remove_tree(module_path)
        if not os.path.exists(module_path) or not os.listdir(module_path):
            self._get_module(module, module_path)

        if module_path not in sys.path:
            sys.path.insert(0, module_path)

    def __enter__(self):
        if isinstance(self.module, str):
            self._load_module(self.module)
        else:
            for module in self.module:
                self._load_module(module)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
