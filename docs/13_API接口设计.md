# API 接口设计

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/health | 健康检查 |
| POST | /api/emails/import-samples | 导入样例邮件 |
| POST | /api/emails/sync | IMAP 按时间范围同步，支持 `since_date`、`until_date`、`limit` 和 `replace_snapshot` |
| GET | /api/llm/status | 查看 LLM 是否配置、模型名、Base URL 和最近错误，不返回 API Key |
| GET | /api/emails | 邮件列表 |
| GET | /api/emails/{id} | 邮件详情 |
| POST | /api/emails/{id}/process | 运行 Agent |
| GET | /api/todos | Todo 列表 |
| PATCH | /api/todos/{id} | 更新 Todo |
| GET | /api/drafts | 草稿列表 |
| PATCH | /api/drafts/{id} | 更新草稿 |
| GET | /api/attachments | 附件列表 |
| GET | /api/agent-logs | Agent 日志 |
