"""实验二：B 站排行榜 AJAX 数据采集。

该页面的可视数据由浏览器调用 JSON 接口获得。脚本通过构造请求头访问公开接口，
用于说明“直接解析 HTML 不完整，需要定位 AJAX 接口”的反爬处理思路。
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"


CATEGORY_RIDS = {
    "all": 0,
    "douga": 1,
    "music": 3,
    "game": 4,
    "knowledge": 36,
    "tech": 188,
    "life": 160,
}


@dataclass
class BilibiliVideo:
    category: str
    rank: int
    bvid: str
    title: str
    owner: str
    tname: str
    view: int
    danmaku: int
    reply: int
    favorite: int
    coin: int
    share: int
    like: int
    duration: int
    pubdate: int
    url: str


def browser_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }


def request_json(url: str) -> dict:
    """先用 requests 访问；若触发 SSL/风控，再降级到 curl 保留浏览器式请求。

    B 站接口偶尔会对 Python TLS 指纹返回 -352 或直接断开连接。这里保留失败证据，
    再使用系统 curl 复现浏览器请求头，便于实验二报告说明反爬处理过程。
    """

    evidence_path = RAW_DIR / "bilibili_request_evidence.txt"
    try:
        response = requests.get(url, headers=browser_headers(), timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") == 0:
            return payload
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            f"requests 返回异常：{payload}\n请求地址：{url}\n", encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001 - 实验二需要记录各种请求失败现象
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            f"requests 请求失败：{type(exc).__name__}: {exc}\n请求地址：{url}\n", encoding="utf-8"
        )

    with tempfile.NamedTemporaryFile(prefix="bili_cookie_", suffix=".txt", delete=False) as cookie_file:
        cookie_path = cookie_file.name
    subprocess.run(
        [
            "curl.exe",
            "-L",
            "--max-time",
            "25",
            "-c",
            cookie_path,
            "-A",
            browser_headers()["User-Agent"],
            "https://www.bilibili.com/",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    command = [
        "curl.exe",
        "-L",
        "--max-time",
        "25",
        "-b",
        cookie_path,
        "-A",
        browser_headers()["User-Agent"],
        "-H",
        f"Referer: {browser_headers()['Referer']}",
        "-H",
        f"Origin: {browser_headers()['Origin']}",
        "-H",
        f"Accept: {browser_headers()['Accept']}",
        "-H",
        f"Accept-Language: {browser_headers()['Accept-Language']}",
        url,
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def fetch_ranking(category: str) -> list[BilibiliVideo]:
    rid = CATEGORY_RIDS[category]
    url = f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all"
    payload = request_json(url)
    if payload.get("code") != 0:
        raise RuntimeError(f"B 站接口返回异常：{payload}")
    result: list[BilibiliVideo] = []
    for index, item in enumerate(payload.get("data", {}).get("list", []), start=1):
        stat = item.get("stat", {})
        owner = item.get("owner", {})
        result.append(
            BilibiliVideo(
                category=category,
                rank=index,
                bvid=item.get("bvid", ""),
                title=item.get("title", ""),
                owner=owner.get("name", ""),
                tname=item.get("tnamev2") or item.get("tname", ""),
                view=int(stat.get("view", 0) or 0),
                danmaku=int(stat.get("danmaku", 0) or 0),
                reply=int(stat.get("reply", 0) or 0),
                favorite=int(stat.get("favorite", 0) or 0),
                coin=int(stat.get("coin", 0) or 0),
                share=int(stat.get("share", 0) or 0),
                like=int(stat.get("like", 0) or 0),
                duration=int(item.get("duration", 0) or 0),
                pubdate=int(item.get("pubdate", 0) or 0),
                url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
            )
        )
    return result


def save_csv(items: list[BilibiliVideo], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(items[0]).keys()))
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def save_json(items: list[BilibiliVideo], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_sqlite(items: list[BilibiliVideo], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS bilibili_ranking")
        conn.execute(
            """
            CREATE TABLE bilibili_ranking (
                category TEXT,
                rank INTEGER,
                bvid TEXT,
                title TEXT,
                owner TEXT,
                tname TEXT,
                view INTEGER,
                danmaku INTEGER,
                reply INTEGER,
                favorite INTEGER,
                coin INTEGER,
                share INTEGER,
                like INTEGER,
                duration INTEGER,
                pubdate INTEGER,
                url TEXT,
                PRIMARY KEY(category, bvid)
            )
            """
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO bilibili_ranking
            VALUES (:category, :rank, :bvid, :title, :owner, :tname, :view,
                    :danmaku, :reply, :favorite, :coin, :share, :like,
                    :duration, :pubdate, :url)
            """,
            [asdict(item) for item in items],
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="采集 B 站排行榜 AJAX 数据")
    parser.add_argument(
        "--categories",
        default="all,douga,music,knowledge",
        help=f"逗号分隔分类，可选：{','.join(CATEGORY_RIDS)}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    categories = [item.strip() for item in args.categories.split(",") if item.strip()]
    unknown = [category for category in categories if category not in CATEGORY_RIDS]
    if unknown:
        raise SystemExit(f"未知分类：{','.join(unknown)}")
    videos: list[BilibiliVideo] = []
    for category in categories:
        videos.extend(fetch_ranking(category))
    if not videos:
        raise SystemExit("未获取到 B 站数据")
    save_csv(videos, RAW_DIR / "bilibili_ranking.csv")
    save_json(videos, RAW_DIR / "bilibili_ranking.json")
    save_sqlite(videos, RAW_DIR / "bilibili_ranking.sqlite")
    print(f"完成：共保存 {len(videos)} 条 B 站排行榜记录")


if __name__ == "__main__":
    main()
