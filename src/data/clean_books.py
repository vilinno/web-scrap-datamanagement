"""实验三数据准备：清洗豆瓣读书原始数据并生成 SQLite 数据库。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "douban_books_raw.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_CSV = PROCESSED_DIR / "douban_books_clean.csv"
PROCESSED_DB = PROCESSED_DIR / "web_data_management.sqlite"


def normalize_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def normalize_price(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def clean() -> pd.DataFrame:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"缺少原始数据文件：{RAW_CSV}")
    df = pd.read_csv(RAW_CSV, dtype=str).fillna("")
    df = df.drop_duplicates(subset=["detail_url"]).copy()
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce").fillna(0).astype(int)
    df["publish_year"] = df["publish_date"].apply(normalize_year)
    df["price_number"] = df["price"].apply(normalize_price)
    df["author"] = df["author"].replace("", "未知作者")
    df["publisher"] = df["publisher"].replace("", "未知出版社")
    df["tag"] = df["tag"].replace("", "未分类")
    df["summary_length"] = df["summary"].str.len()
    df = df.sort_values(["publish_year", "rating_count"], ascending=[False, False], na_position="last")
    return df


def save(df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_CSV, index=False, encoding="utf-8-sig")
    with sqlite3.connect(PROCESSED_DB) as conn:
        df.to_sql("books", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_books_tag ON books(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_books_year ON books(publish_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_books_rating ON books(rating)")


def main() -> None:
    df = clean()
    save(df)
    print(f"清洗完成：{len(df)} 条记录")
    print(f"CSV：{PROCESSED_CSV}")
    print(f"SQLite：{PROCESSED_DB}")


if __name__ == "__main__":
    main()

