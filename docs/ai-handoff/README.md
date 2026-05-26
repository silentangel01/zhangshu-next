# AI Handoff

本目录用于 Codex 与 Claude Code 的单任务交接。

流转顺序：

1. Codex 阅读项目结构和相关代码，生成 `CODEX_PLAN.md`。
2. Claude Code 按计划执行，实现、运行命令、修复报错，并生成 `CLAUDE_EXECUTION_REPORT.md`。
3. Codex 读取计划、执行报告和当前 `git diff`，生成 `CODEX_REVIEW.md`。

活跃交接文件一次只代表一个任务。开始新任务前，如已有旧的 `CODEX_PLAN.md`、`CLAUDE_EXECUTION_REPORT.md` 或 `CODEX_REVIEW.md`，应先询问用户是否归档，或在用户已明确要求开始新任务时归档到 `archive/<YYYY-MM-DD-short-task-name>/`。
