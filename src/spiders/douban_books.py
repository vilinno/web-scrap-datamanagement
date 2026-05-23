"""实验一：豆瓣读书数据爬虫。

本脚本优先从豆瓣读书标签页采集最近出版/热门书籍信息，并保留可选的详情页解析能力。
爬取时采用较低频率访问、请求头模拟和异常重试，避免对目标网站造成压力。
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


TAGS = [
    "小说",
    "文学",
    "历史",
    "心理学",
    "社会学",
    "经济学",
    "科幻",
    "推理",
    "传记",
    "哲学",
    "互联网",
    "编程",
]


@dataclass
class BookItem:
    title: str
    author: str
    tag: str
    rating: str
    rating_count: str
    publisher: str
    publish_date: str
    price: str
    summary: str
    detail_url: str
    cover_url: str
    isbn: str = ""
    pages: str = ""


class DoubanBookSpider:
    """豆瓣读书标签页爬虫。"""

    def __init__(
        self,
        tags: Iterable[str],
        target: int,
        pages: int,
        delay: tuple[float, float],
        sort_type: str = "R",
        with_details: bool = False,
    ) -> None:
        self.tags = list(tags)
        self.target = target
        self.pages = pages
        self.delay = delay
        self.sort_type = sort_type
        self.with_details = with_details
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
                ),
                "Referer": "https://book.douban.com/",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

    def crawl(self) -> list[BookItem]:
        seen_urls: set[str] = set()
        books: list[BookItem] = []
        for tag in self.tags:
            for page in range(self.pages):
                if len(books) >= self.target:
                    return books
                start = page * 20
                url = f"https://book.douban.com/tag/{quote(tag)}?start={start}&type={self.sort_type}"
                html = self.fetch(url)
                items = self.parse_list_page(html, tag)
                if not items:
                    print(f"未解析到数据，停止标签 {tag} 第 {page + 1} 页")
                    break
                for item in items:
                    if item.detail_url in seen_urls:
                        continue
                    if self.with_details:
                        self.enrich_detail(item)
                    seen_urls.add(item.detail_url)
                    books.append(item)
                    if len(books) >= self.target:
                        return books
                self.sleep()
        return books

    def fetch(self, url: str, retry: int = 3) -> str:
        last_error: Exception | None = None
        for attempt in range(1, retry + 1):
            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
                if "检测到有异常请求" in response.text or "sec.douban.com" in response.url:
                    raise RuntimeError("豆瓣返回验证页面")
                return response.text
            except Exception as exc:  # noqa: BLE001 - 需要把网络异常统一重试
                last_error = exc
                print(f"请求失败({attempt}/{retry})：{url}，原因：{exc}")
                time.sleep(2 * attempt)
        raise RuntimeError(f"多次请求失败：{url}") from last_error

    def parse_list_page(self, html: str, tag: str) -> list[BookItem]:
        soup = BeautifulSoup(html, "lxml")
        books: list[BookItem] = []
        for node in soup.select("li.subject-item"):
            title_node = node.select_one("h2 a")
            pub_node = node.select_one(".pub")
            if not title_node or not pub_node:
                continue
            title = title_node.get("title") or title_node.get_text(" ", strip=True)
            detail_url = title_node.get("href", "").strip()
            cover_node = node.select_one(".pic img")
            rating_node = node.select_one(".rating_nums")
            people_node = node.select_one(".pl")
            summary_node = node.select_one("p")
            author, publisher, publish_date, price = parse_pub_line(pub_node.get_text(" ", strip=True))
            books.append(
                BookItem(
                    title=clean_text(title),
                    author=author,
                    tag=tag,
                    rating=rating_node.get_text(strip=True) if rating_node else "",
                    rating_count=parse_rating_count(people_node.get_text(" ", strip=True) if people_node else ""),
                    publisher=publisher,
                    publish_date=publish_date,
                    price=price,
                    summary=summary_node.get_text(" ", strip=True) if summary_node else "",
                    detail_url=detail_url,
                    cover_url=cover_node.get("src", "") if cover_node else "",
                )
            )
        return books

    def enrich_detail(self, item: BookItem) -> None:
        try:
            html = self.fetch(item.detail_url, retry=2)
            soup = BeautifulSoup(html, "lxml")
            info = soup.select_one("#info")
            if not info:
                return
            text = info.get_text("\n", strip=True)
            item.isbn = extract_field(text, "ISBN")
            item.pages = extract_field(text, "页数")
            self.sleep()
        except Exception as exc:  # noqa: BLE001 - 详情页失败不影响列表数据交付
            print(f"详情页解析失败：{item.detail_url}，原因：{exc}")

    def sleep(self) -> None:
        time.sleep(random.uniform(*self.delay))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_pub_line(line: str) -> tuple[str, str, str, str]:
    """解析豆瓣列表页的出版信息行。

    常见格式为：作者 / 译者 / 出版社 / 出版时间 / 价格。
    出版社、日期、价格在末尾相对稳定；作者部分可能包含多个斜杠。
    """

    parts = [clean_text(part) for part in line.split("/") if clean_text(part)]
    if not parts:
        return "", "", "", ""
    price = parts[-1] if parts else ""
    publish_date = parts[-2] if len(parts) >= 2 else ""
    publisher = parts[-3] if len(parts) >= 3 else ""
    author = " / ".join(parts[:-3]) if len(parts) >= 4 else parts[0]
    return author, publisher, publish_date, price


def parse_rating_count(text: str) -> str:
    match = re.search(r"(\d+)", text.replace(",", ""))
    return match.group(1) if match else ""


def extract_field(text: str, name: str) -> str:
    pattern = rf"{re.escape(name)}\s*:\s*([^\n]+)"
    match = re.search(pattern, text)
    return clean_text(match.group(1)) if match else ""


def save_csv(items: list[BookItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(items[0]).keys()))
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def save_sqlite(items: list[BookItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS douban_books_raw")
        conn.execute(
            """
            CREATE TABLE douban_books_raw (
                title TEXT,
                author TEXT,
                tag TEXT,
                rating TEXT,
                rating_count TEXT,
                publisher TEXT,
                publish_date TEXT,
                price TEXT,
                summary TEXT,
                detail_url TEXT PRIMARY KEY,
                cover_url TEXT,
                isbn TEXT,
                pages TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO douban_books_raw
            VALUES (:title, :author, :tag, :rating, :rating_count, :publisher,
                    :publish_date, :price, :summary, :detail_url, :cover_url, :isbn, :pages)
            """,
            [asdict(item) for item in items],
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="爬取豆瓣读书标签页数据")
    parser.add_argument("--target", type=int, default=520, help="目标记录数")
    parser.add_argument("--pages", type=int, default=30, help="每个标签最多爬取页数")
    parser.add_argument("--tags", default=",".join(TAGS), help="逗号分隔的标签列表")
    parser.add_argument("--min-delay", type=float, default=0.6, help="最小请求间隔秒数")
    parser.add_argument("--max-delay", type=float, default=1.5, help="最大请求间隔秒数")
    parser.add_argument("--sort-type", default="R", choices=["R", "T", "S"], help="豆瓣标签页排序方式：R 为出版时间较新")
    parser.add_argument("--with-details", action="store_true", help="是否访问详情页补充 ISBN/页数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    spider = DoubanBookSpider(
        tags=tags,
        target=args.target,
        pages=args.pages,
        delay=(args.min_delay, args.max_delay),
        sort_type=args.sort_type,
        with_details=args.with_details,
    )
    items = spider.crawl()
    if not items:
        raise SystemExit("未爬取到数据，请检查网络或目标网站返回内容。")
    csv_path = RAW_DIR / "douban_books_raw.csv"
    db_path = RAW_DIR / "douban_books_raw.sqlite"
    save_csv(items, csv_path)
    save_sqlite(items, db_path)
    print(f"完成：共保存 {len(items)} 条豆瓣读书记录")
    print(f"CSV：{csv_path}")
    print(f"SQLite：{db_path}")


if __name__ == "__main__":
    main()
