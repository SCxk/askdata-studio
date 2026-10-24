# 学校教学问数评测报告

运行：school_20261019T140131Z；进度：40/40。

## 核心指标

| 指标 | 结果 |
|---|---|
| 字段级Schema召回率（micro） | 69.23%（234/338） |
| 字段级Schema召回率（macro） | 72.58% |
| 补充关联键后的召回率（micro） | 84.62% |
| SQL执行成功率 | 100.00%（40/40） |
| 首条SQL执行成功 | 25/40 |
| 查询结果正确率 | 82.50%（33/40） |
| 已执行SQL中的结果正确率 | 82.50% |
| 平均单题耗时（含模型调用） | 23.2秒 |

## 分类结果

| 类别 | 题数 | 字段召回micro | SQL成功 | 结果正确 |
|---|---:|---:|---:|---:|
| 成绩 | 8 | 67.11% | 8 | 5 |
| 考勤 | 8 | 66.18% | 8 | 7 |
| 作业 | 8 | 64.71% | 8 | 8 |
| 知识点 | 8 | 66.25% | 8 | 5 |
| 教学安排 | 8 | 89.13% | 8 | 8 |

## 评测口径与边界

- 使用当前完整QueryWorkflow：意图识别、模型提取检索词、混合召回、Schema图、MCP执行及结果说明；不向模型传入标准SQL、字段、检索词或结果。使用独立空会话、学校账户权限。
- 标准字段为预先编写标准SQL实际引用的物理字段（含筛选、分组、聚合和关联键），由SQL AST解析；同题去重，跨题累计。COUNT实体也显式引用实体ID。等价SQL可能使用不同关联路径，字段召回反映相对于该参考路径的覆盖。
- micro为所有题召回必要字段总数/必要字段总数，macro为各题召回率均值。仅统计最终检索hits，自动补充关联键另报，不将完整表目录计入召回。检索前失败按零召回纳入。
- SQL成功指最终数据库执行成功，包含应用内最多3次工具调用的修复；澄清、路由错误或异常均保留在总题数分母。结果说明状态另存，不与SQL执行混淆。
- 结果正确率以SQL返回结构化数据为准，必须满足全部要求列、全部行及重复次数。列名允许预定义中英文别名；排名严格检查顺序，其他分组忽略行序。整数严格比较，分数绝对容差0.005，比率绝对容差0.00005；不接受百分数与小数倍数差异。空结果也检查列。
- 每题参考SQL先在同一数据快照上执行，结果少于200行避免页面截断。标准结果是SQL oracle，未经独立人工双人标注；本批40题为人工设计的固定题集，非随机抽样，不据此推断生产准确率。
- 学校SQL生成器还会获得授权范围内完整字段目录，因此SQL正确率不能解释为仅靠检索的效果。
- 数据为单校合成数据，只有一个学期；不覆盖多轮上下文、并发压力、安全越权、真实脏数据，也未单独评价文字解释与图表正确率。具体模型、阈值、代码与CSV哈希见JSON metadata；不记录密钥。

## 失败案例

### EDU-001：八年级期中数学各班平均分是多少？输出班级名称、平均分，按原始满分计，排除缺考。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：63.64%。

生成SQL：
```sql
SELECT
  c.class_name AS "班级",
  ROUND(AVG(er.score), 2) AS "平均分"
FROM exam_results er
JOIN enrollments e ON er.enrollment_id = e.enrollment_id
JOIN classes c ON e.class_id = c.class_id
JOIN exams ex ON er.exam_id = ex.exam_id
JOIN subjects s ON ex.subject_id = s.subject_id
WHERE ex.grade = 8
  AND ex.exam_type = 'midterm'
  AND s.subject_name = '数学'
  AND er.exam_status = 'attended'
GROUP BY c.class_name
ORDER BY c.class_name
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, AVG(r.score) AS 平均分 FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id
JOIN enrollments e ON r.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id WHERE x.grade=8 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1
```

### EDU-002：七年级期末英语各班及格率是多少？输出班级名称、及格率，及格线为满分的60%，分母为实考人数，比率用0到1。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：58.33%。

生成SQL：
```sql
SELECT 
  c.class_name AS "班级",
  COUNT(CASE WHEN er.exam_status = 'attended' AND er.score >= e.max_score * s.pass_ratio THEN 1 END) * 1.0 / NULLIF(COUNT(CASE WHEN er.exam_status = 'attended' THEN 1 END), 0) AS "及格率"
FROM exam_results er
JOIN exams e ON er.exam_id = e.exam_id
JOIN enrollments en ON er.enrollment_id = en.enrollment_id
JOIN classes c ON en.class_id = c.class_id
JOIN subjects s ON e.subject_id = s.subject_id
WHERE c.grade = 7
  AND e.exam_type = 'final'
  AND s.subject_name = '英语'
GROUP BY c.class_name
ORDER BY c.class_name
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, COUNT(*) FILTER(WHERE r.score/x.max_score>=0.6)*1.0/COUNT(r.score) AS 及格率 FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id
JOIN enrollments e ON r.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='ENG' GROUP BY 1
```

### EDU-007：七年级期中语文各班实考人数和应考人数分别是多少？只输出班级名称、实考人数、应考人数。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：83.33%。

生成SQL：
```sql
SELECT 
  c.class_name AS "班级",
  COUNT(CASE WHEN er.exam_status = 'attended' THEN 1 END) AS "实考人数",
  COUNT(er.result_id) AS "应考人数"
FROM exam_results er
JOIN exams e ON er.exam_id = e.exam_id
JOIN enrollments en ON er.enrollment_id = en.enrollment_id
JOIN classes c ON en.class_id = c.class_id
WHERE e.grade = 7
  AND e.exam_type = 'midterm'
  AND e.subject_id = 'CHN'
GROUP BY c.class_name
ORDER BY c.class_name
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, COUNT(r.score) AS 实考人数, COUNT(r.result_id) AS 应考人数 FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id
JOIN enrollments e ON r.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id WHERE x.grade=7 AND x.exam_type='midterm' AND x.subject_id='CHN' GROUP BY 1
```

### EDU-014：2026年4月各班出勤率是多少？输出班级名称、出勤率；正常和迟到算出勤，所有应到记录作分母，用0到1。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：90.00%。

生成SQL：
```sql
SELECT
  c.class_name AS "班级",
  CAST(SUM(CASE WHEN a.attendance_status IN ('present', 'late') THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) AS "出勤率"
FROM attendance a
JOIN lessons l ON a.lesson_id = l.lesson_id
JOIN enrollments e ON a.enrollment_id = e.enrollment_id
JOIN classes c ON e.class_id = c.class_id
WHERE l.lesson_date >= '2026-04-01' AND l.lesson_date < '2026-05-01'
GROUP BY c.class_name
ORDER BY c.class_name
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, COUNT(*) FILTER(WHERE a.attendance_status IN ('present','late'))*1.0/COUNT(a.attendance_id) AS 出勤率 FROM attendance a JOIN lessons l ON a.lesson_id=l.lesson_id
JOIN enrollments e ON a.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id WHERE l.lesson_date>='2026-04-01' AND l.lesson_date<'2026-05-01' GROUP BY 1
```

### EDU-029：八年级期末数学答题记录按作答状态统计数量，输出作答状态（原始编码）、记录数。

判定：缺少或无法识别列：记录数
SQL成功：True；字段召回：45.45%。

生成SQL：
```sql
SELECT
  qr.response_status AS "作答状态",
  COUNT(*) AS "记录数量"
FROM question_responses qr
JOIN exam_results er ON qr.result_id = er.result_id
JOIN exams e ON er.exam_id = e.exam_id
WHERE e.grade = 8
  AND e.exam_type = 'final'
  AND e.subject_id = 'MAT'
GROUP BY qr.response_status
ORDER BY "记录数量" DESC
```
参考SQL：
```sql
SELECT r.response_status AS 作答状态, COUNT(r.response_id) AS 记录数 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=8 AND x.exam_type='final' AND x.subject_id='MAT' GROUP BY 1
```

### EDU-030：七年级期中数学试卷按知识点统计题目数，输出知识点名称、题目数；每道题只算一次。

判定：缺少或无法识别列：题目数
SQL成功：True；字段召回：100.00%。

生成SQL：
```sql
SELECT 
  kp.knowledge_name AS "知识点名称",
  COUNT(DISTINCT eq.question_id) AS "题目数量"
FROM exam_questions eq
JOIN exams e ON eq.exam_id = e.exam_id
JOIN knowledge_points kp ON eq.knowledge_id = kp.knowledge_id
WHERE e.grade = 7
  AND e.subject_id = 'MAT'
  AND e.exam_type = 'midterm'
GROUP BY kp.knowledge_name
ORDER BY "题目数量" DESC, kp.knowledge_name ASC
```
参考SQL：
```sql
SELECT k.knowledge_name AS 知识点名称, COUNT(q.question_id) AS 题目数 FROM exam_questions q JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=7 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1
```

### EDU-032：七年级期末语文各题型平均每条答题记录得分是多少？输出题型（原始编码）、平均得分，SQL平均值排除空分数。

判定：缺少或无法识别列：题型
SQL成功：True；字段召回：72.73%。

生成SQL：
```sql
SELECT
  eq.question_type AS "题型原始编码",
  AVG(qr.score) AS "平均得分"
FROM question_responses qr
JOIN exam_results er ON qr.result_id = er.result_id
JOIN exams e ON er.exam_id = e.exam_id
JOIN subjects s ON e.subject_id = s.subject_id
JOIN exam_questions eq ON qr.question_id = eq.question_id
WHERE e.grade = 7
  AND e.exam_type = 'final'
  AND s.subject_name = '语文'
GROUP BY eq.question_type
ORDER BY eq.question_type
```
参考SQL：
```sql
SELECT q.question_type AS 题型, AVG(r.score) AS 平均得分 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='CHN' GROUP BY 1
```

