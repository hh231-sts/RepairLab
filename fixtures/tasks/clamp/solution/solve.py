from pathlib import Path

Path("/workspace/src/calculator.py").write_text('''def clamp(value, low, high):
    """Clamp value to the inclusive bounds."""
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))
''')
