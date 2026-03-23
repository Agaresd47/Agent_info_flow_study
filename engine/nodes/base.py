from abc import ABC, abstractmethod
from typing import Any, Dict


class RuntimeStep(ABC):
    async def execute(self, config: Dict[str, Any], context: Any) -> Any:
        return await self.run(config, context)

    async def run(self, config: Dict[str, Any], runtime: Any) -> Any:
        raise NotImplementedError


BaseStep = RuntimeStep
