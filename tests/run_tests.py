import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

try:
    from quant_react_interview.engine.core.engine import PipelineEngine
except Exception:
    from engine.core.engine import PipelineEngine


class CaseRunner:
    def __init__(self) -> None:
        self.engine = PipelineEngine()

    async def run_all(self, case_paths: List[Path]) -> int:
        passed = 0
        for case_path in case_paths:
            if await self.run_one(case_path):
                passed += 1
        return passed

    async def run_one(self, case_path: Path) -> bool:
        print('Running {0}'.format(case_path.name))
        case = self._load_case(case_path)
        try:
            result = await self.engine.run_pipeline(case['pipeline'])
        except Exception as exc:
            print('  ERROR: {0}'.format(exc))
            return False

        failures = self._collect_failures(case['expected'], result['outputs'])
        if failures:
            for failure in failures:
                print('  FAIL: {0}'.format(failure))
            return False

        print('  PASS')
        return True

    def _load_case(self, case_path: Path) -> Dict[str, Any]:
        with open(case_path, 'r', encoding='utf-8') as handle:
            return yaml.safe_load(handle)

    def _collect_failures(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
        failures: List[str] = []
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if not _matches(expected_value, actual_value):
                failures.append('{0} expected {1}, got {2}'.format(key, expected_value, actual_value))
        return failures


def _matches(expected: Any, actual: Any) -> bool:
    if expected == '*':
        return actual is not None
    if expected is None:
        return actual is None
    if expected == actual:
        return True
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(
            key in actual and _matches(child_expected, actual[key])
            for key, child_expected in expected.items()
        )
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        return all(_matches(left, right) for left, right in zip(expected, actual))
    return False


async def main() -> None:
    case_paths = sorted((ROOT / 'tests' / 'public' / 'cases').glob('*.yaml'))
    runner = CaseRunner()
    passed = await runner.run_all(case_paths)
    print('Summary: {0}/{1} passed'.format(passed, len(case_paths)))


if __name__ == '__main__':
    asyncio.run(main())
