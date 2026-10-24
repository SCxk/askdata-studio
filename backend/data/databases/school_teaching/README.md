# 学校教学分析模拟数据

**本目录所有学校、人员、教学记录和成绩均为完全合成数据，不来自真实学校。**

## 范围

- 虚构学校：明川实验中学（模拟），杭州，普通初中。
- 学期：2026-02-23 至 2026-07-10，2025-2026 学年第二学期。
- 七至九年级共 18 个平行班，780 名学生，66 名文化课教师。
- 18 张 CSV 表，共 721,465 条记录。CSV 为 UTF-8 BOM，可在 Excel 中直接查看。
- 九年级在 6 月 15-17 日进行校内毕业测评并结课；七八年级在 7 月 6-8 日期末考试。没有模拟中考成绩。
- 七年级不含物理、化学，八年级新增物理，九年级增加化学并不再排地理和生物。
- 仅覆盖文化课；课表缺口是未纳入本数据的体育、艺术、班会等课程。
- 作业为隔周抽样的一次巩固作业，不代表全量布置，也不能用来估计学生全部作业负担。

## 数据真实性设计

- 学生存在稳定能力差异、偏科、知识点差异和不同进步轨迹；同一学生多次测评相关，但有临场波动。
- 作业受到查阅资料、个体完成方式等独立偏差影响，作业高分不会机械对应考试高分。
- 存在随机班级差异；性别和姓名不参与能力、习惯或成绩生成。内部生成参数不作为真实学生标签导出。
- 请假可能连续多天，同一天病假影响各节课；迟到更多发生在第一节，且有少量无故缺勤。
- 课表避免教师和班级冲突；考试按年级错开学科时间，考试当天参考年级暂停常规课。
- 三月测评覆盖每科前两个知识点，期中覆盖前四个，期末覆盖五个；知识点取常见课程内容，不对应特定教材教学进度。
- 每份试卷含 20 道评分题，客观题按对错给分，分步题有部分得分，总分严格等于逐题得分之和。
- 缺考成绩为空、没有逐题记录；未交作业也保留应交记录，提交和批改时间符合先后顺序。
- 所有趋势和相关关系均由生成规则构造，适合功能演示与查询验证，不能作为教育研究的实证证据。

## 文件

- `_schema.json`：与项目现有结构一致的表、字段、关系和字段分布；包含指标口径。
- `_data_dictionary.md`：逐字段中文说明、类型、空值含义和记录粒度。
- `_database_manifest.json`：随机种子、各表行数和文件 SHA-256 校验值。
- `_create_tables.sql`、`_load_data.sql`：DuckDB 建表与导入脚本，含主键、外键和非空约束。
- `_validation_report.json`：运行校验后产生的完整性检查、成绩分布和相关性统计。
- `_example_queries.json`：运行校验后产生的 10 个典型问题、标准 SQL 和实际结果。

## 指标口径

- **平均分**：仅exam_status='attended'的成绩参与AVG(score)；缺考保持NULL，不补零。跨不同满分试卷用100*score/max_score；标准分只消除满分差异，不消除难度差异。
- **及格率**：同一统计范围内，实考且score/max_score>=subjects.pass_ratio的人次 / 实考人次。跨学科分母为考试人次，不能标成学生人数。
- **优秀率**：实考且score/max_score>=subjects.excellent_ratio的人次 / 实考人次。
- **出勤率**：(present课次人次+late课次人次)/全部应到课次人次；请假和无故缺勤均计入应到分母。分母剔除请假的指标必须另称扣除请假出勤率。
- **迟到率**：late课次人次/全部应到课次人次。
- **作业完成率**：(on_time记录数+late记录数)/全部应交记录数；missing记录保留在分母。
- **按时提交率**：on_time记录数/全部应交记录数。
- **知识点得分率**：SUM(question_responses.score)/SUM(exam_questions.max_score)，仅包括实际参考学生。不是学习能力或因果效果的测量。
- **进步幅度**：同一学生同一学科两轮均实考时的百分制得分差；不同试卷未做等值处理，只作描述比较，不能直接归因于教师。

## 重新生成与校验

在项目的 backend 目录运行：

```powershell
.\.venv\Scripts\python.exe scripts\generate_school_teaching_data.py --overwrite
.\.venv\Scripts\python.exe scripts\validate_school_teaching.py
```

默认随机种子为 20261019，同一 Python 版本和相同种子会生成相同 CSV。可通过 `--seed` 改变样本。重新生成后须重新运行校验以刷新报告和示例结果。

如果使用 DuckDB Python 库，在本目录执行以下代码即可创建真实数据表：

```python
from pathlib import Path
import duckdb
con = duckdb.connect(':memory:')
con.execute(Path('_create_tables.sql').read_text(encoding='utf-8'))
con.execute(Path('_load_data.sql').read_text(encoding='utf-8'))
print(con.execute('SELECT COUNT(*) FROM students').fetchone())
```

## 与当前应用的关系

项目仅加载 `school_teaching` 目录中的 18 张学校模拟数据表。
使用 `school` / `school123` 登录页面即可查询学校数据；管理员也仅访问学校数据库。
`academic_admin` 是全校教务角色，尚未实现教师按班级、学生按本人的行级权限。
