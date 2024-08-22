import secrets

# Genera una clave secreta segura
secret_key = secrets.token_urlsafe(32)
print(secret_key)

# Genera una clave secreta segura
secret_key_func = secrets.token_urlsafe(32)
print(secret_key_func)