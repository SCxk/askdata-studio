from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

import duckdb

from school_teaching_definitions import (
    DATABASE, DATABASE_DIR, KNOWLEDGE, METRICS, NULLABLE_FIELDS, RELATIONS, SUBJECT_SPECS, TABLES,
    subjects_for_grade,
)


SEED = 20261019
START = date(2026, 2, 23)
END = date(2026, 7, 10)
TERM = "T2025_2026_2"
SCHOOL = "SCH001"
GRADE_NINE_END = date(2026, 6, 17)
EXAM_ROUNDS = [
    ("monthly", "三月阶段测评", date(2026, 3, 25)),
    ("midterm", "期中考试", date(2026, 4, 28)),
    ("final", "期末考试", date(2026, 7, 6)),
]
HOLIDAYS = {date(2026, 4, 6): "清明假期", date(2026, 5, 1): "劳动节假期", date(2026, 5, 4): "劳动节假期", date(2026, 5, 5): "劳动节假期", date(2026, 6, 19): "端午假期"}
PERIOD_STARTS = [time(8), time(8, 55), time(10), time(10, 55), time(14), time(14, 55), time(15, 50)]
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦许何吕张孔曹严华金魏陶姜谢邹苏潘范彭鲁韦马方" )
GIVEN_NAMES = ["子涵", "雨桐", "浩然", "思远", "欣怡", "宇航", "梓萱", "明轩", "诗涵", "俊杰", "语彤", "嘉宁", "一诺", "景行", "沐阳", "书瑶", "泽宇", "若溪", "亦辰", "可欣", "奕帆", "晨曦", "知夏", "博文", "安琪", "瑞霖", "以宁", "清越", "云舒", "承泽", "星辰", "嘉树", "思齐", "乐言", "怀瑾", "予安", "舒然", "文博", "锦程", "芷晴", "昕悦", "柏舟", "奕宁", "言蹊", "青禾", "星野", "雨晨", "思源", "若宁", "沛然"]


def clamp(value: float, low: float = 0.02, high: float = 0.98) -> float:
    return max(low, min(high, value))


def open_school_database(folder: Path) -> duckdb.DuckDBPyConnection:
    """Load typed tables without depending on the application's active scenario."""
    connection = duckdb.connect(":memory:")
    try:
        for name, spec in TABLES.items():
            types = {field: source_type for field, _, source_type, _ in spec["fields"]}
            file_name = (folder / f"{name}.csv").resolve().as_posix().replace("'", "''")
            type_sql = "{" + ", ".join(f"'{key}': '{value}'" for key, value in types.items()) + "}"
            connection.execute(
                f'CREATE TABLE "{name}" AS SELECT * FROM read_csv(\'{file_name}\', '
                f"header=true, auto_detect=false, columns={type_sql}, nullstr='')"
            )
        return connection
    except Exception:
        connection.close()
        raise


class SchoolTeachingGenerator:
    def __init__(self, output_dir: Path = DATABASE_DIR, seed: int = SEED) -> None:
        self.output_dir = output_dir
        self.seed = seed
        self.rng = random.Random(seed)
        self.tables: dict[str, list[dict]] = {}
        self.counts: dict[str, int] = {}
        self.latent: dict[str, dict] = {}
        self.class_students: dict[str, list[dict]] = defaultdict(list)
        self.day_states: dict[tuple[str, date], tuple[str, str]] = {}
        self.schedule: dict[tuple[str, int, int], dict] = {}

    def write(self, name: str, rows: Iterable[dict], *, remember: bool = True) -> None:
        if remember:
            rows = list(rows)
            self.tables[name] = rows
        columns = [field[0] for field in TABLES[name]["fields"]]
        count = 0
        with (self.output_dir / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
                count += 1
        self.counts[name] = count

    def foundations(self) -> None:
        names = [surname + given for surname in SURNAMES for given in GIVEN_NAMES]
        self.rng.shuffle(names)
        self.write("schools", [{"school_id": SCHOOL, "school_name": "明川实验中学（模拟）", "city": "杭州", "school_type": "初中"}])
        self.write("terms", [{"term_id": TERM, "school_id": SCHOOL, "academic_year": "2025-2026", "term_name": "2025-2026学年第二学期", "start_date": START, "end_date": END}])
        self.write("subjects", [{"subject_id": code, "subject_name": label, "pass_ratio": 0.6, "excellent_ratio": 0.85} for code, label, _, _ in SUBJECT_SPECS])
        teachers, classes, students, enrollments, teaching = [], [], [], [], []
        for grade in (7, 8, 9):
            subject_specs = subjects_for_grade(grade)
            teacher_map = {}
            for subject, _, _, _ in subject_specs:
                for pair in range(3):
                    teacher_id = f"T{grade}{subject}{pair + 1}"
                    years = self.rng.randint(2, 27)
                    teachers.append({"teacher_id": teacher_id, "school_id": SCHOOL, "teacher_name": names.pop(), "teaching_years": years, "title": "高级教师" if years >= 18 else "一级教师" if years >= 7 else "二级教师"})
                    teacher_map[subject, pair] = teacher_id
            for class_no in range(1, 7):
                class_id = f"C{grade}{class_no:02d}"
                homeroom_subject = subject_specs[(class_no - 1) % 3][0]
                classes.append({"class_id": class_id, "school_id": SCHOOL, "term_id": TERM, "grade": grade, "class_name": f"{ {7: '七', 8: '八', 9: '九'}[grade]}年级{class_no}班", "homeroom_teacher_id": teacher_map[homeroom_subject, (class_no - 1) // 2]})
                class_effect = self.rng.gauss(0, 0.018)
                for subject, _, periods, _ in subject_specs:
                    teaching.append({"teaching_id": f"TA_{class_id}_{subject}", "term_id": TERM, "class_id": class_id, "subject_id": subject, "teacher_id": teacher_map[subject, (class_no - 1) // 2], "weekly_periods": periods})
                for _ in range(self.rng.randint(40, 46)):
                    student_id = f"S{len(students) + 1:05d}"
                    enrollment_id = f"EN{len(students) + 1:05d}"
                    admission_year = 2025 - (grade - 7)
                    birth_start = date(admission_year - 13, 9, 1)
                    student = {"student_id": student_id, "school_id": SCHOOL, "student_name": names.pop(), "gender": self.rng.choice(["男", "女"]), "birth_date": birth_start + timedelta(days=self.rng.randrange(365)), "enrollment_year": admission_year}
                    enrollment = {"enrollment_id": enrollment_id, "student_id": student_id, "class_id": class_id, "term_id": TERM, "valid_from": START, "valid_to": GRADE_NINE_END if grade == 9 else END}
                    students.append(student)
                    enrollments.append(enrollment)
                    self.class_students[class_id].append(enrollment)
                    ability = clamp(self.rng.gauss(0.70, 0.12), 0.30, 0.94)
                    habit = clamp(0.55 * self.rng.betavariate(6, 2) + 0.45 * ability)
                    trajectory = self.rng.gauss(0.018, 0.045)
                    if self.rng.random() < 0.07:
                        trajectory += self.rng.choice([-0.10, 0.10])
                    self.latent[enrollment_id] = {"ability": ability, "habit": habit, "trend": trajectory, "class_effect": class_effect, "homework_offset": self.rng.gauss(0.04, 0.085), "exam_offset": self.rng.gauss(0, 0.035), "absence_propensity": self.rng.uniform(0.5, 1.8), "subject": {spec[0]: self.rng.gauss(0, 0.09) for spec in subject_specs}, "knowledge": {f"K{grade}_{spec[0]}_{i}": self.rng.gauss(0, 0.065) for spec in subject_specs for i in range(1, 6)}}
        for name, rows in [("teachers", teachers), ("classes", classes), ("students", students), ("enrollments", enrollments), ("teaching_assignments", teaching)]:
            self.write(name, rows)
        self.write("knowledge_points", [{"knowledge_id": f"K{grade}_{subject}_{i}", "subject_id": subject, "grade": grade, "knowledge_name": label} for subject, grades in KNOWLEDGE.items() for grade, labels in grades.items() for i, label in enumerate(labels, 1)])

    def calendar_and_lessons(self) -> None:
        grade_exam_days = {grade: {self.exam_start(grade, exam_type, start) + timedelta(days=i) for exam_type, _, start in EXAM_ROUNDS for i in range(3)} for grade in (7, 8, 9)}
        exam_days = set.union(*grade_exam_days.values())
        days = []
        for offset in range((END - START).days + 1):
            current = START + timedelta(days=offset)
            kind, note = "teaching", "文化课教学"
            if current.weekday() >= 5:
                kind, note = "weekend", "周末"
            elif current in HOLIDAYS:
                kind, note = "holiday", HOLIDAYS[current]
            elif current in exam_days:
                kind, note = "exam", "分年级考试；非参考年级照常上课"
            days.append({"calendar_date": current, "term_id": TERM, "week_no": offset // 7 + 1, "day_type": kind, "note": note})
        self.write("academic_calendar", days)
        teacher_slots = set()
        for cls in self.tables["classes"]:
            class_id = cls["class_id"]
            assignments = [item for item in self.tables["teaching_assignments"] if item["class_id"] == class_id]
            daily_load = defaultdict(int)
            for teaching in sorted(assignments, key=lambda item: -item["weekly_periods"]):
                subject_days = defaultdict(int)
                for _ in range(teaching["weekly_periods"]):
                    candidates = [(day, period) for day in range(5) for period in range(1, 8) if (class_id, day, period) not in self.schedule and (teaching["teacher_id"], day, period) not in teacher_slots]
                    if not candidates:
                        raise ValueError(f"Cannot schedule {teaching['teaching_id']}")
                    jitter = {slot: self.rng.random() for slot in candidates}
                    day, period = min(candidates, key=lambda slot: (subject_days[slot[0]], daily_load[slot[0]], jitter[slot]))
                    self.schedule[class_id, day, period] = teaching
                    teacher_slots.add((teaching["teacher_id"], day, period))
                    daily_load[day] += 1
                    subject_days[day] += 1
        lessons = []
        for day in days:
            if day["day_type"] not in {"teaching", "exam"}:
                continue
            current = day["calendar_date"]
            for cls in self.tables["classes"]:
                if current in grade_exam_days[cls["grade"]] or (cls["grade"] == 9 and current > GRADE_NINE_END):
                    continue
                for period in range(1, 8):
                    teaching = self.schedule.get((cls["class_id"], current.weekday(), period))
                    if not teaching:
                        continue
                    starts = datetime.combine(current, PERIOD_STARTS[period - 1])
                    lessons.append({"lesson_id": f"L{len(lessons) + 1:06d}", "teaching_id": teaching["teaching_id"], "lesson_date": current, "period_no": period, "start_at": starts, "end_at": starts + timedelta(minutes=45)})
        self.write("lessons", lessons)
        # Day-level illness persists across classes and may span multiple school days.
        for enrollment in self.tables["enrollments"]:
            eid = enrollment["enrollment_id"]
            latent = self.latent[eid]
            ill_until = START - timedelta(days=1)
            for day in days:
                current = day["calendar_date"]
                if day["day_type"] not in {"teaching", "exam"}:
                    continue
                seasonal = 1.5 if current.month in {3, 4} else 0.8
                if current > ill_until and self.rng.random() < 0.006 * seasonal * latent["absence_propensity"]:
                    ill_until = current + timedelta(days=self.rng.randint(0, 3))
                if current <= ill_until:
                    state, reason = "excused", "病假"
                elif self.rng.random() < 0.002:
                    state, reason = "excused", "事假"
                elif self.rng.random() < 0.003 + (1 - latent["habit"]) * 0.008:
                    state, reason = "absent", "未履行请假手续"
                else:
                    state, reason = "present", ""
                self.day_states[eid, current] = state, reason

    def attendance_rows(self) -> Iterable[dict]:
        teaching_map = {row["teaching_id"]: row for row in self.tables["teaching_assignments"]}
        sequence = 0
        for lesson in self.tables["lessons"]:
            teaching = teaching_map[lesson["teaching_id"]]
            for enrollment in self.class_students[teaching["class_id"]]:
                sequence += 1
                eid = enrollment["enrollment_id"]
                state, reason = self.day_states[eid, lesson["lesson_date"]]
                minutes = 0
                if state == "present":
                    late_probability = 0.006 + (1 - self.latent[eid]["habit"]) * (0.07 if lesson["period_no"] == 1 else 0.02)
                    if self.rng.random() < late_probability:
                        state, reason, minutes = "late", "到校或课间返回延误", self.rng.randint(1, 18)
                yield {"attendance_id": f"AT{sequence:07d}", "lesson_id": lesson["lesson_id"], "enrollment_id": eid, "attendance_status": state, "late_minutes": minutes, "reason": reason}

    def mastery(self, eid: str, subject: str, current: date) -> float:
        latent = self.latent[eid]
        progress = (current - START).days / (END - START).days
        return clamp(latent["ability"] + latent["subject"][subject] + latent["class_effect"] + latent["trend"] * progress)

    def homework(self) -> None:
        labels = {code: label for code, label, _, _ in SUBJECT_SPECS}
        teaching_map = {row["teaching_id"]: row for row in self.tables["teaching_assignments"]}
        first_lesson = {}
        for lesson in self.tables["lessons"]:
            week = (lesson["lesson_date"] - START).days // 7 + 1
            # Export one sampled homework per subject every other week.
            if week % 2 == 1 and week < 19:
                first_lesson.setdefault((lesson["teaching_id"], week), lesson)
        class_days = defaultdict(set)
        for lesson in self.tables["lessons"]:
            class_days[teaching_map[lesson["teaching_id"]]["class_id"]].add(lesson["lesson_date"])
        assignments, submissions = [], []
        for (tid, week), lesson in first_lesson.items():
            teaching = teaching_map[tid]
            due_day = min(day for day in class_days[teaching["class_id"]] if day > lesson["lesson_date"])
            assigned_at = lesson["end_at"] + timedelta(minutes=10)
            due_at = datetime.combine(due_day, time(20))
            aid = f"HW{len(assignments) + 1:05d}"
            assignments.append({"assignment_id": aid, "teaching_id": tid, "assignment_title": f"{labels[teaching['subject_id']]}第{week}周巩固作业", "assigned_at": assigned_at, "due_at": due_at, "max_score": 100, "estimated_minutes": self.rng.randint(15, 30)})
            for enrollment in self.class_students[teaching["class_id"]]:
                eid = enrollment["enrollment_id"]
                habit = self.latent[eid]["habit"]
                day_status = self.day_states[eid, lesson["lesson_date"]][0]
                disrupted = 0.10 if day_status in {"excused", "absent"} else 0
                draw = self.rng.random()
                missing_probability = 0.008 + (1 - habit) ** 2 * 0.24 + disrupted
                late_probability = 0.02 + (1 - habit) * 0.16
                submitted_at = graded_at = score = None
                if draw < missing_probability:
                    status = "missing"
                else:
                    status = "late" if draw < missing_probability + late_probability else "on_time"
                    if status == "late":
                        submitted_at = due_at + timedelta(hours=self.rng.randint(1, 44), minutes=self.rng.randint(0, 59))
                    else:
                        # Submitted in the evening, after class and before the deadline.
                        submitted_at = datetime.combine(lesson["lesson_date"], time(18)) + timedelta(minutes=self.rng.randint(0, 210))
                    graded_at = submitted_at + timedelta(hours=self.rng.randint(4, 30))
                    score = round(clamp(self.mastery(eid, teaching["subject_id"], due_day) + self.latent[eid]["homework_offset"] + self.rng.gauss(0, 0.09), 0.05, 1) * 100, 1)
                submissions.append({"submission_id": f"HS{len(submissions) + 1:07d}", "assignment_id": aid, "enrollment_id": eid, "submission_status": status, "submitted_at": submitted_at, "graded_at": graded_at, "score": score})
        self.write("assignments", assignments)
        self.write("assignment_submissions", submissions, remember=False)

    def examinations(self) -> None:
        exams, questions, results = [], [], []
        responses_path = self.output_dir / "question_responses.csv"
        response_columns = [field[0] for field in TABLES["question_responses"]["fields"]]
        response_count = 0
        with responses_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=response_columns, lineterminator="\n")
            writer.writeheader()
            for round_index, (exam_type, exam_name, start_day) in enumerate(EXAM_ROUNDS):
                for grade in (7, 8, 9):
                    for subject_index, (subject, label, _, maximum) in enumerate(subjects_for_grade(grade)):
                        exam_id = f"EX{grade}_{subject}_{round_index + 1}"
                        exam_day = self.exam_start(grade, exam_type, start_day) + timedelta(days=subject_index // 3)
                        start_at = datetime.combine(exam_day, [time(8), time(10, 30), time(14)][subject_index % 3])
                        exams.append({"exam_id": exam_id, "term_id": TERM, "grade": grade, "subject_id": subject, "exam_name": f"{exam_name}·{label}", "exam_type": exam_type, "exam_date": exam_day, "start_at": start_at, "duration_minutes": 120 if maximum == 120 else 60, "max_score": maximum})
                        difficulty = self.rng.gauss(0.01, 0.035)
                        paper = []
                        for number in range(1, 21):
                            kind = "choice" if number <= 10 else "constructed"
                            max_score = (4 if maximum == 120 else 3) if kind == "choice" else (8 if maximum == 120 else 7)
                            topic_count = [2, 4, 5][round_index]
                            question = {"question_id": f"{exam_id}_Q{number:02d}", "exam_id": exam_id, "knowledge_id": f"K{grade}_{subject}_{(number - 1) % topic_count + 1}", "question_no": number, "question_type": kind, "max_score": max_score}
                            paper.append((question, self.rng.gauss(0, 0.095)))
                            questions.append(question)
                        grade_classes = [cls for cls in self.tables["classes"] if cls["grade"] == grade]
                        for cls in grade_classes:
                            for enrollment in self.class_students[cls["class_id"]]:
                                eid = enrollment["enrollment_id"]
                                result_id = f"ER{len(results) + 1:06d}"
                                day_status, day_reason = self.day_states[eid, exam_day]
                                absent = day_status in {"excused", "absent"}
                                score = None
                                if not absent:
                                    score = 0.0
                                    performance = self.mastery(eid, subject, exam_day) + self.latent[eid]["exam_offset"] - difficulty + self.rng.gauss(0, 0.055)
                                    for question, item_difficulty in paper:
                                        knowledge = self.latent[eid]["knowledge"][question["knowledge_id"]]
                                        probability = clamp(performance + knowledge - item_difficulty)
                                        blank = self.rng.random() < 0.004 + max(0, 0.55 - probability) * 0.04
                                        if blank:
                                            points = 0.0
                                        elif question["question_type"] == "choice":
                                            points = question["max_score"] if self.rng.random() < probability else 0.0
                                        else:
                                            fraction = clamp(self.rng.gauss(probability, 0.16), 0, 1)
                                            points = round(fraction * question["max_score"] * 2) / 2
                                        score += points
                                        response_count += 1
                                        writer.writerow({"response_id": f"QR{response_count:08d}", "result_id": result_id, "question_id": question["question_id"], "response_status": "blank" if blank else "answered", "score": points})
                                results.append({"result_id": result_id, "exam_id": exam_id, "enrollment_id": eid, "exam_status": "absent" if absent else "attended", "score": score, "absence_reason": day_reason if absent else ""})
        self.counts["question_responses"] = response_count
        self.write("exams", exams)
        self.write("exam_questions", questions)
        self.write("exam_results", results, remember=False)

    @staticmethod
    def exam_start(grade: int, exam_type: str, default: date) -> date:
        return date(2026, 6, 15) if grade == 9 and exam_type == "final" else default

    def metadata(self) -> dict:
        schema_tables = []
        connection = open_school_database(self.output_dir)
        try:
            for name, spec in TABLES.items():
                fields = []
                foreign = {child_key for _, _, child, child_key in RELATIONS if child == name}
                for field, label, source_type, description in spec["fields"]:
                    count, non_null, distinct = connection.execute(f'SELECT COUNT(*), COUNT("{field}"), COUNT(DISTINCT "{field}") FROM "{name}"').fetchone()
                    samples = [str(row[0]) if isinstance(row[0], (date, datetime)) else row[0] for row in connection.execute(f'SELECT DISTINCT "{field}" FROM "{name}" WHERE "{field}" IS NOT NULL ORDER BY "{field}" LIMIT 5').fetchall()]
                    profile = {"row_count": count, "null_ratio": round((count - non_null) / count, 6), "distinct_count": distinct, "sample_values": samples}
                    if source_type in {"INTEGER", "DOUBLE", "DATE", "TIMESTAMP"}:
                        minimum, maximum = connection.execute(f'SELECT MIN("{field}"), MAX("{field}") FROM "{name}"').fetchone()
                        profile.update({"min": str(minimum) if isinstance(minimum, (date, datetime)) else minimum, "max": str(maximum) if isinstance(maximum, (date, datetime)) else maximum})
                    if source_type in {"INTEGER", "DOUBLE"}:
                        profile["avg"] = round(connection.execute(f'SELECT AVG("{field}") FROM "{name}"').fetchone()[0], 4)
                    role = "identifier" if field in spec["pk"] else "foreign_key" if field in foreign else "time" if source_type in {"DATE", "TIMESTAMP"} else "metric" if field == "score" else "dimension"
                    field_type = {"INTEGER": "整数", "DOUBLE": "数值", "DATE": "日期", "TIMESTAMP": "日期", "VARCHAR": "文本"}[source_type]
                    fields.append({"name": field, "label": label, "source_type": source_type, "type": field_type, "description": description, "aliases": [label], "role": role, "aggregation": "avg" if field == "score" else "none" if role in {"identifier", "foreign_key"} or source_type in {"INTEGER", "DOUBLE"} else "group", "data_profile": profile})
                schema_tables.append({"id": f"{DATABASE}.{name}", "name": name, "database": DATABASE, "label": spec["label"], "domain": spec["domain"], "description": f"{spec['label']}；粒度：{spec['grain']}。", "business_terms": [spec["label"], spec["domain"]], "primary_key": spec["pk"], "row_count": self.counts[name], "fields": fields})
        finally:
            connection.close()
        schema = {"schema_version": "1.0.0", "database": DATABASE, "scenario": "学校教学与学情分析（完全合成数据）", "synthetic": True, "metric_definitions": METRICS, "role_tables": {"academic_admin": list(TABLES)}, "tables": schema_tables, "relations": [{"left_table": f"{DATABASE}.{parent}", "left_table_name": parent, "left_field": pk, "right_table": f"{DATABASE}.{child}", "right_table_name": child, "right_field": fk, "relation_type": "foreign_key", "description": f"{TABLES[parent]['label']}关联{TABLES[child]['label']}"} for parent, pk, child, fk in RELATIONS]}
        self.write_json("_schema.json", schema)
        manifest = {"database": DATABASE, "scenario": schema["scenario"], "synthetic": True, "seed": self.seed, "data_start": str(START), "data_end": str(END), "table_count": len(TABLES), "total_rows": sum(self.counts.values()), "tables": {name: {"row_count": self.counts[name], "columns": [field[0] for field in spec["fields"]], "sha256": hashlib.sha256((self.output_dir / f"{name}.csv").read_bytes()).hexdigest()} for name, spec in TABLES.items()}}
        self.write_json("_database_manifest.json", manifest)
        self.documentation(manifest)
        return manifest

    def documentation(self, manifest: dict) -> None:
        ddl = ["-- Fully synthetic school teaching dataset. DuckDB SQL.\n"]
        loads = ["-- Run after _create_tables.sql, with this data folder as working directory.\n"]
        dictionary = ["# 学校教学数据字典\n", "全部记录均为合成数据。编号保持文本类型；CSV 空白单元格读作 NULL。\n"]
        for name, spec in TABLES.items():
            definitions = [f'  "{field}" {source_type}' + ("" if (name, field) in NULLABLE_FIELDS else " NOT NULL") for field, _, source_type, _ in spec["fields"]]
            keys = ", ".join(f'"{key}"' for key in spec["pk"])
            definitions.append(f"  PRIMARY KEY ({keys})")
            for parent, pk, child, fk in RELATIONS:
                if child == name:
                    definitions.append(f'  FOREIGN KEY ("{fk}") REFERENCES "{parent}" ("{pk}")')
            ddl.append(f'CREATE TABLE "{name}" (\n' + ",\n".join(definitions) + "\n);\n")
            loads.append(f'COPY "{name}" FROM \'{name}.csv\' (HEADER TRUE, NULL \'\');')
            dictionary.extend([f"## {spec['label']} / {name}\n", f"粒度：{spec['grain']}。记录数：{self.counts[name]:,}。\n", "| 字段 | 中文名 | 类型 | 可空 | 说明 |", "| --- | --- | --- | --- | --- |"])
            dictionary.extend(f"| {field} | {label} | {source_type} | {'是' if (name, field) in NULLABLE_FIELDS else '否'} | {description} |" for field, label, source_type, description in spec["fields"])
            dictionary.append("")
        (self.output_dir / "_create_tables.sql").write_text("\n".join(ddl), encoding="utf-8")
        (self.output_dir / "_load_data.sql").write_text("\n".join(loads) + "\n", encoding="utf-8")
        (self.output_dir / "_data_dictionary.md").write_text("\n".join(dictionary) + "\n", encoding="utf-8")
        overview = [
            "# 学校教学分析模拟数据\n",
            "**本目录所有学校、人员、教学记录和成绩均为完全合成数据，不来自真实学校。**\n",
            "## 范围\n",
            f"- 虚构学校：明川实验中学（模拟），杭州，普通初中。",
            f"- 学期：{START} 至 {END}，2025-2026 学年第二学期。",
            f"- 七至九年级共 {self.counts['classes']} 个平行班，{self.counts['students']} 名学生，{self.counts['teachers']} 名文化课教师。",
            f"- {len(TABLES)} 张 CSV 表，共 {manifest['total_rows']:,} 条记录。CSV 为 UTF-8 BOM，可在 Excel 中直接查看。",
            "- 九年级在 6 月 15-17 日进行校内毕业测评并结课；七八年级在 7 月 6-8 日期末考试。没有模拟中考成绩。",
            "- 七年级不含物理、化学，八年级新增物理，九年级增加化学并不再排地理和生物。",
            "- 仅覆盖文化课；课表缺口是未纳入本数据的体育、艺术、班会等课程。",
            "- 作业为隔周抽样的一次巩固作业，不代表全量布置，也不能用来估计学生全部作业负担。\n",
            "## 数据真实性设计\n",
            "- 学生存在稳定能力差异、偏科、知识点差异和不同进步轨迹；同一学生多次测评相关，但有临场波动。",
            "- 作业受到查阅资料、个体完成方式等独立偏差影响，作业高分不会机械对应考试高分。",
            "- 存在随机班级差异；性别和姓名不参与能力、习惯或成绩生成。内部生成参数不作为真实学生标签导出。",
            "- 请假可能连续多天，同一天病假影响各节课；迟到更多发生在第一节，且有少量无故缺勤。",
            "- 课表避免教师和班级冲突；考试按年级错开学科时间，考试当天参考年级暂停常规课。",
            "- 三月测评覆盖每科前两个知识点，期中覆盖前四个，期末覆盖五个；知识点取常见课程内容，不对应特定教材教学进度。",
            "- 每份试卷含 20 道评分题，客观题按对错给分，分步题有部分得分，总分严格等于逐题得分之和。",
            "- 缺考成绩为空、没有逐题记录；未交作业也保留应交记录，提交和批改时间符合先后顺序。",
            "- 所有趋势和相关关系均由生成规则构造，适合功能演示与查询验证，不能作为教育研究的实证证据。\n",
            "## 文件\n",
            "- `_schema.json`：与项目现有结构一致的表、字段、关系和字段分布；包含指标口径。",
            "- `_data_dictionary.md`：逐字段中文说明、类型、空值含义和记录粒度。",
            "- `_database_manifest.json`：随机种子、各表行数和文件 SHA-256 校验值。",
            "- `_create_tables.sql`、`_load_data.sql`：DuckDB 建表与导入脚本，含主键、外键和非空约束。",
            "- `_validation_report.json`：运行校验后产生的完整性检查、成绩分布和相关性统计。",
            "- `_example_queries.json`：运行校验后产生的 10 个典型问题、标准 SQL 和实际结果。\n",
            "## 指标口径\n",
        ]
        overview.extend(f"- **{label}**：{definition}" for label, definition in METRICS.items())
        overview.extend([
            "\n## 重新生成与校验\n",
            "在项目的 backend 目录运行：\n",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\generate_school_teaching_data.py --overwrite",
            ".\\.venv\\Scripts\\python.exe scripts\\validate_school_teaching.py",
            "```\n",
            f"默认随机种子为 {self.seed}，同一 Python 版本和相同种子会生成相同 CSV。可通过 `--seed` 改变样本。重新生成后须重新运行校验以刷新报告和示例结果。\n",
            "如果使用 DuckDB Python 库，在本目录执行以下代码即可创建真实数据表：\n",
            "```python",
            "from pathlib import Path",
            "import duckdb",
            "con = duckdb.connect(':memory:')",
            "con.execute(Path('_create_tables.sql').read_text(encoding='utf-8'))",
            "con.execute(Path('_load_data.sql').read_text(encoding='utf-8'))",
            "print(con.execute('SELECT COUNT(*) FROM students').fetchone())",
            "```\n",
            "## 与当前应用的关系\n",
            "项目仅加载 `school_teaching` 目录中的 18 张学校模拟数据表。",
            "使用 `school` / `school123` 登录页面即可查询学校数据；管理员也仅访问学校数据库。",
            "`academic_admin` 是全校教务角色，尚未实现教师按班级、学生按本人的行级权限。\n",
        ])
        (self.output_dir / "README.md").write_text("\n".join(overview), encoding="utf-8")

    def write_json(self, name: str, value: object) -> None:
        (self.output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def generate(self, overwrite: bool = False) -> dict:
        expected_files = [f"{name}.csv" for name in TABLES] + ["_schema.json", "_database_manifest.json", "_validation_report.json", "_example_queries.json"]
        if not overwrite and any((self.output_dir / name).exists() for name in expected_files):
            raise FileExistsError("School data already exists; use --overwrite to regenerate it")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.foundations()
        self.calendar_and_lessons()
        self.write("attendance", self.attendance_rows(), remember=False)
        self.homework()
        self.examinations()
        return self.metadata()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a separate, fully synthetic school dataset")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--overwrite", action="store_true", help="Replace this school dataset only")
    args = parser.parse_args()
    result = SchoolTeachingGenerator(seed=args.seed).generate(overwrite=args.overwrite)
    print(json.dumps({"database": result["database"], "tables": result["table_count"], "rows": result["total_rows"], "path": str(DATABASE_DIR)}, ensure_ascii=False, indent=2))
