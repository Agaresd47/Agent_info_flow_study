# 项目说明

## 任务理解

这次作业的目标是补完整个 research planning 流程，并提高 planner loop 的稳定性。核心范围包括三部分：

- 接入真实的市场数据与 LLM 能力
- 提高 handwritten loop 的恢复能力与终止质量
- 在保持 generic tools 的前提下，让模型更容易规划出可执行 pipeline

## 关键处理

### 1. 真实集成

任务：
把 `data.market_bars` 和 `research_chat` 从占位实现改成真实能力。

处理：
`data.market_bars` 接入 BaoStock，支持 `symbols` 和 `lookback_days`。`research_chat` 接入 chat completions API，返回统一结构。

结果：
pipeline 可以真实拉取行情、计算因子、排序并生成解释文本。

### 2. 题目未显式提出的失败场景

任务：
补足 loop 在异常输入和不收敛状态下的行为定义。

处理：
为 tool 参数非法 JSON、step 未成功时导出、symbol 级行情查询失败、模型多轮不调用工具等情况增加保护与测试。

结果：
loop 在常见失败路径下可以给出明确反馈，导出条件更严格，停止原因更清楚。

### 3. planner 可用性

任务：
降低 generic tools 的使用歧义。

处理：
补充 step metadata、output fields、reference examples，并统一 catalog、tool schema、runtime 输出字段的描述。

结果：
模型更容易理解每个 step 的输入、输出和引用方式，减少空壳 pipeline 或错误引用。

## 额外思考

### 1. 信息流比新增功能更重要

观察：
这个项目的主要问题在 step 数量相对充足的情况下，模型每一轮拿到的信息是否足够清楚。

处理：
优先补 catalog、details、tool feedback 和 draft summary。

结果：
planner 的改进集中在信息质量、恢复路径和终止规则，和题目关注点保持一致。

### 2. 完成条件需要可验证

观察：
如果只依赖模型自己说“完成”，loop 很容易提前结束。

处理：
把完成条件收敛到 `get_pipeline` 成功，且所有 steps 已成功执行。

结果：
pipeline 导出变成一个可验证状态，不依赖主模型的主观判断。

### 3. reviewer 思维比 happy path 更重要

观察：
公开用例覆盖有限，真实风险更多出现在 bad case 和 edge case。

处理：
补充 failure-oriented tests，并检查错误传播、空转、引用一致性和停止策略。

结果：
提交内容更接近一个可讨论的工程结果，后续面试也更容易围绕控制逻辑展开。

## 未来改进方向

任务：
提高 planner 在多轮失败后的纠偏能力。

处理：
可以在主 loop 连续失败时引入一个独立 reviewer，只读取当前 draft、错误信息和 step 状态，给出修复建议。

结果：
主 loop 继续负责执行和结束判定，外部评审负责提供新的检查视角，适合后续演进时再引入。
