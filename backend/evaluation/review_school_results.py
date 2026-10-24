"""Audit explicit synonymous output labels without changing the raw baseline."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from evaluation.run_school_benchmark import compare


def review_case(case: dict, mapping: dict) -> tuple[bool, str]:
    reference = copy.deepcopy(case)
    specs = {s["name"]: s for s in reference["columns"]}
    for canonical, actual in mapping["aliases"].items():
        if canonical not in specs or actual not in case["actual_columns"]:
            raise ValueError(f"Invalid reviewed column: {case['case_id']} {canonical}: {actual}")
        specs[canonical]["aliases"].append(actual)
    return compare(reference, case["actual_columns"], case["actual_rows"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("mappings", type=Path)
    args = parser.parse_args()
    raw_bytes = args.report.read_bytes()
    report = json.loads(raw_bytes)
    if not report["complete"]:
        raise ValueError("Only a completed batch can be reviewed")
    mappings = json.loads(args.mappings.read_text(encoding="utf-8"))
    rows = report["cases"]
    if set(mappings) - {r["case_id"] for r in rows}:
        raise ValueError("Unknown case ID in alias review")
    decisions = []
    for row in rows:
        success = row["result_correct"]
        reason = row["comparison_reason"]
        mapping = mappings.get(row["case_id"])
        if mapping:
            if success or not mapping.get("basis"):
                raise ValueError("Only originally failed cases with documented rationale may be reviewed")
            success, reason = review_case(row, mapping)
        decisions.append({
            "case_id": row["case_id"], "category": row["category"], "query": row["query"],
            "strict_correct": row["result_correct"], "reviewed_correct": success,
            "reviewed_aliases": mapping, "comparison_reason": reason,
        })
    count = len(rows)
    correct = sum(d["reviewed_correct"] for d in decisions)
    adjusted = sum(d["reviewed_correct"] and not d["strict_correct"] for d in decisions)
    infrastructure = [r for r in rows if "Arrearage" in (r["error"] + str((r.get("intent") or {}).get("reason", "")))]
    retrieval_rows = [r for r in rows if r["retrieval_completed"]]
    retrieval_gold = sum(len(r["gold_fields"]) for r in retrieval_rows)
    retrieval_tp = sum(r["true_positive"] for r in retrieval_rows)
    attempted_sql = [r for r in rows if r["sql_attempt_count"]]
    sql_success = sum(r["sql_execution_success"] for r in attempted_sql)
    first_success = sum(r["first_sql_execution_success"] for r in attempted_sql)
    correct_given_sql = sum(d["reviewed_correct"] for d in decisions
                            if next(r for r in rows if r["case_id"] == d["case_id"])["sql_execution_success"])
    summary = {
        "case_count": count, "strict_correct_count": report["summary"]["correct_count"],
        "strict_result_accuracy": report["summary"]["result_accuracy"],
        "alias_review_count": len(mappings), "alias_only_corrected_count": adjusted,
        "reviewed_correct_count": correct, "reviewed_result_accuracy": correct / count,
        "infrastructure_blocked_count": len(infrastructure),
        "infrastructure_blocked_ids": [r["case_id"] for r in infrastructure],
        "capability_benchmark_complete": not infrastructure,
        "retrieval_completed_count": len(retrieval_rows),
        "retrieval_completed_gold_fields": retrieval_gold,
        "schema_recall_given_completed_retrieval": retrieval_tp / retrieval_gold if retrieval_gold else None,
        "sql_attempted_case_count": len(attempted_sql),
        "sql_success_given_attempted_sql": sql_success / len(attempted_sql) if attempted_sql else None,
        "first_sql_success_given_attempted_sql": first_success / len(attempted_sql) if attempted_sql else None,
        "reviewed_accuracy_given_executed_sql": correct_given_sql / sql_success if sql_success else None,
    }
    output = args.report.with_name(args.report.stem + "_reviewed.json")
    body = {"source_report": str(args.report), "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "mapping_sha256": hashlib.sha256(args.mappings.read_bytes()).hexdigest(),
            "review_method": "Agent inspected SQL projections for explicitly recorded synonymous labels; same comparator, same rows and tolerances; no model rerun, no data edits, no numeric corrections. Not independent human annotation.",
            "summary": summary, "original_summary": report["summary"], "cases": decisions}
    output.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# 学校教学问数评测结果及列名复核", "", f"批次：{report['metadata']['run_id']}，已尝试{count}题。以下全题指标包含服务失败。",
             "", "| 指标 | 结果 |", "|---|---|",
             f"| 字段级Schema召回率micro | {report['summary']['schema_recall_micro']:.2%}（{report['summary']['recalled_field_count']}/{report['summary']['gold_field_count']}） |",
             f"| 字段级Schema召回率macro | {report['summary']['schema_recall_macro']:.2%} |",
             f"| SQL执行成功率 | {report['summary']['sql_execution_success_rate']:.2%}（{report['summary']['sql_success_count']}/{count}） |",
             f"| 结果正确率：严格列名自动判定 | {summary['strict_result_accuracy']:.2%}（{summary['strict_correct_count']}/{count}） |",
             f"| 结果正确率：同义列名复核后 | {summary['reviewed_result_accuracy']:.2%}（{correct}/{count}） |",
             ""]
    if infrastructure:
        lines += ["## 模型账户欠费：本轮不能作为完整能力基线", "",
                  f"40题均已尝试，但有{len(infrastructure)}题出现明确的Arrearage欠费错误；仅{sql_success}题产生并成功执行了SQL。全题指标把服务失败计入分母，反映本次实际端到端可用情况，不能直接解释为SQL生成能力。模型可用后需要另开批次完整重跑，保留本次原始报告。",
                  "", "| 可用阶段的条件统计 | 结果 |", "|---|---|",
                  f"| 已完成召回的{len(retrieval_rows)}题字段召回micro | {summary['schema_recall_given_completed_retrieval']:.2%}（{retrieval_tp}/{retrieval_gold}） |",
                  f"| 已产生SQL的{len(attempted_sql)}题最终执行成功率 | {summary['sql_success_given_attempted_sql']:.2%}（{sql_success}/{len(attempted_sql)}） |",
                  f"| 已产生SQL的题目首条SQL成功率 | {summary['first_sql_success_given_attempted_sql']:.2%}（{first_success}/{len(attempted_sql)}） |",
                  f"| 成功执行SQL的题目结果正确率（同义列名复核后） | {summary['reviewed_accuracy_given_executed_sql']:.2%}（{correct_given_sql}/{sql_success}） |",
                  "", "条件统计只描述相应已完成阶段的子集，存在样本选择限制，不能替代全部40题结果。成绩、考勤各完成8题，作业完成4题；知识点和教学安排各8题均未得到有效SQL结果。",
                  "", "应用对部分模型不可用请求返回completed状态的兜底文本，因此页面状态completed也不能当成成功回答。统计SQL成功只依据真实数据库执行记录。",
                  "", "## 本轮暴露的问题", "",
                  "7题首条SQL错误地带有school_teaching.前缀，而当前DuckDB将表注册在默认schema；应用已有修复机制移除前缀后成功。该问题增加模型调用及耗时，尚未修改应用行为或提示词。",
                  "", "原始Schema召回存在漏字段；SQL生成可借助完整授权目录补足，因此不能以子集SQL成功率100%推断字段召回充分。", ""]
    lines += ["## 同义列名复核", "",
             "原始报告未覆盖所有同义列名。下面逐项核对生成SQL投影的含义，只补充有证据的列名对应关系，再使用相同的比较器检查全部数据；不改变数值、行数、排序、比率或容差，也不重新调用模型。原始报告、失败判定及SQL完整保留。这是代理复核，未经独立人工标注。",
             "", "| 题号 | 复核映射 | SQL含义依据 | 数据再比较 |", "|---|---|---|---|"]
    for d in decisions:
        m = d["reviewed_aliases"]
        if m:
            names = "；".join(f"{k} → {v}" for k, v in m["aliases"].items())
            lines.append(f"| {d['case_id']} | {names} | {m['basis']} | {d['comparison_reason']} |")
    lines += ["", "## 复核后仍不一致的题目", ""]
    failed = [d for d in decisions if not d["reviewed_correct"]]
    infrastructure_ids = {r["case_id"] for r in infrastructure}
    lines.extend(f"- {d['case_id']}：{'模型服务欠费，未完成有效SQL查询' if d['case_id'] in infrastructure_ids else d['comparison_reason']}；{d['query']}" for d in failed)
    if not failed:
        lines.append("本批未发现剩余结构化结果差异；不代表在其他提问或真实数据上都能正确。")
    lines += ["", "## 使用边界", "",
              "本次为单次运行的40道固定设计题，涵盖单校合成数据16张表、67个不同字段。问题明确了输出列和部分计算口径，参考答案为SQL oracle。SQL生成还获得完整授权字段目录，召回率与SQL正确率应分开理解；本结果不能外推为生产环境准确率。",
              "", f"运行前后代码和数据哈希一致：{report['metadata']['application_and_data_unchanged']}。",
              f"SQL首条即成功：{report['summary']['first_sql_success_count']}/{count}；页面返回状态：{report['summary']['response_status_counts']}。",
              "原始报告包含逐题标准/生成SQL、标准/实际结果、缺失字段及耗时。复核JSON包含原报告SHA256、映射SHA256与每题判定，便于追溯。", ""]
    output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    print(output)


if __name__ == "__main__":
    main()
