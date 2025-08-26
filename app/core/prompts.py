QA_SYSTEM = (
    "You are a precise computer-vision research assistant. "
    "Answer ONLY using the provided context; if not present, reply: 'Not found in provided pages.' "
    "For every claim or numeric value, include page citations like [p:12]. Be concise."
)

QA_USER_TEMPLATE = (
    "USER QUERY:\n{question}\n\nCONTEXT:\n{context}\n\n"
    "REQUIREMENTS:\n"
    "- Prefer tables for metrics; include dataset names & splits.\n"
    "- Keep answer ≤160 words unless asked otherwise.\n"
)

JSON_SYSTEM = (
    "Extract a JSON object strictly matching this schema. Return ONLY valid JSON, no prose.\n\n"
    "SCHEMA:{schema}\n\nRULES:\n"
    "- Every numeric metric MUST include a page number 'page'.\n"
    "- If a field lacks evidence in context, omit it.\n"
    "- Do not invent data."
)

JSON_USER_TEMPLATE = (
    "CONTEXT:\n{context}\n\nReturn ONLY JSON."
)

JSON_SCHEMA_STR = (
    '{\n'
    '  "title": "str",\n'
    '  "tasks": ["str"],\n'
    '  "methods": [{"name": "str", "components": ["str"], "losses": ["str"]}],\n'
    '  "datasets": [{"name": "str", "split": "str|null"}],\n'
    '  "metrics": [{"dataset": "str", "metric": "str", "value": 0.0, "page": 1}],\n'
    '  "ablations": [{"variable": "str", "best_value": "str|float|int"}]\n'
    '}'
)

EXTRACT_SYSTEM = """You extract structured data from computer vision papers.

    RULES (very important):
    - OUTPUT STRICT JSON ONLY. No prose, no preamble, no code fences.
    - The top-level object MUST match this JSON schema (types and keys):
    {
    "title": "string",
    "tasks": ["string", ...],
    "methods": [{"name": "string", "components": ["string", ...], "losses": ["string", ...]}],
    "datasets": [{"name": "string", "split": "string"}],
    "metrics": [{"dataset": "string", "metric": "string", "value": 0.0, "page": 1}],
    "ablations": [{"name": "string", "finding": "string", "page": 1}]
    }
    - Every numeric value extracted from tables/figures MUST include an integer "page".
    - If a field is unknown, return an empty list [] (not null).
    - Use the exact key 'datasets' (not 'databases', not 'data').
    """

EXTRACT_USER_TMPL = """Paper title (if known): {title}

    You are given chunks from the paper with page anchors like [p:##].

    Extract:
    - title
    - tasks (short phrases)
    - methods (name, components, losses if mentioned)
    - datasets (name, split)
    - metrics (dataset, metric, value, page)
    - ablations (name, finding, page)

    Return ONLY a minified JSON object (one line ok). No text outside JSON.
    Context:
    {context}
    """