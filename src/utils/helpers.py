import importlib
import sys
import time
import requests

_OPTIONAL_DEPENDENCY_ERRORS = {}

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

def check_dependency(name, install_name=None):
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
            importlib.import_module(mod_name)
        except Exception:
            missing.append(pkg_name)
    return missing
