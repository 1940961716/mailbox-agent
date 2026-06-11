# 智能邮箱助理与自动化待办生成 Agent 项目落地 TodoList

> 目标：以敏捷开发方式真正实现一个可运行的 Agent 邮件助手，完成从需求分析、计划、迭代执行到最终交付的全过程，并保留完整中间过程性文件。

---

## 0. MVP 落地范围确认

### 0.1 推荐实现边界

本项目不再只做概念规划，而是实现一个可运行 MVP：

- 支持真实邮箱读取，优先使用 **IMAP/SMTP**。
- 推荐邮箱：**163 邮箱或 QQ 邮箱**，通过授权码接入。
- 支持邮件分类、Todo 自动生成、回复草稿生成、Excel/CSV 附件分析。
- 使用 Triage Agent、Action Agent、Critic Agent 三类智能体完成任务。
- 用户最终确认 Todo 和回复草稿，系统不自动发送最终邮件。

### 0.2 MVP 技术栈

| 层次 | 技术选型 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus |
| 后端 | Python FastAPI |
| Agent 编排 | LangGraph |
| LLM 接入 | 单一主模型 API |
| 邮箱接入 | IMAP 读取邮件，SMTP 可选保存/发送草稿 |
| 数据库 | SQLite |
| 附件处理 | pandas + openpyxl |
| 本地文件 | attachments/ 保存附件，samples/ 保存样例邮件 |
| 测试 | pytest + 手工验收用例 |

---

# 一、过程性文件 Todo

这些文件是课程项目过程证据，建议全部放在 `docs/` 目录下。

## 1.1 启动阶段文件

- [ ] `docs/01_项目愿景与问题定义.md`
  - 内容：项目背景、用户痛点、目标用户、核心价值。
  - 对应课程实践：提出问题、电梯演讲、产品包装。

- [ ] `docs/02_电梯演讲与产品包装.md`
  - 内容：30 秒电梯演讲、核心卖点、Killer Features。
  - 重点体现：邮件转 Todo、反思审查、附件 Code as Action。

- [ ] `docs/03_NotList_否定清单.md`
  - 内容：不做即时通讯、不自动发送最终邮件、不做完整 OA、不做企业 SSO 等。
  - 目的：控制范围，防止功能膨胀。

- [ ] `docs/04_邻居清单与外部依赖.md`
  - 内容：邮箱服务器、LLM API、SQLite、附件目录、前端、后端依赖。
  - 重点区分：MVP 必需依赖与后续扩展依赖。

## 1.2 计划阶段文件

- [ ] `docs/05_产品Backlog.md`
  - 内容：所有用户故事、优先级、故事点、验收标准。
  - 至少包含：邮件读取、分类、Todo 生成、草稿生成、附件分析、Critic 审查。

- [ ] `docs/06_用户故事地图.md`
  - 内容：用户从“连接邮箱”到“确认 Todo”的完整路径。
  - 建议结构：活动、任务、用户故事、MVP 切片。

- [ ] `docs/07_发布计划.md`
  - 内容：Sprint 0 到 Sprint 4 的目标、范围、交付物。
  - 重点体现：每个 Sprint 都能产生可演示增量。

- [ ] `docs/08_Sprint1_计划.md`
  - 内容：Sprint 1 目标、任务拆分、负责人、验收标准。

- [ ] `docs/09_Sprint2_计划.md`
  - 内容：Sprint 2 目标、任务拆分、负责人、验收标准。

- [ ] `docs/10_Sprint3_计划.md`
  - 内容：Sprint 3 目标、任务拆分、负责人、验收标准。

- [ ] `docs/11_风险清单.md`
  - 内容：隐私、授权码泄露、LLM 误判、Token 成本、时间解析错误、附件安全。

- [ ] `docs/12_架构设计说明.md`
  - 内容：系统架构图、Agent 工作流、模块划分、数据流。

- [ ] `docs/13_API接口设计.md`
  - 内容：FastAPI 接口、请求响应、错误码。

- [ ] `docs/14_数据库设计.md`
  - 内容：SQLite 表结构，包括 email、todo、draft、attachment、agent_log。

- [ ] `docs/15_Prompt与Agent设计.md`
  - 内容：Triage Agent、Action Agent、Critic Agent 的职责、输入、输出 JSON 格式。

## 1.3 执行阶段文件

- [ ] `docs/16_每日站会记录.md`
  - 内容：昨天完成、今天计划、遇到阻碍。
  - 每个开发日补一条即可。

- [ ] `docs/17_任务看板记录.md`
  - 内容：To Do、Doing、Done、Blocked 四列任务流转记录。

- [ ] `docs/18_燃尽图数据.md`
  - 内容：日期、剩余故事点、实际完成点数。
  - 可以用 Markdown 表格表示，不一定真的画图。

- [ ] `docs/19_Sprint评审记录.md`
  - 内容：每个 Sprint 展示了什么，老师/同学/组内反馈是什么。

- [ ] `docs/20_Sprint回顾记录.md`
  - 内容：做得好的、需要改进的、下一轮行动项。

## 1.4 验收与交付文件

- [ ] `docs/21_测试用例与验收报告.md`
  - 内容：功能测试、Agent 输出测试、附件分析测试、异常场景测试。

- [ ] `docs/22_部署与运行说明.md`
  - 内容：环境变量、启动后端、启动前端、配置邮箱授权码。

- [ ] `docs/23_最终项目总结.md`
  - 内容：完成情况、未完成项、敏捷实践总结、技术亮点、后续迭代方向。

- [ ] `docs/24_答辩演示脚本.md`
  - 内容：演示顺序、样例账号、样例邮件、每一步讲什么。

---

# 二、产品 Backlog Todo

## P0：必须完成

- [ ] 用户可以配置邮箱 IMAP 信息。
  - 验收：输入邮箱地址、授权码、IMAP 服务器后，系统能读取最近邮件。

- [ ] 系统可以读取邮件标题、发件人、时间、正文。
  - 验收：后端返回标准化 email JSON。

- [ ] 系统可以下载并保存 Excel/CSV 附件。
  - 验收：附件进入本地 `attachments/` 目录，并在数据库中记录路径。

- [ ] Triage Agent 可以对邮件分类。
  - 验收：输出 `task`、`meeting`、`notification`、`needs_reply`、`ignore` 等类别。

- [ ] Action Agent 可以从任务邮件生成 Todo。
  - 验收：Todo 包含标题、描述、截止时间、优先级、来源邮件、证据。

- [ ] Action Agent 可以生成回复草稿。
  - 验收：草稿保存到数据库，用户可在前端查看和修改。

- [ ] Action Agent 可以分析 Excel/CSV 附件。
  - 验收：系统能读取表格列名和关键行，生成摘要或 Todo。

- [ ] Critic Agent 可以审查 Todo 和草稿。
  - 验收：对模糊时间、缺失字段、低置信度结果给出风险提示。

- [ ] 用户可以在前端确认、编辑或拒绝 Todo。
  - 验收：Todo 状态可以从 `pending` 变为 `confirmed`、`rejected` 或 `done`。

- [ ] 用户可以在前端查看和编辑回复草稿。
  - 验收：草稿不会自动发送。

## P1：尽量完成

- [ ] 支持按关键词或时间范围筛选邮件。
- [ ] 支持邮件处理历史记录。
- [ ] 支持 Todo 按优先级和截止时间排序。
- [ ] 支持对邮件线程进行摘要。
- [ ] 支持导入本地样例邮件，避免演示时真实邮箱失败。
- [ ] 支持将草稿复制到剪贴板。
- [ ] 支持附件分析结果可视化展示。

## P2：后续迭代

- [ ] 支持 Gmail API 或 Outlook Graph API。
- [ ] 支持 MCP 工具服务器封装。
- [ ] 支持多模型切换。
- [ ] 支持日历 API 同步。
- [ ] 支持多用户登录。
- [ ] 支持 MySQL/PostgreSQL。
- [ ] 支持 Redis 缓存。
- [ ] 支持 Docker 云部署。

---

# 三、Sprint 计划 Todo

## Sprint 0：项目启动与设计

目标：完成项目共识、需求范围、架构设计和过程文档模板。

- [ ] 创建项目目录结构。
- [ ] 创建 `backend/`、`frontend/`、`docs/`、`samples/`、`attachments/`。
- [ ] 完成项目愿景与问题定义文档。
- [ ] 完成产品 Backlog 初版。
- [ ] 完成用户故事地图。
- [ ] 完成系统架构设计。
- [ ] 完成数据库表设计。
- [ ] 完成 API 接口设计。
- [ ] 确定邮箱接入方案：163 或 QQ 邮箱 IMAP。
- [ ] 准备 5-10 封样例邮件。

交付物：

- [ ] `docs/01_项目愿景与问题定义.md`
- [ ] `docs/05_产品Backlog.md`
- [ ] `docs/12_架构设计说明.md`
- [ ] `docs/14_数据库设计.md`

## Sprint 1：邮箱读取与基础看板

目标：实现真实邮箱或样例邮件读取，并能在前端展示邮件列表。

后端任务：

- [ ] 初始化 FastAPI 项目。
- [ ] 实现 SQLite 初始化脚本。
- [ ] 实现 `emails` 表。
- [ ] 实现 IMAP 邮件读取模块。
- [ ] 实现邮件正文解析，支持纯文本和 HTML。
- [ ] 实现附件识别和下载。
- [ ] 实现本地样例邮件导入。
- [ ] 实现 `GET /api/emails`。
- [ ] 实现 `POST /api/emails/sync`。

前端任务：

- [ ] 初始化 Vue 3 + Vite 项目。
- [ ] 搭建综合看板布局。
- [ ] 实现邮件列表展示。
- [ ] 实现邮件详情查看。
- [ ] 实现同步邮件按钮。

过程文件：

- [ ] 更新每日站会记录。
- [ ] 更新任务看板记录。
- [ ] 更新燃尽图数据。
- [ ] 完成 Sprint 1 评审记录。
- [ ] 完成 Sprint 1 回顾记录。

验收标准：

- [ ] 可以读取至少 10 封邮件或样例邮件。
- [ ] 前端可以展示邮件标题、发件人、时间、正文摘要。
- [ ] 附件可以保存到本地目录。

## Sprint 2：Agent 分类、Todo 生成与草稿生成

目标：实现核心 Agent 工作流，让邮件变成 Todo 和回复草稿。

后端任务：

- [ ] 集成 LLM API。
- [ ] 设计 Triage Agent Prompt。
- [ ] 实现 Triage Agent 分类节点。
- [ ] 设计 Action Agent Prompt。
- [ ] 实现 Todo 抽取节点。
- [ ] 实现回复草稿生成节点。
- [ ] 实现 `todos` 表。
- [ ] 实现 `drafts` 表。
- [ ] 实现 `agent_logs` 表。
- [ ] 实现 `POST /api/emails/{id}/process`。
- [ ] 实现 `GET /api/todos`。
- [ ] 实现 `GET /api/drafts`。

前端任务：

- [ ] 邮件详情页展示分类结果。
- [ ] Todo 区域展示待确认任务。
- [ ] 草稿区域展示回复草稿。
- [ ] 实现 Todo 编辑、确认、拒绝。
- [ ] 实现草稿编辑。

过程文件：

- [ ] 更新 Prompt 与 Agent 设计文档。
- [ ] 更新每日站会记录。
- [ ] 更新任务看板记录。
- [ ] 更新燃尽图数据。
- [ ] 完成 Sprint 2 评审记录。
- [ ] 完成 Sprint 2 回顾记录。

验收标准：

- [ ] 任务邮件能自动生成 Todo。
- [ ] 需要回复的邮件能生成草稿。
- [ ] Todo 和草稿均可追溯到原始邮件。

## Sprint 3：附件分析与 Critic Agent 审查

目标：实现 Code as Action 附件分析和反思审查机制。

后端任务：

- [ ] 实现 Excel/CSV 附件读取工具。
- [ ] 使用 pandas 分析表格列名、行数和关键字段。
- [ ] 支持从附件表格中生成 Todo 候选项。
- [ ] 设计 Critic Agent Prompt。
- [ ] 实现 Critic Agent 审查节点。
- [ ] 检查模糊时间、缺失字段、低置信度结果。
- [ ] 实现 `attachments` 表。
- [ ] 实现 `GET /api/attachments/{id}/analysis`。
- [ ] 实现处理结果风险等级：low、medium、high。

前端任务：

- [ ] 展示附件分析结果。
- [ ] 展示 Critic Agent 审查意见。
- [ ] 对高风险 Todo 显示确认提示。
- [ ] 支持用户手动修正截止时间和优先级。

过程文件：

- [ ] 更新风险清单。
- [ ] 更新测试用例。
- [ ] 更新每日站会记录。
- [ ] 更新任务看板记录。
- [ ] 更新燃尽图数据。
- [ ] 完成 Sprint 3 评审记录。
- [ ] 完成 Sprint 3 回顾记录。

验收标准：

- [ ] Excel/CSV 附件可以被读取并生成分析摘要。
- [ ] Critic Agent 能指出至少三类问题：模糊时间、缺少负责人、低置信度。
- [ ] 用户可以基于审查建议修正 Todo。

## Sprint 4：测试、演示与最终交付

目标：完成系统稳定性、文档、演示脚本和答辩材料。

开发任务：

- [ ] 编写核心 API 测试。
- [ ] 编写 Agent 输出格式测试。
- [ ] 准备演示邮箱或样例邮件数据。
- [ ] 准备含附件的测试邮件。
- [ ] 修复前端展示问题。
- [ ] 增加错误提示：邮箱连接失败、LLM 调用失败、附件解析失败。
- [ ] 整理运行说明。
- [ ] 整理最终项目总结。
- [ ] 准备答辩演示脚本。

验收任务：

- [ ] 完成端到端演示：同步邮件 -> 分类 -> 生成 Todo -> 生成草稿 -> 分析附件 -> Critic 审查 -> 用户确认。
- [ ] 完成测试用例与验收报告。
- [ ] 完成最终项目总结。
- [ ] 完成答辩演示脚本。

---

# 四、代码实现 Todo

## 4.1 后端目录建议

```text
backend/
  app/
    main.py
    config.py
    db.py
    models/
      email.py
      todo.py
      draft.py
      attachment.py
      agent_log.py
    routers/
      emails.py
      todos.py
      drafts.py
      attachments.py
    services/
      imap_service.py
      email_parser.py
      attachment_service.py
      llm_service.py
    agents/
      triage_agent.py
      action_agent.py
      critic_agent.py
      graph.py
    tools/
      time_tool.py
      sqlite_tool.py
      python_analysis_tool.py
  tests/
```

## 4.2 前端目录建议

```text
frontend/
  src/
    api/
      emails.ts
      todos.ts
      drafts.ts
    views/
      Dashboard.vue
    components/
      EmailList.vue
      EmailDetail.vue
      TodoPanel.vue
      DraftPanel.vue
      AttachmentPanel.vue
      CriticPanel.vue
```

## 4.3 数据库表 Todo

- [ ] `emails`
  - id、message_id、subject、sender、received_at、body、summary、category、processed_status。

- [ ] `todos`
  - id、email_id、title、description、deadline、priority、status、evidence、confidence。

- [ ] `drafts`
  - id、email_id、subject、body、status、created_at、updated_at。

- [ ] `attachments`
  - id、email_id、filename、path、file_type、analysis_summary。

- [ ] `agent_logs`
  - id、email_id、agent_name、input_summary、output_json、risk_level、created_at。

## 4.4 API Todo

- [ ] `POST /api/emails/sync`
- [ ] `POST /api/emails/import-samples`
- [ ] `GET /api/emails`
- [ ] `GET /api/emails/{id}`
- [ ] `POST /api/emails/{id}/process`
- [ ] `GET /api/todos`
- [ ] `PATCH /api/todos/{id}`
- [ ] `GET /api/drafts`
- [ ] `PATCH /api/drafts/{id}`
- [ ] `GET /api/attachments/{id}/analysis`
- [ ] `GET /api/agent-logs`

---

# 五、Agent 工作流 Todo

## 5.1 Triage Agent

- [ ] 输入：邮件标题、发件人、正文摘要、附件列表。
- [ ] 输出：分类、优先级、是否需要 Todo、是否需要回复、是否需要附件分析。
- [ ] 输出必须为 JSON。
- [ ] 记录分类依据。

## 5.2 Action Agent

- [ ] 输入：邮件正文、Triage 结果、附件分析结果。
- [ ] 输出：Todo 候选项。
- [ ] 输出：回复草稿。
- [ ] 输出：需要用户确认的字段。
- [ ] Todo 必须包含原文证据。

## 5.3 Critic Agent

- [ ] 输入：Action Agent 输出。
- [ ] 检查截止时间是否模糊。
- [ ] 检查 Todo 是否缺少标题、负责人、截止时间。
- [ ] 检查草稿语气是否合适。
- [ ] 检查是否存在高风险自动化动作。
- [ ] 输出风险等级和修改建议。

## 5.4 LangGraph 编排

- [ ] 节点 1：读取邮件。
- [ ] 节点 2：Triage 分类。
- [ ] 节点 3：附件分析。
- [ ] 节点 4：Action 生成 Todo / 草稿。
- [ ] 节点 5：Critic 审查。
- [ ] 节点 6：保存结果到 SQLite。
- [ ] 节点 7：返回前端等待用户确认。

---

# 六、演示样例 Todo

至少准备以下邮件样例：

- [ ] 任务邮件：要求在某日期前提交材料。
- [ ] 会议邮件：包含会议时间、地点、参会人。
- [ ] 需要回复邮件：询问项目进度或请求确认。
- [ ] 附件邮件：包含 Excel 任务表。
- [ ] 模糊时间邮件：包含“明天下班前”“下周三前”等表达。
- [ ] 通知类邮件：不应生成 Todo。
- [ ] 垃圾或低价值邮件：应标记为 ignore。

---

# 七、最终验收 Todo

- [ ] 系统能连接真实 IMAP 邮箱或导入样例邮件。
- [ ] 系统能展示邮件列表和详情。
- [ ] 系统能自动分类邮件。
- [ ] 系统能生成 Todo。
- [ ] 系统能生成回复草稿。
- [ ] 系统能分析 Excel/CSV 附件。
- [ ] 系统能通过 Critic Agent 审查结果。
- [ ] 用户能确认、编辑、拒绝 Todo。
- [ ] 用户能查看和编辑草稿。
- [ ] 所有 Agent 输出有日志可追溯。
- [ ] 有完整过程性文件。
- [ ] 有可复现运行说明。
- [ ] 有端到端演示脚本。

