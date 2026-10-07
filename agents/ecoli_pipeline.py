from schemas.process import ModelResult
from agents.process_understanding import understand_process
from agents.scientific.ecoli_runner import run_from_process_state


def simulate_from_description(
    description: str,
) -> ModelResult:
    """
    Convert a natural-language process description into a ProcessState
    and run the E. coli scientific model.

    The process-understanding layer is responsible for interpreting
    the description. The E. coli runner is responsible for translating
    the resulting ProcessState into scientific model inputs.
    """

    process_state = understand_process(
        description
    )

    return run_from_process_state(
        process_state
    )