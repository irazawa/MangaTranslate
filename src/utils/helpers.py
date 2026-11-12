import importlib
import importlib.util
import sys
import time
import requests

_OPTIONAL_DEPENDENCY_ERRORS = {}


class _LazyModuleProxy:
    """Lazy module proxy that only imports the underlying package on attribute access."""

    def __init__(self, module_name: str):
        object.__setattr__(self, "_module_name", module_name)
        object.__setattr__(self, "_module", None)

    def _load(self):
        mod = object.__getattribute__(self, "_module")
        if mod is None:
            name = object.__getattribute__(self, "_module_name")
            mod = importlib.import_module(name)
            object.__setattr__(self, "_module", mod)
        return mod

    def __getattr__(self, item):
        return getattr(self._load(), item)

    def __bool__(self):
        return True


def is_module_installed(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def robust_post(url, headers=None, json_payload=None, timeout=60, max_retries=3, backoff_factor=1.5):
    last_exc = None
    delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(delay)
                delay *= backoff_factor
                continue
            return response
        except (requests.RequestException, requests.Timeout) as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(delay)
                delay *= backoff_factor
            else:
                raise last_exc
    if last_exc:
        raise last_exc
    raise requests.RequestException("Request failed after retries")

def check_dependency(name, install_name=None, lazy=False):
    if lazy:
        try:
            if importlib.util.find_spec(name) is not None:
                return _LazyModuleProxy(name)
            _OPTIONAL_DEPENDENCY_ERRORS[name] = f"Module '{name}' is not installed."
            return None
        except Exception as exc:
            _OPTIONAL_DEPENDENCY_ERRORS[name] = str(exc)
            return None
    try:
        return importlib.import_module(name)
    except Exception as exc:
        _OPTIONAL_DEPENDENCY_ERRORS[name] = str(exc)
        return None

def get_optional_dependency_errors():
    return dict(_OPTIONAL_DEPENDENCY_ERRORS)

def ensure_dependencies(parent, pkgs):
    missing = []
    for mod_name, pkg_name in pkgs:
        try:
            if importlib.util.find_spec(mod_name) is None:
                missing.append(pkg_name)
        except Exception:
            missing.append(pkg_name)
    return missing
