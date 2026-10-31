def clamp(value, low, high):
    """Clamp value to the inclusive bounds."""
    return max(low, min(value, high))
