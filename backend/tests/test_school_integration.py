from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import DATABASE_SCHEMAS, SCHEMA, database_query_context
from app.main import app
from app.querying.duckdb_engine import DuckDbEngine
from app.querying.single_database_agent import SingleDatabaseAgent
from app.retrieval import SchemaIndex
from app.security import AccessController, AccessScope


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "databases" / "school_teaching"


class SchoolIntegrationTest(unittest.TestCase):
    def test_only_school_database_is_present_and_loaded(self) -> None:
        self.assertEqual(set(DATABASE_SCHEMAS), {"school_teaching"})
        self.assertEqual(len(SCHEMA), 18)
        self.assertEqual(sum(t["database"] == "school_teaching" for t in SCHEMA), 18)
        csv_files = list(DATA_DIR.parent.rglob("*.csv"))
        self.assertEqual(len(csv_files), 18)
        self.assertEqual({path.parent.name for path in csv_files}, {"school_teaching"})

    def test_school_login_exposes_only_school_schema_and_tools(self) -> None:
        with TestClient(app) as client:
            for username in ("school", "admin"):
                with self.subTest(username=username):
                    login = client.post("/api/auth/login", json={"username": username, "password": username + "123"})
                    self.assertEqual(login.status_code, 200)
                    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
                    schema = client.get("/api/schema", headers=headers)
                    self.assertEqual(schema.status_code, 200)
                    self.assertEqual(len(schema.json()), 18)
                    self.assertEqual({table["database"] for table in schema.json()}, {"school_teaching"})
                    tools = client.get("/api/mcp/tools", headers=headers).json()
                    names = {tool["name"] for tool in tools if tool["name"].startswith("query_")}
                    self.assertEqual(names, {"query_school_teaching"})

    def test_removed_accounts_cannot_log_in_or_query(self) -> None:
        with TestClient(app) as client:
            for username in ("growth", "channel", "content"):
                with self.subTest(username=username):
                    response = client.post("/api/auth/login", json={"username": username, "password": username + "123"})
                    self.assertEqual(response.status_code, 401)
                    scope = AccessController().resolve(f"demo_{username}_ops")
                    self.assertEqual(scope.allowed_tables, frozenset())
                    result = DuckDbEngine().execute("school_teaching", "SELECT COUNT(student_id) AS students FROM students", scope)
                    self.assertFalse(result.success)
                    self.assertIn("无权访问", result.error)

    def test_school_scope_and_default_user_have_only_school_tables(self) -> None:
        engine = DuckDbEngine()
        school = AccessController().resolve("demo_school")
        self.assertEqual(AccessController().resolve(None), school)
        self.assertEqual(school.allowed_databases, frozenset({"school_teaching"}))
        self.assertEqual(len(AccessController.filter_schema(school)), 18)
        self.assertEqual(len(AccessController.filter_schema(AccessController().resolve("demo_admin"))), 18)
        result = engine.execute("school_teaching", "SELECT COUNT(student_id) AS students FROM students", school)
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.rows, [{"students": 780}])
        denied = engine.execute("short_video_ops", "SELECT COUNT(user_id) AS users FROM users", school)
        self.assertFalse(denied.success)
        self.assertIn("无权访问", denied.error)

    def test_restricted_school_scope_and_read_only_sql(self) -> None:
        scope = AccessScope("restricted", (), frozenset({"school_teaching"}), frozenset({"school_teaching.students"}))
        engine = DuckDbEngine()
        allowed = engine.execute("school_teaching", "SELECT student_id FROM students LIMIT 1", scope)
        self.assertTrue(allowed.success, allowed.error)
        for sql in ("SELECT class_id FROM classes", "DELETE FROM students", "SELECT * FROM students"):
            with self.subTest(sql=sql):
                self.assertFalse(engine.execute("school_teaching", sql, scope).success)

    def test_search_documents_contain_only_school_fields(self) -> None:
        documents = SchemaIndex()._build_raw_documents()
        self.assertEqual(len(documents), sum(len(table["fields"]) for table in SCHEMA))
        self.assertEqual({document["database_id"] for document in documents}, {"school_teaching"})

    def test_school_metric_context_does_not_leak_other_tables(self) -> None:
        scope = AccessController().resolve("demo_school")
        context = database_query_context("school_teaching", scope.allowed_tables)
        self.assertIn("及格率", context["metric_definitions"])
        self.assertEqual(len(context["tables"]), 18)
        self.assertEqual(context["default_term"]["term_id"], "T2025_2026_2")
        restricted = database_query_context("school_teaching", frozenset({"school_teaching.students"}))
        self.assertEqual([table["name"] for table in restricted["tables"]], ["students"])
        self.assertEqual(restricted["relations"], [])
        self.assertNotIn("default_term", restricted)

    def test_historical_school_term_does_not_follow_todays_date(self) -> None:
        scope = AccessController().resolve("demo_school")
        payload = {"query": "查看本学期每月出勤率", "database_context": database_query_context("school_teaching", scope.allowed_tables)}
        decision = {"action": "call_tool", "tool_name": "query_school_teaching", "arguments": {"sql": "SELECT term_id FROM terms WHERE start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE"}}
        self.assertIn("T2025_2026_2", SingleDatabaseAgent._academic_term_error(decision, payload))
        decision["arguments"]["sql"] = "SELECT term_id FROM terms WHERE term_id='T2025_2026_2'"
        self.assertEqual(SingleDatabaseAgent._academic_term_error(decision, payload), "")
        payload["query"] = "查看本学期本月的出勤率"
        decision["arguments"]["sql"] = "SELECT calendar_date FROM academic_calendar WHERE calendar_date=CURRENT_DATE"
        self.assertEqual(SingleDatabaseAgent._academic_term_error(decision, payload), "")

    def test_school_queries_match_validated_expected_rows(self) -> None:
        engine = DuckDbEngine()
        scope = AccessController().resolve("demo_school")
        cases = json.loads((DATA_DIR / "_example_queries.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = engine.execute("school_teaching", case["gold_sql"], scope)
                self.assertTrue(result.success, result.error)
                self.assertEqual(result.rows, case["expected_rows"])


if __name__ == "__main__":
    unittest.main()
