"""
aura/tools/calculator.py
------------------------
Safe arithmetic & SymPy algebraic equation solver tool.
"""

import re
import logging
from langchain_core.tools import tool
from aura.tools.base import TOOL_REGISTRY, LANGCHAIN_TOOLS

logger = logging.getLogger(__name__)

_SAFE_CHARS = re.compile(r"^[\d\s\+\-\*\/\%\(\)\.]+$")
_VAR_PATTERN = re.compile(r"[a-zA-Z]")


@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Supports pure numeric expressions ('(10 - 4) / 2') and single-variable algebraic equations ('20 - (x + x + 6) = 0').
    """
    expr = expression.strip()

    # Route to SymPy for algebraic solver if variables are detected
    if _VAR_PATTERN.search(expr):
        try:
            import sympy
            if ";" in expr:
                expr = expr.split(";")[0].strip()
            if "=" in expr:
                parts = expr.split("=")
                if len(parts) == 2:
                    expr = f"({parts[0].strip()}) - ({parts[1].strip()})"

            variables = sorted(set(_VAR_PATTERN.findall(expr)))
            if len(variables) > 1:
                return f"Error: Multiple variables detected ({', '.join(variables)}). Only single-variable equations are supported."

            var = sympy.Symbol(variables[0])
            solutions = sympy.solve(sympy.sympify(expr), var)
            if not solutions:
                return f"No solution found for '{variables[0]}' in expression: {expression}"

            results = []
            for sol in solutions:
                try:
                    v = float(sol)
                    results.append(str(int(v)) if v.is_integer() else str(v))
                except Exception:
                    results.append(str(sol))

            return f"Result: {variables[0]} = {', '.join(results)}"
        except Exception as e:
            return f"Error solving algebraic expression: {e}"

    # Pure arithmetic evaluation
    if not _SAFE_CHARS.match(expr):
        return "Error: Expression contains invalid characters. Only numbers and basic operators (+, -, *, /, %, brackets) are allowed."
    if any(kw in expr for kw in ("__", "import", "eval", "exec", "open")):
        return "Error: Unsafe expression detected."

    try:
        res = eval(expr, {"__builtins__": None}, {})
        if isinstance(res, float) and res.is_integer():
            res = int(res)
        return f"Result: {res}"
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"


# Register in registry
TOOL_REGISTRY["calculate"] = calculate
LANGCHAIN_TOOLS.append(calculate)
