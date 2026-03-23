import re
from typing import Any, Dict, Iterable, Tuple


class ExecutionContext:
    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        self.step_outputs: Dict[str, Any] = {}

    def set_output(self, step_id: str, output: Any) -> None:
        self.step_outputs[step_id] = output

    def get_output(self, step_id: str) -> Any:
        return self.step_outputs[step_id]

    def resolve_reference(self, ref: str) -> Any:
        root_name, access_path = self._split_reference(ref)
        value = self.get_output(root_name)
        for accessor in access_path:
            value = self._apply_accessor(value, accessor)
        return value

    def _split_reference(self, ref: str) -> Tuple[str, Iterable[Any]]:
        if not isinstance(ref, str) or not ref.startswith("$"):
            raise ValueError("Invalid reference: {0}".format(ref))

        expression = ref[1:]
        root_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", expression)
        if root_match is None:
            raise ValueError("Invalid reference root: {0}".format(ref))

        root_name = root_match.group(1)
        remainder = expression[len(root_name):]
        return root_name, list(self._parse_accessors(remainder))

    def _parse_accessors(self, text: str) -> Iterable[Any]:
        token_pattern = re.compile(r"\[['\"]([^'\"]+)['\"]\]|\[(\d+)\]")
        for match in token_pattern.finditer(text):
            field_name = match.group(1)
            if field_name is not None:
                yield field_name
            else:
                yield int(match.group(2))

    def _apply_accessor(self, value: Any, accessor: Any) -> Any:
        return value[accessor]
