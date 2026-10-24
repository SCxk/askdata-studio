# 学校教学场景评测

固定题集共40题，成绩、考勤、作业、知识点、教学安排各8题；覆盖16张教学表、67个不同物理字段，按题去重后的标准字段引用总数为338。学校及学期基础信息表不在直接查询覆盖范围内。

## 复现

在 `backend` 目录执行：

```powershell
# 校验40题参考SQL并生成标准结果，不调用模型
.\.venv\Scripts\python.exe -m evaluation.run_school_benchmark --gold-only

# 校验结果比较器
.\.venv\Scripts\python.exe -m unittest tests.test_school_benchmark -v

# 调用已配置模型，运行完整学校问数流程（默认并发3）
.\.venv\Scripts\python.exe -m evaluation.run_school_benchmark --workers 3
```

可通过 `--output evaluation/results/自定义文件名.json` 指定输出；请使用新的文件名保留历史基线。`--limit 1` 可单独验证评测链路，不能当作正式40题报告。

## 指标口径

- 字段级Schema召回率micro：所有题正确召回标准字段的总次数 / 所有题标准字段总次数。标准字段由事先写好的SQL AST解析，涵盖聚合目标、筛选、分组、关联键；字段在同题中只计一次。macro为各题召回率的平均值。
- 仅将实际检索返回的hits算作原始召回；Schema图补充的关联键单独报告。SQL生成阶段获得的完整授权字段目录不算召回。
- SQL执行成功率：最终SQL在数据库执行成功的题数 / 全部40题。保留应用已有的最多3次工具调用及SQL修复，另外报告首条SQL执行成功数。
- 查询结果正确率：SQL返回结构化结果符合标准答案的题数 / 全部40题。另报在SQL执行成功题目中的正确率。
- 路由错误、需要澄清、网络或模型异常均不剔除。无检索结果的题按零召回纳入。页面结果说明的完成状态另存，不等同于SQL成功。

结果比较检查要求的全部列、行数、行重复次数、数值及明确指定的排序。列名允许题集中预定义的中英文别名；整数严格比较，分数允许0.005的绝对误差，0到1比率允许0.00005的绝对误差。不接受原始分与百分制互换、不接受比率乘以100。分组结果可忽略行顺序；空结果仍要求列正确。

每次运行使用独立空会话，执行与页面一致的QueryWorkflow，从意图识别及模型生成的检索词开始，不注入参考字段、参考SQL或标准答案。参考SQL先执行生成期望值，并检查所有参考结果均小于200行，避免页面截断。默认并发3仅为缩短评测时长，不是吞吐量压力测试。

## 输出与可解释边界

`cases/school_teaching_v1.json` 保存问题、标准SQL、标准字段、列定义、标准结果。`school_cases.py` 为题目来源。`results/` 下输出JSON、CSV、Markdown，按完成题目持续保存；JSON的 `complete` 为true代表整批均已尝试，不保证模型服务正常或全部查询完成。

JSON记录逐题检索字段、缺失字段、生成SQL、实际及期望结果、工具调用、模型重试计数、结果判定和耗时。metadata记录模型配置、阈值、数据和代码SHA256及运行前后是否变化，不保存密钥。正式基线与单题试跑应分开保存。

该题集是单校合成数据上的固定设计题集，问题为了明确比较标准而列明了输出列及部分指标口径。参考答案来自SQL oracle，未经过独立双人标注；字段召回也依赖参考SQL选择的关联路径。不能把40题的结果直接当作生产环境准确率，也未覆盖多轮记忆、真实数据噪声、图表和文字解释的正确率。

## 2026-10-19运行与复核

`school_teaching_baseline_20261019.json` 保留全部40题尝试，其中20题未完成查询，错误包含模型服务返回的 `Arrearage`（欠费）。该批次不能作为完整模型能力基线；服务可用后应换输出文件名完整重跑。

自动比较中有4题只因同义列名失败。`cases/school_alias_review_20261019.json` 逐题记录映射及SQL语义依据，以下命令只重比原始结果，不调用模型、不修改结果，也不覆盖原始报告：

```powershell
.\.venv\Scripts\python.exe -m evaluation.review_school_results evaluation/results/school_teaching_baseline_20261019.json evaluation/cases/school_alias_review_20261019.json
```

复核报告名称带 `_reviewed`，同时保留严格列名判定和同义列名复核判定。受欠费影响的题仍记失败，条件统计仅描述实际完成相应阶段的子集。完整的模型能力基线标志为 `capability_benchmark_complete`，本次为false。

## 2026-10-19完整重测

`results/school_teaching_rerun_20261019_2_summary.md` 为本轮汇总。40题均已完成，无模型服务异常，数据、代码及模型配置与上轮一致。原始字段召回micro为69.23%（234/338），SQL最终执行成功率100%（40/40），严格列名结果正确率82.5%（33/40），同义列名复核后为100%（40/40）。15题首条SQL因schema前缀错误需要应用自动修复，首次SQL执行成功率62.5%。

原始JSON、CSV、Markdown与上轮分开保存。复核可重现为：

```powershell
.\.venv\Scripts\python.exe -m evaluation.review_school_results evaluation/results/school_teaching_rerun_20261019_2.json evaluation/cases/school_alias_review_rerun_20261019_2.json
```

该批复核报告的 `capability_benchmark_complete` 为true；含义是本轮未被欠费阻断，不代表题集覆盖所有生产能力。
