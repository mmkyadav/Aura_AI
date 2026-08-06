"""
tests/test_tools.py
-------------------
Unit tests for Aura's tool functions (calculator, weather, search).
"""

import pytest
from aura.tools.calculator import calculate
from aura.tools.weather import fetch_weather
from aura.tools.search import google_search


def test_calculator_arithmetic():
    """Test pure numeric calculations."""
    res = calculate.invoke({"expression": "(5 * 10) + 20"})
    assert "Result: 70" in res


def test_calculator_algebraic():
    """Test single-variable SymPy equation solving."""
    res = calculate.invoke({"expression": "20 - (x + x + 6) = 0"})
    assert "Result: x = 7" in res


def test_calculator_safety():
    """Test forbidden characters or malicious code prevention."""
    res = calculate.invoke({"expression": "__import__('os').system('dir')"})
    assert "Error:" in res


def test_weather_empty_location():
    """Test weather tool with invalid location."""
    res = fetch_weather.invoke({"location": ""})
    assert "Error:" in res
