# 发行日历维护说明

网站由 GitHub Pages 从 `main` 根目录直接发布。改动 `index.html`、JSON 或 `img/` 后，推送到 `main` 即会触发 Pages 构建。

## 文件与数据来源

| 文件 | 用途 | 核对来源 |
| --- | --- | --- |
| `releases.json` | 本月和下月的游戏、平台、价格、Metacritic 评分 | Steam、PlayStation 香港、Nintendo 香港商店的游戏条目；`mc_url` 指向 Metacritic |
| `movies.json` | 本月和下月的电影、上映日期、豆瓣评分和人数 | 豆瓣“正在上映”“即将上映”及对应的 `sid` 条目 |
| `img/` | 已保存到仓库的电影海报和暂未显示的音乐图片 | 图片文件应与 JSON 引用一致 |
| `music.json` | 保留的音乐数据 | 当前页面不显示音乐标签，也不在下面的更新计划内 |

数据来源会变化；这些链接是核对入口，不代表商店或豆瓣保证长期提供自动抓取接口。游戏和电影的收录范围含人工筛选，仓库没有可复现的“所有值得收录作品”算法。

## 每天：刷新现有评分和 Steam 国区现价

GitHub Actions 的 `daily-scores.yml` 每天北京时间 18:00 运行，也可在 Actions 页面手动运行。脚本只读取现有 `mc_url`、电影 `sid` 和 Steam 游戏链接；不会增删作品、改日期或平台。Steam 使用官方商店接口的中国区人民币现价（含折扣），并同步顶层与平台内的价格；游戏编号或币种不符、价格未开放、接口失败时保留旧价。Metacritic 页面没有评分、豆瓣未开放评分或来源请求失败时，保留原分数。只有分数、豆瓣评分人数或 Steam 现价变化时才更新 JSON 并提交。多半来源请求失败时整次运行报错，避免把异常抓取当成正常结果。

本地核对：

```text
python scripts/check_data.py
python scripts/update_scores.py --dry-run
```

要实际写入数据，去掉 `--dry-run`。更新后再执行 `python scripts/check_data.py`，确认差异仅涉及评分、人数、Steam 价格和更新时间。

## 每月 1 日：重新整理两个月的清单

北京时间每月 1 日 09:00 的 Codex 定时维护任务负责重建当月与下月列表。维护者即使不使用该任务，也可按以下步骤手工接管：

1. 从上述商店和豆瓣的实际条目确认收录对象、日期、地区、平台、价格与详情链接。缺少可核对条目时不要猜测日期或价格。
2. 只保留当月、下月两个 `groups`。每条作品的 `date` 必须与 `year`、`month`、`day` 和所属月份一致。跨年时检查年份切换。游戏的不同平台可以有各自的发售日期。
3. 对原有评分保留可信值，再按每日评分来源复核；来源失效不能把有效评分改为空。
4. 核对封面。游戏封面按 `cover_img`（如果有）、Steam、Nintendo、PlayStation 的顺序尝试。外链必须返回真正的图片；仅有一个来源的作品尤其需要检查。电影 `poster` 可指向 `img/` 下的本地文件。
5. 运行 `python scripts/check_data.py`。网络条件允许时再运行 `python scripts/check_data.py --images`，或在 Actions 页面手动运行 `Check displayed images`；失败项需在浏览器中复核，因为图片源站可能拦截非浏览器请求。
6. 审阅 JSON 差异，确认没有无关字段被删除后提交并推送 `main`，检查 Pages 构建及线上内容。

`index.html` 从相对路径读取两份 JSON；切换数据结构前须同步修改页面。不要把第三方网站的登录凭据、Cookie 或访问令牌写入仓库。

## 已知限制

每月清单没有端到端自动采集程序，仍需核对和挑选；定时任务的可运行性依赖 Codex 主机与 GitHub 连接。每日评分依赖外部页面结构，来源改版时需更新 `scripts/update_scores.py`。图片检测用于发现疑似失效链接，不能代替浏览器中的视觉检查。
