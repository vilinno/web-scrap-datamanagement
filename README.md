# Web 数据管理课程项目

本项目用于完成《WEB 数据管理》课程的三个实验：

1. 实验一：豆瓣读书数据爬取。
2. 实验二：动态加载 / AJAX 反爬分析与数据采集。
3. 实验三：基于爬取数据的 Web 可视化应用。

## 快速运行

```powershell
python -m pip install -r requirements.txt
python src/spiders/douban_books.py --target 520 --pages 30
python src/spiders/bilibili_ajax.py --categories all,douga,music,knowledge
python src/data/clean_books.py
python -m uvicorn src.web.main:app --reload --host 127.0.0.1 --port 8000
```

浏览器访问：`http://127.0.0.1:8000`

## 目录说明

- `src/spiders`：实验 1 和实验 2 的爬虫代码。
- `src/data`：数据清洗、入库和统计脚本。
- `src/web`：FastAPI + Jinja2 + ECharts 可视化网站。
- `data/raw`：原始爬取数据。
- `data/processed`：清洗后的 CSV 和 SQLite 数据库。
- `notes`：中文实验报告和入门教程。
- `screenshots`：报告和验收用截图。

