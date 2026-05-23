const charts = {
  rating: echarts.init(document.getElementById("ratingChart")),
  tag: echarts.init(document.getElementById("tagChart")),
  year: echarts.init(document.getElementById("yearChart")),
  publisher: echarts.init(document.getElementById("publisherChart")),
  scatter: echarts.init(document.getElementById("scatterChart")),
};

const tagFilter = document.getElementById("tagFilter");
const ratingFilter = document.getElementById("ratingFilter");
const ratingValue = document.getElementById("ratingValue");
const yearFilter = document.getElementById("yearFilter");
const resetButton = document.getElementById("resetButton");

function queryString() {
  const params = new URLSearchParams();
  if (tagFilter.value) params.set("tag", tagFilter.value);
  if (Number(ratingFilter.value) > 0) params.set("min_rating", ratingFilter.value);
  if (yearFilter.value) params.set("year", yearFilter.value);
  return params.toString();
}

async function fetchJson(path) {
  const qs = queryString();
  const response = await fetch(qs ? `${path}?${qs}` : path);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

function updateSummary(data) {
  document.getElementById("totalMetric").textContent = data.total;
  document.getElementById("ratingMetric").textContent = data.avg_rating;
  document.getElementById("peopleMetric").textContent = data.avg_rating_count;
  document.getElementById("publisherMetric").textContent = data.publisher_count;
}

function barOption(title, seriesName, data, color) {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 20, top: 24, bottom: 62 },
    xAxis: {
      type: "category",
      data: data.labels,
      axisLabel: { rotate: data.labels.length > 6 ? 28 : 0, color: "#66706b" },
    },
    yAxis: { type: "value", axisLabel: { color: "#66706b" } },
    series: [{ name: seriesName, type: "bar", data: data.values, itemStyle: { color } }],
  };
}

function updateCharts(data) {
  charts.rating.setOption({
    tooltip: { trigger: "item" },
    color: ["#2f7d62", "#77a889", "#c9892b", "#d45f43", "#783f8e"],
    series: [
      {
        name: "书籍数量",
        type: "pie",
        radius: ["42%", "70%"],
        data: data.rating_distribution.labels.map((name, index) => ({
          name,
          value: data.rating_distribution.values[index],
        })),
      },
    ],
  });
  charts.tag.setOption(barOption("类型分布", "数量", data.tag_distribution, "#2f7d62"));
  charts.year.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 20, top: 24, bottom: 42 },
    xAxis: { type: "category", data: data.year_trend.labels, axisLabel: { color: "#66706b" } },
    yAxis: { type: "value", axisLabel: { color: "#66706b" } },
    series: [{ name: "出版数量", type: "line", smooth: true, data: data.year_trend.values, color: "#c9892b" }],
  });
  charts.publisher.setOption(barOption("热门出版社", "数量", data.publisher_top, "#195d49"));
  charts.scatter.setOption({
    tooltip: {
      trigger: "item",
      formatter: (item) => `${item.data[2]}<br/>评分：${item.data[0]}<br/>评价人数：${item.data[1]}`,
    },
    grid: { left: 64, right: 28, top: 24, bottom: 48 },
    xAxis: { type: "value", name: "评分", min: 0, max: 10, axisLabel: { color: "#66706b" } },
    yAxis: { type: "value", name: "评价人数", axisLabel: { color: "#66706b" } },
    series: [
      {
        type: "scatter",
        symbolSize: (value) => Math.max(8, Math.min(28, Math.log(value[1] + 1) * 2.2)),
        data: data.scatter.map((item) => [item.rating, item.rating_count, item.title, item.tag]),
        itemStyle: { color: "#2f7d62", opacity: 0.72 },
      },
    ],
  });
}

function updateTable(rows) {
  const tbody = document.getElementById("bookTable");
  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td><a href="${row.detail_url}" target="_blank" rel="noreferrer">${row.title}</a></td>
          <td>${row.author}</td>
          <td>${row.tag}</td>
          <td>${row.rating || ""}</td>
          <td>${row.rating_count}</td>
          <td>${row.publisher}</td>
          <td>${row.publish_year || ""}</td>
        </tr>
      `,
    )
    .join("");
}

async function refresh() {
  ratingValue.textContent = ratingFilter.value;
  const [summary, chartData, books] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson("/api/charts"),
    fetchJson("/api/books"),
  ]);
  updateSummary(summary);
  updateCharts(chartData);
  updateTable(books);
}

[tagFilter, ratingFilter, yearFilter].forEach((control) => {
  control.addEventListener("input", refresh);
});

resetButton.addEventListener("click", () => {
  tagFilter.value = "";
  ratingFilter.value = "0";
  yearFilter.value = "";
  refresh();
});

window.addEventListener("resize", () => Object.values(charts).forEach((chart) => chart.resize()));
refresh();

