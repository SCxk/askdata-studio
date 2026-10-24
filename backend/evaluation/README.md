# 学校教学问数评测

当前项目仅使用 `school_teaching` 学校模拟数据库，固定评测集包含 40 道学校教学分析问题。

## 指标

- 字段级 Schema 召回率：正确召回字段数 / 标准字段数
- 字段级 Schema 准确率：正确召回字段数 / 实际召回字段数
- SQL 执行成功率：成功执行 SQL 数 / 测试用例数
- 查询结果正确率：模型 SQL 与标准 SQL 的执行结果一致数 / 测试用例数
- SQL 执行时间：DuckDB 执行层平均耗时与 P95 耗时

结果比较检查全部列、行数、重复次数、数值及明确指定的排序；只接受题集预定义的中英文列名别名。

## 运行

在 `backend` 目录执行：

```powershell
# 验证全部标准 SQL，不调用模型
.\.venv\Scripts\python.exe -m evaluation.run_school_benchmark --gold-only

# 运行全部 40 条学校用例，会调用模型服务
.\.venv\Scripts\python.exe -u -m evaluation.run_school_benchmark --workers 3
```

已完成的历史报告保存在 `evaluation/results`，包含 JSON、CSV 和 Markdown 三种格式。完整问数评测会产生接口调用费用。题集范围、指标口径和历史报告的解释边界见 [SCHOOL_BENCHMARK.md](SCHOOL_BENCHMARK.md)。
