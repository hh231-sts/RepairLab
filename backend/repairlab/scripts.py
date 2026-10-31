"""Trusted fixture scripts; these encode a known development task, not model skill."""

FIXED_CODE = '''def clamp(value, low, high):
    """Clamp value to the inclusive bounds."""
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))
'''


def tool(name, **arguments):
    return {"calls": [{"id": name, "name": name, "arguments": arguments}]}


def script(name: str) -> list[dict]:
    base = [tool("search", query="clamp"), tool("read_file", path="src/calculator.py")]
    match name:
        case "repair":
            return [
                *base,
                tool("run_tests", paths=["tests"]),
                tool("write_file", path="src/calculator.py", content=FIXED_CODE),
                tool("run_tests", paths=["tests"]),
                {
                    "finish": True,
                    "content": "Development fixture repaired; request independent verification.",
                },
            ]
        case "empty":
            return [{"finish": True}]
        case "wrong":
            return [
                tool(
                    "write_file",
                    path="src/calculator.py",
                    content="def clamp(value, low, high):\n    return low\n",
                ),
                {"finish": True},
            ]
        case "investigate":
            return [
                *base,
                tool("note", text="src/calculator.py contains clamp; investigate reversed bounds behavior."),
                {"finish": True},
            ]
        case "reproduce":
            return [
                tool("run_tests", paths=["tests"]),
                tool("note", text="Public test execution is attached as evidence."),
                {"finish": True},
            ]
        case "implement":
            return [
                tool("write_file", path="src/calculator.py", content=FIXED_CODE),
                tool("run_tests", paths=["tests"]),
                {"finish": True},
            ]
        case "forged":
            return [{"finish": True, "content": "I produced artifact nonexistent and everything passed."}]
        case "injection":
            return [tool("read_file", path="../.env"), {"finish": True}]
        case _:
            raise ValueError("unknown trusted development script")


def fixed_delegations():
    return [
        {
            "key": "investigation",
            "role": "code_investigation",
            "objective": "Locate clamp implementation and provide evidence",
            "scope": ["src/"],
            "deliverables": ["note"],
            "hypothesis": "Boundary handling differs from issue",
            "evidence": ["issue"],
            "script": "investigate",
        },
        {
            "key": "reproduction",
            "role": "reproduction",
            "objective": "Run the public regression test",
            "scope": ["src/", "tests/"],
            "deliverables": ["test_output"],
            "hypothesis": "Public tests reproduce failure",
            "evidence": ["issue"],
            "script": "reproduce",
        },
    ]


def supervisor_script(strategy: str, name: str):
    if name != "repair" or strategy == "single":
        return script(name)
    # Adaptive uses a model-shaped evidence-based request; deterministic here for observability testing.
    delegations = fixed_delegations()
    if strategy == "adaptive":
        return [
            tool("search", query="clamp"),
            {"delegations": delegations},
            {
                "delegations": [
                    {
                        "key": "implementation",
                        "role": "implementation",
                        "objective": "Prepare a repair patch in isolation",
                        "scope": ["src/"],
                        "deliverables": ["patch"],
                        "hypothesis": "Validated source evidence supports a boundary fix",
                        "evidence": ["investigation", "reproduction"],
                        "script": "implement",
                    }
                ]
            },
            tool("integrate", key="implementation"),
            {"finish": True},
        ]
    if strategy == "fixed":
        return [
            {"delegations": delegations},
            {
                "delegations": [
                    {
                        "key": "implementation",
                        "role": "implementation",
                        "objective": "Prepare a scoped patch using accepted evidence",
                        "scope": ["src/"],
                        "deliverables": ["patch"],
                        "hypothesis": "Accepted source and test evidence permit a repair",
                        "evidence": ["investigation", "reproduction"],
                        "script": "implement",
                    }
                ]
            },
            tool("integrate", key="implementation"),
            {"finish": True},
        ]
    return [{"delegations": delegations}, *script("repair")]
