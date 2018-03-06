#!/usr/bin/env python
# -*- coding: utf-8 -*-

from import_module import ImportModule

with ImportModule("github.com/i96751414/py-dummy", reload=False):
    import dummy

if __name__ == "__main__":
    print(dir(dummy))
