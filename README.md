<h1 align="center">
  <img alt="import-module" src="https://www.python.org/static/opengraph-icon-200x200.png" width="200px" height="200px"/>
  <br/>
  import-module
</h1>
<p align="center">Golang style imports in python</p>
<div align="center">
  <a href="https://www.codacy.com/app/i96751414/import-module?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=i96751414/import-module&amp;utm_campaign=Badge_Grade"><img alt="Codacy Badge" src="https://api.codacy.com/project/badge/Grade/269e5b83c5c14f0e80fa627d4f7fad52" /></a>
  <a href="https://travis-ci.org/i96751414/import-module"><img alt="Build Status" src="https://travis-ci.org/i96751414/import-module.svg?branch=master" /></a>
  <a href="https://www.gnu.org/licenses/"><img alt="License" src="https://img.shields.io/:license-GPL--3.0-blue.svg?style=flat" /></a>
</div>
<br/>

import-module is a python package which allows to import packages as in golang.
Currently it supports modules from [github.com](https://github.com/), [bitbucket.org](https://bitbucket.org), [git.launchpad.net](https://launchpad.net/), and [pypi.python.org](https://pypi.python.org/pypi).

#### Usage

Importing a module (```with``` statement must be used):

```python
from import_module import ImportModule

with ImportModule("github.com/i96751414/py-dummy"):
    import dummy

print("The output of dummy.call is '{}'".format(dummy.call()))
```

Output:
```
The output of dummy.call is 'call'
```

#### API

- **ImportModule**(module, path=None, reload_module=False, use_pip=False)

    Import the specified module. If the module already exists and `reload_module` is True, then re-import the module. If `path` is given, the module will be imported to the given path. If `use_pip` is True, the module will be imported with pip, even if it is a git repository.
