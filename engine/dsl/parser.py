from pathlib import Path
from typing import Any, Dict, Union

import yaml

from .models import Pipeline
from .validator import PipelineValidator


class PipelineParser:
    def __init__(self) -> None:
        self.validator = PipelineValidator()

    def parse_file(self, path: Union[str, Path]) -> Pipeline:
        document = self._read_yaml(path)
        return self.parse_dict(document)

    def parse_dict(self, data: Dict[str, Any]) -> Pipeline:
        payload = self._unwrap_pipeline_payload(data)
        pipeline = Pipeline(**payload)
        self.validator.validate(pipeline)
        return pipeline

    def _read_yaml(self, path: Union[str, Path]) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _unwrap_pipeline_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "pipeline" in data:
            return data["pipeline"]
        return data
