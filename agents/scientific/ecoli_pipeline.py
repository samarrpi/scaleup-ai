from schemas.process import ModelResult
from agents.process_understanding import understand_process
from agents.scientific.ecoli_runner import run_from_process_state


def simulate_from_description(description: str) -> ModelResult:
    process_state = understand_process(description)
    return run_from_process_state(process_state)