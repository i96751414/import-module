#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import git


class ImportModule(object):
    def __init__(self, module, reload=False):
        if not isinstance(module, (str, tuple, list)):
            raise AttributeError("module must be either str or tuple/list")
        if isinstance(module, (tuple, list)):
            for value in module:
                if not isinstance(value, str):
                    raise AttributeError("url must be composed of str values")

        self.module = module
        self.reload = reload
        self.modules_path = os.path.abspath("__importmodule__")

    def _get_module(self, module, path):
        # TODO Add Bitbucket, GitHub, Google Code, and Launchpad
        if module.startswith("github.com/"):
            git.Repo.clone_from("https://{}".format(module), path)
            self._chmod(path, 0o777)
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
        module_path = os.path.join(self.modules_path, module)

        if self.reload and os.path.exists(module_path):
            self._remove_tree(module_path)
        if not os.path.exists(module_path):
            os.makedirs(module_path)
            self._get_module(module, module_path)
        elif not os.listdir(module_path):
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
