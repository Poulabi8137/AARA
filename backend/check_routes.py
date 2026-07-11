from app.main import app

routes = [r for r in app.routes if hasattr(r, 'path')]
project_routes = [r for r in routes if 'project' in getattr(r, 'path', '')]
for r in project_routes:
    print(f"Path: {r.path}, Methods: {getattr(r, 'methods', 'N/A')}")
