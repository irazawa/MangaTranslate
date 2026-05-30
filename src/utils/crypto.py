import os
import copy
from cryptography.fernet import Fernet

def _get_fernet():
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.secret.key')
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read().strip()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
    return Fernet(key)

def _is_secret_key(k):
    return k in ('api_key', 'value')

def _encrypt_dict(d, fernet):
    if isinstance(d, dict):
        new_d = {}
        for k, v in d.items():
            if _is_secret_key(k) and isinstance(v, str) and v and not v.startswith('gAAAAA'):
                new_d[k] = fernet.encrypt(v.encode('utf-8')).decode('utf-8')
            else:
                new_d[k] = _encrypt_dict(v, fernet)
        return new_d
    elif isinstance(d, list):
        return [_encrypt_dict(i, fernet) for i in d]
    else:
        return d

def _decrypt_in_place(d, fernet):
    if isinstance(d, dict):
        for k, v in d.items():
            if _is_secret_key(k) and isinstance(v, str) and v.startswith('gAAAAA'):
                try:
                    d[k] = fernet.decrypt(v.encode('utf-8')).decode('utf-8')
                except Exception:
                    pass
            else:
                _decrypt_in_place(v, fernet)
    elif isinstance(d, list):
        for i in d:
            _decrypt_in_place(i, fernet)

def encrypt_settings_keys(settings):
    """Encrypt settings keys on save."""
    if not settings:
        return settings
    return _encrypt_dict(settings, _get_fernet())

def decrypt_settings_keys(settings):
    """Decrypt settings keys on load. Keys are mutated in-place."""
    if not settings:
        return settings
    _decrypt_in_place(settings, _get_fernet())
    return settings
