"""Minimal stand-in for the parts of ``mmcv`` 1.7.x that SANA imports.

The upstream SANA environment installs ``mmcv==1.7.2`` purely for its
``Registry`` / ``Config`` helpers. That package only ships an sdist whose
``setup.py`` imports ``pkg_resources`` (removed in setuptools 81), so it
cannot be pip-installed on a modern Spaces image. Only the handful of
symbols SANA actually touches are reimplemented here, with the same
semantics as mmcv 1.7.2.
"""

import inspect
import json
import os
import pickle


def mkdir_or_exist(dir_name, mode=0o777):
    if dir_name == "":
        return
    os.makedirs(os.path.expanduser(dir_name), mode=mode, exist_ok=True)


def dump(obj, file, **kwargs):
    with open(file, "wb") as handle:
        pickle.dump(obj, handle)


def load(file, **kwargs):
    with open(file, "rb") as handle:
        return pickle.load(handle)


def build_from_cfg(cfg, registry, default_args=None):
    """Build a module from a config dict (mmcv 1.7.2 semantics)."""
    if not isinstance(cfg, dict):
        raise TypeError(f"cfg must be a dict, but got {type(cfg)}")
    if "type" not in cfg:
        raise KeyError(f'`cfg` must contain the key "type", but got {cfg}')
    args = cfg.copy()
    if default_args is not None:
        for name, value in default_args.items():
            args.setdefault(name, value)

    obj_type = args.pop("type")
    if isinstance(obj_type, str):
        obj_cls = registry.get(obj_type)
        if obj_cls is None:
            raise KeyError(f"{obj_type} is not in the {registry.name} registry")
    elif inspect.isclass(obj_type) or inspect.isfunction(obj_type):
        obj_cls = obj_type
    else:
        raise TypeError(f"type must be a str or valid type, but got {type(obj_type)}")
    return obj_cls(**args)


class Registry:
    def __init__(self, name, build_func=None):
        self.name = name
        self._module_dict = {}
        self.build_func = build_func or build_from_cfg

    def __len__(self):
        return len(self._module_dict)

    def __contains__(self, key):
        return key in self._module_dict

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, items={list(self._module_dict)})"

    @property
    def module_dict(self):
        return self._module_dict

    def get(self, key):
        return self._module_dict.get(key)

    def build(self, *args, **kwargs):
        return self.build_func(*args, **kwargs, registry=self)

    def _register(self, module, name=None, force=False):
        names = name if isinstance(name, (list, tuple)) else [name or module.__name__]
        for key in names:
            if not force and key in self._module_dict:
                raise KeyError(f"{key} is already registered in {self.name}")
            self._module_dict[key] = module
        return module

    def register_module(self, name=None, force=False, module=None):
        if module is not None:
            return self._register(module, name=name, force=force)

        def _wrapper(cls):
            return self._register(cls, name=name, force=force)

        return _wrapper


class ConfigDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class Config(ConfigDict):
    """Very small subset of ``mmcv.Config`` (only ever used for dict access)."""

    @staticmethod
    def fromfile(filename):
        with open(filename) as handle:
            return Config(json.load(handle))

    @staticmethod
    def _merge_a_into_b(a, b):
        merged = dict(b)
        merged.update(a)
        return Config(merged)
