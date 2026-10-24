# 学校教学问数评测报告

运行：school_20261019T134332Z；进度：40/40。

## 核心指标

| 指标 | 结果 |
|---|---|
| 字段级Schema召回率（micro） | 35.21%（119/338） |
| 字段级Schema召回率（macro） | 35.66% |
| 补充关联键后的召回率（micro） | 45.86% |
| SQL执行成功率 | 50.00%（20/40） |
| 首条SQL执行成功 | 13/40 |
| 查询结果正确率 | 40.00%（16/40） |
| 已执行SQL中的结果正确率 | 80.00% |
| 平均单题耗时（含模型调用） | 12.9秒 |

## 分类结果

| 类别 | 题数 | 字段召回micro | SQL成功 | 结果正确 |
|---|---:|---:|---:|---:|
| 成绩 | 8 | 61.84% | 8 | 6 |
| 考勤 | 8 | 63.24% | 8 | 7 |
| 作业 | 8 | 42.65% | 4 | 3 |
| 知识点 | 8 | 0.00% | 0 | 0 |
| 教学安排 | 8 | 0.00% | 0 | 0 |

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

### EDU-002：七年级期末英语各班及格率是多少？输出班级名称、及格率，及格线为满分的60%，分母为实考人数，比率用0到1。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：58.33%。

生成SQL：
```sql
SELECT 
  c.class_name AS "班级",
  CAST(SUM(CASE WHEN er.exam_status = 'attended' AND er.score >= e.max_score * s.pass_ratio THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(CAST(SUM(CASE WHEN er.exam_status = 'attended' THEN 1 ELSE 0 END) AS DOUBLE), 0) AS "及格率"
FROM exam_results er
JOIN exams e ON er.exam_id = e.exam_id
JOIN enrollments en ON er.enrollment_id = en.enrollment_id
JOIN classes c ON en.class_id = c.class_id
JOIN subjects s ON e.subject_id = s.subject_id
WHERE e.grade = 7
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

### EDU-006：八年级各班数学从期中到期末平均原始分提高了多少？输出班级名称、期中平均分、期末平均分、提升分数；各次考试分别排除缺考。

判定：缺少或无法识别列：期中平均分
SQL成功：True；字段召回：63.64%。

生成SQL：
```sql
WITH midterm_scores AS (
    SELECT
        c.class_name,
        AVG(er.score) AS avg_score
    FROM exam_results er
    JOIN exams e ON er.exam_id = e.exam_id
    JOIN enrollments en ON er.enrollment_id = en.enrollment_id
    JOIN classes c ON en.class_id = c.class_id
    WHERE e.grade = 8
      AND e.subject_id = 'MAT'
      AND e.exam_type = 'midterm'
      AND er.exam_status = 'attended'
    GROUP BY c.class_name
),
final_scores AS (
    SELECT
        c.class_name,
        AVG(er.score) AS avg_score
    FROM exam_results er
    JOIN exams e ON er.exam_id = e.exam_id
    JOIN enrollments en ON er.enrollment_id = en.enrollment_id
    JOIN classes c ON en.class_id = c.class_id
    WHERE e.grade = 8
      AND e.subject_id = 'MAT'
      AND e.exam_type = 'final'
      AND er.exam_status = 'attended'
    GROUP BY c.class_name
)
SELECT
    m.class_name AS "班级名称",
    ROUND(m.avg_score, 2) AS "期中数学平均分",
    ROUND(f.avg_score, 2) AS "期末数学平均分",
    ROUND(f.avg_score - m.avg_score, 2) AS "提升分数"
FROM midterm_scores m
JOIN final_scores f ON m.class_name = f.class_name
ORDER BY m.class_name
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, AVG(r.score) FILTER(WHERE x.exam_type='midterm') AS 期中平均分, AVG(r.score) FILTER(WHERE x.exam_type='final') AS 期末平均分, AVG(r.score) FILTER(WHERE x.exam_type='final')-AVG(r.score) FILTER(WHERE x.exam_type='midterm') AS 提升分数 FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id
JOIN enrollments e ON r.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id WHERE x.grade=8 AND x.subject_id='MAT' AND x.exam_type IN ('midterm','final') GROUP BY 1
```

### EDU-014：2026年4月各班出勤率是多少？输出班级名称、出勤率；正常和迟到算出勤，所有应到记录作分母，用0到1。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：80.00%。

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

### EDU-017：本学期各班作业完成率和按时提交率是多少？输出班级名称、完成率、按时提交率；分母包括未交，补交算完成，比率用0到1。

判定：缺少或无法识别列：班级名称
SQL成功：True；字段召回：70.00%。

生成SQL：
```sql
SELECT
  c.class_name AS "班级",
  CAST(SUM(CASE WHEN s.submission_status IN ('on_time', 'late') THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) AS "完成率",
  CAST(SUM(CASE WHEN s.submission_status = 'on_time' THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) AS "按时提交率"
FROM assignment_submissions s
JOIN enrollments e ON s.enrollment_id = e.enrollment_id
JOIN classes c ON e.class_id = c.class_id
WHERE c.term_id = 'T2025_2026_2'
GROUP BY c.class_name
ORDER BY c.class_name
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, COUNT(*) FILTER(WHERE s.submission_status IN ('on_time','late'))*1.0/COUNT(s.submission_id) AS 完成率, COUNT(*) FILTER(WHERE s.submission_status='on_time')*1.0/COUNT(s.submission_id) AS 按时提交率 FROM assignment_submissions s JOIN assignments a ON s.assignment_id=a.assignment_id
JOIN teaching_assignments t ON a.teaching_id=t.teaching_id
JOIN classes c ON t.class_id=c.class_id WHERE t.term_id='T2025_2026_2' GROUP BY 1
```

### EDU-021：全学期各学科作业平均预计用时是多少分钟？每份作业等权，输出学科名称、平均预计分钟数。

判定：PipelineStageError: 模型接口调用失败: 模型接口返回 HTTP 400: {"error":{"message":"Access denied, please make sure your account is in good standing. For details, see: https://help.aliyun.com/zh/model-studio/error-code#overdue-payment","type":"Arrearage","param":null,"code":"Arrearage"},"id":"chatcmpl-779848d5-c773-9976-af7c-03465d9b311d","request_id":"779848d5-c773-9976-af7c-03465d9b311d"}
SQL成功：False；字段召回：83.33%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT s.subject_name AS 学科名称, AVG(a.estimated_minutes) AS 平均预计分钟数 FROM assignments a JOIN teaching_assignments t ON a.teaching_id=t.teaching_id JOIN subjects s ON t.subject_id=s.subject_id GROUP BY 1
```

### EDU-022：全学期补交（late）作业人次最多的前5个班级是什么？输出班级名称、补交人次；人次降序，同值按班级名称升序。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, COUNT(s.submission_id) AS 补交人次 FROM assignment_submissions s JOIN assignments a ON s.assignment_id=a.assignment_id
JOIN teaching_assignments t ON a.teaching_id=t.teaching_id
JOIN classes c ON t.class_id=c.class_id WHERE s.submission_status='late' GROUP BY 1 ORDER BY 2 DESC,1 ASC LIMIT 5
```

### EDU-023：各年级英语作业完成率是多少？输出年级、完成率，按时和补交算完成，全部应交记录作分母，用0到1。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT c.grade AS 年级, COUNT(*) FILTER(WHERE s.submission_status IN ('on_time','late'))*1.0/COUNT(s.submission_id) AS 完成率 FROM assignment_submissions s JOIN assignments a ON s.assignment_id=a.assignment_id
JOIN teaching_assignments t ON a.teaching_id=t.teaching_id
JOIN classes c ON t.class_id=c.class_id WHERE t.subject_id='ENG' GROUP BY 1
```

### EDU-024：本学期按提交状态统计作业应交记录数，输出提交状态（原始英文编码）、记录数。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT s.submission_status AS 提交状态, COUNT(s.submission_id) AS 记录数 FROM assignment_submissions s JOIN assignments a ON s.assignment_id=a.assignment_id JOIN teaching_assignments t ON a.teaching_id=t.teaching_id WHERE t.term_id='T2025_2026_2' GROUP BY 1
```

### EDU-025：八年级期中数学各知识点得分率是多少？输出知识点名称、得分率，以学生题目总得分除以对应题目总满分，用0到1，包含缺考答题记录。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT k.knowledge_name AS 知识点名称, SUM(r.score)*1.0/SUM(q.max_score) AS 得分率 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=8 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1
```

### EDU-026：七年级期末英语得分率最低的3个知识点是什么？输出知识点名称、得分率；总得分除以对应总满分，包含缺考记录，用0到1，按得分率升序，同值按知识点名称升序。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT k.knowledge_name AS 知识点名称, SUM(r.score)*1.0/SUM(q.max_score) AS 得分率 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='ENG' GROUP BY 1 ORDER BY 2,1 LIMIT 3
```

### EDU-027：九年级期中物理试卷按题型统计题目数和总满分，输出题型（原始编码）、题目数、总满分。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT q.question_type AS 题型, COUNT(q.question_id) AS 题目数, SUM(q.max_score) AS 总满分 FROM exam_questions q JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=9 AND x.exam_type='midterm' AND x.subject_id='PHY' GROUP BY 1
```

### EDU-028：各学科各年级配置了多少个知识点？输出学科名称、年级、知识点数。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT s.subject_name AS 学科名称, k.grade AS 年级, COUNT(k.knowledge_id) AS 知识点数 FROM knowledge_points k JOIN subjects s ON k.subject_id=s.subject_id GROUP BY 1,2
```

### EDU-029：八年级期末数学答题记录按作答状态统计数量，输出作答状态（原始编码）、记录数。

判定：PipelineStageError: 模型接口调用失败: 模型接口返回 HTTP 400: {"error":{"message":"Access denied, please make sure your account is in good standing. For details, see: https://help.aliyun.com/zh/model-studio/error-code#overdue-payment","type":"Arrearage","param":null,"code":"Arrearage"},"id":"e2b0c5ce-96f7-9750-945d-d332d96ed9e2","request_id":"e2b0c5ce-96f7-9750-945d-d332d96ed9e2"}
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT r.response_status AS 作答状态, COUNT(r.response_id) AS 记录数 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=8 AND x.exam_type='final' AND x.subject_id='MAT' GROUP BY 1
```

### EDU-030：七年级期中数学试卷按知识点统计题目数，输出知识点名称、题目数；每道题只算一次。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT k.knowledge_name AS 知识点名称, COUNT(q.question_id) AS 题目数 FROM exam_questions q JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=7 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1
```

### EDU-031：九年级期末化学各知识点的应答记录数和满分总和是多少？输出知识点名称、应答记录数、满分总和；包含缺考记录，每条学生答题记录对应一次题目满分。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT k.knowledge_name AS 知识点名称, COUNT(r.response_id) AS 应答记录数, SUM(q.max_score) AS 满分总和 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=9 AND x.exam_type='final' AND x.subject_id='CHE' GROUP BY 1
```

### EDU-032：七年级期末语文各题型平均每条答题记录得分是多少？输出题型（原始编码）、平均得分，SQL平均值排除空分数。

判定：PipelineStageError: 模型接口调用失败: 模型接口返回 HTTP 400: {"error":{"message":"Access denied, please make sure your account is in good standing. For details, see: https://help.aliyun.com/zh/model-studio/error-code#overdue-payment","type":"Arrearage","param":null,"code":"Arrearage"},"id":"8a8621f9-0612-9f9a-916b-a9402fea4fd4","request_id":"8a8621f9-0612-9f9a-916b-a9402fea4fd4"}
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT q.question_type AS 题型, AVG(r.score) AS 平均得分 FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='CHN' GROUP BY 1
```

### EDU-033：本学期各年级在籍学生有多少人？输出年级、学生人数，按本学期学籍记录统计。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT c.grade AS 年级, COUNT(e.enrollment_id) AS 学生人数 FROM enrollments e JOIN classes c ON e.class_id=c.class_id WHERE e.term_id='T2025_2026_2' GROUP BY 1
```

### EDU-034：列出本学期所有班级的班主任，只输出班级名称、班主任姓名。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, t.teacher_name AS 班主任姓名 FROM classes c JOIN teachers t ON c.homeroom_teacher_id=t.teacher_id WHERE c.term_id='T2025_2026_2'
```

### EDU-035：本学期八年级各班数学任课教师是谁，每周几课时？只输出班级名称、教师姓名、周课时数。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, t.teacher_name AS 教师姓名, a.weekly_periods AS 周课时数 FROM teaching_assignments a JOIN classes c ON a.class_id=c.class_id JOIN teachers t ON a.teacher_id=t.teacher_id WHERE a.term_id='T2025_2026_2' AND c.grade=8 AND a.subject_id='MAT'
```

### EDU-036：本学期每月实际排课多少节？输出月份（YYYY-MM）、课节数，按课节日期分组。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT strftime(l.lesson_date,'%Y-%m') AS 月份, COUNT(l.lesson_id) AS 课节数 FROM lessons l JOIN teaching_assignments t ON l.teaching_id=t.teaching_id WHERE t.term_id='T2025_2026_2' GROUP BY 1
```

### EDU-037：教师按职称统计人数和平均教龄，只输出职称、教师人数、平均教龄。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT t.title AS 职称, COUNT(t.teacher_id) AS 教师人数, AVG(t.teaching_years) AS 平均教龄 FROM teachers t GROUP BY 1
```

### EDU-038：本学期各班男女学生分别有多少人？输出班级名称、性别（原始编码）、学生人数。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT c.class_name AS 班级名称, s.gender AS 性别, COUNT(e.enrollment_id) AS 学生人数 FROM enrollments e JOIN classes c ON e.class_id=c.class_id JOIN students s ON e.student_id=s.student_id WHERE e.term_id='T2025_2026_2' GROUP BY 1,2
```

### EDU-039：本学期校历按日期类型统计天数，输出日期类型（原始编码）、天数。

判定：未成功执行SQL
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT a.day_type AS 日期类型, COUNT(a.calendar_date) AS 天数 FROM academic_calendar a WHERE a.term_id='T2025_2026_2' GROUP BY 1
```

### EDU-040：本学期各学科实际排课多少节？输出学科名称、课节数。

判定：PipelineStageError: 模型接口调用失败: 模型接口返回 HTTP 400: {"error":{"message":"Access denied, please make sure your account is in good standing. For details, see: https://help.aliyun.com/zh/model-studio/error-code#overdue-payment","type":"Arrearage","param":null,"code":"Arrearage"},"id":"0b7d56d8-5150-9bb6-b535-cac6295e0543","request_id":"0b7d56d8-5150-9bb6-b535-cac6295e0543"}
SQL成功：False；字段召回：0.00%。

生成SQL：
```sql
-- 未生成
```
参考SQL：
```sql
SELECT s.subject_name AS 学科名称, COUNT(l.lesson_id) AS 课节数 FROM lessons l JOIN teaching_assignments t ON l.teaching_id=t.teaching_id JOIN subjects s ON t.subject_id=s.subject_id WHERE t.term_id='T2025_2026_2' GROUP BY 1
```

