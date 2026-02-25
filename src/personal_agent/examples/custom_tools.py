"""
Example custom tools
"""
from personal_agent.tools.base import BaseTool, ToolResult, tool_registry


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "执行数学计算"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2 + 3 * 4'"
            }
        },
        "required": ["expression"]
    }

    async def execute(self, expression: str) -> ToolResult:
        try:
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return ToolResult(
                    success=False,
                    output="",
                    error="表达式包含不允许的字符"
                )

            result = eval(expression)
            return ToolResult(
                success=True,
                output=str(result),
                data={"expression": expression, "result": result}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"计算错误: {str(e)}"
            )


class WeatherTool(BaseTool):
    name = "get_weather"
    description = "获取指定城市的天气信息"
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称"
            }
        },
        "required": ["city"]
    }

    async def execute(self, city: str) -> ToolResult:
        return ToolResult(
            success=True,
            output=f"{city}今天天气晴朗，温度适宜",
            data={"city": city, "weather": "晴", "temperature": "25°C"}
        )


def register_custom_tools():
    tool_registry.register(CalculatorTool())
    tool_registry.register(WeatherTool())


if __name__ == "__main__":
    register_custom_tools()
    print("Custom tools registered!")
    print("Available tools:", tool_registry.list_tools())
