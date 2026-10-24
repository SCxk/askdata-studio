# 学校教学数据字典

全部记录均为合成数据。编号保持文本类型；CSV 空白单元格读作 NULL。

## 学校 / schools

粒度：一所虚构学校。记录数：1。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| school_id | 学校编号 | VARCHAR | 否 | 学校唯一标识 |
| school_name | 学校名称 | VARCHAR | 否 | 明确标注为模拟学校 |
| city | 所在城市 | VARCHAR | 否 | 模拟学校所在城市 |
| school_type | 办学类型 | VARCHAR | 否 | 初中 |

## 学期 / terms

粒度：学校的一个学期。记录数：1。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| term_id | 学期编号 | VARCHAR | 否 | 学期唯一标识 |
| school_id | 学校编号 | VARCHAR | 否 | 所属学校 |
| academic_year | 学年 | VARCHAR | 否 | 跨自然年的学年 |
| term_name | 学期名称 | VARCHAR | 否 | 学校教学学期 |
| start_date | 开学日期 | DATE | 否 | 学期起始日期 |
| end_date | 结束日期 | DATE | 否 | 学期结束日期 |

## 教师 / teachers

粒度：一位虚构教师。记录数：66。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| teacher_id | 教师编号 | VARCHAR | 否 | 教师唯一标识 |
| school_id | 学校编号 | VARCHAR | 否 | 所属学校 |
| teacher_name | 教师姓名 | VARCHAR | 否 | 随机合成姓名，无真实人员对应 |
| teaching_years | 教龄 | INTEGER | 否 | 模拟教龄，不用于推断教学效果 |
| title | 职称 | VARCHAR | 否 | 与教龄大致相符的模拟职称 |

## 行政班 / classes

粒度：学期内的一个行政班。记录数：18。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| class_id | 班级编号 | VARCHAR | 否 | 班级唯一标识 |
| school_id | 学校编号 | VARCHAR | 否 | 所属学校 |
| term_id | 学期编号 | VARCHAR | 否 | 班级所属学期 |
| grade | 年级 | INTEGER | 否 | 7、8、9分别表示七、八、九年级 |
| class_name | 班级名称 | VARCHAR | 否 | 普通平行班，没有重点班标签 |
| homeroom_teacher_id | 班主任编号 | VARCHAR | 否 | 班主任同时是本班的一名任课教师 |

## 学生 / students

粒度：一位虚构学生。记录数：780。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| student_id | 学号 | VARCHAR | 否 | 合成学号，不是真实学籍号 |
| school_id | 学校编号 | VARCHAR | 否 | 所属学校 |
| student_name | 学生姓名 | VARCHAR | 否 | 随机合成姓名，无真实人员对应 |
| gender | 性别 | VARCHAR | 否 | 模拟基本信息，不参与能力和成绩生成 |
| birth_date | 出生日期 | DATE | 否 | 与年级相符的合成日期 |
| enrollment_year | 入学年份 | INTEGER | 否 | 该学生进入七年级的年份 |

## 学期班级学籍 / enrollments

粒度：学生在学期内的一段班级归属。记录数：780。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| enrollment_id | 学籍记录编号 | VARCHAR | 否 | 学籍记录唯一标识 |
| student_id | 学号 | VARCHAR | 否 | 所属学生 |
| class_id | 班级编号 | VARCHAR | 否 | 该时段所在行政班 |
| term_id | 学期编号 | VARCHAR | 否 | 所属学期 |
| valid_from | 归属开始日期 | DATE | 否 | 包含起始日 |
| valid_to | 归属结束日期 | DATE | 否 | 包含结束日；九年级6月17日结课，其他年级7月10日结课；没有学期中转班 |

## 学科 / subjects

粒度：一门学科。记录数：9。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| subject_id | 学科编号 | VARCHAR | 否 | 学科唯一标识 |
| subject_name | 学科名称 | VARCHAR | 否 | 语文、数学、英语等 |
| pass_ratio | 及格分数比例 | DOUBLE | 否 | 得分/满分达到0.6视为及格 |
| excellent_ratio | 优秀分数比例 | DOUBLE | 否 | 得分/满分达到0.85视为优秀 |

## 任课安排 / teaching_assignments

粒度：学期内教师对一个班级一门学科的任课安排。记录数：132。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| teaching_id | 任课编号 | VARCHAR | 否 | 任课安排唯一标识 |
| term_id | 学期编号 | VARCHAR | 否 | 所属学期 |
| class_id | 班级编号 | VARCHAR | 否 | 授课班级 |
| subject_id | 学科编号 | VARCHAR | 否 | 授课学科 |
| teacher_id | 教师编号 | VARCHAR | 否 | 任课教师 |
| weekly_periods | 每周课时 | INTEGER | 否 | 仅覆盖本数据中的文化课程，不代表完整课表 |

## 教学日历 / academic_calendar

粒度：学期内的一个自然日。记录数：138。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| calendar_date | 日历日期 | DATE | 否 | 日期唯一键 |
| term_id | 学期编号 | VARCHAR | 否 | 所属学期 |
| week_no | 教学周 | INTEGER | 否 | 从开学周起连续编号，假期不重置 |
| day_type | 日期类型 | VARCHAR | 否 | teaching教学日、exam有年级考试的教学日、holiday假日、weekend周末；非参考年级照常上课 |
| note | 日历备注 | VARCHAR | 否 | 虚构学校的校历设定，不是官方放假安排 |

## 课次 / lessons

粒度：一个班级一次实际排定的学科课堂。记录数：7,156。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| lesson_id | 课次编号 | VARCHAR | 否 | 课次唯一标识 |
| teaching_id | 任课编号 | VARCHAR | 否 | 通过任课安排关联班级、学科和教师 |
| lesson_date | 上课日期 | DATE | 否 | 教学日上课，参考年级考试当天暂停常规课 |
| period_no | 节次 | INTEGER | 否 | 一天第1至7节；未包含体育、艺术等课程 |
| start_at | 上课时间 | TIMESTAMP | 否 | 课堂开始时间 |
| end_at | 下课时间 | TIMESTAMP | 否 | 课堂结束时间；每节45分钟 |

## 课堂考勤 / attendance

粒度：一名学生在一个课次的考勤。记录数：310,088。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| attendance_id | 考勤编号 | VARCHAR | 否 | 考勤唯一标识 |
| lesson_id | 课次编号 | VARCHAR | 否 | 所属课堂 |
| enrollment_id | 学籍记录编号 | VARCHAR | 否 | 上课当天的班级归属 |
| attendance_status | 出勤状态 | VARCHAR | 否 | present到课、late迟到、excused请假、absent无故缺勤 |
| late_minutes | 迟到分钟数 | INTEGER | 否 | 仅迟到时大于0，其余为0 |
| reason | 考勤备注 | VARCHAR | 是 | 请假及缺勤的模拟记录；正常到课留空 |

## 考试 / exams

粒度：年级在一轮考试中的一门学科试卷。记录数：66。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| exam_id | 考试编号 | VARCHAR | 否 | 同年级同学科使用同一份试卷 |
| term_id | 学期编号 | VARCHAR | 否 | 所属学期 |
| grade | 年级 | INTEGER | 否 | 考试面向的年级 |
| subject_id | 学科编号 | VARCHAR | 否 | 考试学科 |
| exam_name | 考试名称 | VARCHAR | 否 | 三月阶段测评、期中考试、期末考试 |
| exam_type | 考试类型 | VARCHAR | 否 | monthly、midterm、final |
| exam_date | 考试日期 | DATE | 否 | 校历中为exam的日期 |
| start_at | 开考时间 | TIMESTAMP | 否 | 同年级多学科考试不重叠 |
| duration_minutes | 考试时长 | INTEGER | 否 | 语数英120分钟，其他学科60分钟 |
| max_score | 试卷满分 | DOUBLE | 否 | 语数英120，其他学科100；以本字段为准 |

## 考试成绩 / exam_results

粒度：学生参加一门考试的主考成绩。记录数：17,157。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| result_id | 成绩编号 | VARCHAR | 否 | 成绩唯一标识 |
| exam_id | 考试编号 | VARCHAR | 否 | 所属考试 |
| enrollment_id | 学籍记录编号 | VARCHAR | 否 | 考试日学生的班级归属 |
| exam_status | 参考状态 | VARCHAR | 否 | attended实考或absent缺考，缺考不按零分处理 |
| score | 考试得分 | DOUBLE | 是 | 等于逐题得分之和；缺考为空 |
| absence_reason | 缺考原因 | VARCHAR | 是 | 仅缺考时填写，不生成补考成绩 |

## 作业布置 / assignments

粒度：给一个班级布置的一份学科作业。记录数：1,121。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| assignment_id | 作业编号 | VARCHAR | 否 | 作业唯一标识 |
| teaching_id | 任课编号 | VARCHAR | 否 | 布置作业的任课关系 |
| assignment_title | 作业名称 | VARCHAR | 否 | 学科及教学周名称 |
| assigned_at | 布置时间 | TIMESTAMP | 否 | 在该学科实际课堂结束后布置 |
| due_at | 截止时间 | TIMESTAMP | 否 | 下一教学日20点 |
| max_score | 作业满分 | DOUBLE | 否 | 满分100 |
| estimated_minutes | 预计完成分钟 | INTEGER | 否 | 单科一次作业预计时长 |

## 作业提交 / assignment_submissions

粒度：一名应交学生对一份作业的最终提交记录。记录数：48,582。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| submission_id | 提交编号 | VARCHAR | 否 | 提交记录唯一标识 |
| assignment_id | 作业编号 | VARCHAR | 否 | 所属作业 |
| enrollment_id | 学籍记录编号 | VARCHAR | 否 | 应交学生；未交也保留一条记录作为分母 |
| submission_status | 提交状态 | VARCHAR | 否 | on_time按时、late迟交、missing未交 |
| submitted_at | 提交时间 | TIMESTAMP | 是 | 未交为空；迟交严格晚于截止时间 |
| graded_at | 批改时间 | TIMESTAMP | 是 | 晚于提交时间，不超过学期结束 |
| score | 作业得分 | DOUBLE | 是 | 未交为空；已交作业全部完成批改 |

## 知识点 / knowledge_points

粒度：年级学科的一个知识点。记录数：110。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| knowledge_id | 知识点编号 | VARCHAR | 否 | 知识点唯一标识 |
| subject_id | 学科编号 | VARCHAR | 否 | 所属学科 |
| grade | 年级 | INTEGER | 否 | 所属年级 |
| knowledge_name | 知识点名称 | VARCHAR | 否 | 采用真实课程中常见知识点名称；非特定教材进度 |

## 试题 / exam_questions

粒度：一份试卷中的一道评分题。记录数：1,320。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| question_id | 试题编号 | VARCHAR | 否 | 试题唯一标识 |
| exam_id | 考试编号 | VARCHAR | 否 | 所属试卷 |
| knowledge_id | 知识点编号 | VARCHAR | 否 | 该题唯一主知识点，避免多标签关联重复计分 |
| question_no | 题号 | INTEGER | 否 | 试卷内第1至20题 |
| question_type | 题型 | VARCHAR | 否 | choice客观题或constructed分步评分题 |
| max_score | 试题满分 | DOUBLE | 否 | 20题满分合计等于试卷满分 |

## 逐题得分 / question_responses

粒度：一条实考成绩对应的一道题得分。记录数：333,940。

| 字段 | 中文名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- | --- |
| response_id | 答题记录编号 | VARCHAR | 否 | 答题记录唯一标识 |
| result_id | 成绩编号 | VARCHAR | 否 | 所属学生的实考成绩，缺考无答题记录 |
| question_id | 试题编号 | VARCHAR | 否 | 所属试题 |
| response_status | 作答状态 | VARCHAR | 否 | answered已作答或blank未作答；未作答得0分 |
| score | 试题得分 | DOUBLE | 否 | 客观题0或满分，分步题按0.5分给分 |

