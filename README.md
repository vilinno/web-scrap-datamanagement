# Web 数据管理课程项目

本项目用于完成《WEB 数据管理》课程的三个实验：

1. 实验一：豆瓣读书数据爬取。
2. 实验二：动态加载 / AJAX 反爬分析与数据采集。
3. 实验三：基于爬取数据的 Web 可视化应用。

## 快速运行

如果只想打开已经生成好的数据展示页面，可以先安装依赖，然后直接启动 Web 服务：

```powershell
python -m pip install -r requirements.txt
python -m uvicorn src.web.main:app --reload --host 127.0.0.1 --port 8000
```

浏览器访问：`http://127.0.0.1:8000`

如果需要从头重新生成数据，按下面顺序执行：

```powershell
python -m pip install -r requirements.txt
python src/spiders/douban_books.py --target 620 --pages 8 --sort-type R
python src/spiders/bilibili_ajax.py --categories all,douga,music,knowledge
python src/data/clean_books.py
python -m uvicorn src.web.main:app --reload --host 127.0.0.1 --port 8000
```

## 测试

```powershell
python tests/test_project.py
```

测试会检查豆瓣数据规模、B 站反爬数据、SQLite 入库结果、FastAPI 首页和 JSON 接口。

## Web 应用架构

本项目采用轻量级前后端分层架构：

- 数据层：`data/processed/douban_books_clean.csv` 和 `data/processed/web_data_management.sqlite` 保存清洗后的书籍数据。
- 后端层：FastAPI 读取 CSV，提供 `/` 页面和 `/api/summary`、`/api/charts`、`/api/books` 三个 JSON 接口。
- 模板层：Jinja2 渲染首页 HTML，并把类型、年份等筛选选项传给页面。
- 前端层：原生 HTML/CSS/JavaScript 构建仪表盘界面，ECharts 绘制饼图、柱状图、折线图和散点图。
- 交互方式：用户在浏览器中选择类型、最低评分、出版年份，前端重新请求 API 并刷新指标、图表和榜单。

## 目录说明

- `src/spiders`：实验 1 和实验 2 的爬虫代码。
- `src/data`：数据清洗、入库和统计脚本。
- `src/web`：FastAPI + Jinja2 + ECharts 可视化网站。
- `data/raw`：原始爬取数据。
- `data/processed`：清洗后的 CSV 和 SQLite 数据库。
- `notes`：中文实验报告和入门教程。
- `screenshots`：报告和验收用截图。
