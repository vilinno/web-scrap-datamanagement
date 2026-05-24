"""项目验收测试。

运行方式：
    python tests/test_project.py

该脚本不重新爬取网站，只检查已经生成的数据文件、清洗结果和 Web API。
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.web.main import app


def test_douban_processed_data() -> None:
    path = ROOT / "data" / "processed" / "douban_books_clean.csv"
    assert path.exists(), f"缺少清洗后的豆瓣数据：{path}"
    df = pd.read_csv(path)
    required_columns = {
        "title",
        "author",
        "tag",
        "rating",
        "rating_count",
        "publisher",
        "publish_date",
        "publish_year",
        "detail_url",
    }
    assert len(df) >= 500, "实验一数据量应不少于 500 条"
    assert required_columns.issubset(df.columns), "豆瓣数据字段不完整"
    assert df["tag"].nunique() >= 3, "实验三需要多个类型维度"
    assert len(df[df["publish_year"] >= 2025]) >= 500, "最近出版数据量不足"
    assert pd.to_numeric(df["rating"], errors="coerce").dropna().between(0, 10).all(), "评分范围异常"
    assert df["detail_url"].is_unique, "详情页 URL 应去重"


def test_bilibili_ajax_data() -> None:
    path = ROOT / "data" / "raw" / "bilibili_ranking.csv"
    evidence = ROOT / "data" / "raw" / "bilibili_request_evidence.txt"
    assert path.exists(), f"缺少实验二 B 站数据：{path}"
    assert evidence.exists(), "缺少反爬请求证据文件"
    df = pd.read_csv(path)
    assert len(df) >= 300, "实验二采集记录数不足"
    assert df["category"].nunique() >= 4, "排行榜分类不足"
    assert {"title", "owner", "view", "like", "url"}.issubset(df.columns), "B 站字段不完整"


def test_sqlite_database() -> None:
    db_path = ROOT / "data" / "processed" / "web_data_management.sqlite"
    assert db_path.exists(), f"缺少 SQLite 数据库：{db_path}"
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        tag_count = conn.execute("SELECT COUNT(DISTINCT tag) FROM books").fetchone()[0]
    assert count >= 500, "SQLite 中书籍记录数不足"
    assert tag_count >= 3, "SQLite 中类型维度不足"


def test_web_api() -> None:
    client = TestClient(app)
    index = client.get("/")
    assert index.status_code == 200
    assert "豆瓣读书数据可视化" in index.text

    summary = client.get("/api/summary").json()
    assert summary["total"] >= 500
    assert summary["tag_count"] >= 3

    charts = client.get("/api/charts").json()
    assert {"rating_distribution", "tag_distribution", "year_trend", "publisher_top", "scatter"}.issubset(charts)
    assert len(charts["tag_distribution"]["labels"]) >= 3

    filtered = client.get("/api/books?tag=小说&min_rating=8&limit=5")
    assert filtered.status_code == 200
    assert isinstance(filtered.json(), list)


def run_all() -> None:
    tests = [
        test_douban_processed_data,
        test_bilibili_ajax_data,
        test_sqlite_database,
        test_web_api,
    ]
    for test in tests:
        test()
        print(f"通过：{test.__name__}")
    print("全部测试通过。")


if __name__ == "__main__":
    run_all()
