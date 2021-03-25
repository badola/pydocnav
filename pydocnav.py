#!/usr/bin/env python

from flask import *
import importlib
import inspect
from contextlib import redirect_stdout
import functools
import pkg_resources
import io
import os

def str_to_class(class_name_str):
    components = class_name_str.split('.')
    module_name = '.'.join(components[0:-1])
    class_name = components[-1]
    return getattr(importlib.import_module(module_name), class_name)

def safe_execute(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try   : return func(*args, **kwargs)
        except: return None
    return inner

@safe_execute
def _version(qualified_module_name):
    version = pkg_resources.get_distribution(qualified_module_name).version
    return '[{}]'.format(version) if version else ''

@safe_execute
def _file_location(qualified_module_name):
    location = inspect.getfile(str_to_class(qualified_module_name))
    return '({})'.format(location) if location else ''

@safe_execute
def _guess_parent_module(qualified_module_name):
    module_location = inspect.getmodule(str_to_class(qualified_module_name))
    if module_location:
        return '{}'.format(module_location)
    return None

@safe_execute
def _getmembers(qualified_module_name):
    members = inspect.getmembers(str_to_class(qualified_module_name))
    return '\n'.join(members) if members else ''

@safe_execute
def _gethelp(qualified_module_name):
    with io.StringIO() as buf, redirect_stdout(buf):
        help(qualified_module_name)
        return buf.getvalue()

@safe_execute
def _getstr(qualified_module_name, function_to_apply):
    with io.StringIO() as buf, redirect_stdout(buf):
        print(function_to_apply(str_to_class(qualified_module_name)))
        return buf.getvalue()

def _doc_str(qualified_module_name):
    return _getstr(qualified_module_name, inspect.getdoc)

def _source_str(qualified_module_name):
    return _getstr(qualified_module_name, inspect.getsource)

def _getdir(import_statement, module_address, max_depth, display_qualified_name):
    res = {}

    @safe_execute
    def _dirs():
        qualified_module_name = '{0}.{1}'.format(import_statement, module_address) if module_address else import_statement
        return dir(str_to_class(qualified_module_name))

    if max_depth > 0:
        modules = _dirs()
        if modules:
            for module in modules:
                if not module.startswith('_'): # omit private members and internal functions
                    module = '{0}.{1}'.format(module_address, module) if module_address else module
                    qualified_module_name = '{0}.{1}'.format(import_statement, module) if display_qualified_name else module.split('.')[-1]
                    res[qualified_module_name] = _getdir(import_statement, module, max_depth - 1, display_qualified_name)
    return res

def _dir(qualified_module_name):
    modules = _getdir(qualified_module_name, '', 1, True)
    return '\n'.join(modules) if modules else ''

def _child_modules(qualified_module_name):
    members_via_inspect = _getmembers(qualified_module_name)
    members_via_dir = _dir(qualified_module_name)
    return members_via_inspect if members_via_inspect else members_via_dir

def _parent(qualified_module_name):
    parent_module = _guess_parent_module(qualified_module_name)
    return parent_module if parent_module else '.'.join(qualified_module_name.split('.')[0:-1])

def _module_header(qualified_module_name):
    def _append_fmt(value):
        return ' {}'.format(value) if value else ''

    header = qualified_module_name
    header += _append_fmt(_version(qualified_module_name))
    header += _append_fmt(_file_location(qualified_module_name))
    return header

def render(mod_name):
    return render_template('pydocnav.jinja'
                          ,module_header     = _module_header(mod_name)
                          ,module_name       = mod_name
                          ,parent_module_name= _parent(mod_name)
                          ,child_modules     = _child_modules(mod_name)
                          ,documentation     = _doc_str(mod_name)
                          ,help_str          = _gethelp(mod_name)
                          ,source_code       = _source_str(mod_name)
                          )

app = Flask(__name__)

@app.route('/response', methods=['POST'])
def response():
    f_module_name = request.form.get('f_module_name')
    return render(f_module_name.strip())

@app.route("/")
def index():
    mod_name = 'os.path'
    return render(mod_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8085', debug=True)
