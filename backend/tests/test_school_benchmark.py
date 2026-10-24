import copy
import json
import unittest

from app.config import BASE_DIR
from evaluation.run_school_benchmark import cell_equal, compare, gold_cases
from evaluation.review_school_results import review_case


class SchoolBenchmarkComparisonTest(unittest.TestCase):
    def setUp(self):
        self.case = {
            "columns": [{"name": "class", "aliases": ["class", "班级"], "kind": "text"},
                        {"name": "rate", "aliases": ["rate", "比率"], "kind": "ratio"}],
            "expected_rows": [{"class": "A", "rate": 0.87654}, {"class": "B", "rate": 0.9}],
            "order_sensitive": False,
        }

    def test_aliases_and_unordered_rows(self):
        self.assertTrue(compare(self.case, ["比率", "班级"],
                                [{"班级": "B", "比率": 0.9}, {"班级": "A", "比率": 0.8765}])[0])

    def test_ordered_rank(self):
        self.case["order_sensitive"] = True
        self.assertFalse(compare(self.case, ["class", "rate"], list(reversed(self.case["expected_rows"])))[0])

    def test_no_percent_scaling_or_normalization(self):
        self.assertFalse(cell_equal(87.654, 0.87654, "ratio"))
        self.assertFalse(cell_equal(65.0, 78.0, "score"))

    def test_missing_extra_duplicate_columns(self):
        for columns in (["class"], ["class", "rate", "extra"], ["class", "class"]):
            self.assertFalse(compare(self.case, columns, self.case["expected_rows"])[0])

    def test_duplicates_not_lost(self):
        rows = [self.case["expected_rows"][0]] * 2
        self.assertFalse(compare(self.case, ["class", "rate"], rows)[0])

    def test_empty_still_requires_columns(self):
        self.case["expected_rows"] = []
        self.assertTrue(compare(self.case, ["class", "rate"], [])[0])
        self.assertFalse(compare(self.case, [], [])[0])

    def test_null_and_integer_rules(self):
        self.assertFalse(cell_equal(0, None, "score"))
        self.assertFalse(cell_equal(10.1, 10, "integer"))
        self.assertFalse(cell_equal(True, 1, "integer"))
        self.assertFalse(cell_equal(float("nan"), 0.0, "ratio"))

    def test_close_values_can_match_without_greedy_false_negative(self):
        case = copy.deepcopy(self.case)
        case["expected_rows"] = [{"class": "A", "rate": 0.8}, {"class": "A", "rate": 0.80008}]
        rows = [{"class": "A", "rate": 0.80004}, {"class": "A", "rate": 0.8}]
        self.assertTrue(compare(case, ["class", "rate"], rows)[0])

    def test_alias_review_cannot_repair_wrong_values(self):
        self.case.update({"case_id": "test", "actual_columns": ["班级同义名", "rate"],
                          "actual_rows": [{"班级同义名": "A", "rate": 0.4}, {"班级同义名": "B", "rate": 0.9}]})
        mapping = {"aliases": {"class": "班级同义名"}}
        self.assertFalse(review_case(self.case, mapping)[0])
        self.assertNotIn("班级同义名", self.case["columns"][0]["aliases"])

    def test_alias_review_rejects_invented_output_columns(self):
        self.case.update({"case_id": "test", "actual_columns": ["class", "rate"], "actual_rows": []})
        with self.assertRaises(ValueError):
            review_case(self.case, {"aliases": {"class": "nonexistent"}})


class SchoolBenchmarkOracleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c["case_id"]: c for c in gold_cases()}
        path = BASE_DIR / "data" / "databases" / "school_teaching" / "_example_queries.json"
        cls.seeds = {c["case_id"]: c for c in json.loads(path.read_text(encoding="utf-8"))}

    def test_raw_exam_averages_match_previously_fixed_fixture(self):
        expected = {r["class_name"]: r["average_score"]
                    for r in self.seeds["SCHOOL-001"]["expected_rows"]}
        for row in self.cases["EDU-001"]["expected_rows"]:
            self.assertAlmostEqual(row["平均分"], expected[row["班级名称"]], delta=0.00500001)

    def test_monthly_attendance_matches_previously_fixed_fixture(self):
        expected = {r["month"]: r["attendance_rate_pct"] / 100
                    for r in self.seeds["SCHOOL-002"]["expected_rows"]}
        for row in self.cases["EDU-009"]["expected_rows"]:
            self.assertAlmostEqual(row["出勤率"], expected[row["月份"]], delta=0.000050001)

    def test_known_population_and_absent_period(self):
        self.assertEqual(sum(r["学生人数"] for r in self.cases["EDU-033"]["expected_rows"]), 780)
        self.assertEqual(self.cases["EDU-008"]["expected_rows"], [{"考试场次": 0}])
        self.assertEqual(self.cases["EDU-016"]["expected_rows"], [])


if __name__ == "__main__":
    unittest.main()
