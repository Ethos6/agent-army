"""Form Builder

Describe a form ("event registration with dietary needs and a plus-one") and get a production-ready,
accessible HTML form: semantic labels, sensible input types, client-side validation, helpful error
messages and a JSON preview of submitted data. It is one self-contained file you can drop into any
site.
"""
from army import Agent
from army.tools import write_file

META = {
    "category": "ui",
    "description": "Plain-English description to an accessible, validated, self-contained HTML form.",
    "example": "A volunteer sign-up form: name, email, availability by weekday, skills, t-shirt size, consent checkbox",
}
EVALS = [{"input": "A simple contact form with name, email and message", "must_contain": ["saved", ".html"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="form-builder",
        instructions="""You are a senior front-end engineer focused on accessibility.
Write ONE self-contained HTML file: <label for> on every field, correct input types (email, tel, date, number),
required/pattern attributes, fieldsets for groups, inline error messages linked with aria-describedby, keyboard-friendly,
responsive, no external assets. On submit, prevent default and show the collected data as formatted JSON.
Save with `write_file` (form.html). Final answer: path and a field list (name, type, validation).""",
        tools=[write_file],
        llm=llm,
    )
