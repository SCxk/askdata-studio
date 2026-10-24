from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from generate_school_teaching_data import END, START, open_school_database
from school_teaching_definitions import DATABASE, DATABASE_DIR, NULLABLE_FIELDS, RELATIONS, TABLES


EXAMPLES = [
    ("八年级期中数学各班平均分、及格率和缺考人数是多少？", """
        SELECT c.class_name, COUNT(*) AS expected_students,
               COUNT(r.score) AS attended_students,
               COUNT(*) FILTER (WHERE r.exam_status='absent') AS absent_students,
               ROUND(AVG(r.score), 2) AS average_score,
               ROUND(100.0*COUNT(*) FILTER (WHERE r.score/x.max_score>=s.pass_ratio)
                     /NULLIF(COUNT(r.score),0),2) AS pass_rate_pct
        FROM exam_results r JOIN exams x USING(exam_id)
        JOIN enrollments e USING(enrollment_id) JOIN classes c USING(class_id)
        JOIN subjects s ON x.subject_id=s.subject_id
        WHERE x.grade=8 AND x.subject_id='MAT' AND x.exam_type='midterm'
        GROUP BY c.class_name ORDER BY c.class_name"""),
    ("全校每月出勤率、迟到人次和请假人次是多少？", """
        SELECT strftime(l.lesson_date,'%Y-%m') AS month, COUNT(*) AS expected_lesson_persons,
               ROUND(100.0*COUNT(*) FILTER (WHERE a.attendance_status IN ('present','late'))/COUNT(*),2) AS attendance_rate_pct,
               COUNT(*) FILTER (WHERE a.attendance_status='late') AS late_lesson_persons,
               COUNT(*) FILTER (WHERE a.attendance_status='excused') AS excused_lesson_persons
        FROM attendance a JOIN lessons l USING(lesson_id) GROUP BY 1 ORDER BY 1"""),
    ("各班作业完成率和按时提交率是多少？", """
        SELECT c.class_name, COUNT(*) AS expected_submissions,
               ROUND(100.0*COUNT(*) FILTER (WHERE h.submission_status IN ('on_time','late'))/COUNT(*),2) AS completion_rate_pct,
               ROUND(100.0*COUNT(*) FILTER (WHERE h.submission_status='on_time')/COUNT(*),2) AS on_time_rate_pct
        FROM assignment_submissions h JOIN enrollments e USING(enrollment_id)
        JOIN classes c USING(class_id) GROUP BY 1 ORDER BY 1"""),
    ("八年级期末数学得分率最低的知识点有哪些？", """
        SELECT k.knowledge_name, COUNT(*) AS answered_question_persons,
               ROUND(100.0*SUM(r.score)/SUM(q.max_score),2) AS score_rate_pct
        FROM question_responses r JOIN exam_questions q USING(question_id)
        JOIN knowledge_points k USING(knowledge_id) JOIN exams x USING(exam_id)
        WHERE x.grade=8 AND x.subject_id='MAT' AND x.exam_type='final'
        GROUP BY 1 ORDER BY score_rate_pct, k.knowledge_name"""),
    ("七年级各班数学从三月到期末平均进步多少？只比较两次均实考的学生。", """
        WITH paired AS (
            SELECT r.enrollment_id,
                   MAX(CASE WHEN x.exam_type='monthly' THEN 100*r.score/x.max_score END) AS baseline,
                   MAX(CASE WHEN x.exam_type='final' THEN 100*r.score/x.max_score END) AS final_score
            FROM exam_results r JOIN exams x USING(exam_id)
            WHERE x.grade=7 AND x.subject_id='MAT' AND r.exam_status='attended'
            GROUP BY r.enrollment_id
        )
        SELECT c.class_name, COUNT(*) AS paired_students,
               ROUND(AVG(p.final_score-p.baseline),2) AS percentage_point_change
        FROM paired p JOIN enrollments e USING(enrollment_id) JOIN classes c USING(class_id)
        WHERE p.baseline IS NOT NULL AND p.final_score IS NOT NULL GROUP BY 1 ORDER BY 1"""),
    ("各年级各轮考试缺考率是多少？", """
        SELECT x.grade, x.exam_type, COUNT(*) AS expected_exam_persons,
               COUNT(*) FILTER (WHERE r.exam_status='absent') AS absent_exam_persons,
               ROUND(100.0*COUNT(*) FILTER (WHERE r.exam_status='absent')/COUNT(*),2) AS absence_rate_pct
        FROM exam_results r JOIN exams x USING(exam_id) GROUP BY 1,2 ORDER BY 1,2"""),
    ("哪些学生在本学期至少有三个教学日发生无故缺勤？", """
        SELECT s.student_id, s.student_name, c.class_name,
               COUNT(DISTINCT l.lesson_date) AS absent_days
        FROM attendance a JOIN lessons l USING(lesson_id)
        JOIN enrollments e USING(enrollment_id) JOIN students s USING(student_id)
        JOIN classes c USING(class_id) WHERE a.attendance_status='absent'
        GROUP BY 1,2,3 HAVING COUNT(DISTINCT l.lesson_date)>=3
        ORDER BY absent_days DESC,s.student_id LIMIT 20"""),
    ("全校各学科期末平均百分制成绩是多少？", """
        SELECT s.subject_name, COUNT(r.score) AS attended_exam_persons,
               ROUND(AVG(100*r.score/x.max_score),2) AS average_percentage_score
        FROM exam_results r JOIN exams x USING(exam_id) JOIN subjects s USING(subject_id)
        WHERE x.exam_type='final' AND r.exam_status='attended'
        GROUP BY 1 ORDER BY 1"""),
    ("各教学周的迟到率是多少？", """
        SELECT cal.week_no, COUNT(*) AS expected_lesson_persons,
               ROUND(100.0*COUNT(*) FILTER (WHERE a.attendance_status='late')/COUNT(*),2) AS late_rate_pct
        FROM attendance a JOIN lessons l USING(lesson_id)
        JOIN academic_calendar cal ON l.lesson_date=cal.calendar_date
        GROUP BY 1 ORDER BY 1"""),
    ("哪些学生本学期未交作业最多？", """
        SELECT s.student_id, s.student_name, c.class_name,
               COUNT(*) AS expected_submissions,
               COUNT(*) FILTER (WHERE h.submission_status='missing') AS missing_submissions
        FROM assignment_submissions h JOIN enrollments e USING(enrollment_id)
        JOIN students s USING(student_id) JOIN classes c USING(class_id)
        GROUP BY 1,2,3 ORDER BY missing_submissions DESC,s.student_id LIMIT 20"""),
]


def normalize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def validate(folder: Path = DATABASE_DIR) -> dict:
    manifest = json.loads((folder / "_database_manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((folder / "_schema.json").read_text(encoding="utf-8"))
    connection = open_school_database(folder)
    checks: list[dict] = []

    def check(name: str, sql: str) -> None:
        bad_rows = connection.execute(sql).fetchone()[0]
        checks.append({"check": name, "passed": bad_rows == 0, "violations": bad_rows})

    def records(sql: str) -> list[dict]:
        cursor = connection.execute(sql)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    try:
        for name, spec in TABLES.items():
            keys = ",".join(f'"{key}"' for key in spec["pk"])
            null_keys = " OR ".join(f'"{key}" IS NULL' for key in spec["pk"])
            check(f"{name}: non-null primary key", f'SELECT COUNT(*) FROM "{name}" WHERE {null_keys}')
            check(f"{name}: unique primary key", f'SELECT COUNT(*) FROM (SELECT {keys} FROM "{name}" GROUP BY {keys} HAVING COUNT(*)>1)')
            required = " OR ".join(f'"{field}" IS NULL' for field, _, _, _ in spec["fields"] if (name, field) not in NULLABLE_FIELDS)
            check(f"{name}: required fields", f'SELECT COUNT(*) FROM "{name}" WHERE {required}')
            actual = connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            checks.append({"check": f"{name}: manifest count", "passed": actual == manifest["tables"][name]["row_count"], "violations": abs(actual - manifest["tables"][name]["row_count"])})
            digest = hashlib.sha256((folder / f"{name}.csv").read_bytes()).hexdigest()
            checks.append({"check": f"{name}: file checksum", "passed": digest == manifest["tables"][name]["sha256"], "violations": int(digest != manifest["tables"][name]["sha256"])})
            metadata = next(table for table in schema["tables"] if table["name"] == name)
            actual_fields = [(row[0], row[1]) for row in connection.execute(f'DESCRIBE "{name}"').fetchall()]
            expected_fields = [(field["name"], field["source_type"]) for field in metadata["fields"]]
            consistent = actual_fields == expected_fields and metadata["row_count"] == actual and metadata["primary_key"] == spec["pk"]
            checks.append({"check": f"{name}: schema metadata", "passed": consistent, "violations": int(not consistent)})
        for parent, pk, child, fk in RELATIONS:
            check(f"{child}.{fk}: foreign key", f'SELECT COUNT(*) FROM "{child}" c LEFT JOIN "{parent}" p ON c."{fk}"=p."{pk}" WHERE c."{fk}" IS NULL OR p."{pk}" IS NULL')

        rules = {
            "single enrollment per student and term": "SELECT COUNT(*) FROM (SELECT student_id,term_id FROM enrollments GROUP BY 1,2 HAVING COUNT(*)<>1)",
            "student ages and admission years": "SELECT COUNT(*) FROM students s JOIN enrollments e USING(student_id) JOIN classes c USING(class_id) WHERE s.enrollment_year<>2025-(c.grade-7) OR s.birth_date<make_date(s.enrollment_year-13,9,1) OR s.birth_date>=make_date(s.enrollment_year-12,9,1)",
            "one teacher per class subject term": "SELECT COUNT(*) FROM (SELECT class_id,subject_id,term_id FROM teaching_assignments GROUP BY 1,2,3 HAVING COUNT(*)<>1)",
            "homeroom teacher teaches their class": "SELECT COUNT(*) FROM classes c WHERE NOT EXISTS (SELECT 1 FROM teaching_assignments t WHERE t.class_id=c.class_id AND t.teacher_id=c.homeroom_teacher_id)",
            "class timetable has no overlaps": "SELECT COUNT(*) FROM (SELECT t.class_id,l.lesson_date,l.period_no FROM lessons l JOIN teaching_assignments t USING(teaching_id) GROUP BY 1,2,3 HAVING COUNT(*)>1)",
            "teacher timetable has no overlaps": "SELECT COUNT(*) FROM (SELECT t.teacher_id,l.lesson_date,l.period_no FROM lessons l JOIN teaching_assignments t USING(teaching_id) GROUP BY 1,2,3 HAVING COUNT(*)>1)",
            "lessons only on teaching days": "SELECT COUNT(*) FROM lessons l JOIN academic_calendar c ON l.lesson_date=c.calendar_date WHERE c.day_type NOT IN ('teaching','exam') OR CAST(l.start_at AS DATE)<>l.lesson_date OR l.end_at-l.start_at<>INTERVAL '45 minutes' OR l.period_no NOT BETWEEN 1 AND 7",
            "no lessons on grade examination days": "SELECT COUNT(*) FROM lessons l JOIN teaching_assignments t USING(teaching_id) JOIN classes c USING(class_id) WHERE EXISTS (SELECT 1 FROM exams x WHERE x.grade=c.grade AND x.exam_date=l.lesson_date)",
            "unique student per lesson": "SELECT COUNT(*) FROM (SELECT lesson_id,enrollment_id FROM attendance GROUP BY 1,2 HAVING COUNT(*)<>1)",
            "attendance matches enrollment and lesson": "SELECT COUNT(*) FROM attendance a JOIN lessons l USING(lesson_id) JOIN teaching_assignments t USING(teaching_id) JOIN enrollments e USING(enrollment_id) WHERE t.class_id<>e.class_id OR l.lesson_date NOT BETWEEN e.valid_from AND e.valid_to OR t.term_id<>e.term_id",
            "complete lesson rosters": "SELECT COUNT(*) FROM (SELECT l.lesson_id,COUNT(a.attendance_id) n,(SELECT COUNT(*) FROM enrollments e WHERE e.class_id=t.class_id) expected FROM lessons l JOIN teaching_assignments t USING(teaching_id) LEFT JOIN attendance a USING(lesson_id) GROUP BY l.lesson_id,t.class_id HAVING n<>expected)",
            "valid attendance states and minutes": "SELECT COUNT(*) FROM attendance WHERE attendance_status NOT IN ('present','late','excused','absent') OR (attendance_status='late' AND late_minutes NOT BETWEEN 1 AND 18) OR (attendance_status<>'late' AND late_minutes<>0)",
            "full-day leave and absence are consistent": "SELECT COUNT(*) FROM (SELECT a.enrollment_id,l.lesson_date FROM attendance a JOIN lessons l USING(lesson_id) GROUP BY 1,2 HAVING COUNT(*) FILTER (WHERE a.attendance_status IN ('excused','absent'))>0 AND COUNT(DISTINCT a.attendance_status)>1)",
            "exams only on exam days": "SELECT COUNT(*) FROM exams x JOIN academic_calendar c ON x.exam_date=c.calendar_date WHERE c.day_type<>'exam' OR CAST(x.start_at AS DATE)<>x.exam_date",
            "exam schedules do not overlap": "SELECT COUNT(*) FROM exams a JOIN exams b ON a.grade=b.grade AND a.exam_date=b.exam_date AND a.exam_id<b.exam_id WHERE a.start_at<b.start_at+b.duration_minutes*INTERVAL '1 minute' AND b.start_at<a.start_at+a.duration_minutes*INTERVAL '1 minute'",
            "exam roster unique": "SELECT COUNT(*) FROM (SELECT exam_id,enrollment_id FROM exam_results GROUP BY 1,2 HAVING COUNT(*)<>1)",
            "exam results match grade term enrollment": "SELECT COUNT(*) FROM exam_results r JOIN exams x USING(exam_id) JOIN enrollments e USING(enrollment_id) JOIN classes c USING(class_id) WHERE x.grade<>c.grade OR x.term_id<>e.term_id OR x.exam_date NOT BETWEEN e.valid_from AND e.valid_to",
            "complete exam rosters": "SELECT COUNT(*) FROM (SELECT x.exam_id,COUNT(r.result_id) n,(SELECT COUNT(*) FROM enrollments e JOIN classes c USING(class_id) WHERE c.grade=x.grade) expected FROM exams x LEFT JOIN exam_results r USING(exam_id) GROUP BY x.exam_id,x.grade HAVING n<>expected)",
            "absent scores null and attended scores in range": "SELECT COUNT(*) FROM exam_results r JOIN exams x USING(exam_id) WHERE r.exam_status NOT IN ('attended','absent') OR (r.exam_status='absent' AND (r.score IS NOT NULL OR r.absence_reason IS NULL)) OR (r.exam_status='attended' AND (r.score IS NULL OR r.score<0 OR r.score>x.max_score OR r.absence_reason IS NOT NULL))",
            "paper totals and twenty questions": "SELECT COUNT(*) FROM (SELECT x.exam_id,x.max_score,COUNT(q.question_id) n,SUM(q.max_score) total FROM exams x LEFT JOIN exam_questions q USING(exam_id) GROUP BY 1,2 HAVING n<>20 OR total<>x.max_score)",
            "knowledge matches exam grade subject": "SELECT COUNT(*) FROM exam_questions q JOIN exams x USING(exam_id) JOIN knowledge_points k USING(knowledge_id) WHERE x.grade<>k.grade OR x.subject_id<>k.subject_id",
            "one response per student question": "SELECT COUNT(*) FROM (SELECT result_id,question_id FROM question_responses GROUP BY 1,2 HAVING COUNT(*)<>1)",
            "response belongs to the correct exam": "SELECT COUNT(*) FROM question_responses p JOIN exam_results r USING(result_id) JOIN exam_questions q USING(question_id) WHERE r.exam_id<>q.exam_id OR r.exam_status<>'attended'",
            "response scores and blank answers": "SELECT COUNT(*) FROM question_responses r JOIN exam_questions q USING(question_id) WHERE r.score IS NULL OR r.score<0 OR r.score>q.max_score OR r.response_status NOT IN ('answered','blank') OR (r.response_status='blank' AND r.score<>0) OR (q.question_type='choice' AND r.score NOT IN (0,q.max_score)) OR r.score*2<>ROUND(r.score*2)",
            "total scores reconcile with responses": "SELECT COUNT(*) FROM (SELECT r.result_id,r.exam_status,r.score,COUNT(p.response_id) n,SUM(p.score) total FROM exam_results r LEFT JOIN question_responses p USING(result_id) GROUP BY 1,2,3 HAVING (r.exam_status='attended' AND (n<>20 OR total<>r.score)) OR (r.exam_status='absent' AND n<>0))",
            "one homework record per required student": "SELECT COUNT(*) FROM (SELECT assignment_id,enrollment_id FROM assignment_submissions GROUP BY 1,2 HAVING COUNT(*)<>1)",
            "homework matches class enrollment": "SELECT COUNT(*) FROM assignment_submissions s JOIN assignments a USING(assignment_id) JOIN teaching_assignments t USING(teaching_id) JOIN enrollments e USING(enrollment_id) WHERE t.class_id<>e.class_id OR t.term_id<>e.term_id OR CAST(a.assigned_at AS DATE) NOT BETWEEN e.valid_from AND e.valid_to",
            "complete homework rosters": "SELECT COUNT(*) FROM (SELECT a.assignment_id,COUNT(s.submission_id) n,(SELECT COUNT(*) FROM enrollments e WHERE e.class_id=t.class_id) expected FROM assignments a JOIN teaching_assignments t USING(teaching_id) LEFT JOIN assignment_submissions s USING(assignment_id) GROUP BY a.assignment_id,t.class_id HAVING n<>expected)",
            "homework state timestamps and scores": "SELECT COUNT(*) FROM assignment_submissions s JOIN assignments a USING(assignment_id) WHERE s.submission_status NOT IN ('missing','late','on_time') OR (s.submission_status='missing' AND (s.submitted_at IS NOT NULL OR s.graded_at IS NOT NULL OR s.score IS NOT NULL)) OR (s.submission_status<>'missing' AND (s.submitted_at IS NULL OR s.graded_at IS NULL OR s.score IS NULL OR s.submitted_at<a.assigned_at OR s.graded_at<s.submitted_at OR s.score<0 OR s.score>a.max_score)) OR (s.submission_status='on_time' AND s.submitted_at>a.due_at) OR (s.submission_status='late' AND s.submitted_at<=a.due_at)",
            "assignment follows actual class lesson": "SELECT COUNT(*) FROM assignments a WHERE NOT EXISTS (SELECT 1 FROM lessons l WHERE l.teaching_id=a.teaching_id AND l.end_at<=a.assigned_at AND CAST(a.assigned_at AS DATE)=l.lesson_date)",
            "observations remain inside the term": f"SELECT (SELECT COUNT(*) FROM assignment_submissions WHERE CAST(submitted_at AS DATE)>'{END}' OR CAST(graded_at AS DATE)>'{END}')+(SELECT COUNT(*) FROM assignments WHERE assigned_at<'{START}' OR due_at>'{END}'::DATE+INTERVAL '1 day' OR due_at<assigned_at)+(SELECT COUNT(*) FROM academic_calendar WHERE calendar_date NOT BETWEEN '{START}' AND '{END}')",
        }
        for name, sql in rules.items():
            check(name, sql)

        examples = []
        for index, (query, sql) in enumerate(EXAMPLES, 1):
            result = records(sql)
            checks.append({"check": f"example query {index}: nonempty executable result", "passed": bool(result), "violations": int(not result)})
            examples.append({"case_id": f"SCHOOL-{index:03d}", "query": query, "gold_sql": sql.strip(), "expected_rows": result, "order_sensitive": True})
        summary = {
            "students": connection.execute("SELECT COUNT(*) FROM students").fetchone()[0],
            "classes": connection.execute("SELECT COUNT(*) FROM classes").fetchone()[0],
            "teachers": connection.execute("SELECT COUNT(*) FROM teachers").fetchone()[0],
            "class_sizes": records("SELECT c.class_name,COUNT(*) AS students FROM enrollments JOIN classes c USING(class_id) GROUP BY 1 ORDER BY 1"),
            "exam_score_distribution": records("SELECT x.grade,x.exam_type,s.subject_name,COUNT(*) AS expected_exam_persons,COUNT(r.score) AS attended_exam_persons,ROUND(AVG(100*r.score/x.max_score),2) AS average_pct,ROUND(STDDEV_POP(100*r.score/x.max_score),2) AS stddev_pct,ROUND(100.0*COUNT(*) FILTER (WHERE r.score/x.max_score>=s.pass_ratio)/COUNT(r.score),2) AS pass_rate_pct,ROUND(MIN(100*r.score/x.max_score),2) AS minimum_pct,ROUND(MAX(100*r.score/x.max_score),2) AS maximum_pct FROM exam_results r JOIN exams x USING(exam_id) JOIN subjects s USING(subject_id) GROUP BY 1,2,3 ORDER BY 1,2,3"),
            "attendance_states": records("SELECT attendance_status,COUNT(*) AS count,ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),3) AS percentage FROM attendance GROUP BY 1 ORDER BY 1"),
            "submission_states": records("SELECT submission_status,COUNT(*) AS count,ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),3) AS percentage FROM assignment_submissions GROUP BY 1 ORDER BY 1"),
            "exam_states": records("SELECT exam_status,COUNT(*) AS count FROM exam_results GROUP BY 1 ORDER BY 1"),
            "baseline_final_correlation": connection.execute("WITH paired AS (SELECT r.enrollment_id,x.subject_id,MAX(CASE WHEN x.exam_type='monthly' THEN 100*r.score/x.max_score END) a,MAX(CASE WHEN x.exam_type='final' THEN 100*r.score/x.max_score END) b FROM exam_results r JOIN exams x USING(exam_id) GROUP BY 1,2) SELECT ROUND(CORR(a,b),4) FROM paired").fetchone()[0],
            "homework_exam_correlation": connection.execute("WITH h AS (SELECT enrollment_id,AVG(score) s FROM assignment_submissions GROUP BY 1),x AS (SELECT enrollment_id,AVG(100*r.score/e.max_score) s FROM exam_results r JOIN exams e USING(exam_id) GROUP BY 1) SELECT ROUND(CORR(h.s,x.s),4) FROM h JOIN x USING(enrollment_id)").fetchone()[0],
        }
        totals_consistent = manifest["table_count"] == len(TABLES) == len(schema["tables"]) and manifest["total_rows"] == sum(t["row_count"] for t in manifest["tables"].values())
        checks.append({"check": "manifest totals and schema table counts", "passed": totals_consistent, "violations": int(not totals_consistent)})
        report = {"database": DATABASE, "synthetic": True, "tables": len(TABLES), "rows": manifest["total_rows"], "checks_passed": sum(check["passed"] for check in checks), "checks_total": len(checks), "errors": [check for check in checks if not check["passed"]], "summary": summary, "checks": checks}
        (folder / "_validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=normalize) + "\n", encoding="utf-8")
        (folder / "_example_queries.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2, default=normalize) + "\n", encoding="utf-8")
        return report
    finally:
        connection.close()


if __name__ == "__main__":
    result = validate()
    print(json.dumps({key: result[key] for key in ("database", "tables", "rows", "checks_passed", "checks_total", "errors", "summary")}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
