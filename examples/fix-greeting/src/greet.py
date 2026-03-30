"""Greeting utilities — a tiny library with a deliberate bug."""


def greet(name: str) -> str:
    """Return a personalised greeting for *name*.

    Args:
        name: The person to greet.

    Returns:
        A greeting string like ``"Hello, Alice!"``.
    """
    # BUG: the greeting is missing the person's name.
    return "Hello, !"
