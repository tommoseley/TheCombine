import sys
sys.path.insert(0, '.')
try:
    from app.domain.services.render_model_builder import RenderModelBuilder
    print('IMPORT_SUCCESS')
except Exception as e:
    print(f'IMPORT_FAILED: {type(e).__name__}: {e}')
