# mcp_server.py
import sys
import os

# Ensure project root is in sys.path so aura imports work regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP

# Import existing tool functions from aura/tools
from aura.tools.calculator import calculate as calc_tool
from aura.tools.weather import fetch_weather as weather_tool
from aura.tools.search import google_search as search_tool

# Initialize FastMCP Server
mcp = FastMCP("Aura Tools Server")


@mcp.tool()
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Supports arithmetic ('(10 - 4) / 2') and single-variable algebraic equations ('20 - (x + x + 6) = 0').
    """
    return calc_tool.invoke({"expression": expression})


@mcp.tool()
def fetch_weather(location: str = "") -> str:
    """
    Fetch current weather report for a given city or location string (e.g. 'Hyderabad', 'Tokyo').
    """
    return weather_tool.invoke({"location": location})


@mcp.tool()
def google_search(query: str) -> str:
    """
    Search Google via SerpAPI for real-time news, current facts, live updates, or real-time event information.
    """
    return search_tool.invoke({"query": query})


if __name__ == "__main__":
    # Runs the MCP server over stdio (standard input/output stream)
    mcp.run(transport="stdio")

