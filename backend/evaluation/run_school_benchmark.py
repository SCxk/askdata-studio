"""Reproducible evaluation of the unmodified, full school query workflow.

Run from backend: .venv/Scripts/python.exe -m evaluation.run_school_benchmark
Gold annotations and expected results are only used outside the workflow.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import threading
import time
from typing import Any
import uuid

from app.config import BASE_DIR, settings
from app.model_client import ModelClient
from app.querying.duckdb_engine import DuckDbEngine
from app.retrieval import SchemaIndex
from app.security import AccessController
from app.workflows.query_graph import QueryWorkflow
from evaluation.school_cases import definitions


LOCAL = threading.local()


def cell_equal(actual: Any, expected: Any, kind: str) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if kind in {"integer", "score", "ratio"}:
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            return False
        if not math.isfinite(float(actual)):
            return False
        tolerance = {"integer": 1e-8, "score": 0.005000001, "ratio": 0.000050001}[kind]
        return math.isclose(actual, expected, abs_tol=tolerance, rel_tol=1e-10)
    if kind == "month":
        # A month can also be returned as its first day's ISO date/timestamp.
        return str(actual) == str(expected) or str(actual) in {
            str(expected) + "-01", str(expected) + "-01T00:00:00",
            str(expected) + "-01 00:00:00",
        }
    return str(actual) == str(expected)


def compare(case: dict[str, Any], columns: list[str], rows: list[dict[str, Any]]) -> tuple[bool, str]:
    specs = case["columns"]
    if len(columns) != len(specs) or len(set(columns)) != len(columns):
        return False, "返回列数与要求不一致或存在重名列"
    mapped: list[str] = []
    for spec in specs:
        options = [c for c in columns if c in spec["aliases"]]
        if len(options) != 1 or options[0] in mapped:
            return False, f"缺少或无法识别列：{spec['name']}"
        mapped.append(options[0])
    expected = case["expected_rows"]
    if len(rows) != len(expected):
        return False, f"行数不一致：实际{len(rows)}，标准{len(expected)}"

    def row_equal(actual: dict[str, Any], reference: dict[str, Any]) -> bool:
        return all(c in actual and cell_equal(actual[c], reference[s["name"]], s["kind"])
                   for c, s in zip(mapped, specs))

    if case["order_sensitive"]:
        matched = all(row_equal(a, e) for a, e in zip(rows, expected))
    else:
        # Bipartite matching preserves duplicate rows and handles overlapping tolerances.
        edges = [[j for j, e in enumerate(expected) if row_equal(a, e)] for a in rows]
        owners: dict[int, int] = {}

        def match(i: int, seen: set[int]) -> bool:
            for j in edges[i]:
                if j in seen:
                    continue
                seen.add(j)
                if j not in owners or match(owners[j], seen):
                    owners[j] = i
                    return True
            return False

        matched = all(match(i, set()) for i in range(len(rows)))
    return matched, "结果一致" if matched else "数值、记录内容或要求的排名顺序不一致"


def fingerprints() -> dict[str, str]:
    paths = list((BASE_DIR / "app").rglob("*.py"))
    paths += list((BASE_DIR / "app" / "skills").rglob("*.md"))
    paths += list((BASE_DIR / "data" / "databases" / "school_teaching").glob("*.csv"))
    paths += [BASE_DIR / "data" / "databases" / "school_teaching" / "_schema.json",
              BASE_DIR / "data" / "schema_store.json", Path(__file__),
              Path(__file__).with_name("school_cases.py")]
    return {str(p.relative_to(BASE_DIR)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def gold_cases() -> list[dict[str, Any]]:
    cases = definitions()
    engine = DuckDbEngine()
    scope = AccessController().resolve("demo_school")
    with engine.connect("school_teaching") as connection:
        for case in cases:
            sql = engine._validate_sql("school_teaching", case["gold_sql"], scope)
            cursor = connection.execute(sql)
            names = [c[0] for c in cursor.description]
            assert names == [s["name"] for s in case["columns"]], case["case_id"]
            raw = cursor.fetchall()
            assert len(raw) < 200, "Oracle must not be truncated by page row limit"
            case["expected_rows"] = [dict(zip(names, (engine._json_value(v) for v in row))) for row in raw]
            assert compare(case, names, case["expected_rows"])[0], case["case_id"]
    return cases


def run_case(case: dict[str, Any], run_id: str) -> dict[str, Any]:
    started = time.perf_counter()
    client = ModelClient(settings)
    if not hasattr(LOCAL, "index"):
        LOCAL.index = SchemaIndex(client, settings)
        LOCAL.index.ensure_built()
    index = LOCAL.index
    index.model_client = client
    workflow = QueryWorkflow(client, index, settings)
    task_id = f"{run_id}-{case['case_id']}-{uuid.uuid4().hex[:8]}"
    payload = {
        "task_id": task_id, "query": case["query"], "session_id": task_id,
        "workspace": {}, "access_scope": AccessController().resolve("demo_school").public(),
        "route_context": "", "short_term_context": "", "recent_result_context": "",
        "analysis_context": "", "analysis_sources": [], "tool_facts": {},
        "execution_log": [], "tool_calls": [], "clarification": None,
    }
    state: dict[str, Any] = {}
    error = ""
    try:
        state = workflow.graph.invoke(payload, config=workflow.run_config(task_id))
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        state = dict(workflow.graph.get_state(workflow.run_config(task_id)).values or {})
    retrieval = state.get("retrieval") or {}
    retrieved = sorted({h["doc_id"] for h in retrieval.get("hits", [])})
    expanded = sorted({f["id"] for f in (state.get("schema_graph") or {}).get("fields", [])})
    gold = set(case["gold_fields"])
    execution = state.get("mcp_execution") or {}
    success = bool(execution.get("success"))
    correct, reason = compare(case, execution.get("columns") or [], execution.get("rows") or []) if success else (False, error or str(execution.get("error") or "未成功执行SQL"))
    trace = state.get("mcp_tool_trace") or []
    queries = [t for t in trace if t.get("tool") == "query_school_teaching"]
    result = state.get("result") or {}
    return {
        **case, "retrieved_fields": retrieved, "expanded_fields": expanded,
        "missing_fields": sorted(gold - set(retrieved)),
        "true_positive": len(gold & set(retrieved)),
        "expanded_true_positive": len(gold & set(expanded)),
        "schema_recall": len(gold & set(retrieved)) / len(gold),
        "expanded_recall": len(gold & set(expanded)) / len(gold),
        "retrieval_completed": bool(retrieval), "extraction": state.get("extraction"),
        "intent": state.get("intent"), "generated_sql": execution.get("sql", ""),
        "sql_execution_success": success,
        "first_sql_execution_success": bool(queries and queries[0].get("result", {}).get("success")),
        "sql_attempt_count": len(queries), "result_correct": correct,
        "comparison_reason": reason, "actual_columns": execution.get("columns") or [],
        "actual_rows": execution.get("rows") or [], "tool_trace": trace,
        "response_status": result.get("status"), "clarification": state.get("clarification"),
        "error": error, "elapsed_seconds": round(time.perf_counter() - started, 3),
        "model_metrics": client.metrics(),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    fields = sum(len(r["gold_fields"]) for r in rows)
    successful = sum(r["sql_execution_success"] for r in rows)
    correct = sum(r["result_correct"] for r in rows)
    return {
        "case_count": count, "gold_field_count": fields,
        "recalled_field_count": sum(r["true_positive"] for r in rows),
        "schema_recall_micro": sum(r["true_positive"] for r in rows) / fields if fields else 0,
        "schema_recall_macro": statistics.fmean(r["schema_recall"] for r in rows) if count else 0,
        "expanded_recall_micro": sum(r["expanded_true_positive"] for r in rows) / fields if fields else 0,
        "retrieval_completed": sum(r["retrieval_completed"] for r in rows),
        "sql_success_count": successful, "sql_execution_success_rate": successful / count if count else 0,
        "first_sql_success_count": sum(r["first_sql_execution_success"] for r in rows),
        "correct_count": correct, "result_accuracy": correct / count if count else 0,
        "result_accuracy_given_executed_sql": correct / successful if successful else 0,
        "response_status_counts": dict(Counter(r["response_status"] for r in rows)),
        "exception_count": sum(bool(r["error"]) for r in rows),
        "mean_seconds": statistics.fmean(r["elapsed_seconds"] for r in rows) if count else 0,
    }


def save(output: Path, metadata: dict[str, Any], rows: list[dict[str, Any]], total: int) -> None:
    rows = sorted(rows, key=lambda r: r["case_id"])
    summary = summarize(rows)
    by_category = {c: summarize([r for r in rows if r["category"] == c])
                   for c in dict.fromkeys(r["category"] for r in rows)}
    body = {"metadata": metadata, "complete": len(rows) == total, "summary": summary,
            "by_category": by_category, "cases": rows}
    temp = output.with_suffix(".json.tmp")
    temp.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(output)
    with output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as stream:
        cols = ["case_id", "category", "difficulty", "query", "schema_recall", "expanded_recall",
                "sql_execution_success", "first_sql_execution_success", "result_correct",
                "comparison_reason", "elapsed_seconds", "response_status", "error", "generated_sql"]
        writer = csv.DictWriter(stream, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# 学校教学问数评测报告", "", f"运行：{metadata['run_id']}；进度：{len(rows)}/{total}。",
             "", "## 核心指标", "", "| 指标 | 结果 |", "|---|---|",
             f"| 字段级Schema召回率（micro） | {summary['schema_recall_micro']:.2%}（{summary['recalled_field_count']}/{summary['gold_field_count']}） |",
             f"| 字段级Schema召回率（macro） | {summary['schema_recall_macro']:.2%} |",
             f"| 补充关联键后的召回率（micro） | {summary['expanded_recall_micro']:.2%} |",
             f"| SQL执行成功率 | {summary['sql_execution_success_rate']:.2%}（{summary['sql_success_count']}/{len(rows)}） |",
             f"| 首条SQL执行成功 | {summary['first_sql_success_count']}/{len(rows)} |",
             f"| 查询结果正确率 | {summary['result_accuracy']:.2%}（{summary['correct_count']}/{len(rows)}） |",
             f"| 已执行SQL中的结果正确率 | {summary['result_accuracy_given_executed_sql']:.2%} |",
             f"| 平均单题耗时（含模型调用） | {summary['mean_seconds']:.1f}秒 |",
             "", "## 分类结果", "", "| 类别 | 题数 | 字段召回micro | SQL成功 | 结果正确 |", "|---|---:|---:|---:|---:|"]
    for category, s in by_category.items():
        lines.append(f"| {category} | {s['case_count']} | {s['schema_recall_micro']:.2%} | {s['sql_success_count']} | {s['correct_count']} |")
    lines += ["", "## 评测口径与边界", "",
              "- 使用当前完整QueryWorkflow：意图识别、模型提取检索词、混合召回、Schema图、MCP执行及结果说明；不向模型传入标准SQL、字段、检索词或结果。使用独立空会话、学校账户权限。",
              "- 标准字段为预先编写标准SQL实际引用的物理字段（含筛选、分组、聚合和关联键），由SQL AST解析；同题去重，跨题累计。COUNT实体也显式引用实体ID。等价SQL可能使用不同关联路径，字段召回反映相对于该参考路径的覆盖。",
              "- micro为所有题召回必要字段总数/必要字段总数，macro为各题召回率均值。仅统计最终检索hits，自动补充关联键另报，不将完整表目录计入召回。检索前失败按零召回纳入。",
              "- SQL成功指最终数据库执行成功，包含应用内最多3次工具调用的修复；澄清、路由错误或异常均保留在总题数分母。结果说明状态另存，不与SQL执行混淆。",
              "- 结果正确率以SQL返回结构化数据为准，必须满足全部要求列、全部行及重复次数。列名允许预定义中英文别名；排名严格检查顺序，其他分组忽略行序。整数严格比较，分数绝对容差0.005，比率绝对容差0.00005；不接受百分数与小数倍数差异。空结果也检查列。",
              "- 每题参考SQL先在同一数据快照上执行，结果少于200行避免页面截断。标准结果是SQL oracle，未经独立人工双人标注；本批40题为人工设计的固定题集，非随机抽样，不据此推断生产准确率。",
              "- 学校SQL生成器还会获得授权范围内完整字段目录，因此SQL正确率不能解释为仅靠检索的效果。",
              "- 数据为单校合成数据，只有一个学期；不覆盖多轮上下文、并发压力、安全越权、真实脏数据，也未单独评价文字解释与图表正确率。具体模型、阈值、代码与CSV哈希见JSON metadata；不记录密钥。",
              "", "## 失败案例", ""]
    for r in rows:
        if r["result_correct"]:
            continue
        lines += [f"### {r['case_id']}：{r['query']}", "", f"判定：{r['comparison_reason']}",
                  f"SQL成功：{r['sql_execution_success']}；字段召回：{r['schema_recall']:.2%}。", "",
                  "生成SQL：", "```sql", r["generated_sql"] or "-- 未生成", "```",
                  "参考SQL：", "```sql", r["gold_sql"], "```", ""]
    if all(r["result_correct"] for r in rows):
        lines.append("本次未出现结果不一致案例。")
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-only", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = gold_cases()
    if args.limit:
        cases = cases[:args.limit]
    case_path = BASE_DIR / "evaluation" / "cases" / "school_teaching_v1.json"
    case_path.parent.mkdir(parents=True, exist_ok=True)
    if not args.limit:
        case_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validated {len(cases)} gold cases; {sum(len(c['gold_fields']) for c in cases)} field references", flush=True)
    if args.gold_only:
        return
    if not settings.api_key:
        raise RuntimeError("Model API key is not configured")
    index = SchemaIndex()
    index.ensure_built()
    run_id = datetime.now(timezone.utc).strftime("school_%Y%m%dT%H%M%SZ")
    output = args.output or BASE_DIR / "evaluation" / "results" / f"{run_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"run_id": run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "settings": settings.public_status(), "workers": args.workers,
                "fingerprints_before": fingerprints(),
                "case_sha256": hashlib.sha256(json.dumps(cases, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    rows: list[dict[str, Any]] = []
    save(output, metadata, rows, len(cases))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_case, case, run_id): case for case in cases}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            save(output, metadata, rows, len(cases))
            print(f"[{len(rows)}/{len(cases)}] {row['case_id']} recall={row['schema_recall']:.3f} sql={row['sql_execution_success']} correct={row['result_correct']} {row['elapsed_seconds']:.1f}s {row['comparison_reason']}", flush=True)
    metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["fingerprints_after"] = fingerprints()
    metadata["application_and_data_unchanged"] = metadata["fingerprints_before"] == metadata["fingerprints_after"]
    save(output, metadata, rows, len(cases))
    print(json.dumps(summarize(rows), ensure_ascii=False), flush=True)
    print(output, flush=True)


if __name__ == "__main__":
    main()
