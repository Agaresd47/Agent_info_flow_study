from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StepSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    name: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    next: List[str] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def fill_display_name(cls, value: Any, info: Any) -> str:
        if value in (None, ""):
            return info.data.get("kind", "step")
        return value

    @field_validator("next", mode="before")
    @classmethod
    def normalize_edges(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)


class PipelineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_id: Optional[str] = "generated_pipeline"
    name: str = "Untitled Pipeline"
    steps: List[StepSpec] = Field(..., min_length=1)


Pipeline = PipelineSpec
Step = StepSpec
