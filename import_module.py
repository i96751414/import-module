#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["GitError", "ModuleNotFound", "DownloadFailed", "ImportModule"]

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

_TYPE_GIT = 0
_TYPE_PYPI = 1


class GitError(ImportError):
    pass


class ModuleNotFound(ImportError):
    pass


class DownloadFailed(ImportError):
    pass


class _Function:
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


def _get_tar_sub_folder(tar):
    prefix = tar.members[0].name + "/"
    prefix_size = len(prefix)
    for member in tar.getmembers():
        if member.name.startswith(prefix):
            member.path = member.path[prefix_size:]
            yield member


class _ModuleInfo:
    def __init__(self, module, path=None):
        module = module.replace("\\", "/")
        while "//" in module:
            module = module.replace("//", "")
        if module.endswith("/"):
            module = module[:-1]

        if re.match("^(github.com|bitbucket.org|git.launchpad.net)/", module):
            _type = _TYPE_GIT
            _path = re.sub(r"(?<=[^/]).git$", "", module)

        elif re.match(r"^pypi.python.org/pypi/[-\w.]+/[\w.]+$", module):
            _type = _TYPE_PYPI
            _path = module

        elif re.match(r"^pypi.python.org/pypi/[-\w.]+$", module):
            _type = _TYPE_PYPI
            _path = "{}/latest".format(module)

        else:
            raise NotImplementedError("Type of module not supported")

        if path is not None:
            _path = path

        if not self._is_pathname_valid(_path):
            _path = self._get_valid_path(_path)

        self.module = module
        self.path = os.path.join(_MODULES_PATH, _path)
        self.type = _type

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

    @staticmethod
    def _make_dirs(path):
        if not os.path.exists(path):
            os.makedirs(path)

    def _get_module(self, module_info):
        if module_info.type == _TYPE_GIT:
            try:
                git.Repo.clone_from("https://{}".format(module_info.module),
                                    module_info.path)
            except Exception as e:
                raise GitError(e)
            self._chmod(module_info.path, 0o755)

        elif module_info.type == _TYPE_PYPI:
            r = requests.get("https://{}/json".format(module_info.module))
            try:
                json_data = r.json()
            except Exception:
                raise ModuleNotFound(
                    "Unable to get module '{}' from pypi".format(
                        module_info.module))

            module = None
            for url in json_data["urls"]:
                if url["packagetype"] == "sdist":
                    module = url

            if module is None:
                raise ModuleNotFound(
                    "Unable to get module '{}' from pypi".format(
                        module_info.module))

            tar_path = os.path.join(module_info.path, module["filename"])
            h = hashlib.md5()
            with requests.get(module["url"], stream=True) as stream:
                self._make_dirs(module_info.path)
                with open(tar_path, "wb") as f:
                    for chunk in stream.iter_content(1024):
                        f.write(chunk)
                        h.update(chunk)

            if h.hexdigest() != module["md5_digest"]:
                os.remove(tar_path)
                raise DownloadFailed(
                    "Failed to download '{}'".format(module["url"]))

            with tarfile.open(tar_path) as tar:
                tar.extractall(module_info.path, _get_tar_sub_folder(tar))

            os.remove(tar_path)

        else:
            raise NotImplementedError("Type of module not supported")

    def _load_module(self, module, path=None):
        module_info = _ModuleInfo(module, path)

        if self.reload and os.path.exists(module_info.path):
            self._remove_tree(module_info.path)

        if (not os.path.exists(module_info.path) or
                not os.listdir(module_info.path)):
            self._get_module(module_info)

        if module_info.path not in sys.path:
            sys.path.insert(0, module_info.path)

    def __enter__(self):
        if isinstance(self.module, str):
            self._load_module(self.module, self.path)
        else:
            for module in self.module:
                self._load_module(module, self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
