"""
Simple hello world function module for demonstration purposes.
"""


def hello_world():
    """Return a simple hello world greeting."""
    return "Hello, World!"


def greet(name="World"):
    """Return a personalized greeting."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(hello_world())
    print(greet("Summit AI"))
