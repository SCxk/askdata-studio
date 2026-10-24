# EduQuery

面向学校教学分析的自然语言问数项目，包含 Vue 前端、FastAPI + LangGraph 后端、18 张学校模拟数据表、字段级 Schema 索引、测试脚本和评测报告。

## 环境要求

- Python 3.11
- Node.js 20.19 或更高版本
- 兼容 OpenAI 接口的大模型、Embedding 和 Rerank 服务

## 安装

以下命令均从项目根目录执行。

后端（Windows PowerShell）：

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

后端（macOS / Linux）：

```bash
cd backend
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

编辑 `backend/.env`，填写 `LLM_API_KEY`。默认模型配置为 `qwen3.7-plus`、`text-embedding-v4` 和 `qwen3-rerank`。

前端：

```powershell
cd frontend
npm install
```

## 启动

分别打开两个终端。

后端（Windows）：

```powershell
cd backend
.\.venv\Scripts\python.exe run.py
```

后端（macOS / Linux）：

```bash
cd backend
./.venv/bin/python run.py
```

前端：

```powershell
cd frontend
npm run dev
```

访问 `http://127.0.0.1:5173`，API 文档位于 `http://127.0.0.1:8000/docs`。

## 测试

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe scripts\validate_school_teaching.py
.\.venv\Scripts\python.exe -m evaluation.run_school_benchmark --gold-only
```

评测命令与指标说明见 `backend/evaluation/README.md`。现有评测结果位于 `backend/evaluation/results`。

## 测试账号

- 学校教务（默认）：`school` / `school123`，仅访问 18 张学校模拟数据表。
- 管理员：`admin` / `admin123`

## 学校教学分析

使用学校教务账号登录，可直接点击教育示例问题，或询问：

- 八年级期中数学各班平均分和及格率是多少？
- 各班本学期作业完成率和按时提交率是多少？
- 查看本学期每月出勤率和迟到人次。

学校数据覆盖 2025-2026 学年第二学期，共 780 名学生。详细数据说明与指标口径位于 `backend/data/databases/school_teaching/README.md`。
项目仅保留学校教学数据库，学校账号和管理员均可访问这 18 张模拟数据表。学校账号为全校教务角色，没有模拟教师按班级或学生按本人的行级权限。

如需重新生成模拟数据，在 `backend` 目录执行 `.\.venv\Scripts\python.exe scripts\generate_school_teaching_data.py --overwrite`，然后重新运行数据校验。字段向量索引 `backend/data/schema_store.json` 是本地生成缓存，不纳入版本控制；首次检索时会使用已配置的 Embedding 服务自动构建。
