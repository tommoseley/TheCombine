import sys
sys.path.insert(0, '/home/tommoseley/dev/TheCombine')
try:
    from app.domain.workflow.plan_executor import PlanExecutor
    from app.api.v1.routers.document_workflows import router
    print("OK - imports successful")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"FAIL: {e}")