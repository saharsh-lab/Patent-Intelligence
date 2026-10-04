"""Markdown report of an invention analysis (download from the UI, paste into documents).

Every chart cell is backed by a cited passage; the report says so, and carries the
disclaimer that this is a technical comparison of retrieved documents only.
"""

SYMBOL = {"disclosed": "✓", "partially_disclosed": "~", "not_found": "–"}


def _cell(cells: dict, feature: str, candidate: str) -> dict:
    return cells.get((feature, candidate), {"verdict": "not_found", "passage": None})


def to_markdown(result: dict, *, created_at: str | None = None) -> str:
    candidates = result["candidates"]
    features = result["features"]
    cells = {(c["feature"], c["candidate"]): c for c in result["cells"]}
    short = {c["key"]: f"D{i}" for i, c in enumerate(candidates, 1)}

    lines = ["# Invention analysis — technical comparison", ""]
    if created_at:
        lines += [f"Created: {created_at}", ""]
    lines += [
        f"> {result['disclaimer']}",
        "",
        "## Invention as described",
        "",
        result["description"],
        "",
    ]

    lines += ["## Technical features", ""]
    for f in features:
        lines.append(f"- **{f['id']}** {f['text']}")
    lines += ["", f"Features were taken from: {features[0]['origin'].replace('_', ' ')}.", ""]

    lines += ["## Closest documents found", ""]
    if not candidates:
        lines += ["No sufficiently similar documents were found in the searched sources.", ""]
    for c in candidates:
        title = f" — {c['title']}" if c.get("title") else ""
        link = f" ({c['url']})" if c.get("url") else ""
        lines.append(
            f"- **{short[c['key']]}** {c['label']}{title}{link}: features disclosed "
            f"{c['disclosed']}/{len(features)}, partially {c['partially']} "
            f"(overlap {round(c['overlap'] * 100)}%)"
        )
    lines.append("")

    if candidates:
        lines += [
            "## Feature chart",
            "",
            "✓ disclosed · ~ partially disclosed · – not found in the retrieved passages",
            "",
        ]
        lines.append("| Feature | " + " | ".join(short[c["key"]] for c in candidates) + " |")
        lines.append("|---|" + "---|" * len(candidates))
        for f in features:
            row = [SYMBOL[_cell(cells, f["id"], c["key"])["verdict"]] for c in candidates]
            lines.append(f"| {f['id']} | " + " | ".join(row) + " |")
        lines.append("")

    not_found = result["not_found_features"]
    lines += ["## Features not found in any retrieved document", ""]
    if not_found:
        text_of = {f["id"]: f["text"] for f in features}
        lines += [f"- **{fid}** {text_of[fid]}" for fid in not_found]
        lines += [
            "",
            "These features were not found in the documents retrieved here. Other documents may "
            "still disclose them.",
        ]
    else:
        lines.append("Every feature was found, at least partially, in a retrieved document.")
    lines.append("")

    lines += ["## Evidence", ""]
    for f in features:
        for c in candidates:
            cell = _cell(cells, f["id"], c["key"])
            if cell.get("passage"):
                quote = " ".join(cell["passage"]["text"].split())
                if len(quote) > 500:
                    quote = quote[:500].rsplit(" ", 1)[0] + " …"
                lines += [
                    f"**{f['id']} in {short[c['key']]}** ({cell['verdict'].replace('_', ' ')}; "
                    f"{cell['passage']['location']}):",
                    "",
                    f"> {quote}",
                    "",
                ]
    lines += [
        "---",
        f"Each ✓/~ was decided by retrieval and an automatic {result['verifier']} check "
        "against the quoted passage, not written by a language model. Automatic checks can "
        "err; read the evidence before relying on it.",
    ]
    return "\n".join(lines) + "\n"
