# Prompt 与 Agent 设计

## Triage Agent

输入邮件标题、正文和附件列表，输出分类、优先级、是否需要 Todo、是否需要回复、是否需要附件分析。

## Action Agent

输入邮件、分类结果和附件分析结果，输出 Todo 候选项和回复草稿。

## Critic Agent

输入 Action Agent 输出，检查模糊时间、缺失字段、低置信度、过强承诺和自动化风险。

## 兜底策略

无 LLM API Key 时使用规则型 Agent，保证系统可离线演示。

