# T2 Taxonomy

- goal_drift: The planner or worker shifts away from the real task goal.
- constraint_omission: Important limits are missing from the delegated spec or worker interpretation.
- vague_delegation: The planner leaves the worker with unclear actions or success criteria.
- wrong_file_targeting: The delegated files do not line up with the request or repo summary.
- false_confidence: The worker states unsupported facts as certain.
- planner_overreach: The planner adds work or assumptions beyond the request.
- revision_failure: Planner v2 does not resolve issues exposed by worker v1.
- revision_overcorrection: Planner v2 adds incorrect constraints while fixing v1.
- worker_capability_ceiling: The worker recognizes the task but cannot translate it into useful next actions.
