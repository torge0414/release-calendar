# 发行日历维护说明

网站由 GitHub Pages 从 `main` 根目录直接发布。改动 `index.html`、JSON 或 `img/` 后，推送到 `main` 即会触发 Pages 构建。

## 文件与数据来源

| 文件 | 用途 | 核对来源 |
| --- | --- | --- |
| `releases.json` | 上月、本月和下月的游戏、平台、价格、Metacritic 评分 | Steam、PlayStation 香港、Nintendo 香港商店的游戏条目；`mc_url` 指向 Metacritic |
| `movies.json` | 上月、本月和下月的电影、上映日期、豆瓣评分和人数 | 豆瓣“正在上映”“即将上映”及对应的 `sid` 条目 |
| `img/` | 已保存到仓库的游戏封面、电影海报和暂未显示的音乐图片 | 图片文件应与 JSON 引用一致 |
| `music.json` | 保留的音乐数据 | 当前页面不显示音乐标签，也不在下面的更新计划内 |

数据来源会变化；这些链接是核对入口，不代表商店或豆瓣保证长期提供自动抓取接口。游戏是重点精选，不是全部新发售清单；先遵循 [GAME_SELECTION.md](GAME_SELECTION.md) 的用户确认规则及逐条复审决定，再核对商店资料。游戏和电影的收录范围含人工筛选，仓库没有可复现的“所有值得收录作品”算法。

## 游戏收录：排除旧作换平台再发行

以作品本身的首次发售为准，不把旧游戏后来登陆 Steam、PlayStation、Switch 或 Switch 2 的日期当成新作发售日期。排除跨平台移植、次世代升级版，以及只是加入既有内容的完全版、豪华版、合集、Encore Edition；不能只凭新平台商店日期、版名变化或已有高评分判断为新作。每月整理前，须查原版商店或发行商页面确认是否已在其他平台发售。

真正重新制作并由官方明确标注的重制版（remake），以及有首次发售新内容的重点新作／大型新扩展，须同时符合 GAME_SELECTION.md 的精选范围，不按“移植”误删；小体量独立作品默认不收录，只有用户指定才作为例外。不能把只有画质提升的 remaster 或升级通行证冒充重制新作。不确定是移植还是重制／新内容时先核对官方说明，仍不明确则请用户决定。新扩展与本体同捆的条目必须明确代表新扩展，不能用旧本体日期或旧本体评分冒充它。

2026 年 10 月 1 日已按用户要求剔除的旧作跨平台条目，后续不能因新平台开放预购又重新加入：

| 排除条目 | 新平台商品编号 | 原作已发售的核对来源 |
| --- | --- | --- |
| Marvel's Guardians of the Galaxy: Encore Edition | Nintendo 70010000119220 | [Steam 原作（2021 年）](https://store.steampowered.com/app/1088850/) |
| 剑星 完全版 | Nintendo 70010000123391 | [Steam 原作（2025 年已发售）](https://store.steampowered.com/app/3489700/) |
| 暗喻幻想：ReFantazio（NS2 版） | Nintendo 70010000105918 | [Steam 原作（2024 年）](https://store.steampowered.com/app/2679460/) |
| 皮克敏4 Nintendo Switch 2 Edition + 大家来挑战！当多虑检定 | Nintendo 70010000135062 | [Nintendo Switch 原作（2023 年）](https://www.nintendo.com/jp/switch/ampya/index.html) |

本规则只适用于游戏，不改变电影收录方式；上月保留策略也不能阻止用户明确要求的旧作移植清理。

## 每天：刷新现有评分和 Steam 国区现价

GitHub Actions 的 `daily-scores.yml` 每天北京时间 18:00 运行，也可在 Actions 页面手动运行。脚本只读取现有 `mc_url`、电影 `sid` 和 Steam 游戏链接；不会增删作品、改日期或平台。Steam 使用官方商店接口的中国区人民币现价（含折扣），并同步顶层与平台内的价格；游戏编号或币种不符、价格未开放、接口失败时保留旧价。Metacritic 页面没有评分、豆瓣未开放评分或来源请求失败时，保留原分数。只有分数、豆瓣评分人数或 Steam 现价变化时才更新 JSON 并提交。多半来源请求失败时整次运行报错，避免把异常抓取当成正常结果。

同捆版的 Steam 链接可使用官方 `sub` 页面，但必须提供 `steam_package_apps` 列出预期本体及扩展的编号；每日脚本先核对套装包含这些作品，再接受中国区人民币售价，避免把扩展包单卖价格当成完整版本价格。

本地核对：

```text
python scripts/check_data.py
python scripts/test_calendar.py
node scripts/test_month_tabs.js
node scripts/test_game_cover.js
python scripts/update_scores.py --dry-run
```

要实际写入数据，去掉 `--dry-run`。更新后再执行 `python scripts/check_data.py`，确认差异仅涉及评分、人数、Steam 价格和更新时间。

## 每月 1 日：保留上月，重新整理本月与下月

北京时间每月 1 日 09:00 的定时任务负责保留上月已发布列表、重建当月与下月列表；当前任务托管在 Kimi Code 会话（详见 HANDOVER.md §7B，含会话绑定与 7 天过期续建规则），此前先后由 Codex 桌面任务和 Kimi Work 任务承担，当时调度器使用 UTC，须核验实际下次执行为 UTC 01:00，避免误排为北京时间 17:00。维护者即使不使用该任务，也可按以下步骤手工接管：

1. 先阅读 GAME_SELECTION.md，按重点精选规则及已记录决定过滤游戏，再排除旧作换平台再发行，然后从商店和豆瓣的实际条目确认日期、地区、平台、价格与详情链接。不能仅凭商店有页面、知名 IP、售价或评分扩大名单，也不能在月度任务里重新加入已暂不收录的边界作品。缺少可核对条目时不要猜测日期或价格。
2. 只保留上月、当月、下月三个 `groups`，按月份升序。上月沿用已发布列表，不重新猜填历史记录；当月与下月按来源重新核对。每条作品的 `date` 必须与 `year`、`month`、`day` 和所属月份一致。跨年时检查年份切换。游戏的不同平台可以有各自的发售日期；PlayStation 的 UTC 时间转换为香港／北京时间后再写入日期。
3. 对原有评分保留可信值，再按每日评分来源复核；来源失效不能把有效评分改为空。
4. 核对封面。游戏封面按 `cover_img`（如果有）、Steam、Nintendo、PlayStation 的顺序尝试。优先使用对应作品／扩展的正常横版图，避免把比例大于 2.35 的套装横幅直接作为首选而导致留白、缩小。已验证的适配封面保存到 img/ 后由 cover_img 优先显示，不能在刷新价格时覆盖回不适配的套装横幅。外链必须返回真正的图片；仅有一个来源的作品尤其需要检查。电影 `poster` 可指向 `img/` 下的本地文件。
5. 运行 `python scripts/check_data.py`。网络条件允许时再运行 `python scripts/check_data.py --images`，或在 Actions 页面手动运行 `Check displayed images`；失败项需在浏览器中复核，因为图片源站可能拦截非浏览器请求。
6. 审阅 JSON 差异，确认没有无关字段被删除后提交并推送 `main`，检查 Pages 构建及线上内容。

`index.html` 从相对路径读取两份 JSON；切换数据结构前须同步修改页面。不要把第三方网站的登录凭据、Cookie 或访问令牌写入仓库。

## 已知限制

每月清单没有端到端自动采集程序，仍需核对和挑选；定时任务的可运行性依赖托管它的会话／主机与 GitHub 连接。每日评分依赖外部页面结构，来源改版时需更新 `scripts/update_scores.py`。图片检测用于发现疑似失效链接，不能代替浏览器中的视觉检查。
