"""实验三：Web 数据可视化应用。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "douban_books_clean.csv"
WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Web 数据管理可视化系统")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")


@lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"请先运行数据清洗脚本：python src/data/clean_books.py")
    df = pd.read_csv(DATA_PATH)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce").fillna(0).astype(int)
    df["publish_year"] = pd.to_numeric(df["publish_year"], errors="coerce")
    return df


def apply_filters(
    df: pd.DataFrame,
    tag: str | None = None,
    min_rating: float | None = None,
    year: int | None = None,
) -> pd.DataFrame:
    result = df.copy()
    if tag:
        result = result[result["tag"] == tag]
    if min_rating is not None:
        result = result[result["rating"].fillna(0) >= min_rating]
    if year is not None:
        result = result[result["publish_year"] == year]
    return result


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    df = load_data()
    tags = sorted(df["tag"].dropna().unique().tolist())
    years = sorted(df["publish_year"].dropna().astype(int).unique().tolist(), reverse=True)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "tags": tags,
            "years": years,
        },
    )


@app.get("/api/summary")
def summary(
    tag: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    year: int | None = Query(default=None),
) -> dict:
    df = apply_filters(load_data(), tag=tag, min_rating=min_rating, year=year)
    return {
        "total": int(len(df)),
        "avg_rating": round(float(df["rating"].mean()), 2) if len(df) else 0,
        "avg_rating_count": round(float(df["rating_count"].mean()), 1) if len(df) else 0,
        "publisher_count": int(df["publisher"].nunique()) if len(df) else 0,
        "tag_count": int(df["tag"].nunique()) if len(df) else 0,
    }


@app.get("/api/charts")
def charts(
    tag: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    year: int | None = Query(default=None),
) -> dict:
    df = apply_filters(load_data(), tag=tag, min_rating=min_rating, year=year)
    rating_bins = pd.cut(
        df["rating"].dropna(),
        bins=[0, 6, 7, 8, 9, 10],
        labels=["6分以下", "6-7分", "7-8分", "8-9分", "9分以上"],
        include_lowest=True,
    ).value_counts().sort_index()
    tag_counts = df["tag"].value_counts().head(12)
    year_counts = df.dropna(subset=["publish_year"])["publish_year"].astype(int).value_counts().sort_index()
    publisher_counts = df["publisher"].value_counts().head(10)
    top_books = (
        df.sort_values(["rating", "rating_count"], ascending=[False, False])
        .head(20)[["title", "author", "tag", "rating", "rating_count", "publisher", "publish_year", "detail_url"]]
        .fillna("")
        .to_dict(orient="records")
    )
    scatter = (
        df.dropna(subset=["rating"])
        .sort_values("rating_count", ascending=False)
        .head(120)[["title", "rating", "rating_count", "tag"]]
        .to_dict(orient="records")
    )
    return {
        "rating_distribution": {
            "labels": rating_bins.index.astype(str).tolist(),
            "values": rating_bins.astype(int).tolist(),
        },
        "tag_distribution": {
            "labels": tag_counts.index.tolist(),
            "values": tag_counts.astype(int).tolist(),
        },
        "year_trend": {
            "labels": year_counts.index.astype(str).tolist(),
            "values": year_counts.astype(int).tolist(),
        },
        "publisher_top": {
            "labels": publisher_counts.index.tolist(),
            "values": publisher_counts.astype(int).tolist(),
        },
        "top_books": top_books,
        "scatter": scatter,
    }


@app.get("/api/books")
def books(
    tag: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    year: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    df = apply_filters(load_data(), tag=tag, min_rating=min_rating, year=year)
    return (
        df.sort_values(["rating", "rating_count"], ascending=[False, False])
        .head(limit)[["title", "author", "tag", "rating", "rating_count", "publisher", "publish_year", "price", "detail_url"]]
        .fillna("")
        .to_dict(orient="records")
    )
