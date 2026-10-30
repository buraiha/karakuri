from pathlib import Path
from django.core.exceptions import ImproperlyConfigured


def database_config(env, base_dir):
    backend = env.get("DB_BACKEND", "sqlite")
    if backend == "sqlite":
        name = Path(env.get("SQLITE_PATH", ".data/db.sqlite3"))
        if not name.is_absolute():
            name = base_dir / name
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name, "OPTIONS": {"timeout": 20}}
    if backend == "postgresql":
        password = env.get("POSTGRES_PASSWORD")
        if not password:
            raise ImproperlyConfigured("POSTGRES_PASSWORD is required for DB_BACKEND=postgresql.")
        return {"ENGINE": "django.db.backends.postgresql", "NAME": env.get("POSTGRES_DB", "karakuri"),
                "USER": env.get("POSTGRES_USER", "karakuri"), "PASSWORD": password,
                "HOST": env.get("POSTGRES_HOST", "127.0.0.1"), "PORT": env.get("POSTGRES_PORT", "55434")}
    if backend == "mysql":
        password = env.get("MYSQL_PASSWORD")
        if not password:
            raise ImproperlyConfigured("MYSQL_PASSWORD is required for DB_BACKEND=mysql.")
        return {"ENGINE": "django.db.backends.mysql", "NAME": env.get("MYSQL_DATABASE", "karakuri"),
                "USER": env.get("MYSQL_USER", "karakuri"), "PASSWORD": password,
                "HOST": env.get("MYSQL_HOST", "127.0.0.1"), "PORT": env.get("MYSQL_PORT", "53306"),
                "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES', default_storage_engine='InnoDB'"},
                "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_0900_ai_ci"}}
    raise ImproperlyConfigured("DB_BACKEND must be sqlite, postgresql or mysql.")
