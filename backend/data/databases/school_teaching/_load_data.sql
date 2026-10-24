-- Run after _create_tables.sql, with this data folder as working directory.

COPY "schools" FROM 'schools.csv' (HEADER TRUE, NULL '');
COPY "terms" FROM 'terms.csv' (HEADER TRUE, NULL '');
COPY "teachers" FROM 'teachers.csv' (HEADER TRUE, NULL '');
COPY "classes" FROM 'classes.csv' (HEADER TRUE, NULL '');
COPY "students" FROM 'students.csv' (HEADER TRUE, NULL '');
COPY "enrollments" FROM 'enrollments.csv' (HEADER TRUE, NULL '');
COPY "subjects" FROM 'subjects.csv' (HEADER TRUE, NULL '');
COPY "teaching_assignments" FROM 'teaching_assignments.csv' (HEADER TRUE, NULL '');
COPY "academic_calendar" FROM 'academic_calendar.csv' (HEADER TRUE, NULL '');
COPY "lessons" FROM 'lessons.csv' (HEADER TRUE, NULL '');
COPY "attendance" FROM 'attendance.csv' (HEADER TRUE, NULL '');
COPY "exams" FROM 'exams.csv' (HEADER TRUE, NULL '');
COPY "exam_results" FROM 'exam_results.csv' (HEADER TRUE, NULL '');
COPY "assignments" FROM 'assignments.csv' (HEADER TRUE, NULL '');
COPY "assignment_submissions" FROM 'assignment_submissions.csv' (HEADER TRUE, NULL '');
COPY "knowledge_points" FROM 'knowledge_points.csv' (HEADER TRUE, NULL '');
COPY "exam_questions" FROM 'exam_questions.csv' (HEADER TRUE, NULL '');
COPY "question_responses" FROM 'question_responses.csv' (HEADER TRUE, NULL '');
