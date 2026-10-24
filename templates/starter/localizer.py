"""Translator & Localizer

Translates text so it reads as if written by a native speaker for the target market: it adapts
idioms, units, dates and formality, keeps your brand terms consistent with a glossary, and lists
every place it deliberately changed meaning so a reviewer can check them.
"""
from army import Agent

META = {
    "category": "starter",
    "description": "Native-sounding translation that adapts idioms, units and formality, with a glossary and change log.",
    "example": "Localize for Japanese customers: 'Our new plan is a home run - sign up by Friday and save 20%!'",
}
EVALS = [{"input": "Translate to Spanish (Mexico), formal: 'Your order ships tomorrow.'", "must_contain": ["Translation", "Notes"], "max_seconds": 60}]


def build(llm=None, glossary: str = ""):
    extra = f"\nAlways keep these terms exactly as given: {glossary}" if glossary else ""
    return Agent(
        name="localizer",
        instructions=f"""You are a professional localizer. Detect the source language; infer the target language, region and
formality from the request (ask yourself what a native copywriter in that market would write).{extra}

Output:
## Translation
<the localized text>
## Back-translation
<literal English rendering so a reviewer can check meaning>
## Notes
- every idiom, unit, date, currency or cultural reference you adapted, and why
- formality level used
## Glossary
| Source term | Target term |""",
        llm=llm,
    )
