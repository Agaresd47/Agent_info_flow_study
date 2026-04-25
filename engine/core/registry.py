from typing import Any, Dict, List, Optional, Type

from ..nodes.eval.planner_spec import PlannerSpecStep
from ..nodes.eval.revision_score import RevisionScoreStep
from ..nodes.eval.task import EvalTaskStep
from ..nodes.eval.worker_review import WorkerReviewStep


class RuntimeCatalog:
    def __init__(self) -> None:
        self._constructors: Dict[str, Type] = {}
        self._install_defaults()

    def build(self, kind: str) -> Any:
        constructor = self._constructors.get(kind)
        if constructor is None:
            raise ValueError("Unknown step kind: {0}".format(kind))
        return constructor()

    def create(self, kind: str) -> Any:
        return self.build(kind)

    def supported_kinds(self) -> List[str]:
        return sorted(self._constructors.keys())

    def register(self, kind: str, step_cls: Type) -> None:
        self._constructors[kind] = step_cls

    def _install_defaults(self) -> None:
        self.register("eval.task", EvalTaskStep)
        self.register("planner.spec", PlannerSpecStep)
        self.register("worker.review", WorkerReviewStep)
        self.register("revision.score", RevisionScoreStep)


_catalog_singleton: Optional[RuntimeCatalog] = None


def get_registry() -> RuntimeCatalog:
    global _catalog_singleton
    if _catalog_singleton is None:
        _catalog_singleton = RuntimeCatalog()
    return _catalog_singleton
