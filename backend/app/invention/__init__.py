"""Invention analysis: from an invention description to a cited feature-by-feature chart.

    description (text, or an uploaded draft)
        → technical features              features.py   (claim elements, or LLM + checks)
        → candidate prior-art documents   analysis.py   (local index + EPO search, ranked)
        → feature × candidate chart       analysis.py   (retrieval + NLI per cell, cited)
        → report                          report.py     (Markdown, every cell cited)

Design rule: the chart is *computed*, not written by the LLM. Whether a feature appears
in a document is decided by retrieval plus the NLI verifier, with the passage cited, so
the chart cannot contain an invented disclosure. The output describes technical overlap
only, never novelty, patentability or infringement.
"""
