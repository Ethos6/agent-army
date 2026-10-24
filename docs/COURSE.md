# Build AI agents with Agent Army: a hands-on course

Eight short lessons. Each one runs with any model, including a free local one:

```bash
pip install -e .
export ARMY_MODEL=ollama:llama3.2      # or anthropic:..., openai:..., gemini:...
```

## Lesson 1: your first agent

```python
from army import Agent

agent = Agent("haiku-bot", "You write haiku about whatever the user mentions.")
print(agent.run("a cold cup of coffee on Monday"))
```

An agent is a name, instructions and (optionally) tools. With no tools, it is a single model call.

## Lesson 2: give it tools

```python
from army import Agent, tool

@tool
def celsius_to_fahrenheit(c: float) -> float:
    """Convert a temperature from Celsius to Fahrenheit."""
    return c * 9 / 5 + 32

agent = Agent("weather-helper", "Answer temperature questions using your tools.", tools=[celsius_to_fahrenheit])
result = agent.run("Is 31 C hot in Fahrenheit terms?")
print(result.output)
for step in result.steps:
    print(step.kind, step.tool, step.args, step.content[:80])
```

The type hints and the first docstring line become the tool spec the model sees. The step trace shows exactly what happened.

## Lesson 3: built-in tools

```python
from army import Agent
from army.web import web_search, weather
from army.tools import calculate

agent = Agent("trip-check", "Answer with live data. Cite sources.", tools=[web_search, weather, calculate])
print(agent.run("Will it rain in Mumbai this week, and what is 1,500 INR in USD roughly?"))
```

Browse `army/tools.py` and `army/web.py`: every tool is a short, readable function.

## Lesson 4: structured output

Put the format in the instructions and verify it with evals (Lesson 8):

```python
agent = Agent("triage", """Classify the support message.
Reply as JSON: {"final": {"category": "billing|bug|how-to", "urgency": 1-5, "summary": "..."}}""")
print(agent.run("I was charged twice this month and need a refund today"))
```

## Lesson 5: retrieval (RAG)

```python
from army import Agent
from army.rag import index_folder, search_tool

index = index_folder("examples/knowledge-base")
agent = Agent("docs", "Answer only from search_docs results and cite [file:lines].", tools=[search_tool(index)])
print(agent.run("What is the refund window?"))
```

Swap in `HybridIndex(index)` for keyword plus embedding search; the agent code doesn't change.

## Lesson 6: memory

```python
from army import Agent
from army.memory import MEMORY_RULES, Memory

mem = Memory("course")
agent = Agent("buddy", "You are a helpful friend.\n" + MEMORY_RULES, tools=mem.tools())
agent.run("My dog is called Biscuit.")
print(agent.run("What's my dog's name?"))   # works in a new Python session too
```

## Lesson 7: teams

```python
from army import Agent, Panel, Pipeline

writer = Agent("writer", "Write a 100-word product blurb.")
editor = Agent("editor", "Tighten the draft. Return only the final copy.")
print(Pipeline(writer, editor).run("A water bottle that tracks hydration"))

judges = [Agent(f"judge{i}", "Rate the slogan 1-10 with one reason.") for i in range(3)]
chair = Agent("chair", "Combine the ratings into a verdict.")
print(Panel(judges, chair).run("Slogan: 'Drink smarter.'"))
```

Use `worker.as_tool("description")` to let a manager agent delegate, and give each agent its own `llm=get_llm(...)` to mix models.

## Lesson 8: ship it as a template

```bash
army new marketing tagline-tester       # scaffolds templates/marketing/tagline_tester.py
army validate
army eval tagline-tester --model ollama:llama3.2
army catalog && army docs               # your agent appears in the README and docs
army serve                              # ...and in the playground
army export-skill tagline-tester        # ...and as a SKILL.md for coding agents
```

Add at least three `EVALS` cases: a normal request, an edge case, and one where the right answer is "I don't know". Then open a pull request.
