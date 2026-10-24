"""Versioned school benchmark definitions; never supplied to the model."""
from __future__ import annotations

from typing import Any

from sqlglot import exp, parse_one
from sqlglot.optimizer.qualify import qualify

from app.database import SCHEMA, physical_table_name


EXAM_JOIN = """FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id
JOIN enrollments e ON r.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id"""
ATTENDANCE_JOIN = """FROM attendance a JOIN lessons l ON a.lesson_id=l.lesson_id
JOIN enrollments e ON a.enrollment_id=e.enrollment_id
JOIN classes c ON e.class_id=c.class_id"""
HOMEWORK_JOIN = """FROM assignment_submissions s JOIN assignments a ON s.assignment_id=a.assignment_id
JOIN teaching_assignments t ON a.teaching_id=t.teaching_id
JOIN classes c ON t.class_id=c.class_id"""
KNOWLEDGE_JOIN = """FROM question_responses r JOIN exam_questions q ON r.question_id=q.question_id
JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id
JOIN exams x ON q.exam_id=x.exam_id"""


def definitions() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(category: str, question: str, sql: str, columns: list[tuple[str, str, str]],
            *, ordered: bool = False, difficulty: str = "medium") -> None:
        cases.append({
            "case_id": f"EDU-{len(cases) + 1:03d}", "category": category,
            "difficulty": difficulty, "query": question, "gold_sql": sql,
            "columns": [{"name": name, "aliases": [name, alias], "kind": kind}
                        for name, alias, kind in columns],
            "order_sensitive": ordered,
        })

    add("成绩", "八年级期中数学各班平均分是多少？输出班级名称、平均分，按原始满分计，排除缺考。",
        f"SELECT c.class_name AS 班级名称, AVG(r.score) AS 平均分 {EXAM_JOIN} WHERE x.grade=8 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("平均分", "average_score", "score")])
    add("成绩", "七年级期末英语各班及格率是多少？输出班级名称、及格率，及格线为满分的60%，分母为实考人数，比率用0到1。",
        f"SELECT c.class_name AS 班级名称, COUNT(*) FILTER(WHERE r.score/x.max_score>=0.6)*1.0/COUNT(r.score) AS 及格率 {EXAM_JOIN} WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='ENG' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("及格率", "pass_rate", "ratio")])
    add("成绩", "各年级期中考试缺考记录有多少条？输出年级、缺考人次。",
        "SELECT x.grade AS 年级, COUNT(r.result_id) AS 缺考人次 FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id WHERE x.exam_type='midterm' AND r.exam_status='absent' GROUP BY 1",
        [("年级", "grade", "integer"), ("缺考人次", "absent_count", "integer")])
    add("成绩", "九年级期末物理原始成绩最高的前5名是谁？输出学号、姓名、成绩；成绩降序，同分按学号升序。排除缺考。",
        f"SELECT s.student_id AS 学号, s.student_name AS 姓名, r.score AS 成绩 {EXAM_JOIN} JOIN students s ON e.student_id=s.student_id WHERE x.grade=9 AND x.exam_type='final' AND x.subject_id='PHY' AND r.score IS NOT NULL ORDER BY r.score DESC,s.student_id LIMIT 5",
        [("学号", "student_id", "text"), ("姓名", "student_name", "text"), ("成绩", "score", "score")], ordered=True, difficulty="hard")
    add("成绩", "八年级期末各学科平均得分率是多少？输出学科名称、平均得分率，先算每个实考学生的成绩除以该考试满分，再求平均，用0到1。",
        "SELECT s.subject_name AS 学科名称, AVG(r.score/x.max_score) AS 平均得分率 FROM exam_results r JOIN exams x ON r.exam_id=x.exam_id JOIN subjects s ON x.subject_id=s.subject_id WHERE x.grade=8 AND x.exam_type='final' GROUP BY 1",
        [("学科名称", "subject_name", "text"), ("平均得分率", "average_score_ratio", "ratio")])
    add("成绩", "八年级各班数学从期中到期末平均原始分提高了多少？输出班级名称、期中平均分、期末平均分、提升分数；各次考试分别排除缺考。",
        f"SELECT c.class_name AS 班级名称, AVG(r.score) FILTER(WHERE x.exam_type='midterm') AS 期中平均分, AVG(r.score) FILTER(WHERE x.exam_type='final') AS 期末平均分, AVG(r.score) FILTER(WHERE x.exam_type='final')-AVG(r.score) FILTER(WHERE x.exam_type='midterm') AS 提升分数 {EXAM_JOIN} WHERE x.grade=8 AND x.subject_id='MAT' AND x.exam_type IN ('midterm','final') GROUP BY 1",
        [("班级名称", "class_name", "text"), ("期中平均分", "midterm_average", "score"), ("期末平均分", "final_average", "score"), ("提升分数", "improvement", "score")], difficulty="hard")
    add("成绩", "七年级期中语文各班实考人数和应考人数分别是多少？只输出班级名称、实考人数、应考人数。",
        f"SELECT c.class_name AS 班级名称, COUNT(r.score) AS 实考人数, COUNT(r.result_id) AS 应考人数 {EXAM_JOIN} WHERE x.grade=7 AND x.exam_type='midterm' AND x.subject_id='CHN' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("实考人数", "attended_students", "integer"), ("应考人数", "expected_students", "integer")])
    add("成绩", "2026年9月举行了多少场考试？输出考试场次。",
        "SELECT COUNT(x.exam_id) AS 考试场次 FROM exams x WHERE x.exam_date>='2026-09-01' AND x.exam_date<'2026-10-01'",
        [("考试场次", "exam_count", "integer")], difficulty="easy")

    add("考勤", "本学期每月出勤率是多少？输出月份（YYYY-MM）、出勤率；出勤含正常和迟到，分母含请假和缺勤，用0到1。",
        f"SELECT strftime(l.lesson_date,'%Y-%m') AS 月份, COUNT(*) FILTER(WHERE a.attendance_status IN ('present','late'))*1.0/COUNT(a.attendance_id) AS 出勤率 {ATTENDANCE_JOIN} WHERE c.term_id='T2025_2026_2' GROUP BY 1",
        [("月份", "month", "month"), ("出勤率", "attendance_rate", "ratio")])
    add("考勤", "2026年3月各年级迟到人次是多少？输出年级、迟到人次。",
        f"SELECT c.grade AS 年级, COUNT(a.attendance_id) AS 迟到人次 {ATTENDANCE_JOIN} WHERE l.lesson_date>='2026-03-01' AND l.lesson_date<'2026-04-01' AND a.attendance_status='late' GROUP BY 1",
        [("年级", "grade", "integer"), ("迟到人次", "late_count", "integer")])
    add("考勤", "全学期各班请假人次是多少？只输出班级名称、请假人次。",
        f"SELECT c.class_name AS 班级名称, COUNT(a.attendance_id) AS 请假人次 {ATTENDANCE_JOIN} WHERE a.attendance_status='excused' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("请假人次", "excused_count", "integer")])
    add("考勤", "全学期各年级迟到记录的平均迟到分钟数是多少？只统计迟到，输出年级、平均迟到分钟数。",
        f"SELECT c.grade AS 年级, AVG(a.late_minutes) AS 平均迟到分钟数 {ATTENDANCE_JOIN} WHERE a.attendance_status='late' GROUP BY 1",
        [("年级", "grade", "integer"), ("平均迟到分钟数", "average_late_minutes", "score")])
    add("考勤", "全学期缺勤（absent）人次最多的前5个班级是什么？输出班级名称、缺勤人次；人次降序，同值按班级名称升序。",
        f"SELECT c.class_name AS 班级名称, COUNT(a.attendance_id) AS 缺勤人次 {ATTENDANCE_JOIN} WHERE a.attendance_status='absent' GROUP BY 1 ORDER BY 2 DESC,1 ASC LIMIT 5",
        [("班级名称", "class_name", "text"), ("缺勤人次", "absent_count", "integer")], ordered=True)
    add("考勤", "2026年4月各班出勤率是多少？输出班级名称、出勤率；正常和迟到算出勤，所有应到记录作分母，用0到1。",
        f"SELECT c.class_name AS 班级名称, COUNT(*) FILTER(WHERE a.attendance_status IN ('present','late'))*1.0/COUNT(a.attendance_id) AS 出勤率 {ATTENDANCE_JOIN} WHERE l.lesson_date>='2026-04-01' AND l.lesson_date<'2026-05-01' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("出勤率", "attendance_rate", "ratio")])
    add("考勤", "全学期按考勤状态统计课堂考勤记录数，输出考勤状态（原始英文编码）、记录数。",
        "SELECT a.attendance_status AS 考勤状态, COUNT(a.attendance_id) AS 记录数 FROM attendance a GROUP BY 1",
        [("考勤状态", "attendance_status", "text"), ("记录数", "record_count", "integer")], difficulty="easy")
    add("考勤", "2026年9月各班有多少条考勤记录？输出班级名称、记录数；仅返回有记录的班级。",
        f"SELECT c.class_name AS 班级名称, COUNT(a.attendance_id) AS 记录数 {ATTENDANCE_JOIN} WHERE l.lesson_date>='2026-09-01' AND l.lesson_date<'2026-10-01' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("记录数", "record_count", "integer")])

    add("作业", "本学期各班作业完成率和按时提交率是多少？输出班级名称、完成率、按时提交率；分母包括未交，补交算完成，比率用0到1。",
        f"SELECT c.class_name AS 班级名称, COUNT(*) FILTER(WHERE s.submission_status IN ('on_time','late'))*1.0/COUNT(s.submission_id) AS 完成率, COUNT(*) FILTER(WHERE s.submission_status='on_time')*1.0/COUNT(s.submission_id) AS 按时提交率 {HOMEWORK_JOIN} WHERE t.term_id='T2025_2026_2' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("完成率", "completion_rate", "ratio"), ("按时提交率", "on_time_rate", "ratio")])
    add("作业", "各年级作业未交人次是多少？只输出年级、未交人次。",
        f"SELECT c.grade AS 年级, COUNT(s.submission_id) AS 未交人次 {HOMEWORK_JOIN} WHERE s.submission_status='missing' GROUP BY 1",
        [("年级", "grade", "integer"), ("未交人次", "missing_count", "integer")])
    add("作业", "2026年3月各学科布置了多少份作业？按布置时间筛选，输出学科名称、作业份数，每份作业只算一次。",
        "SELECT s.subject_name AS 学科名称, COUNT(a.assignment_id) AS 作业份数 FROM assignments a JOIN teaching_assignments t ON a.teaching_id=t.teaching_id JOIN subjects s ON t.subject_id=s.subject_id WHERE a.assigned_at>='2026-03-01' AND a.assigned_at<'2026-04-01' GROUP BY 1",
        [("学科名称", "subject_name", "text"), ("作业份数", "assignment_count", "integer")])
    add("作业", "八年级各班数学作业的已批改平均原始分是多少？排除无成绩记录，输出班级名称、平均分。",
        f"SELECT c.class_name AS 班级名称, AVG(s.score) AS 平均分 {HOMEWORK_JOIN} WHERE c.grade=8 AND t.subject_id='MAT' GROUP BY 1",
        [("班级名称", "class_name", "text"), ("平均分", "average_score", "score")])
    add("作业", "全学期各学科作业平均预计用时是多少分钟？每份作业等权，输出学科名称、平均预计分钟数。",
        "SELECT s.subject_name AS 学科名称, AVG(a.estimated_minutes) AS 平均预计分钟数 FROM assignments a JOIN teaching_assignments t ON a.teaching_id=t.teaching_id JOIN subjects s ON t.subject_id=s.subject_id GROUP BY 1",
        [("学科名称", "subject_name", "text"), ("平均预计分钟数", "average_estimated_minutes", "score")])
    add("作业", "全学期补交（late）作业人次最多的前5个班级是什么？输出班级名称、补交人次；人次降序，同值按班级名称升序。",
        f"SELECT c.class_name AS 班级名称, COUNT(s.submission_id) AS 补交人次 {HOMEWORK_JOIN} WHERE s.submission_status='late' GROUP BY 1 ORDER BY 2 DESC,1 ASC LIMIT 5",
        [("班级名称", "class_name", "text"), ("补交人次", "late_count", "integer")], ordered=True)
    add("作业", "各年级英语作业完成率是多少？输出年级、完成率，按时和补交算完成，全部应交记录作分母，用0到1。",
        f"SELECT c.grade AS 年级, COUNT(*) FILTER(WHERE s.submission_status IN ('on_time','late'))*1.0/COUNT(s.submission_id) AS 完成率 {HOMEWORK_JOIN} WHERE t.subject_id='ENG' GROUP BY 1",
        [("年级", "grade", "integer"), ("完成率", "completion_rate", "ratio")])
    add("作业", "本学期按提交状态统计作业应交记录数，输出提交状态（原始英文编码）、记录数。",
        "SELECT s.submission_status AS 提交状态, COUNT(s.submission_id) AS 记录数 FROM assignment_submissions s JOIN assignments a ON s.assignment_id=a.assignment_id JOIN teaching_assignments t ON a.teaching_id=t.teaching_id WHERE t.term_id='T2025_2026_2' GROUP BY 1",
        [("提交状态", "submission_status", "text"), ("记录数", "record_count", "integer")], difficulty="easy")

    add("知识点", "八年级期中数学各知识点得分率是多少？输出知识点名称、得分率，以学生题目总得分除以对应题目总满分，用0到1，包含缺考答题记录。",
        f"SELECT k.knowledge_name AS 知识点名称, SUM(r.score)*1.0/SUM(q.max_score) AS 得分率 {KNOWLEDGE_JOIN} WHERE x.grade=8 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1",
        [("知识点名称", "knowledge_name", "text"), ("得分率", "score_ratio", "ratio")], difficulty="hard")
    add("知识点", "七年级期末英语得分率最低的3个知识点是什么？输出知识点名称、得分率；总得分除以对应总满分，包含缺考记录，用0到1，按得分率升序，同值按知识点名称升序。",
        f"SELECT k.knowledge_name AS 知识点名称, SUM(r.score)*1.0/SUM(q.max_score) AS 得分率 {KNOWLEDGE_JOIN} WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='ENG' GROUP BY 1 ORDER BY 2,1 LIMIT 3",
        [("知识点名称", "knowledge_name", "text"), ("得分率", "score_ratio", "ratio")], ordered=True, difficulty="hard")
    add("知识点", "九年级期中物理试卷按题型统计题目数和总满分，输出题型（原始编码）、题目数、总满分。",
        "SELECT q.question_type AS 题型, COUNT(q.question_id) AS 题目数, SUM(q.max_score) AS 总满分 FROM exam_questions q JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=9 AND x.exam_type='midterm' AND x.subject_id='PHY' GROUP BY 1",
        [("题型", "question_type", "text"), ("题目数", "question_count", "integer"), ("总满分", "total_max_score", "score")])
    add("知识点", "各学科各年级配置了多少个知识点？输出学科名称、年级、知识点数。",
        "SELECT s.subject_name AS 学科名称, k.grade AS 年级, COUNT(k.knowledge_id) AS 知识点数 FROM knowledge_points k JOIN subjects s ON k.subject_id=s.subject_id GROUP BY 1,2",
        [("学科名称", "subject_name", "text"), ("年级", "grade", "integer"), ("知识点数", "knowledge_count", "integer")], difficulty="easy")
    add("知识点", "八年级期末数学答题记录按作答状态统计数量，输出作答状态（原始编码）、记录数。",
        f"SELECT r.response_status AS 作答状态, COUNT(r.response_id) AS 记录数 {KNOWLEDGE_JOIN} WHERE x.grade=8 AND x.exam_type='final' AND x.subject_id='MAT' GROUP BY 1",
        [("作答状态", "response_status", "text"), ("记录数", "record_count", "integer")])
    add("知识点", "七年级期中数学试卷按知识点统计题目数，输出知识点名称、题目数；每道题只算一次。",
        "SELECT k.knowledge_name AS 知识点名称, COUNT(q.question_id) AS 题目数 FROM exam_questions q JOIN knowledge_points k ON q.knowledge_id=k.knowledge_id JOIN exams x ON q.exam_id=x.exam_id WHERE x.grade=7 AND x.exam_type='midterm' AND x.subject_id='MAT' GROUP BY 1",
        [("知识点名称", "knowledge_name", "text"), ("题目数", "question_count", "integer")])
    add("知识点", "九年级期末化学各知识点的应答记录数和满分总和是多少？输出知识点名称、应答记录数、满分总和；包含缺考记录，每条学生答题记录对应一次题目满分。",
        f"SELECT k.knowledge_name AS 知识点名称, COUNT(r.response_id) AS 应答记录数, SUM(q.max_score) AS 满分总和 {KNOWLEDGE_JOIN} WHERE x.grade=9 AND x.exam_type='final' AND x.subject_id='CHE' GROUP BY 1",
        [("知识点名称", "knowledge_name", "text"), ("应答记录数", "response_count", "integer"), ("满分总和", "total_max_score", "score")], difficulty="hard")
    add("知识点", "七年级期末语文各题型平均每条答题记录得分是多少？输出题型（原始编码）、平均得分，SQL平均值排除空分数。",
        f"SELECT q.question_type AS 题型, AVG(r.score) AS 平均得分 {KNOWLEDGE_JOIN} WHERE x.grade=7 AND x.exam_type='final' AND x.subject_id='CHN' GROUP BY 1",
        [("题型", "question_type", "text"), ("平均得分", "average_score", "score")])

    add("教学安排", "本学期各年级在籍学生有多少人？输出年级、学生人数，按本学期学籍记录统计。",
        "SELECT c.grade AS 年级, COUNT(e.enrollment_id) AS 学生人数 FROM enrollments e JOIN classes c ON e.class_id=c.class_id WHERE e.term_id='T2025_2026_2' GROUP BY 1",
        [("年级", "grade", "integer"), ("学生人数", "student_count", "integer")])
    add("教学安排", "列出本学期所有班级的班主任，只输出班级名称、班主任姓名。",
        "SELECT c.class_name AS 班级名称, t.teacher_name AS 班主任姓名 FROM classes c JOIN teachers t ON c.homeroom_teacher_id=t.teacher_id WHERE c.term_id='T2025_2026_2'",
        [("班级名称", "class_name", "text"), ("班主任姓名", "homeroom_teacher_name", "text")], difficulty="easy")
    add("教学安排", "本学期八年级各班数学任课教师是谁，每周几课时？只输出班级名称、教师姓名、周课时数。",
        "SELECT c.class_name AS 班级名称, t.teacher_name AS 教师姓名, a.weekly_periods AS 周课时数 FROM teaching_assignments a JOIN classes c ON a.class_id=c.class_id JOIN teachers t ON a.teacher_id=t.teacher_id WHERE a.term_id='T2025_2026_2' AND c.grade=8 AND a.subject_id='MAT'",
        [("班级名称", "class_name", "text"), ("教师姓名", "teacher_name", "text"), ("周课时数", "weekly_periods", "integer")])
    add("教学安排", "本学期每月实际排课多少节？输出月份（YYYY-MM）、课节数，按课节日期分组。",
        "SELECT strftime(l.lesson_date,'%Y-%m') AS 月份, COUNT(l.lesson_id) AS 课节数 FROM lessons l JOIN teaching_assignments t ON l.teaching_id=t.teaching_id WHERE t.term_id='T2025_2026_2' GROUP BY 1",
        [("月份", "month", "month"), ("课节数", "lesson_count", "integer")])
    add("教学安排", "教师按职称统计人数和平均教龄，只输出职称、教师人数、平均教龄。",
        "SELECT t.title AS 职称, COUNT(t.teacher_id) AS 教师人数, AVG(t.teaching_years) AS 平均教龄 FROM teachers t GROUP BY 1",
        [("职称", "title", "text"), ("教师人数", "teacher_count", "integer"), ("平均教龄", "average_teaching_years", "score")], difficulty="easy")
    add("教学安排", "本学期各班男女学生分别有多少人？输出班级名称、性别（原始编码）、学生人数。",
        "SELECT c.class_name AS 班级名称, s.gender AS 性别, COUNT(e.enrollment_id) AS 学生人数 FROM enrollments e JOIN classes c ON e.class_id=c.class_id JOIN students s ON e.student_id=s.student_id WHERE e.term_id='T2025_2026_2' GROUP BY 1,2",
        [("班级名称", "class_name", "text"), ("性别", "gender", "text"), ("学生人数", "student_count", "integer")])
    add("教学安排", "本学期校历按日期类型统计天数，输出日期类型（原始编码）、天数。",
        "SELECT a.day_type AS 日期类型, COUNT(a.calendar_date) AS 天数 FROM academic_calendar a WHERE a.term_id='T2025_2026_2' GROUP BY 1",
        [("日期类型", "day_type", "text"), ("天数", "day_count", "integer")], difficulty="easy")
    add("教学安排", "本学期各学科实际排课多少节？输出学科名称、课节数。",
        "SELECT s.subject_name AS 学科名称, COUNT(l.lesson_id) AS 课节数 FROM lessons l JOIN teaching_assignments t ON l.teaching_id=t.teaching_id JOIN subjects s ON t.subject_id=s.subject_id WHERE t.term_id='T2025_2026_2' GROUP BY 1",
        [("学科名称", "subject_name", "text"), ("课节数", "lesson_count", "integer")])

    schema = {physical_table_name(t): {f["name"]: f["type"] for f in t["fields"]}
              for t in SCHEMA if t.get("database") == "school_teaching"}
    for case in cases:
        tree = qualify(parse_one(case["gold_sql"], read="duckdb"), schema=schema, dialect="duckdb")
        aliases = {t.alias_or_name: t.name for t in tree.find_all(exp.Table)}
        case["gold_fields"] = sorted({f"school_teaching.{aliases[c.table]}.{c.name}"
                                     for c in tree.find_all(exp.Column) if c.table in aliases})
        if not case["gold_fields"]:
            raise ValueError(f"No gold fields: {case['case_id']}")
    return cases
