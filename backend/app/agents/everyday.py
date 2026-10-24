"""Everyday questions in the chat: exact answers that need no source, and general
knowledge when no source has the answer.

Observed (2026-10-22): "What day is it?" took 18 s of searching and ended in "I couldn't
find this". The user asked for the chat to handle such questions like a general assistant.

- Date and time come from the clock (in the user's time zone), arithmetic from a small
  calculator: computed, not generated, so exact.
- General knowledge: when the library, the patent offices and the web have nothing, or for
  a writing task ("write a poem about batteries"), the language model answers from what it
  learned in training. Such answers are labelled "not from sources, not checked": the
  checker needs passages to check against, so it cannot vouch for them.
Chat only; the /ask API and the experiments never use the general-knowledge answer.
"""

import ast
import math
import operator
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ---------------------------------------------------------------- clock

_CLOCK = re.compile(
    r"^\s*(?:hey|hi|so|ok|okay)?[\s,]*(?:"
    r"what(?:'s|\s+is)?\s+(?:the\s+)?(?:date|day|time|year|month)(?:\s+(?:is\s+it|today|now|"
    r"it\s+is|right\s+now))*"
    r"|what\s+(?:day|date|time|year|month)\s+(?:is\s+it|is\s+today|it\s+is)(?:\s+(?:today|now|"
    r"right\s+now))?"
    r"|(?:tell\s+me\s+)?(?:today'?s|the\s+current|current)\s+(?:date|day|time)"
    r"|which\s+day\s+is\s+(?:it|today)"
    r"|date\s+today|time\s+now"
    r")(?:\s+please)?[\s!.?]*$",
    re.IGNORECASE,
)


def asks_for_time(text: str) -> bool:
    return bool(_CLOCK.match(text or ""))


def zone(name: str | None) -> ZoneInfo | None:
    try:
        return ZoneInfo(name) if name else None
    except (ZoneInfoNotFoundError, ValueError):
        return None


def now_in(timezone: str | None) -> datetime:
    tz = zone(timezone)
    return datetime.now(tz) if tz else datetime.now().astimezone()


def clock_reply(text: str, timezone: str | None) -> str:
    now = now_in(timezone)
    where = f" ({timezone})" if zone(timezone) else ""
    day = f"{now:%A}, {now.day} {now:%B %Y}"
    lowered = text.lower()
    if "time" in lowered and not re.search(r"\b(date|day)\b", lowered):
        return f"It's **{now:%H:%M}**{where}, on {day}."
    if "year" in lowered and not re.search(r"\b(date|day)\b", lowered):
        return f"It's **{now:%Y}**."
    if "month" in lowered and not re.search(r"\b(date|day)\b", lowered):
        return f"It's **{now:%B %Y}**."
    return f"Today is **{day}**. The time is {now:%H:%M}{where}."


# ---------------------------------------------------------------- calculator

_LEAD = re.compile(
    r"^\s*(?:(?:what(?:'s|\s+is)|whats|how\s+much\s+is|calculate|compute|evaluate|solve)\s+)?",
    re.IGNORECASE,
)
_PERCENT_OF = re.compile(
    r"^([\d.]+)\s*(?:%|percent)\s+of\s+([\d.]+)$",
    re.IGNORECASE,
)
_MATH_CHARS = re.compile(r"^[\d\s.+\-*/()^%]+$")
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _evaluate(node: ast.AST) -> float:
    """Numbers and + - * / ** % only: no names, calls or attributes can run."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
            raise ValueError("too large")
        return _OPS[type(node.op)](left, right)
    raise ValueError("not arithmetic")


def _number(value: float) -> str:
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.10g}" if abs(value) < 1e15 else f"{value:.6g}"


def calculation(text: str) -> tuple[str, str] | None:
    """(expression as shown, result) when the whole message is a sum, else None."""
    body = _LEAD.sub("", (text or "").strip()).rstrip("?=. ").strip()
    body = re.sub(r"(?<=\d),(?=\d{3}\b)", "", body)  # 1,200 → 1200
    body = body.replace("×", "*").replace("÷", "/").replace("−", "-")
    body = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", body)
    percent = _PERCENT_OF.match(body)
    try:
        if percent:
            a, b = float(percent.group(1)), float(percent.group(2))
            return f"{_number(a)}% of {_number(b)}", _number(a / 100 * b)
        if not _MATH_CHARS.match(body) or not re.search(r"\d\s*[-+*/^%]\s*[\d(]", body):
            return None
        tree = ast.parse(body.replace("^", "**"), mode="eval")
        value = _evaluate(tree)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    shown = " ".join(body.split()).replace("**", "^").replace("*", " × ").replace("/", " / ")
    return " ".join(shown.split()), _number(value)


def calculator_reply(text: str) -> str | None:
    result = calculation(text)
    return None if result is None else f"{result[0]} = **{result[1]}**"


def is_everyday(text: str) -> bool:
    return asks_for_time(text) or calculation(text) is not None


# ---------------------------------------------------------------- general knowledge

# Writing tasks a source search cannot help with: answered directly in the chat
_CREATIVE = re.compile(
    r"^\s*(?:please\s+|can\s+you\s+|could\s+you\s+)?(?:write|compose|draft|make\s+up|create)"
    r"\s+(?:me\s+)?(?:a|an|some|short|funny)?\s*(?:short\s+|funny\s+)?"
    r"(?:poem|story|joke|song|haiku|limerick|riddle|tagline|slogan|tweet|caption)s?\b"
    r"|^\s*(?:tell|give)\s+me\s+(?:a|another)\s+(?:joke|riddle|fun\s+fact)\b",
    re.IGNORECASE,
)


def is_creative(text: str) -> bool:
    return bool(_CREATIVE.match(text or ""))


GENERAL_PROMPT = """\
You are the assistant of a patent research app. Answer the user's message from your general
knowledge, helpfully and accurately, in the style of a good chat assistant: a direct answer
first, then the key details. Use short paragraphs, and a bulleted list where it helps.
Keep it under about 200 words unless asked for more.
If you are not sure of something, say so. Do not invent sources, citations, patent numbers,
statistics or quotes. Do not give legal advice (validity, infringement, freedom to operate).
Today is {today}."""
