def encrypt_settings_keys(settings):
    """Encrypt settings keys on save. Stored as plain-text for compatibility or direct API use."""
    return settings

def decrypt_settings_keys(settings):
    """Decrypt settings keys on load. Keys are stored as plain-text on disk."""
    return settings
