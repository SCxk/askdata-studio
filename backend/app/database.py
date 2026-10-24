from __future__ import annotations

"""加载各业务数据库的表、字段和表关系定义。"""

import json
import csv
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parents[1] / "data" / "databases"
SCHEMA_PATH = DATABASE_ROOT / "school_teaching" / "_schema.json"
SCHEMA_PATHS = [SCHEMA_PATH]
DATABASE_SCHEMAS: dict[str, dict] = {}


def _load_schema() -> tuple[list[dict], list[dict]]:
    tables, relations = [], []
    for path in SCHEMA_PATHS:
        if not path.exists():
            raise FileNotFoundError(f"未找到业务Schema：{path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        DATABASE_SCHEMAS[str(payload["database"])] = payload
        tables.extend(payload.get("tables") or [])
        relations.extend(payload.get("relations") or [])
    return tables, relations


SCHEMA, RELATIONS = _load_schema()


def physical_table_name(table: dict) -> str:
    return str(table.get("name") or table["id"])


def database_query_context(database: str, allowed_tables: set[str] | frozenset[str]) -> dict:
    payload = DATABASE_SCHEMAS.get(database, {})
    context = {
        "scenario": payload.get("scenario", database),
        "metric_definitions": payload.get("metric_definitions", {}),
    }
    if context["metric_definitions"]:
        if f"{database}.terms" in allowed_tables:
            with (DATABASE_ROOT / database / "terms.csv").open(encoding="utf-8-sig", newline="") as handle:
                terms = list(csv.DictReader(handle))
            context["available_terms"] = terms
            context["default_term"] = max(terms, key=lambda term: term["start_date"]) if terms else None
        # Domain rules need the full permitted catalog to resolve multi-table metrics.
        context["tables"] = [
            {
                "name": table["name"], "description": table["description"],
                "fields": [
                    {
                        "name": field["name"], "description": field.get("description", ""),
                        "type": field.get("source_type", field["type"]),
                        "samples": (field.get("data_profile") or {}).get("sample_values", []),
                    }
                    for field in table["fields"]
                ],
            }
            for table in payload.get("tables", []) if table["id"] in allowed_tables
        ]
        context["relations"] = [
            relation for relation in payload.get("relations", [])
            if relation["left_table"] in allowed_tables and relation["right_table"] in allowed_tables
        ]
    return context
