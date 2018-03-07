#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import git
import errno
import tarfile
import hashlib
import requests

_MODULES_PATH = os.path.abspath("__importmodule__")
_ERROR_INVALID_NAME = 123


class Function:
    """
    Helper class to save the result of a call
    """

    def __init__(self, func=lambda r: r):
        self.__func = func
        self.__result = None

    def __call__(self, *args, **kwargs):
        self.__result = self.__func(*args, **kwargs)
        return self.__result

    @property
    def result(self):
        return self.__result

    def clear(self):
        self.__result = None


class GitError(Exception):
    pass


class ModuleNotFound(Exception):
    pass


class DownloadFailed(Exception):
    pass


def _get_tar_sub_folder(tar):
    prefix = tar.members[0].name + "/"
    prefix_size = len(prefix)
    for member in tar.getmembers():
        if member.name.startswith(prefix):
            member.path = member.path[prefix_size:]
            yield member


class ImportModule(object):
    def __init__(self, module, path=None, reload_module=False):
        if not isinstance(module, (str, tuple, list)):
            raise AttributeError("module must be either str or tuple/list")
        if isinstance(module, (tuple, list)):
            for value in module:
                if not isinstance(value, str):
                    raise AttributeError("url must be composed of str values")
        if not (path is None or isinstance(path, str)):
            raise AttributeError("path must be either None or str")
        if not isinstance(reload_module, bool):
            raise AttributeError("reload must be True or False")

        self.module = module
        self.reload = reload_module
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
                return False

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

    @staticmethod
    def _get_valid_path(path):
        return re.sub(r"(?u)[^-\w. ()+]", "", path)

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

    def _has_module(self, path):
        if self.reload and os.path.exists(path):
            self._remove_tree(path)
        if os.path.exists(path) and os.listdir(path):
            return True
        return False

    def _load_module(self, module):
        _path = module if self.path is None else self.path

        if not self._is_pathname_valid(_path):
            _path = self._get_valid_path(_path)

        module_path = os.path.join(_MODULES_PATH, _path)
        if self._has_module(module_path):
            return

        match = Function(re.match)
        if match(r"^(github.com/|bitbucket.org/|git.launchpad.net/)", module):
            try:
                git.Repo.clone_from("https://{}".format(module), module_path)
            except Exception as e:
                raise GitError(e)
            self._chmod(module_path, 0o755)

        elif match(r"^pypi.python.org/pypi/([-\w]+)", module):
            module_name = match.result.group(1)
            json_url = "https://pypi.python.org/pypi/{}/json".format(
                module_name)

            r = requests.get(json_url)
            try:
                module_info = r.json()
            except Exception:
                raise ModuleNotFound(
                    "Unable to get module '{}' from pypi".format(module_name))

            latest = module_info["urls"][1]

            tar_path = os.path.join(module_path, latest["filename"])
            h = hashlib.md5()
            with requests.get(latest["url"], stream=True) as stream:
                if not os.path.exists(module_path):
                    os.makedirs(module_path)
                with open(tar_path, "wb") as f:
                    for chunk in stream.iter_content(512):
                        f.write(chunk)
                        h.update(chunk)

            if h.hexdigest() != latest["md5_digest"]:
                os.remove(tar_path)
                raise DownloadFailed(
                    "Failed to download '{}'".format(latest["url"]))

            with tarfile.open(tar_path) as tar:
                tar.extractall(module_path, _get_tar_sub_folder(tar))

            os.remove(tar_path)

        else:
            raise NotImplementedError("Type of module not supported")

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
