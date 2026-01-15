import ast
with open('syntax_result.txt', 'w') as out:
    try:
        with open('app/domain/services/render_model_builder.py', 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        out.write('SYNTAX_OK')
    except SyntaxError as e:
        out.write(f'ERROR_LINE:{e.lineno}\n')
        out.write(f'ERROR_MSG:{e.msg}\n')
        if e.text:
            out.write(f'ERROR_TEXT:{e.text}\n')
