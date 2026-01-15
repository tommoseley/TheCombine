import ast
try:
    with open(r'C:\Dev\The Combine\app\domain\services\document_builder.py', 'r', encoding='utf-8') as f:
        ast.parse(f.read())
    with open('syntax_result.txt', 'w') as out:
        out.write('SYNTAX_OK')
except SyntaxError as e:
    with open('syntax_result.txt', 'w') as out:
        out.write(f'ERROR: Line {e.lineno}: {e.msg}')
