# Route Inspector
import sys
sys.path.insert(0, 'app')

from auth.routes import router

print("Router prefix:", router.prefix)
print("Number of routes:", len(router.routes))
print()
print("Registered routes:")
for route in router.routes:
    print(f"  Path: {route.path}")
    if hasattr(route, 'methods'):
        print(f"  Methods: {route.methods}")
    if hasattr(route, 'name'):
        print(f"  Name: {route.name}")
    print()