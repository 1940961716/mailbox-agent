# 智能邮箱助理与自动化待办生成 Agent

这是一个面向课程期末大作业的可运行 MVP。系统可以同步真实 IMAP 邮箱，自动进行邮件分类、Todo 生成、回复草稿生成、CSV/Excel 附件分析，并通过 Critic Agent 对结果进行审查。

项目重点体现：

- 敏捷软件工程过程文档：需求、Backlog、Sprint 计划、评审、回顾、验收记录。
- Agentic AI 设计模式：任务分解、工具使用、反思机制、多智能体协作。
- 可运行产品原型：邮箱同步、邮件看板、Todo 总览、草稿编辑、附件分析、Agent 日志。

## 功能特性

- 按时间范围同步真实邮箱邮件。
- 同步成功后自动运行 Agent。
- 自动分类邮件：任务、会议、通知、需回复、安全提醒等。
- 自动生成 Todo，并保留来源邮件、发件人、证据和置信度。
- 自动生成回复草稿，但不自动发送邮件。
- 支持 CSV/Excel 附件分析，并从表格中提取任务候选。
- 支持 Todo 确认、完成、拒绝、编辑和删除。
- Todo 总览支持按状态和优先级筛选。
- 前端左右分栏独立滚动，邮箱同步面板可折叠。
- 提供 Agent 日志，展示 Triage、Action、Critic、Persistence Guard 等过程。

## 技术栈

当前实现采用轻量可演示方案：

- 前端：原生 HTML + CSS + JavaScript
- 后端：FastAPI
- Agent 工作流：LangGraph
- LLM 接入：OpenAI-compatible API，可接 DeepSeek
- 数据库：SQLite
- 附件处理：pandas / openpyxl
- 邮箱协议：IMAP

说明：早期规划中提到 Vue 3 + Vite。本 MVP 为了降低部署复杂度，前端暂时采用原生实现，后续可以迁移到 Vue。

## 目录结构

```text
backend/
  app/
    agents/          多智能体实现：Triage / Action / Critic / LangGraph workflow
    services/        IMAP、邮件解析、LLM、附件分析等服务
    tools/           时间解析等工具
  run_fastapi.py     FastAPI 启动入口
  requirements.txt   Python 依赖

frontend/
  index.html         前端页面
  static/
    app.js           前端交互逻辑
    styles.css       页面样式

docs/                敏捷过程文档与迭代记录
samples/             样例邮件与测试材料
scripts/             测试邮件发送脚本
```

## 环境准备

进入项目目录：

```powershell
cd "D:\作业\大三下\机器学习的敏捷软件工程\期末大作业"
```

创建虚拟环境：

```powershell
python -m venv .venv
```

安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r backend\requirements.txt
```

## 配置环境变量

复制示例配置：

```powershell
copy .env.example .env
```

在 `.env` 中填写自己的模型配置。DeepSeek 示例：

```text
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

如果不配置 API Key，系统仍可使用规则兜底逻辑运行，但 Agent 效果会弱一些。

重要：不要提交 `.env`。项目的 `.gitignore` 已经排除了 `.env`、数据库、日志、附件和虚拟环境。

## 启动项目

```powershell
.\.venv\Scripts\python.exe backend\run_fastapi.py
```

访问：

```text
http://127.0.0.1:8001
```

健康检查：

```text
http://127.0.0.1:8001/api/health
```

LLM 配置检查：

```text
http://127.0.0.1:8001/api/llm/status
```

## 使用流程

1. 打开页面。
2. 在左侧邮箱授权区选择邮箱类型，例如 QQ 邮箱或 163 邮箱。
3. 输入邮箱账号和授权码。
4. 选择同步时间范围，例如最近 7 天。
5. 点击“同步并运行 Agent”。
6. 系统会自动同步邮件并批量运行 Agent。
7. 右侧会切换到 Todo 总览，展示所有生成的任务。
8. 点击左侧邮件可以查看原文、Agent 结果、回复草稿、附件分析和日志。

注意：不是每封邮件都会生成 Todo 或草稿。通知、广告、安全提醒类邮件可能只会生成分类和日志。

## 邮箱授权说明

请使用邮箱授权码，不要使用登录密码。

常见 IMAP 服务器：

```text
QQ 邮箱：imap.qq.com
163 邮箱：imap.163.com
126 邮箱：imap.126.com
Gmail：imap.gmail.com
Outlook：outlook.office365.com
```

建议使用专门的测试邮箱，不要使用个人主邮箱。

## 测试邮件脚本

项目提供了测试邮件发送脚本：

```powershell
.\.venv\Scripts\python.exe scripts\send_test_emails.py
```

默认是 dry-run，不会真正发送。需要真实发送时使用脚本中的发送参数，并确保 `.env` 中配置了 SMTP 信息。

## 安全边界

系统不会自动发送最终邮件。

它只会：

- 生成 Todo。
- 生成回复草稿。
- 分析附件。
- 给出 Agent 审查结果。

最终是否发送邮件、如何处理任务，仍由用户确认。

## 敏捷过程文档

核心过程文件位于 `docs/`，包括：

- 项目愿景与问题定义
- 电梯演讲与产品包装
- Not-List 否定清单
- 产品 Backlog
- 用户故事地图
- Sprint 计划、评审、回顾
- API、数据库、架构设计
- 测试用例与验收报告
- 多轮迭代记录

最近的重要迭代：

- `docs/29_全量审查整改记录.md`
- `docs/30_邮箱按时间同步迭代记录.md`
- `docs/31_同步后自动运行Agent迭代记录.md`
- `docs/32_前端滚动与同步面板折叠迭代记录.md`

## 上传 GitHub 前检查

提交前建议运行：

```powershell
git status
```

确认以下内容没有被提交：

- `.env`
- `.venv/`
- `backend/data/*.sqlite3`
- `backend/server.*.log`
- `backend/attachments/*`

然后提交：

```powershell
git add .
git commit -m "Initial commit: intelligent mailbox agent"
git push
```
