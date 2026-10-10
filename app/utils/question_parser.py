"""
app/utils/question_parser.py
─────────────────────────────
Parses .txt exam files into question dicts.

Supported format:
    Q: <question text>
    A) <option>
    B) <option>
    C) <option>
    D) <option>
    Answer: A
    Explanation: <text>        ← optional, can span multiple lines
    Reference: <text>          ← optional
    Year: 2018                 ← optional, handles "2018 Yekatit", "2018/19", etc.
"""

import re


# ── Public entry point ────────────────────────────────────────────────────────

def parse_questions_from_text(text: str) -> list[dict]:
    """
    Split text into question blocks (separated by blank lines)
    and parse each one. Returns list of valid question dicts.
    """
    questions = []
    # Split on one or more blank lines
    blocks = re.split(r"\n\s*\n+", text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            q = _parse_block(block)
            if q:
                questions.append(q)
        except Exception:
            continue
    return questions


# ── Single block parser ───────────────────────────────────────────────────────

def _parse_block(block: str) -> dict | None:
    """Parse one question block. Returns dict or None if invalid."""
    result = {
        "question_text": "",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_answer": "",
        "explanation": "",
        "reference": "",
        "year": None,
    }

    lines = [l.rstrip() for l in block.splitlines()]

    # State machine: once we hit Explanation: we collect multi-line text
    mode = None          # None | "question" | "explanation" | "reference"
    explanation_lines = []
    reference_lines   = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line inside block — keep collecting if in multi-line mode
            if mode == "explanation":
                explanation_lines.append("")
            continue

        low = stripped.lower()

        # ── Question text ─────────────────────────────────────────────────
        if re.match(r"^(q:|question:)\s*", stripped, re.IGNORECASE):
            result["question_text"] = re.sub(
                r"^(q:|question:)\s*", "", stripped, flags=re.IGNORECASE
            ).strip()
            mode = "question"
            continue

        # ── Options A–D ───────────────────────────────────────────────────
        m = re.match(r"^([A-Da-d])[)\.\:]\s*(.*)", stripped)
        if m:
            letter = m.group(1).upper()
            value  = m.group(2).strip()
            key    = {"A": "option_a", "B": "option_b",
                      "C": "option_c", "D": "option_d"}.get(letter)
            if key:
                result[key] = value
                mode = None
                continue

        # ── Answer ────────────────────────────────────────────────────────
        if re.match(r"^(answer|ans|correct)\s*:\s*", stripped, re.IGNORECASE):
            ans = re.sub(r"^(answer|ans|correct)\s*:\s*", "",
                         stripped, flags=re.IGNORECASE).strip()
            # Accept "A", "A)", "A." — just take first letter
            ans = ans[0].upper() if ans else ""
            if ans in ("A", "B", "C", "D"):
                result["correct_answer"] = ans
            mode = None
            continue

        # ── Explanation ───────────────────────────────────────────────────
        if re.match(r"^(explanation|exp)\s*:\s*", stripped, re.IGNORECASE):
            first = re.sub(r"^(explanation|exp)\s*:\s*", "",
                           stripped, flags=re.IGNORECASE).strip()
            explanation_lines = [first] if first else []
            mode = "explanation"
            continue

        # ── Reference ────────────────────────────────────────────────────
        if re.match(r"^(reference|ref)\s*:\s*", stripped, re.IGNORECASE):
            first = re.sub(r"^(reference|ref)\s*:\s*", "",
                           stripped, flags=re.IGNORECASE).strip()
            reference_lines = [first] if first else []
            mode = "reference"
            continue

        # ── Year ──────────────────────────────────────────────────────────
        # Handles: "Year: 2018", "Year: 2018 Yekatit", "Year: 2018/19", "Year: E.C 2015"
        if re.match(r"^year\s*:\s*", stripped, re.IGNORECASE):
            year_raw = re.sub(r"^year\s*:\s*", "", stripped, flags=re.IGNORECASE).strip()
            result["year"] = _extract_year(year_raw)
            mode = None
            continue

        # ── Continuation lines ────────────────────────────────────────────
        if mode == "explanation":
            explanation_lines.append(stripped)
        elif mode == "reference":
            reference_lines.append(stripped)
        elif mode == "question":
            # Multi-line question text
            result["question_text"] += " " + stripped

    # Assemble multi-line fields
    if explanation_lines:
        result["explanation"] = " ".join(
            l for l in explanation_lines if l
        ).strip()
    if reference_lines:
        result["reference"] = " ".join(
            l for l in reference_lines if l
        ).strip()

    # ── Validation ────────────────────────────────────────────────────────
    required = ["question_text", "option_a", "option_b",
                "option_c", "option_d", "correct_answer"]
    if not all(result.get(f) for f in required):
        return None

    return result


# ── Year extraction helper ────────────────────────────────────────────────────

def _extract_year(raw: str) -> int | None:
    """
    Extract a 4-digit year from any messy string.
    Examples:
        "2018"            → 2018
        "2018 Yekatit"    → 2018   ← THIS WAS THE BUG
        "2018/19"         → 2018
        "E.C 2015"        → 2015
        "Hidar 2017"      → 2017
        "2023-24"         → 2023
        "not a year"      → None
    """
    # Find all 4-digit numbers in range 1990–2099
    matches = re.findall(r"\b((?:19|20)\d{2})\b", raw)
    if matches:
        return int(matches[0])
    # Fallback: any 4-digit sequence
    matches = re.findall(r"\b(\d{4})\b", raw)
    if matches:
        return int(matches[0])
    return None