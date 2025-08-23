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