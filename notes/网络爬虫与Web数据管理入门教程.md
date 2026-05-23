# 网络爬虫与 Web 数据管理入门教程

## 1. Web 数据管理流程

一个完整的 Web 数据管理项目通常包含五步：

1. 明确目标：确定要研究的问题和需要采集的字段。
2. 采集数据：编写爬虫获取 HTML、JSON 或文件数据。
3. 清洗数据：去重、补缺失、统一字段类型、派生新字段。
4. 存储数据：保存为 CSV、JSON、SQLite、MySQL 等格式。
5. 展示数据：使用 Web 页面、图表或报告展示分析结果。

## 2. 爬虫基础

最简单的爬虫由请求、解析、保存三部分组成。

```python
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}
html = requests.get("https://example.com", headers=headers).text
soup = BeautifulSoup(html, "lxml")
title = soup.select_one("title").get_text(strip=True)
print(title)
```

常用模块：

- `requests`：发送 HTTP 请求。
- `BeautifulSoup`：解析 HTML。
- `lxml`：高性能解析器。
- `csv`：保存 CSV 文件。
- `sqlite3`：保存轻量级关系数据库。
- `pandas`：清洗和分析表格数据。

## 3. 目标网站分析方法

分析网站时建议按以下顺序进行：

1. 打开网页，观察数据是否直接显示在页面上。
2. 右键查看网页源代码，搜索目标字段。
3. 如果源代码中能找到数据，优先解析 HTML。
4. 如果源代码中找不到数据，打开开发者工具 Network 面板。
5. 筛选 XHR/Fetch 请求，寻找返回 JSON 数据的接口。
6. 记录接口 URL、请求方法、请求头、参数和返回字段。

## 4. 常见反爬虫障碍

常见反爬虫方式包括：

- User-Agent 校验：不允许默认 Python 请求头。
- Referer 校验：要求请求来自特定页面。
- Cookie 校验：需要先访问首页或登录页获得 Cookie。
- AJAX 动态加载：初始 HTML 中没有完整数据。
- 请求频率限制：访问过快会返回验证码或空数据。
- IP 限制：同一 IP 大量请求后被封禁。
- 字体反爬：页面数字通过自定义字体映射显示。

实验中应避免暴力绕过验证码、登录权限和付费内容。课程项目只采集公开页面和公开接口数据。

## 5. 数据清洗要点

爬取到的数据通常不能直接分析，需要清洗：

```python
import pandas as pd

df = pd.read_csv("data/raw/douban_books_raw.csv")
df = df.drop_duplicates(subset=["detail_url"])
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce").fillna(0).astype(int)
```

常见清洗任务：

- 去除重复记录。
- 将评分、人数、价格转换为数值。
- 从日期文本中提取年份。
- 填充缺失作者、出版社或分类。
- 删除明显异常数据。

## 6. SQLite 入门

SQLite 适合课程项目和小型 Web 应用，不需要单独安装数据库服务。

```python
import sqlite3

with sqlite3.connect("data/processed/web_data_management.sqlite") as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS books(title TEXT, rating REAL)")
    conn.execute("INSERT INTO books VALUES (?, ?)", ("示例书籍", 8.5))
```

使用 SQLite 的优点：

- 文件即数据库，便于提交和复制。
- 支持 SQL 查询和索引。
- 可以被 Python、Web 后端和数据分析工具读取。

## 7. FastAPI 与 ECharts 可视化

FastAPI 负责提供页面和 JSON 接口，ECharts 负责在浏览器中绘制图表。

后端接口示例：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/summary")
def summary():
    return {"total": 620, "avg_rating": 8.10}
```

前端请求示例：

```javascript
const data = await fetch("/api/summary").then((res) => res.json());
document.querySelector("#total").textContent = data.total;
```

## 8. 项目运行顺序

```powershell
python -m pip install -r requirements.txt
python src/spiders/douban_books.py --target 620 --pages 8 --sort-type R
python src/spiders/bilibili_ajax.py --categories all,douga,music,knowledge
python src/data/clean_books.py
python -m uvicorn src.web.main:app --reload --host 127.0.0.1 --port 8000
```

运行后访问：`http://127.0.0.1:8000`

## 9. 实验报告写作建议

报告不要只写“运行成功”，应包含：

- 目标网站名称和 URL。
- 网页结构或 AJAX 接口分析。
- 使用的开发工具和模块。
- 操作步骤和关键命令。
- 数据字段、保存格式和数据规模。
- 遇到的问题和解决办法。
- 图表截图、图表含义和分析结论。

