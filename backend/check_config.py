from app.core.config import Settings
s = Settings()
for f in dir(s):
    if not f.startswith('_') and f.isupper():
        val = getattr(s, f)
        if isinstance(val, str) and len(val) > 60:
            val = val[:60] + '...'
        print(f"{f}: {val}")
