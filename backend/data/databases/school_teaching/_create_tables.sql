-- Fully synthetic school teaching dataset. DuckDB SQL.

CREATE TABLE "schools" (
  "school_id" VARCHAR NOT NULL,
  "school_name" VARCHAR NOT NULL,
  "city" VARCHAR NOT NULL,
  "school_type" VARCHAR NOT NULL,
  PRIMARY KEY ("school_id")
);

CREATE TABLE "terms" (
  "term_id" VARCHAR NOT NULL,
  "school_id" VARCHAR NOT NULL,
  "academic_year" VARCHAR NOT NULL,
  "term_name" VARCHAR NOT NULL,
  "start_date" DATE NOT NULL,
  "end_date" DATE NOT NULL,
  PRIMARY KEY ("term_id"),
  FOREIGN KEY ("school_id") REFERENCES "schools" ("school_id")
);

CREATE TABLE "teachers" (
  "teacher_id" VARCHAR NOT NULL,
  "school_id" VARCHAR NOT NULL,
  "teacher_name" VARCHAR NOT NULL,
  "teaching_years" INTEGER NOT NULL,
  "title" VARCHAR NOT NULL,
  PRIMARY KEY ("teacher_id"),
  FOREIGN KEY ("school_id") REFERENCES "schools" ("school_id")
);

CREATE TABLE "classes" (
  "class_id" VARCHAR NOT NULL,
  "school_id" VARCHAR NOT NULL,
  "term_id" VARCHAR NOT NULL,
  "grade" INTEGER NOT NULL,
  "class_name" VARCHAR NOT NULL,
  "homeroom_teacher_id" VARCHAR NOT NULL,
  PRIMARY KEY ("class_id"),
  FOREIGN KEY ("school_id") REFERENCES "schools" ("school_id"),
  FOREIGN KEY ("term_id") REFERENCES "terms" ("term_id"),
  FOREIGN KEY ("homeroom_teacher_id") REFERENCES "teachers" ("teacher_id")
);

CREATE TABLE "students" (
  "student_id" VARCHAR NOT NULL,
  "school_id" VARCHAR NOT NULL,
  "student_name" VARCHAR NOT NULL,
  "gender" VARCHAR NOT NULL,
  "birth_date" DATE NOT NULL,
  "enrollment_year" INTEGER NOT NULL,
  PRIMARY KEY ("student_id"),
  FOREIGN KEY ("school_id") REFERENCES "schools" ("school_id")
);

CREATE TABLE "enrollments" (
  "enrollment_id" VARCHAR NOT NULL,
  "student_id" VARCHAR NOT NULL,
  "class_id" VARCHAR NOT NULL,
  "term_id" VARCHAR NOT NULL,
  "valid_from" DATE NOT NULL,
  "valid_to" DATE NOT NULL,
  PRIMARY KEY ("enrollment_id"),
  FOREIGN KEY ("term_id") REFERENCES "terms" ("term_id"),
  FOREIGN KEY ("student_id") REFERENCES "students" ("student_id"),
  FOREIGN KEY ("class_id") REFERENCES "classes" ("class_id")
);

CREATE TABLE "subjects" (
  "subject_id" VARCHAR NOT NULL,
  "subject_name" VARCHAR NOT NULL,
  "pass_ratio" DOUBLE NOT NULL,
  "excellent_ratio" DOUBLE NOT NULL,
  PRIMARY KEY ("subject_id")
);

CREATE TABLE "teaching_assignments" (
  "teaching_id" VARCHAR NOT NULL,
  "term_id" VARCHAR NOT NULL,
  "class_id" VARCHAR NOT NULL,
  "subject_id" VARCHAR NOT NULL,
  "teacher_id" VARCHAR NOT NULL,
  "weekly_periods" INTEGER NOT NULL,
  PRIMARY KEY ("teaching_id"),
  FOREIGN KEY ("term_id") REFERENCES "terms" ("term_id"),
  FOREIGN KEY ("class_id") REFERENCES "classes" ("class_id"),
  FOREIGN KEY ("subject_id") REFERENCES "subjects" ("subject_id"),
  FOREIGN KEY ("teacher_id") REFERENCES "teachers" ("teacher_id")
);

CREATE TABLE "academic_calendar" (
  "calendar_date" DATE NOT NULL,
  "term_id" VARCHAR NOT NULL,
  "week_no" INTEGER NOT NULL,
  "day_type" VARCHAR NOT NULL,
  "note" VARCHAR NOT NULL,
  PRIMARY KEY ("calendar_date"),
  FOREIGN KEY ("term_id") REFERENCES "terms" ("term_id")
);

CREATE TABLE "lessons" (
  "lesson_id" VARCHAR NOT NULL,
  "teaching_id" VARCHAR NOT NULL,
  "lesson_date" DATE NOT NULL,
  "period_no" INTEGER NOT NULL,
  "start_at" TIMESTAMP NOT NULL,
  "end_at" TIMESTAMP NOT NULL,
  PRIMARY KEY ("lesson_id"),
  FOREIGN KEY ("teaching_id") REFERENCES "teaching_assignments" ("teaching_id"),
  FOREIGN KEY ("lesson_date") REFERENCES "academic_calendar" ("calendar_date")
);

CREATE TABLE "attendance" (
  "attendance_id" VARCHAR NOT NULL,
  "lesson_id" VARCHAR NOT NULL,
  "enrollment_id" VARCHAR NOT NULL,
  "attendance_status" VARCHAR NOT NULL,
  "late_minutes" INTEGER NOT NULL,
  "reason" VARCHAR,
  PRIMARY KEY ("attendance_id"),
  FOREIGN KEY ("lesson_id") REFERENCES "lessons" ("lesson_id"),
  FOREIGN KEY ("enrollment_id") REFERENCES "enrollments" ("enrollment_id")
);

CREATE TABLE "exams" (
  "exam_id" VARCHAR NOT NULL,
  "term_id" VARCHAR NOT NULL,
  "grade" INTEGER NOT NULL,
  "subject_id" VARCHAR NOT NULL,
  "exam_name" VARCHAR NOT NULL,
  "exam_type" VARCHAR NOT NULL,
  "exam_date" DATE NOT NULL,
  "start_at" TIMESTAMP NOT NULL,
  "duration_minutes" INTEGER NOT NULL,
  "max_score" DOUBLE NOT NULL,
  PRIMARY KEY ("exam_id"),
  FOREIGN KEY ("term_id") REFERENCES "terms" ("term_id"),
  FOREIGN KEY ("subject_id") REFERENCES "subjects" ("subject_id"),
  FOREIGN KEY ("exam_date") REFERENCES "academic_calendar" ("calendar_date")
);

CREATE TABLE "exam_results" (
  "result_id" VARCHAR NOT NULL,
  "exam_id" VARCHAR NOT NULL,
  "enrollment_id" VARCHAR NOT NULL,
  "exam_status" VARCHAR NOT NULL,
  "score" DOUBLE,
  "absence_reason" VARCHAR,
  PRIMARY KEY ("result_id"),
  FOREIGN KEY ("exam_id") REFERENCES "exams" ("exam_id"),
  FOREIGN KEY ("enrollment_id") REFERENCES "enrollments" ("enrollment_id")
);

CREATE TABLE "assignments" (
  "assignment_id" VARCHAR NOT NULL,
  "teaching_id" VARCHAR NOT NULL,
  "assignment_title" VARCHAR NOT NULL,
  "assigned_at" TIMESTAMP NOT NULL,
  "due_at" TIMESTAMP NOT NULL,
  "max_score" DOUBLE NOT NULL,
  "estimated_minutes" INTEGER NOT NULL,
  PRIMARY KEY ("assignment_id"),
  FOREIGN KEY ("teaching_id") REFERENCES "teaching_assignments" ("teaching_id")
);

CREATE TABLE "assignment_submissions" (
  "submission_id" VARCHAR NOT NULL,
  "assignment_id" VARCHAR NOT NULL,
  "enrollment_id" VARCHAR NOT NULL,
  "submission_status" VARCHAR NOT NULL,
  "submitted_at" TIMESTAMP,
  "graded_at" TIMESTAMP,
  "score" DOUBLE,
  PRIMARY KEY ("submission_id"),
  FOREIGN KEY ("assignment_id") REFERENCES "assignments" ("assignment_id"),
  FOREIGN KEY ("enrollment_id") REFERENCES "enrollments" ("enrollment_id")
);

CREATE TABLE "knowledge_points" (
  "knowledge_id" VARCHAR NOT NULL,
  "subject_id" VARCHAR NOT NULL,
  "grade" INTEGER NOT NULL,
  "knowledge_name" VARCHAR NOT NULL,
  PRIMARY KEY ("knowledge_id"),
  FOREIGN KEY ("subject_id") REFERENCES "subjects" ("subject_id")
);

CREATE TABLE "exam_questions" (
  "question_id" VARCHAR NOT NULL,
  "exam_id" VARCHAR NOT NULL,
  "knowledge_id" VARCHAR NOT NULL,
  "question_no" INTEGER NOT NULL,
  "question_type" VARCHAR NOT NULL,
  "max_score" DOUBLE NOT NULL,
  PRIMARY KEY ("question_id"),
  FOREIGN KEY ("exam_id") REFERENCES "exams" ("exam_id"),
  FOREIGN KEY ("knowledge_id") REFERENCES "knowledge_points" ("knowledge_id")
);

CREATE TABLE "question_responses" (
  "response_id" VARCHAR NOT NULL,
  "result_id" VARCHAR NOT NULL,
  "question_id" VARCHAR NOT NULL,
  "response_status" VARCHAR NOT NULL,
  "score" DOUBLE NOT NULL,
  PRIMARY KEY ("response_id"),
  FOREIGN KEY ("result_id") REFERENCES "exam_results" ("result_id"),
  FOREIGN KEY ("question_id") REFERENCES "exam_questions" ("question_id")
);
