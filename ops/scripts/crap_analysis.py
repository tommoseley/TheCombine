"""
Compute per-function CRAP scores from pytest-cov JSON output + radon complexity.

Usage: python ops/scripts/crap_analysis.py
Output: prints top functions by CRAP score, writes JSON to /tmp/crap_results.json
"""
import json
import ast
import sys
from pathlib import Path
from collections import defaultdict


def get_function_lines(filepath, func_name, lineno):
    """Get the line range for a function using AST parsing."""
    try:
        source = Path(filepath).read_text()
        tree = ast.parse(source)
    except (SyntaxError, FileNotFoundError):
        return set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name and node.lineno == lineno:
                lines = set()
                for child in ast.walk(node):
                    if hasattr(child, 'lineno'):
                        lines.add(child.lineno)
                return lines
    return set()


def compute_function_coverage(filepath, func_lines, coverage_data):
    """Compute coverage percentage for a specific function."""
    file_cov = coverage_data.get("files", {}).get(filepath)
    if not file_cov or not func_lines:
        return 0.0

    executed = set(file_cov.get("executed_lines", []))
    missing = set(file_cov.get("missing_lines", []))

    func_executed = func_lines & executed
    func_missing = func_lines & missing
    func_total = func_executed | func_missing

    if not func_total:
        return 0.0

    return (len(func_executed) / len(func_total)) * 100


def crap_score(complexity, coverage_pct):
    """Compute CRAP score."""
    return (complexity ** 2) * ((1 - coverage_pct / 100) ** 3) + complexity


# Load data
with open("/tmp/combine_complexity.json") as f:
    complexity_data = json.load(f)

with open("/tmp/combine_coverage.json") as f:
    coverage_data = json.load(f)

# Compute scores
results = []
for filepath, functions in complexity_data.items():
    for func in functions:
        if func["type"] in ("function", "method"):
            func_lines = get_function_lines(
                filepath, func["name"], func["lineno"]
            )
            coverage = compute_function_coverage(
                filepath, func_lines, coverage_data
            )
            score = crap_score(func["complexity"], coverage)
            results.append({
                "file": filepath,
                "function": func["name"],
                "class": func.get("classname", ""),
                "line": func["lineno"],
                "complexity": func["complexity"],
                "coverage": round(coverage, 1),
                "crap": round(score, 1),
            })

# Sort by CRAP score descending
results.sort(key=lambda r: r["crap"], reverse=True)

# Summary stats
total = len(results)
critical = sum(1 for r in results if r["crap"] > 30)
smelly = sum(1 for r in results if 15 <= r["crap"] <= 30)
acceptable = sum(1 for r in results if 5 <= r["crap"] < 15)
clean = sum(1 for r in results if r["crap"] < 5)

scores = [r["crap"] for r in results]
median = sorted(scores)[len(scores) // 2] if scores else 0

print(f"\n=== CRAP Score Summary ===")
print(f"Functions analyzed: {total}")
print(f"Critical (>30):    {critical}")
print(f"Smelly (15-30):    {smelly}")
print(f"Acceptable (5-15): {acceptable}")
print(f"Clean (<5):        {clean}")
print(f"Median CRAP:       {median:.1f}")

print(f"\n=== Top 50 by CRAP Score ===")
for r in results[:50]:
    qual = (f"{r['class']}." if r['class'] else "") + r['function']
    print(f"CRAP={r['crap']:>8.1f}  CC={r['complexity']:>3}  "
          f"Cov={r['coverage']:>5.1f}%  {r['file']}:{r['line']}  {qual}")

# Write full results to JSON
with open("/tmp/crap_results.json", "w") as f:
    json.dump({
        "summary": {
            "total": total,
            "critical": critical,
            "smelly": smelly,
            "acceptable": acceptable,
            "clean": clean,
            "median": median,
        },
        "functions": results,
    }, f, indent=2)

print(f"\nFull results written to /tmp/crap_results.json")
