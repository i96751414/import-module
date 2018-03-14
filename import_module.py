#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["GitError", "ModuleNotFound", "DownloadFailed", "ImportModule"]

import os
import re
import sys
import git
import pip
import errno
import pkg_resources

_MODULES_PATH = os.path.abspath("__importmodule__")
_ERROR_INVALID_NAME = 123

_TYPE_GIT = 0
_TYPE_PIP = 1
_TYPE_GIT_PIP = 2


class GitError(ImportError):
    pass


class PipError(ImportError):
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


class _ModuleInfo:
    def __init__(self, module, path=None, use_pip=False):
        module = re.sub(r"[\\/]+", "/", module)
        module = re.sub("/$", "", module)

        match = _Function(re.match)
        if match(r"^(github\.com|bitbucket\.org|git\.launchpad\.net)/", module):
            _path = re.sub(r"(?<=[^/])\.git$", "", module)
            _module_name = _path.split("/")[-1]
            if use_pip:
                _type = _TYPE_GIT_PIP
                module = "git+https://{}".format(module)
            else:
                _type = _TYPE_GIT
                module = "https://{}".format(module)

        elif match(r"^(pypi\.python\.org/pypi)/([-\w.]+)/([\w.]+)$", module):
            _type = _TYPE_PIP
            _path = match.result.group(1)
            _module_name = match.result.group(2)
            module = "{}=={}".format(_module_name, match.result.group(3))

        elif match(r"^(pypi\.python\.org/pypi)/([-\w.]+)$", module):
            _type = _TYPE_PIP
            _path = match.result.group(1)
            _module_name = match.result.group(2)
            module = _module_name

        else:
            raise NotImplementedError("Type of module not supported")

        if path is not None:
            _path = path

        if not self._is_pathname_valid(_path):
            _path = self._get_valid_path(_path)

        self.module = module
        self.module_name = _module_name
        self.path = os.path.join(_MODULES_PATH, _path)
        self.type = _type

    @property
    def is_installed(self):
        if self.type == _TYPE_PIP:
            env = pkg_resources.Environment([self.path])
            for project in env:
                if project == self.module_name:
                    return True
            return False
        else:
            return os.path.exists(self.path) and os.listdir(self.path)

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
    def __init__(self, module, path=None, reload_module=False, use_pip=False):
        """
        Import the specified module. If the module already exists and
        `reload_module` is True, then re-import the module. If `path` is
        given, the module will be imported to the given path. If `use_pip`
        is True, the module will be imported with pip, even if it is a git
        repository.

        :param module: module to import.
        :param path: path where to import the module.
        :param reload_module: reload module if already it exists.
        :param use_pip: always use pip to get modules.
        """
        if not isinstance(module, (str, tuple, list)):
            raise AttributeError("module must be either str or tuple/list")
        if isinstance(module, (tuple, list)):
            for value in module:
                if not isinstance(value, str):
                    raise AttributeError("url must be composed of str values")
        if not (path is None or isinstance(path, str)):
            raise AttributeError("path must be either None or str")
        if not isinstance(reload_module, bool):
            raise AttributeError("reload_module must be either True or False")
        if not isinstance(use_pip, bool):
            raise AttributeError("force_pip must be either True or False")

        self.module = module
        self.path = path
        self.reload = reload_module
        self.use_pip = use_pip

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
            if os.path.exists(module_info.path):
                self._remove_tree(module_info.path)
            try:
                git.Repo.clone_from(
                    module_info.module, module_info.path, depth=1)
            except Exception as e:
                raise GitError(e)
            self._chmod(module_info.path, 0o755)

        elif module_info.type in {_TYPE_PIP, _TYPE_GIT_PIP}:
            args = ["install", module_info.module, "--isolated", "--target",
                    module_info.path, "--quiet"]
            if module_info.type == _TYPE_GIT_PIP:
                args.append("--no-dependencies")
            if self.reload:
                args.append("--upgrade")
            try:
                return_code = pip.main(args)
            except Exception as e:
                raise PipError(e)
            else:
                if return_code != 0:
                    raise PipError(
                        "Failed to import module with error {}".format(
                            return_code))

        else:
            raise NotImplementedError("Type of module not supported")

    def _load_module(self, module):
        module_info = _ModuleInfo(module, self.path, self.use_pip)

        if self.reload or not module_info.is_installed:
            self._get_module(module_info)

        if module_info.path not in sys.path:
            sys.path.insert(0, module_info.path)

    def __enter__(self):
        if isinstance(self.module, str):
            self._load_module(self.module)
        else:
            for module in self.module:
                self._load_module(module)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
