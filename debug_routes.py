import sys
sys.path.insert(0, 'app')

from auth import routes

print("Module loaded successfully")
print(f"Router object: {routes.router}")
print(f"Router type: {type(routes.router)}")
print(f"Router prefix: {routes.router.prefix}")
print(f"Number of routes: {len(routes.router.routes)}")
print()

if len(routes.router.routes) == 0:
    print("ERROR: No routes registered!")
    print()
    print("Checking if functions exist in module:")
    print(f"  login function: {hasattr(routes, 'login')}")
    print(f"  callback function: {hasattr(routes, 'callback')}")
    print(f"  logout function: {hasattr(routes, 'logout')}")
    print()
    print("This means the @router.get() and @router.post() decorators didn't work.")
    print("Possible causes:")
    print("  1. Syntax error in routes.py")
    print("  2. Import error during module load")
    print("  3. Router created after decorators")
else:
    print("Routes registered:")
    for i, route in enumerate(routes.router.routes):
        print(f"{i+1}. Path: {route.path}, Methods: {getattr(route, 'methods', 'N/A')}")