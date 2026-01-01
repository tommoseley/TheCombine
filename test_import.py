import sys
sys.path.insert(0, r'C:\dev\The Combine')
try:
    from app.api.routers.admin import router
    print('Admin router loaded OK')
    for route in router.routes:
        print(f'  {route.methods} {route.path}')
except Exception as e:
    print(f'Error: {e}')
