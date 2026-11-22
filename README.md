# agent-injection-eval

A benchmark that measures prompt-injection attacks and defenses on tool-using LLM agents across
languages (English, Nepali, romanized Nepali, Hindi, code-mixed) and injection channels
(retrieved doc, email, tool output, file). Everything runs in a mocked sandbox.

Design: [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

## Status
Scaffolding only. No results yet.

## Setup
Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and (for live runs) a local
[Ollama](https://ollama.com) server.

```
make setup
make lint test
```
