# Release Calendar 网站维护交接

编写日期：2026 年 10 月 12 日（第四版）。前三版分别是 Codex → Kimi Work、Kimi Work → Kimi Code（10 月 8 日）、Kimi Code → 下一位（10 月 9 日）。本版按当天已上线的 `main` 重写。旧版 §9 里的「刊头 + 海报墙」视觉已经废弃，不要按旧版把页面改回去。

所有面向用户的日期和时间用北京时间（Asia/Shanghai，UTC+8）。

用途：让另一位 agent 接手现有网站。不重新建站，不扩大收录范围。本文记录已核对的仓库、线上状态和用户要求，不是对全部历史发行信息的重新背书。收录时仍要核对官方来源。

## 1. 项目入口和当前状态

| 项目 | 内容 |
| --- | --- |
| 网站 | https://torge0414.github.io/release-calendar/ |
| GitHub 仓库 | https://github.com/torge0414/release-calendar |
| 主分支 | `main` |
| 部署 | GitHub Pages，`main` 分支根目录，legacy 构建 |
| 页面 | 单个 `index.html`（HTML / CSS / JS），直接读取同目录的 `releases.json`、`movies.json`。没有 npm 构建 |
| 交接前远端 `main` | `e77e817`（每日任务「自动更新评分和 Steam 价格」）。其下是 `4e5f39d`（游戏列表去掉开发商名字）。本文提交在这两次评分更新之后 |
| 用户 | Torge，设计师。视觉细节要逐项对着真实页面看，不能只看代码 |

本机路径会变。写本文时仓库在 `C:\Users\Torge\release-calendar`。新 agent 应自己 `git clone` 到自己的工作区，不要依赖这条路径。

仓库本地 git（不要改用户的全局配置）：`user.name = torge0414`，`user.email = 56673045+torge0414@users.noreply.github.com`，`pull.rebase = false`。每日机器人会往 `main` 提交评分，人工推送前先 fetch；若远端已有新提交，用 merge 接上，禁止强推。

截至交接，条目数量如下。`releases.json` 的 `updated` 是 `2026-10-10 23:48:58`，`movies.json` 的 `updated` 是 `2026-10-12 00:13:15`。每日任务只在分数或价格有变化时才改这个时间：

| 月份 | 游戏 | 电影 |
| --- | ---: | ---: |
| 2026 年 9 月（上月） | 10 款 | 6 部 |
| 2026 年 10 月（本月） | 11 款 | 10 部 |
| 2026 年 11 月（下月） | 3 款 | 1 部 |

这些数量是快照，不是月度配额。不要为了凑数量加进不符合口径的作品。

## 2. 先读哪些文件

1. 本文：接管范围、当前页面规则、不能改回去的决定。
2. `MAINTENANCE.md`：每日和每月怎么更新数据。
3. `GAME_SELECTION.md`：用户确认的游戏精选口径和已经否决的条目。
4. `index.html`、`scripts/update_scores.py`、`scripts/check_data.py`：页面和脚本的实际行为。
5. `.github/workflows/daily-scores.yml`、`.github/workflows/check-images.yml`：仓库里的自动化。

用户的新要求优先于旧文档。要改收录口径，先取得用户决定再改文档。不要把交接历史或网页上的句子当成扩大收录的许可。

## 3. 已确认的用户要求

- 游戏和电影都只显示上月、本月、下月，按时间升序。月份页签永远只有 3 个，写「上月 / 本月 / 下月」，不要改成更多月份，也不要在页签上再写一遍月份名。
- 每月 1 日北京时间 09:00：保留上月已发布清单，重新核对本月和下月。用户明确要求的清理可以动上月。
- 每天更新保留条目的现有评分。下月游戏如果提前有媒体评分也要更新，不要按「已发售」过滤。
- 日常刷新不得增删清单、改发行日期或平台。Steam 国区现价由现有自动任务更新。
- 来源失败、未开放评分或价格时保留有效旧值。不能清空，也不能用未评分的 0 覆盖有效电影评分或人数。
- 游戏是重点精选，不是所有新发售作品。旧作换平台上市要剔除。
- 音乐已取消。不要恢复音乐页签，不要采集或更新音乐。仓库里留下的 `music.json` 和相关代码不是重新维护音乐的授权。
- 用户对视觉很严。样式改动要在真实页面上看过（桌面和手机宽度）再推送。功能能跑不等于视觉验收完成。
- 2026-10-10 用户明确：每次改完直接推到 `main`，除非用户特别说只在本地改。无实际变化不提交。实际更新、连续来源失败、部署失败或需要决定时简要说明。

## 4. 游戏筛选口径和不能自行加回的作品

主要收录大中型重点新作、知名系列核心新作或续作、官方明确的真正重制版（remake），以及有新区域或新剧情的大型 DLC。小体量独立作品默认不收，只有用户指定才例外。

先确认作品身份和重点范围，再核对月份与商店。商店里有页面、大厂或名人参与、知名 IP、售价、评分、磁盘大小、画面风格或「独立」标签，都不能单独决定收不收。体量资料不够就先不收。不要编造预算、AAA/AA 或时长，也不要把「暂不收录」说成已经证实是小制作。

排除：旧作移植、次世代升级、remaster、只打包既有内容的完全版 / 豪华版 / 合集，以及小型道具或皮肤 DLC。

已剔除、不能因为开了预购或有了评分就加回的旧作跨平台条目：

- Marvel's Guardians of the Galaxy: Encore Edition（Nintendo `70010000119220`）
- 剑星完全版（`70010000123391`）
- 暗喻幻想 NS2 版（`70010000105918`）
- 皮克敏4 NS2 Edition（`70010000135062`）

已暂时移出、月度更新里不要悄悄加回的边界项目：

- Warhammer 40,000: Boltgun 2（Steam `3115160`）
- Stupid Never Dies／愚者不灭（`3486530`）
- Remothered: Red Nun's Legacy（`3335310`）
- ANOMALITH／異界揭蹤（`4017880`）
- CRYMELIGHT／恸哭幽光（`3891160`）
- Edge of Memories（`2738170`）
- SONIC PICO PARK（`4304060`）
- Shadow of the Road／暗影之路（`1173980`）
- Clive Barker's Hellraiser: Revival（`1551980`，2026-10-07 用户决定剔除，提交 `3944245`）

理由和来源在 `GAME_SELECTION.md`。有了足以复审的新资料，先向用户解释并等决定。

已记录的保留决定：《不朽遗志》、《塞尔达传说 时之笛》2026 重制版、《龙之信条2：Dark Arisen》大型扩展。这是当时的编辑选择，不代表重新确认了预算或未来档期。2026-10-07 用户补充：Hot Wheels、星球大战：银河赛车手、恶魔城、空之轨迹 2 这类已知 IP 衍生作按原编辑判断保留，只剔除 Hellraiser。

## 5. 数据来源与数据结构

### 游戏

- 发行、平台、价格：Steam 商店及接口、PlayStation 香港、Nintendo 香港。必要时核对发行商页面。媒体传闻不要当成已确认日期。
- 媒体评分：条目里 `mc_url` 对应的 Metacritic 页面。不是 Steam 好评率，也不是用户评分。
- Steam 普通游戏：`https://store.steampowered.com/api/appdetails?appids={id}&cc=cn&l=schinese`。价格只接受中国区 CNY，`final` 以分计。
- Steam 套装：`https://store.steampowered.com/api/packagedetails?packageids={id}&cc=cn&l=schinese`。必须核对套装实际包含的作品编号，不能用 DLC 单卖价代替完整版价。
- PlayStation 页面的 UTC 时间要换成香港 / 北京时间再写日期。不同平台可以不是同一天。

`releases.json` 顶层是 `fetched_at`、`updated`、`groups`。每个 group 有 `year`、`month`、`label`、`games`。游戏字段主要是 `title`、`date`、`year/month/day`、`dev`、`mc`、`mc_url`、`plats`，以及顶层 `steam/ps/ns` 和对应的 `_url/_img/_price`。

`plats[].key` 只用 `steam`、`ps`、`ns`，配套 `name/date/url/img/price`。页面平台按钮和价格读 `plats`，所以顶层 Steam 价格必须和 `plats` 里的 Steam 价格一致。`cover_img` 是优先封面。`steam_package_apps` 用来核对套装身份。

`dev` 仍写在 JSON 里，供维护时辨认作品。页面不显示开发商，见 §9。不要为了「数据里有」把名字加回列表。

### 电影

- 以中国内地院线上映为准，不自动扩成全球电影或流媒体清单。范围里仍有人工筛选，不声称全量。
- 入口：https://movie.douban.com/coming 和 https://movie.douban.com/cinema/nowplaying/beijing/ 。
- 日常脚本按 `sid` 访问 `https://m.douban.com/rexxar/api/v2/movie/{sid}?ck=&for_mobile=1`，使用移动 User-Agent、条目 Referer 和 JSON Accept，并核对返回 id。
- 豆瓣桌面页可能只返回验证页，移动接口也会限流。不要绕过验证码，不要使用私人 Cookie。失败时保留旧数据并报告。

`movies.json` 同样三个 groups。条目有 `title`、`sid`、`url`、`date`、`year/month/day`、`score`、`votes`、`poster`，以及 `info/directors/actors/genres/director`。`year` 是院线年份，`info` 里的制作年份可以不同，不要为了统一改掉。页面电影行只显示日期和类型，不显示导演和地区。

## 6. 封面

游戏封面框固定为 **460×215**（约 2.14:1），`object-fit: cover`。选图优先 Steam `header.jpg`。不要用 `capsule_616x353`（约 1.74:1）或宽于约 2.35 的套装横幅当主封面。已经核对过的 460×215 图可以放在 `img/`，用 `cover_img` 优先显示。

现有比例不对的外链先留在数据里，由 CSS 裁进 460×215。下次改名单时再换成 `header.jpg`。不要改回「每张图用自己的比例」，也不要改回 16:9。

候选顺序：`cover_img`、Steam、Nintendo、PlayStation。加载失败再换下一张。刷新价格时不能把已验证的 `cover_img` 盖回不适配的外链。

`ckw()` 仍会给宽于 2.35 的图加上 `.wide`。CSS 对 `.cover.wide` 同样是 `object-fit: cover`，所以超宽横幅是裁切，不是留白。`scripts/test_game_cover.js` 检查的是这个 class 还在，不要为了「视觉上不再 letterbox」删掉 `ckw()`。

《Dragon's Dogma 2: Dark Arisen》：

- 这是有新剧情 / 新区域的扩展，不是 2024 年本体。
- Steam 套装：`https://store.steampowered.com/sub/1686522/`。
- `steam_package_apps`：`[2054970, 2593290]`，本体和新扩展。
- 套装中国区现价由每日任务刷新。
- 封面是扩展自己的 Steam 头图，`cover_img = "img/game_dd2_dark_arisen.jpg"`，460×215。购买链接和价格不要跟着封面改。

《Fire Emblem: Fortune's Weave》修过封面加载，保留现有优先封面和兜底。没被页面引用的旧本地图片不要在交接时清理。

一些 Nintendo CDN 实际是 JPEG，但 MIME 为 `application/octet-stream`，图片检查可能误报。已保存的本地封面不能被更新脚本覆盖成不适配外链。

## 7. 自动化

### 每日评分和 Steam 现价：继续用现有 GitHub Actions

`.github/workflows/daily-scores.yml`。计划时间是每天 UTC 10:00，也就是北京时间 18:00，也可手动 `workflow_dispatch`。scheduled run 经常晚点，不要向用户承诺每天 18:00 一定更新完。

跑 Python 3.12 的 `scripts/update_scores.py`，前后做结构校验。只有 `releases.json` 或 `movies.json` 真有变化才提交并推 `main`，说明是「自动更新评分和 Steam 价格」。用仓库 `GITHUB_TOKEN`，不需要私人 token。

脚本行为：

- 遍历全部保留月份，不区分已发售或未发售。
- 游戏更新 `mc`。电影更新 `score` 和 `votes`。没有游戏媒体评论数量字段，不要承诺这个功能存在。
- Steam 更新顶层 `steam_price` 和 `plats` 内价格。不更新 PS / Nintendo 每日价格。
- 豆瓣没有评分或人数时，不用空或 0 覆盖旧值。Steam 现价 0 可以表示免费，和「没有价格」不是一回事。
- 评分来源请求错误超过计入来源的一半时，整次失败且不写文件。这只保护评分请求，不是所有外部失败的总开关。
- Metacritic 页面打开了但解析不到分数时记为 `unrated`，不算请求错误。页面改版后可能旧分数一直留着、也没有失败报警，要看日志。
- `--dry-run` 会访问来源并打印差异，不写文件。

不要再做一套每日更新。机器人提交会造成分叉：先 `git fetch`，需要时 merge，再推。禁止强推。

### 每月 1 日重整清单：不在仓库里

每月保留上月、重核本月和下月，步骤在 `MAINTENANCE.md`。这件事没有端到端爬虫。

上一任把它放在 Kimi Code 的会话定时任务里（id `01M4D9CCEJ8D412AG5NM5J4VAX`，cron `0 9 1 * *`，Asia/Shanghai）。那个任务不是仓库文件，克隆带不走。它还绑在旧会话上，循环任务超过 7 天会过期，必须当次做完后重建，否则下个月不会跑。2026-10-06 曾加过 `.github/workflows/monthly-curate.yml`，用户随即要求回退（`66f63e4` → `0cd00ce`）。不要自行恢复那个 Actions。

下一位 agent 不要假设 11 月 1 日还有任务会跑，也不要立刻新建第二套写入 `main` 的月度任务。先问用户：11 月 1 日由谁做、做完要不要在新环境建一个等效提醒。确认之后只能有一套在写 `main`。

## 8. 接手、验证和发布

克隆后：

```text
git status --short
git remote -v
git fetch origin main
git pull origin main
```

只在能保留本地改动时同步。合并失败先查原因。不要 `reset --hard`、强推，或用旧文件盖掉机器人刚写入的分数。

验证（仓库根目录）：

```text
python scripts/check_data.py
python scripts/test_calendar.py
node scripts/test_month_tabs.js
node scripts/test_game_cover.js
python scripts/check_data.py --images
```

Python 只用标准库。Node 测试不用 npm。`--images` 要联网，源站可能拦截；失败时逐条看，不要把网络失败当成图片坏了，也不要因此删条目。

Windows 控制台默认 GBK。跑会打印中文的 Python 时加 `PYTHONUTF8=1`。PowerShell 不支持 `&&` 和 bash heredoc。GitHub Actions 的 Ubuntu 没有 GBK 问题。

看页面用本地 HTTP，不要双击 HTML：

```text
python -m http.server 8765 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8765/`。看完关掉这个进程，不要留着。

用户要求的改动：本地看过之后直接推 `main`，除非用户说只改本地。只暂存相关文件，不要 `git add .`。推送前先 fetch；远端有每日提交就 merge。

发布算完成的标准：Pages 部署的 commit 就是刚推的那个，并且线上 `index.html`（加查询参数避开缓存）里能看到新内容。不要只看 Actions 绿勾就说已经上线。

这台机器到 `github.com:443` 会间歇断几分钟到二十分钟。`api.github.com` 和 Pages 通常还能访问。推送失败就隔 40 秒以上再试，不要高频连打。`git fetch` 已经成功、随后的 pull 断了，可以用已有的 `origin/main` 做 `git merge origin/main --no-edit`。

## 9. 当前页面（2026-10-10 上线，不要改回旧刊头）

源码在 `index.html`。下面是已经和用户确认、并且线上在用的规则。旧交接里的英文眉题、全大写「RELEASE CALENDAR」、白卡片、彩色平台底、游戏/电影切换时的横向滑动，都不要恢复。

### 页头

- 左上是小号衬线字标「Release Calendar」。右上是主题开关。
- 月份数字是页面的主视觉，和列表左对齐。年份用无衬线，放在数字旁边。
- 「游戏 / 电影」在年份旁边，用细边框的分段按钮组，与静态年份区分；选中项反色填充，悬停和键盘聚焦有反馈，`aria-pressed` 随切换更新。上月 / 本月 / 下月在右侧细线上，共用一条 1px 下划线（`#tabs > .tabg`），切月时和列表一起以约 0.6 秒滑向选中项；首次加载和恢复保存月份时直接定位，不补播动画。`#topTabs` 的 `.tabg` 仍隐藏。
- 更新时间在细线右端，游戏和电影各自用自己 JSON 的 `updated`。
- 两栏共用 `.wrap` 的 `max-width: 860px`。不要再加 `body.view-movie .wrap { max-width: 1040px }`。那个规则会在淡出时把还看得见的游戏列表突然拉宽。

### 字体和颜色

- 月份数字和字标保留 Georgia / Songti 衬线；作品标题桌面保留衬线（游戏 26px / 1.25 行高、电影 18px / 1.4 行高），手机统一无衬线 16px / 600 字重、1.4 行高。电影和手机游戏标题按实际内容占一行或两行，不预留两行高度。评分仍用默认齐线数字的 Times New Roman / Times 衬线（`--score-serif`）。不要把评分字体改回 Georgia。
- 无衬线（PingFang SC / 微软雅黑 / Noto Sans SC）用于日期、状态、价格、页签、页脚。
- 浅色底 `#eef0f3`，深色底 `#101114`。主文字 `#1c1d21` / `#f4f5f6`，日期 `#444c59` / `#c5ccd6` 加重，类型和已发布状态 `#606772` / `#a3aab4`。正文默认 6px 间距，手机游戏收紧为 4px；日期、类型和状态统一 13px / 1.5 行高。
- 金色用于时间状态：「还有 N 天」「今天 / 明天发售或上映」用 `#8a5200`（深色主题 `#e8b764`）。
- 评分颜色使用主题变量：≥80 绿色 `#1d6a43` / `#72c698`，≥60 黄色 `#d49d48`（深浅主题一致，2026-10-13 按用户要求从灰色恢复），低于 60 红色 `#a3333b` / `#ef9398`。电影仍将豆瓣 10 分制乘 10 再取整。
- 平台与评分链接悬停用下划线反馈，保留文字对比度；评分颜色也跟随统一的 0.22 秒主题过渡。

### 游戏列表

- 通栏细线分隔，没有白底卡片和阴影。圆角只在封面上。
- 封面桌面宽 256px，手机（≤640px）宽 `clamp(108px,32vw,148px)`，给长标题腾出空间；比例仍是 460/215，`object-fit: cover`。
- 桌面（≥641px）右侧信息区与封面等高，标题和日期靠上，平台价格通过 `margin-top:auto` 对齐封面底部。标题放大为 26px，最多自然换行两行；这组规则独立放在桌面媒体查询中，不改变手机的 4px 紧凑间距和触摸区域。
- 平台只显示图标加价格，没有 Steam 紫、PS 蓝、NS 粉的色块。无障碍名字仍带平台名。
- 评分和标题同一行，靠右。标题在手机上最多两行。
- 评分由 `scoreLink()` 拆成每位一个 `.dg`。格子是 `inline-grid`，列宽用 `--score-digit-width: 0.56em`（2026-10-12 按用户要求收紧间距，适配新的齐线评分字体）。不要改回整段文字加 `min-width: 2ch`，也不要改回 `flex` + `1ch`。手机上的 Georgia 数字不等宽，`1ch` 的 flex 格子会被字形撑开，十位和个位会对不齐。评分上的 `font-feature-settings` 保持 `normal`，避免手机为了等宽特性把某一位换成另一套字体。
- 游戏名用 `gameTitle()` 在显示时处理，不要为此改 `releases.json`。有中文就只留中文，去掉英文名。括号里和名字无关的说明要去掉，例如「塞尔达传说 时之笛（2026 重制版）」显示为「塞尔达传说 时之笛」。纯英文标题保持原样。紧贴中文的罗马数字留下，例如「侠盗猎车手VI」。
- `gameTitle()` 必须留在 `function card(` 和 `function firstChar(` 之间。`scripts/test_game_cover.js` 会把这一段切出来单独跑。`scoreLink()` 在 `card()` 前面；测试用的条目没有 `mc`，所以不会调用它。
- 日期行只有「10月2日 · 已发售」这种日期和状态。不显示 `dev`。
- 手机标题取消两行占位，评分与平台链接的行盒为 24px，以伪元素上下各扩展 10px，保留至少 44×44px 触摸范围。链接用 `z-index:3` 高于日期状态文字，避免扩展区域被遮挡。平台图标 13px、图标与价格间距 4px、链接横向间距 6px；价格换行时行间距 20px，让相邻行的触摸范围不重叠。

### 电影列表

- 同一条 860px 栏里的 3 列海报，≤640px 为 2 列。海报 2:3。
- 标题最多两行，要能看全，例如「生化危机：爆发夜」。不要改回单行省略号。
- 评分移到电影标题右侧，桌面 36px、手机 28px，同样用 `.dg` 等宽格子。电影标题仍按内容自然换行，最多两行，不固定占位。
- 日期到状态的间距固定为 6px；有评分和无评分时一致。评分不再放在状态行，也不参与状态的基线对齐。手机评分以 28px 行盒配合上下各 8px 的伪元素保持 44px 触摸高度；横向额外点击范围不挤占标题空间。
- 信息行是日期和类型。不显示导演、地区。

### 动效、主题、测试约束

- 游戏 / 电影切换是约 0.22 秒淡入淡出（`animFade`）。月份切换仍是约 0.6 秒的左右滑动（`animSwap`）。
- 主题变色统一用 `--theme-duration: .22s` 和 `ease`，文字、平台价格、年份、更新时间、游戏日期、电影信息、页脚都要同步；自己声明颜色的元素不能漏掉过渡，只继承颜色的子元素跟随父级。主题旋钮移动仍约 0.35 秒。`prefers-reduced-motion` 要保留。
- iPhone Safari / WebKit 会对继承中的 `color` 叠加过渡，导致衬线字标和作品标题延迟到约 0.4～0.6 秒。`h1`、`.mh .mn`、`.txt .tline .t` 必须直接取 `var(--txt)`；`.item`、`.pic`、`.tabs` 等只继承文字色的容器不能再做 `color` 过渡。保留月份、字标、评分及桌面标题的衬线字体，验收必须包含 WebKit 的手机宽度和双向切换，不能只测 Chromium。
- 主题按钮必须是 `position: relative`。旋钮是绝对定位；按钮若是 static，旋钮会相对 `.mast` 定位，叠到字标上。浅色旋钮是白底琥珀色太阳（`#d18a1d`）。夜间旋钮是深灰（`#565661`）加浅蓝灰月亮（`#d6ddf2`）。不要两个主题都用白旋钮。
- 偏好键：主题 `glwTheme`（`dark` / `light`，没有存过则跟系统），视图 `glwView`（`game` / `movie`），月份 `glwTab_tabs_month`（如 `2026-10`，存的是年月不是页码）。2026-10-13 按用户要求，切换游戏 / 电影保留当前所选月份，不再重置到本月。
- 隐藏类别和月份页都用 `inert` 和 `aria-hidden="true"` 退出键盘、读屏导航；切换开始即更新，保留原有淡出动画。月份按钮用 `aria-pressed` 表示选择。
- 手机（≤640px）月份和类别按钮、平台和评分链接点击范围至少 44×44px；游戏链接用 24px 行盒、电影评分用 28px 行盒，各自加伪元素扩展点击范围。主题按钮保留原尺寸，用伪元素把触摸高度扩到 45px。平台行的间距按扩大后的链接计算，不允许触摸区域重叠。
- 启动时 `#boot` 盖住页面，数据画完才揭开。验收时等它消失再看布局。
- `scripts/test_month_tabs.js` 会把 `function setPageActive` 到 `function showCredit` 切出去跑。不要弄坏它依赖的自由变量：`PAGE_CLASSES`、`animSwap`、`moveGlider`、`stackFit`、`esc`、`today`、`document`、`localStorage`。
- 键盘焦点用 `focus-visible` 描边。不要拿掉。

## 10. 和当前页面对得上的近期提交

| 提交 | 内容 |
| --- | --- |
| `1b00919` | 改成月份目录式页头；游戏封面统一 460×215；有中文名时只显示中文名 |
| `7745d52` | 第一次尝试把评分按位等宽（flex + `1ch`）。手机上无效，不要退回这一版 |
| `1ee509c` | 评分改为 `0.74em` 的格子，十位和个位才能在手机上对齐 |
| `4e5f39d` | 游戏列表不再显示开发商 |
| `3944245` | 剔除 Hellraiser: Revival |
| `66f63e4` → `0cd00ce` | 月度 Actions 加过，用户要求回退 |
| `250f437` / `25f816a` / `b0f52f5` | 三个月窗口、剔除旧作移植、龙之信条封面和精选口径 |

更早的视觉提交（衬线刊头、海报墙、平台色块、悬停上浮）已经被 `1b00919` 替换。不要用那些提交把页面改回去。需要某一处旧实现时用 git 历史查看，不要 `reset --hard`。

## 11. 安全和完成标准

- 不索要、不提交密码、Cookie、token。不把第三方登录凭据写进仓库。
- 普通维护按现有口径做。改变精选标准、加回已排除作品、恢复音乐、新建或关掉月度任务、改系统权限，先问用户。
- 没有变化不做空提交，也不为了留痕去改 `updated`。
- 没有看到对应提交的 Pages 部署和线上文件，不要说已经上线。没有在真实页面上看过，不要说视觉已经验收。

接手时至少确认：远端已同步、本文和另外两份说明已读、四条测试能跑、发布走 `main` 的 Pages、每日 Actions 还在、月度任务没有和另一套同时写 `main`。视觉以 §9 和当前 `index.html` 为准。

## 12. 可交给新 agent 的接手说明

接手 https://github.com/torge0414/release-calendar 的 GitHub Pages 维护。先读 `HANDOVER.md`、`MAINTENANCE.md`、`GAME_SELECTION.md`，克隆到自己的工作区。网站只显示上月、本月、下月的游戏和电影，月份页签永远 3 个，音乐不维护。游戏按 `GAME_SELECTION.md` 精选，不要加回已剔除的移植和暂不收录条目。

页面以 HANDOVER §9 为准，不要恢复旧版刊头、英文眉题、白卡片、彩色平台底、每张封面各自的比例，或游戏/电影切换时的横向滑动。游戏封面保持 460×215。有中文名时只显示中文名，并去掉括号里的重制说明。不显示开发商。评分保持每位 `0.56em` 的等宽格子和齐线衬线数字。游戏和电影共用 860px 栏宽。

用户要求的改动在本地看过之后直接推 `main`，除非用户说只改本地。推送前先 fetch，和每日评分提交分叉时 merge，禁止强推。样式改动要在真实页面上看桌面和手机宽度。每日评分和 Steam 国区现价继续交给现有 GitHub Actions，不要再做一套。月度重整不在仓库里，也不要自行恢复已回退的 `monthly-curate.yml`；11 月 1 日由谁做，先问用户。Windows 上跑 Python 加 `PYTHONUTF8=1`。只读完本文不要就提交、推送或新建定时任务。
