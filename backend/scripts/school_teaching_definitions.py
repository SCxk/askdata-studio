from __future__ import annotations

from pathlib import Path


DATABASE = "school_teaching"
DATABASE_DIR = Path(__file__).resolve().parents[1] / "data" / "databases" / DATABASE
NULLABLE_FIELDS = {
    ("attendance", "reason"), ("exam_results", "score"), ("exam_results", "absence_reason"),
    ("assignment_submissions", "submitted_at"), ("assignment_submissions", "graded_at"),
    ("assignment_submissions", "score"),
}

# Fields are (physical name, Chinese label, SQL type, business meaning).
TABLES = {
    "schools": {
        "label": "学校", "domain": "教学基础", "grain": "一所虚构学校", "pk": ["school_id"],
        "fields": [("school_id", "学校编号", "VARCHAR", "学校唯一标识"), ("school_name", "学校名称", "VARCHAR", "明确标注为模拟学校"), ("city", "所在城市", "VARCHAR", "模拟学校所在城市"), ("school_type", "办学类型", "VARCHAR", "初中")],
    },
    "terms": {
        "label": "学期", "domain": "教学基础", "grain": "学校的一个学期", "pk": ["term_id"],
        "fields": [("term_id", "学期编号", "VARCHAR", "学期唯一标识"), ("school_id", "学校编号", "VARCHAR", "所属学校"), ("academic_year", "学年", "VARCHAR", "跨自然年的学年"), ("term_name", "学期名称", "VARCHAR", "学校教学学期"), ("start_date", "开学日期", "DATE", "学期起始日期"), ("end_date", "结束日期", "DATE", "学期结束日期")],
    },
    "teachers": {
        "label": "教师", "domain": "教学基础", "grain": "一位虚构教师", "pk": ["teacher_id"],
        "fields": [("teacher_id", "教师编号", "VARCHAR", "教师唯一标识"), ("school_id", "学校编号", "VARCHAR", "所属学校"), ("teacher_name", "教师姓名", "VARCHAR", "随机合成姓名，无真实人员对应"), ("teaching_years", "教龄", "INTEGER", "模拟教龄，不用于推断教学效果"), ("title", "职称", "VARCHAR", "与教龄大致相符的模拟职称")],
    },
    "classes": {
        "label": "行政班", "domain": "教学基础", "grain": "学期内的一个行政班", "pk": ["class_id"],
        "fields": [("class_id", "班级编号", "VARCHAR", "班级唯一标识"), ("school_id", "学校编号", "VARCHAR", "所属学校"), ("term_id", "学期编号", "VARCHAR", "班级所属学期"), ("grade", "年级", "INTEGER", "7、8、9分别表示七、八、九年级"), ("class_name", "班级名称", "VARCHAR", "普通平行班，没有重点班标签"), ("homeroom_teacher_id", "班主任编号", "VARCHAR", "班主任同时是本班的一名任课教师")],
    },
    "students": {
        "label": "学生", "domain": "教学基础", "grain": "一位虚构学生", "pk": ["student_id"],
        "fields": [("student_id", "学号", "VARCHAR", "合成学号，不是真实学籍号"), ("school_id", "学校编号", "VARCHAR", "所属学校"), ("student_name", "学生姓名", "VARCHAR", "随机合成姓名，无真实人员对应"), ("gender", "性别", "VARCHAR", "模拟基本信息，不参与能力和成绩生成"), ("birth_date", "出生日期", "DATE", "与年级相符的合成日期"), ("enrollment_year", "入学年份", "INTEGER", "该学生进入七年级的年份")],
    },
    "enrollments": {
        "label": "学期班级学籍", "domain": "教学基础", "grain": "学生在学期内的一段班级归属", "pk": ["enrollment_id"],
        "fields": [("enrollment_id", "学籍记录编号", "VARCHAR", "学籍记录唯一标识"), ("student_id", "学号", "VARCHAR", "所属学生"), ("class_id", "班级编号", "VARCHAR", "该时段所在行政班"), ("term_id", "学期编号", "VARCHAR", "所属学期"), ("valid_from", "归属开始日期", "DATE", "包含起始日"), ("valid_to", "归属结束日期", "DATE", "包含结束日；九年级6月17日结课，其他年级7月10日结课；没有学期中转班")],
    },
    "subjects": {
        "label": "学科", "domain": "教学基础", "grain": "一门学科", "pk": ["subject_id"],
        "fields": [("subject_id", "学科编号", "VARCHAR", "学科唯一标识"), ("subject_name", "学科名称", "VARCHAR", "语文、数学、英语等"), ("pass_ratio", "及格分数比例", "DOUBLE", "得分/满分达到0.6视为及格"), ("excellent_ratio", "优秀分数比例", "DOUBLE", "得分/满分达到0.85视为优秀")],
    },
    "teaching_assignments": {
        "label": "任课安排", "domain": "课程教学", "grain": "学期内教师对一个班级一门学科的任课安排", "pk": ["teaching_id"],
        "fields": [("teaching_id", "任课编号", "VARCHAR", "任课安排唯一标识"), ("term_id", "学期编号", "VARCHAR", "所属学期"), ("class_id", "班级编号", "VARCHAR", "授课班级"), ("subject_id", "学科编号", "VARCHAR", "授课学科"), ("teacher_id", "教师编号", "VARCHAR", "任课教师"), ("weekly_periods", "每周课时", "INTEGER", "仅覆盖本数据中的文化课程，不代表完整课表")],
    },
    "academic_calendar": {
        "label": "教学日历", "domain": "课程教学", "grain": "学期内的一个自然日", "pk": ["calendar_date"],
        "fields": [("calendar_date", "日历日期", "DATE", "日期唯一键"), ("term_id", "学期编号", "VARCHAR", "所属学期"), ("week_no", "教学周", "INTEGER", "从开学周起连续编号，假期不重置"), ("day_type", "日期类型", "VARCHAR", "teaching教学日、exam有年级考试的教学日、holiday假日、weekend周末；非参考年级照常上课"), ("note", "日历备注", "VARCHAR", "虚构学校的校历设定，不是官方放假安排")],
    },
    "lessons": {
        "label": "课次", "domain": "课程教学", "grain": "一个班级一次实际排定的学科课堂", "pk": ["lesson_id"],
        "fields": [("lesson_id", "课次编号", "VARCHAR", "课次唯一标识"), ("teaching_id", "任课编号", "VARCHAR", "通过任课安排关联班级、学科和教师"), ("lesson_date", "上课日期", "DATE", "教学日上课，参考年级考试当天暂停常规课"), ("period_no", "节次", "INTEGER", "一天第1至7节；未包含体育、艺术等课程"), ("start_at", "上课时间", "TIMESTAMP", "课堂开始时间"), ("end_at", "下课时间", "TIMESTAMP", "课堂结束时间；每节45分钟")],
    },
    "attendance": {
        "label": "课堂考勤", "domain": "出勤分析", "grain": "一名学生在一个课次的考勤", "pk": ["attendance_id"],
        "fields": [("attendance_id", "考勤编号", "VARCHAR", "考勤唯一标识"), ("lesson_id", "课次编号", "VARCHAR", "所属课堂"), ("enrollment_id", "学籍记录编号", "VARCHAR", "上课当天的班级归属"), ("attendance_status", "出勤状态", "VARCHAR", "present到课、late迟到、excused请假、absent无故缺勤"), ("late_minutes", "迟到分钟数", "INTEGER", "仅迟到时大于0，其余为0"), ("reason", "考勤备注", "VARCHAR", "请假及缺勤的模拟记录；正常到课留空")],
    },
    "exams": {
        "label": "考试", "domain": "学业成绩", "grain": "年级在一轮考试中的一门学科试卷", "pk": ["exam_id"],
        "fields": [("exam_id", "考试编号", "VARCHAR", "同年级同学科使用同一份试卷"), ("term_id", "学期编号", "VARCHAR", "所属学期"), ("grade", "年级", "INTEGER", "考试面向的年级"), ("subject_id", "学科编号", "VARCHAR", "考试学科"), ("exam_name", "考试名称", "VARCHAR", "三月阶段测评、期中考试、期末考试"), ("exam_type", "考试类型", "VARCHAR", "monthly、midterm、final"), ("exam_date", "考试日期", "DATE", "校历中为exam的日期"), ("start_at", "开考时间", "TIMESTAMP", "同年级多学科考试不重叠"), ("duration_minutes", "考试时长", "INTEGER", "语数英120分钟，其他学科60分钟"), ("max_score", "试卷满分", "DOUBLE", "语数英120，其他学科100；以本字段为准")],
    },
    "exam_results": {
        "label": "考试成绩", "domain": "学业成绩", "grain": "学生参加一门考试的主考成绩", "pk": ["result_id"],
        "fields": [("result_id", "成绩编号", "VARCHAR", "成绩唯一标识"), ("exam_id", "考试编号", "VARCHAR", "所属考试"), ("enrollment_id", "学籍记录编号", "VARCHAR", "考试日学生的班级归属"), ("exam_status", "参考状态", "VARCHAR", "attended实考或absent缺考，缺考不按零分处理"), ("score", "考试得分", "DOUBLE", "等于逐题得分之和；缺考为空"), ("absence_reason", "缺考原因", "VARCHAR", "仅缺考时填写，不生成补考成绩")],
    },
    "assignments": {
        "label": "作业布置", "domain": "作业分析", "grain": "给一个班级布置的一份学科作业", "pk": ["assignment_id"],
        "fields": [("assignment_id", "作业编号", "VARCHAR", "作业唯一标识"), ("teaching_id", "任课编号", "VARCHAR", "布置作业的任课关系"), ("assignment_title", "作业名称", "VARCHAR", "学科及教学周名称"), ("assigned_at", "布置时间", "TIMESTAMP", "在该学科实际课堂结束后布置"), ("due_at", "截止时间", "TIMESTAMP", "下一教学日20点"), ("max_score", "作业满分", "DOUBLE", "满分100"), ("estimated_minutes", "预计完成分钟", "INTEGER", "单科一次作业预计时长")],
    },
    "assignment_submissions": {
        "label": "作业提交", "domain": "作业分析", "grain": "一名应交学生对一份作业的最终提交记录", "pk": ["submission_id"],
        "fields": [("submission_id", "提交编号", "VARCHAR", "提交记录唯一标识"), ("assignment_id", "作业编号", "VARCHAR", "所属作业"), ("enrollment_id", "学籍记录编号", "VARCHAR", "应交学生；未交也保留一条记录作为分母"), ("submission_status", "提交状态", "VARCHAR", "on_time按时、late迟交、missing未交"), ("submitted_at", "提交时间", "TIMESTAMP", "未交为空；迟交严格晚于截止时间"), ("graded_at", "批改时间", "TIMESTAMP", "晚于提交时间，不超过学期结束"), ("score", "作业得分", "DOUBLE", "未交为空；已交作业全部完成批改")],
    },
    "knowledge_points": {
        "label": "知识点", "domain": "知识点分析", "grain": "年级学科的一个知识点", "pk": ["knowledge_id"],
        "fields": [("knowledge_id", "知识点编号", "VARCHAR", "知识点唯一标识"), ("subject_id", "学科编号", "VARCHAR", "所属学科"), ("grade", "年级", "INTEGER", "所属年级"), ("knowledge_name", "知识点名称", "VARCHAR", "采用真实课程中常见知识点名称；非特定教材进度")],
    },
    "exam_questions": {
        "label": "试题", "domain": "知识点分析", "grain": "一份试卷中的一道评分题", "pk": ["question_id"],
        "fields": [("question_id", "试题编号", "VARCHAR", "试题唯一标识"), ("exam_id", "考试编号", "VARCHAR", "所属试卷"), ("knowledge_id", "知识点编号", "VARCHAR", "该题唯一主知识点，避免多标签关联重复计分"), ("question_no", "题号", "INTEGER", "试卷内第1至20题"), ("question_type", "题型", "VARCHAR", "choice客观题或constructed分步评分题"), ("max_score", "试题满分", "DOUBLE", "20题满分合计等于试卷满分")],
    },
    "question_responses": {
        "label": "逐题得分", "domain": "知识点分析", "grain": "一条实考成绩对应的一道题得分", "pk": ["response_id"],
        "fields": [("response_id", "答题记录编号", "VARCHAR", "答题记录唯一标识"), ("result_id", "成绩编号", "VARCHAR", "所属学生的实考成绩，缺考无答题记录"), ("question_id", "试题编号", "VARCHAR", "所属试题"), ("response_status", "作答状态", "VARCHAR", "answered已作答或blank未作答；未作答得0分"), ("score", "试题得分", "DOUBLE", "客观题0或满分，分步题按0.5分给分")],
    },
}

# Parent table / key, child table / foreign key.
RELATIONS = [
    ("schools", "school_id", table, "school_id") for table in ("terms", "teachers", "classes", "students")
] + [
    ("terms", "term_id", table, "term_id") for table in ("classes", "enrollments", "teaching_assignments", "academic_calendar", "exams")
] + [
    ("teachers", "teacher_id", "classes", "homeroom_teacher_id"),
    ("students", "student_id", "enrollments", "student_id"),
    ("classes", "class_id", "enrollments", "class_id"),
    ("classes", "class_id", "teaching_assignments", "class_id"),
    ("subjects", "subject_id", "teaching_assignments", "subject_id"),
    ("teachers", "teacher_id", "teaching_assignments", "teacher_id"),
    ("teaching_assignments", "teaching_id", "lessons", "teaching_id"),
    ("academic_calendar", "calendar_date", "lessons", "lesson_date"),
    ("lessons", "lesson_id", "attendance", "lesson_id"),
    ("enrollments", "enrollment_id", "attendance", "enrollment_id"),
    ("subjects", "subject_id", "exams", "subject_id"),
    ("academic_calendar", "calendar_date", "exams", "exam_date"),
    ("exams", "exam_id", "exam_results", "exam_id"),
    ("enrollments", "enrollment_id", "exam_results", "enrollment_id"),
    ("teaching_assignments", "teaching_id", "assignments", "teaching_id"),
    ("assignments", "assignment_id", "assignment_submissions", "assignment_id"),
    ("enrollments", "enrollment_id", "assignment_submissions", "enrollment_id"),
    ("subjects", "subject_id", "knowledge_points", "subject_id"),
    ("exams", "exam_id", "exam_questions", "exam_id"),
    ("knowledge_points", "knowledge_id", "exam_questions", "knowledge_id"),
    ("exam_results", "result_id", "question_responses", "result_id"),
    ("exam_questions", "question_id", "question_responses", "question_id"),
]

METRICS = {
    "平均分": "仅exam_status='attended'的成绩参与AVG(score)；缺考保持NULL，不补零。跨不同满分试卷用100*score/max_score；标准分只消除满分差异，不消除难度差异。",
    "及格率": "同一统计范围内，实考且score/max_score>=subjects.pass_ratio的人次 / 实考人次。跨学科分母为考试人次，不能标成学生人数。",
    "优秀率": "实考且score/max_score>=subjects.excellent_ratio的人次 / 实考人次。",
    "出勤率": "(present课次人次+late课次人次)/全部应到课次人次；请假和无故缺勤均计入应到分母。分母剔除请假的指标必须另称扣除请假出勤率。",
    "迟到率": "late课次人次/全部应到课次人次。",
    "作业完成率": "(on_time记录数+late记录数)/全部应交记录数；missing记录保留在分母。",
    "按时提交率": "on_time记录数/全部应交记录数。",
    "知识点得分率": "SUM(question_responses.score)/SUM(exam_questions.max_score)，仅包括实际参考学生。不是学习能力或因果效果的测量。",
    "进步幅度": "同一学生同一学科两轮均实考时的百分制得分差；不同试卷未做等值处理，只作描述比较，不能直接归因于教师。",
}

SUBJECT_SPECS = [
    ("CHN", "语文", 5, 120), ("MAT", "数学", 5, 120), ("ENG", "英语", 5, 120),
    ("POL", "道德与法治", 2, 100), ("HIS", "历史", 2, 100),
    ("GEO", "地理", 2, 100), ("BIO", "生物", 2, 100),
    ("PHY", "物理", 3, 100), ("CHE", "化学", 3, 100),
]

KNOWLEDGE = {
    "CHN": {7: ["字音字形", "古诗文理解", "说明性文本阅读", "记叙文阅读", "写作表达"], 8: ["语言运用", "古诗文赏析", "说明文阅读", "议论文阅读", "写作表达"], 9: ["语言综合运用", "古诗文阅读", "文学类文本阅读", "议论性文本阅读", "写作表达"]},
    "MAT": {7: ["整式运算", "相交线与平行线", "实数", "二元一次方程组", "不等式"], 8: ["二次根式", "勾股定理", "平行四边形", "一次函数", "数据分析"], 9: ["二次函数", "相似三角形", "锐角三角函数", "圆的综合", "概率与统计"]},
    "ENG": {7: ["一般现在时", "现在进行时", "情态动词", "阅读理解", "书面表达"], 8: ["过去进行时", "现在完成时", "词汇运用", "阅读理解", "书面表达"], 9: ["时态综合", "被动语态", "定语从句", "阅读理解", "书面表达"]},
    "POL": {7: ["青春成长", "情绪管理", "集体生活", "法律常识", "案例分析"], 8: ["宪法意识", "公民权利", "公民义务", "国家机构", "公平正义"], 9: ["国情认识", "民主法治", "文化认同", "绿色发展", "综合探究"]},
    "HIS": {7: ["隋唐制度", "民族交融", "宋元经济", "明清发展", "史料分析"], 8: ["新中国成立", "社会主义建设", "改革开放", "民族团结", "史料分析"], 9: ["工业革命", "世界大战", "国际格局", "经济全球化", "史料分析"]},
    "GEO": {7: ["亚洲地理", "区域自然环境", "区域人文环境", "地理读图", "区域比较"], 8: ["中国区域地理", "北方地区", "南方地区", "西北与青藏地区", "区域协调发展"]},
    "BIO": {7: ["人体营养", "呼吸与循环", "排泄与调节", "人体健康", "实验探究"], 8: ["生物繁殖", "遗传与变异", "生物进化", "健康生活", "实验探究"]},
    "PHY": {8: ["力与运动", "压强", "浮力", "功与机械能", "简单机械"], 9: ["电学综合", "欧姆定律", "电功与电功率", "电与磁", "实验探究"]},
    "CHE": {9: ["溶液", "酸和碱", "盐与化肥", "化学计算", "实验探究"]},
}


def subjects_for_grade(grade: int) -> list[tuple]:
    return [spec for spec in SUBJECT_SPECS if grade in KNOWLEDGE[spec[0]]]
