# sample-assistant (firmware 0.1.0)

Demo agentic firmware for T-ex LLM.

## Roles
- planner → executor → reviewer → integrator

## Input
```json
{ "goal": "your task" }
```

## Output
Job result with `summary`, `output.answer`, handoffs, and artifacts.

## Load
```bash
python -m texllm.cli "Explain team runners" --provider mock
```
