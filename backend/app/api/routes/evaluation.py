"""Read-only access to experiment results in experiments/results/ (Phase 9).

Experiments are run from the command line (`python -m app.evaluation run ...`), not
through the API: they take minutes to hours and use their own database. The API
only lists and reads the result files they write.
"""

from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.core.errors import NotFoundError
from app.evaluation.results import list_results, read_result
from app.schemas.evaluation import EvaluationListItem, EvaluationResult

router = APIRouter(prefix="/evaluations", tags=["evaluation"])


@router.get("", response_model=list[EvaluationListItem])
def list_evaluations(settings: SettingsDep) -> list[dict]:
    return list_results(settings.experiments_dir)


@router.get("/{experiment}/{run}", response_model=EvaluationResult)
def get_evaluation(experiment: str, run: str, settings: SettingsDep) -> dict:
    result = read_result(settings.experiments_dir, experiment, run)
    if result is None:
        raise NotFoundError("Evaluation result not found.")
    return result
