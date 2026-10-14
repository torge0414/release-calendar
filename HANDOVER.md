# Release Calendar 维护手册

更新日期：2026-10-14。本文合并了原来的 `HANDOVER.md`、`MAINTENANCE.md`、`AGENT_COLLABORATION.md` 和 `GAME_SELECTION.md`，是这个项目唯一的维护、协作与收录说明。

所有面向用户的日期和时间用北京时间（Asia/Shanghai，UTC+8）。

本文记录已经核对过的仓库状态和用户要求，不是对全部发行信息的重新背书；收录作品时仍要核对官方来源。用户的最新要求优先于本文。确认了新要求，就同步更新本文，避免下一位依赖过时的说明。

## 1. 项目概况

这是 Torge 的游戏与电影发行日历，面向中文用户，提供近期发行时间、倒计时、封面、评分和游戏购买入口。游戏是人工精选，电影以中国内地院线上映为准。

| 项目 | 内容 |
| --- | --- |
| 网站 | https://torge0414.github.io/release-calendar/ |
| GitHub 仓库 | https://github.com/torge0414/release-calendar |
| 主分支 | `main` |
| 部署 | GitHub Pages，`main` 分支根目录，legacy 构建；推送 `main` 即触发构建 |
| 技术 | 单个 `index.html`（内联 CSS / JS）直接读取同目录的 `releases.json`、`movies.json`；Python 脚本维护数据；GitHub Actions 每日刷新。没有 npm 构建、前端框架或后端数据库 |
| 工作仓库 | `H:\Release Calendar\release-calendar`，两位 agent 共用这一份（见 §2、§13） |
| 内容窗口 | 上月、本月、下月，共三个连续月份 |
| 页面分类 | 游戏、电影；音乐已下线 |
| 用户 | Torge，设计师。视觉细节要逐项对着真实页面看，不能只看代码 |

本文依据的基准是 `main` 的 `eb39668`（每日评分更新），其上一个人工提交是 `64957a4`（移除页头年份显示）。

当时的条目数量如下。数量是快照，不是月度配额，不要为了凑数加进不符合口径的作品：

| 月份 | 游戏 | 电影 |
| --- | ---: | ---: |
| 2026-09（上月） | 10 | 6 |
| 2026-10（本月） | 11 | 10 |
| 2026-11（下月） | 3 | 1 |

阅读顺序：本文 → `index.html`、`scripts/`、`.github/workflows/` 的实际实现。文档和代码不一致时，分别查用户最新要求、提交记录和实际行为；代码里遗留的注释不等于新需求。

## 2. 负责人与协作

GPT 和 Claude 两位 agent 都是项目负责人，地位对等，不设单一集成负责人。两位都可以按用户要求修改、验收并发布。

| 事项 | 负责方 |
| --- | --- |
| 每月 1 日精选（名单整理） | GPT |
| 用户交给某一位的具体任务 | 接到任务的一方，从改动、验证到发布全程负责 |
| 每日评分与 Steam 价格 | 现有 GitHub Actions，两位都不另建 |

协作规则：

- 谁改动，谁负责验收和发布。发布前同步远端，确认没有覆盖另一位或每日机器人的提交。
- 每项任务开始时明确：目标、基准提交、允许改动的文件或函数、验收标准、是否涉及数据与发布。
- `index.html` 是主要冲突点。两位都要改它时，先后进行；确需并行，就在独立分支或 `git worktree` 里做范围明确的补丁，由后完成的一方负责合并并告知对方。
- 两位共用 `H:\Release Calendar\release-calendar` 这一个 checkout：开始前先 `git status` 看有没有对方未提交的改动；不同时切换分支；不覆盖对方的未提交改动；不替对方暂存或提交不认识的文件。
- 前端任务尽量不碰 JSON；数据任务尽量不碰页面；采集任务分清每日字段刷新和月度名单编辑。每日机器人仍会写 `main`，分工不能消除这个并发来源。
- Claude 不另建月度写入任务，也不自行重排月度名单；发现名单问题时记录下来，交给 GPT 或用户。
- 每次交付说明：基准和成果提交、改了哪些文件或函数、实际行为变化、运行过的检查、浏览器证据、未验证的事项和已知限制。遇到规格冲突，先描述具体差异，不静默改回旧版本。

只读本文不产生新的产品需求。除每月精选由 GPT 负责外，其他具体事项等用户分配；没有任务时可以先检查环境、理解代码、记录问题，但不要就此提交、推送或新建定时任务。

## 3. 用户已确认的要求

- 游戏和电影都只显示上月、本月、下月，按时间升序，跨年也必须成立。月份页签永远只有 3 个，写「上月 / 本月 / 下月」，不要改成更多月份，也不要在页签上再写一遍月份名。
- 每月 1 日北京时间 09:00：保留上月已发布清单，重新核对本月和下月（§10）。用户明确要求的清理可以动上月。
- 每天更新保留条目的现有评分。下月游戏如果提前有媒体评分也要更新，不要按「已发售」过滤。
- 日常刷新不得增删清单、改发行日期或平台。Steam 国区现价由现有自动任务更新。
- 来源失败、未开放评分或价格时保留有效旧值。不能清空，也不能用未评分的 0 覆盖有效的电影评分或人数。
- 游戏是重点精选，不是所有新发售作品。旧作换平台上市要剔除（§4）。
- 音乐已取消。不要恢复音乐页签，不要采集或更新音乐。`music.json` 已于 2026-10-14 删除；`index.html` 里遗留的 `refreshMusic()` 等代码、`img/music_*.webp` 图片和「加回来即可」之类旧注释，都不是重新维护音乐的授权。
- 用户对视觉很严。样式改动要在真实页面上看过（桌面和手机宽度）再推送。功能能跑不等于视觉验收完成。
- 发布授权（2026-10-10、10-13）：按用户要求完成的改动，检查通过后直接提交并推送 `main`，确认 Pages 部署和线上效果，不再逐版询问；用户特别说「只改本地」时服从。无实际变化不提交。实际更新、连续来源失败、部署失败或需要决定时简要说明。这项授权针对现有网站的修改发布，不表示可以自行扩大产品范围。
- 改变收录口径、加回已否决作品、恢复音乐、新建或关掉月度任务、改系统权限，都要先得到用户的具体决定，不能当作普通修复顺带做掉。

## 4. 游戏收录口径

本网站是用户的重点游戏发行日历，不是发行数据库或全部 Steam 新品列表。规则由用户于 2026-10-01 确认：主要收录大中型新作、知名系列新作、真正的重制版（remake）和大型剧情 DLC；小体量独立作品默认不收，除非用户指定。本规则只针对游戏，电影不受影响。

### 判断顺序

1. **发行身份**：确认是新作、完全重新制作的 remake，或有新区域 / 新剧情的大型扩展。旧作移植、次世代升级、remaster、只打包既有内容的完全版，以及小型道具 / 皮肤 DLC 不收录。先核对作品本身的发行历史，不能只看新平台商店日期。
2. **重点范围**：优先主机第一方核心作品、已纳入精选范围的知名系列主线新作 / 续作，以及有官方项目介绍支持的大中型新 IP。重制版、大型剧情 DLC 也须属于这一重点范围。衍生小品不会因为带有知名 IP 自动入选。
3. **体量与编辑判断**：核对官方介绍中的完整战役 / 剧情、新区域、探索结构等内容，再决定是否适合这份重点清单。商店存在、名人参与、大厂发行、售价、磁盘大小、Steam 的「独立」标签或画面风格，都不是独立的入选 / 排除依据。不能凭营销文案宣称作品已经证实为 AAA、AA 或拥有某个预算 / 时长。
4. **边界默认保守**：明显的小体量合作解谜 / 派对小品、未被用户指定的小众项目不加入；预算或规模未公开且不足以判断的作品暂不收录，不把「暂不收录」说成已证实是小制作。之后有了足够的官方规模资料或用户指定，先解释理由、等用户决定再复审，不能在每月任务里悄悄重新加入。
5. **日期与评分**：前三项通过后，才核对上月 / 本月 / 下月、平台和链接。没有评分不影响真正新作入选；高评分也不能让不符合范围的作品入选。

这仍是人工精选，不存在可靠的商店「体量字段」。维护者须在本节记录边界作品的决定及来源；不能把「全部新作」「有官方页面」或「Steam 热门愿望单」当成自动收录标准。上月保留策略不阻止用户明确要求的范围清理。

### 排除旧作换平台再发行

以作品本身的首次发售为准，不把旧游戏后来登陆 Steam、PlayStation、Switch 或 Switch 2 的日期当成新作发售日期。排除跨平台移植、次世代升级版，以及只加入既有内容的完全版、豪华版、合集、Encore Edition；不能只凭新平台商店日期、版名变化或已有高评分判断为新作。每月整理前须查原版商店或发行商页面，确认是否已在其他平台发售。

官方明确标注的 remake，以及有首次发售新内容的大型扩展，只要符合精选范围，就不按「移植」误删；但只有画质提升的 remaster 或升级通行证不能冒充重制新作。分不清是移植还是重制 / 新内容时先核对官方说明，仍不明确就请用户决定。新扩展与本体同捆的条目必须明确代表新扩展，不能用旧本体日期或旧本体评分冒充。

2026-10-01 按用户要求剔除的旧作跨平台条目，不能因为新平台开放预购或有了评分就加回：

| 排除条目 | 新平台商品编号 | 原作已发售的核对来源 |
| --- | --- | --- |
| Marvel's Guardians of the Galaxy: Encore Edition | Nintendo 70010000119220 | [Steam 原作（2021 年）](https://store.steampowered.com/app/1088850/) |
| 剑星 完全版 | Nintendo 70010000123391 | [Steam 原作（2025 年已发售）](https://store.steampowered.com/app/3489700/) |
| 暗喻幻想：ReFantazio（NS2 版） | Nintendo 70010000105918 | [Steam 原作（2024 年）](https://store.steampowered.com/app/2679460/) |
| 皮克敏4 Nintendo Switch 2 Edition + 大家来挑战！当多虑检定 | Nintendo 70010000135062 | [Nintendo Switch 原作（2023 年）](https://www.nintendo.com/jp/switch/ampya/index.html) |

### 暂不收录的边界作品

2026-10-01 复审时，9 月原有 10 款属于既定重点系列 / 核心新作，全部保留；10 月从 16 款收紧为 12 款，11 月从 7 款收紧为 3 款。日期、平台、价格和可信评分都没有因为筛选而改写。

下列作品已移出，月度更新里不要悄悄加回。有了足以复审的新资料，先向用户解释并等决定：

| 条目 | 决定理由 | 已核对的官方来源 |
| --- | --- | --- |
| Warhammer 40,000: Boltgun 2 | 复古射击衍生作，不因战锤授权自动进入重点范围；不是断言所有复古 FPS 都小体量 | [Steam 3115160](https://store.steampowered.com/app/3115160/) |
| 愚者不灭（Stupid Never Dies） | 新工作室动作 RPG；当前缺少足够的重点项目规模依据，暂不收录，不臆测预算 | [Steam 3486530](https://store.steampowered.com/app/3486530/) |
| Remothered: Red Nun's Legacy | 小众恐怖系列续作，不属于当前重点系列范围；三部曲身份不自动取得资格 | [Steam 3335310](https://store.steampowered.com/app/3335310/) |
| 異界揭蹤／ANOMALITH | 小众生存 TPS；当前重点项目规模依据不足，暂不收录 | [Steam 4017880](https://store.steampowered.com/app/4017880/) |
| 恸哭幽光／CRYMELIGHT | 小众 rogue 动作作品，不属于当前重点范围；不因发行商或配音阵容自动入选 | [Steam 3891160](https://store.steampowered.com/app/3891160/) |
| Edge of Memories | 官方介绍支持完整动作 RPG，但当前不足以确认符合本清单的大中型重点项目口径，暂不收录，而非断言为小游戏 | [Steam 2738170](https://store.steampowered.com/app/2738170/) |
| SONIC PICO PARK | 多人合作解谜联动小品，不因索尼克授权自动入选 | [Steam 4304060](https://store.steampowered.com/app/4304060/) |
| 暗影之路／Shadow of the Road | 官方介绍支持剧情驱动的独立回合制 RPG，但当前规模依据不足且未获用户指定，暂不收录 | [Steam 1173980](https://store.steampowered.com/app/1173980/) |
| Clive Barker's Hellraiser: Revival | 2026-10-07 用户决定剔除（提交 `3944245`）：知名度来自恐怖电影 IP，不是知名游戏系列；体量未公开，与 Remothered 同属影视授权恐怖衍生作 | [Steam 1551980](https://store.steampowered.com/app/1551980/) |

2026-10-07 用户补充确认：知名 IP 的衍生作（如 Hot Wheels、星球大战：银河赛车手、恶魔城、空之轨迹 2）仍按既有编辑判断保留，只剔除 Hellraiser。10 月清单由 12 款减为 11 款。

### 已记录的保留决定

以下是当时的编辑选择，不代表重新确认了预算、游玩时长或未来档期：

- **《不朽遗志 Valor Mortis》**：官方定位为有完整剧情、探索和成长系统的第一人称类魂动作项目，由《幽灵行者》开发团队制作，作为重点新 IP 保留。[官方项目页](https://valormortis.com/)
- **《龙之信条2：Dark Arisen》**：新扩展包含新区域、新剧情及 12 个迷宫挑战，符合大型剧情 DLC 范围，不是旧本体换平台。封面和价格处理见 §6。[扩展的 Steam 页面](https://store.steampowered.com/app/2593290/)
- **《塞尔达传说 时之笛》2026 重制版**：Nintendo 官方明确说明为完全重制版，不是旧作移植。[Nintendo 商品页](https://ec.nintendo.com/HK/zh/titles/70010000130795)
- 11 月其余保留《Football Manager 27》和《Grand Theft Auto VI》。

## 5. 数据来源与结构

数据来源会变化；下面的链接是核对入口，不代表商店或豆瓣保证长期提供自动抓取接口。游戏和电影的范围都含人工筛选，仓库没有可复现的「所有值得收录作品」算法。

### 游戏（`releases.json`）

- 发行、平台、价格：Steam 商店及接口、PlayStation 香港、Nintendo 香港。必要时核对发行商页面。媒体传闻不能当成已确认日期。
- 媒体评分：条目 `mc_url` 对应的 Metacritic 页面。不是 Steam 好评率，也不是用户评分。
- Steam 普通游戏：`https://store.steampowered.com/api/appdetails?appids={id}&cc=cn&l=schinese`。价格只接受中国区 CNY，`final` 以分计，数据里存的是换算后的数值。
- Steam 套装：`https://store.steampowered.com/api/packagedetails?packageids={id}&cc=cn&l=schinese`。必须用 `steam_package_apps` 核对套装实际包含的作品编号，不能用 DLC 单卖价代替完整版价。
- PS / Nintendo 用香港商店来源，不要把它们的数字价格当成已换算的人民币。PlayStation 页面的 UTC 时间要换成香港 / 北京时间再写日期。不同平台可以不是同一天。

顶层是 `fetched_at`、`updated`、`groups`。每个 group 有 `year`、`month`、`label`、`games`。游戏字段主要是 `title`、`date`、`year/month/day`、`dev`、`mc`、`mc_url`、`plats`、`cover_img`，以及顶层 `steam/ps/ns` 和对应的 `_url/_img/_price`。

`plats[].key` 只用 `steam`、`ps`、`ns`，配套 `name/date/url/img/price`。页面平台按钮和价格读 `plats`，所以顶层 `steam_price` 必须和 `plats` 里的 Steam 价格一致。

`dev`、中英双语标题和括号说明都可以留在 JSON 里供维护时辨认。页面不显示开发商，标题在显示时处理（§7），不要为了对齐页面改 JSON。

### 电影（`movies.json`）

- 以中国内地院线上映为准，不自动扩成全球电影或流媒体清单。范围里仍有人工筛选，不声称全量。
- 入口：https://movie.douban.com/coming 和 https://movie.douban.com/cinema/nowplaying/beijing/ 。
- 日常脚本按 `sid` 访问 `https://m.douban.com/rexxar/api/v2/movie/{sid}?ck=&for_mobile=1`，使用移动 User-Agent、条目 Referer 和 JSON Accept，并核对返回 id。
- 豆瓣桌面页可能只返回验证页，移动接口也会限流。不要绕过验证码，不要使用私人 Cookie。失败时保留旧数据并报告。

结构同样是三个 groups，内容数组为 `movies`。条目有 `title`、`sid`、`url`、`date`、`year/month/day`、`score`、`votes`、`poster`，以及 `info/directors/actors/genres/director`。`score` 是豆瓣 10 分制，页面显示为乘 10 后取整。`year` 是院线年份，`info` 里的制作年份可以不同，不要为了统一改掉。

### 来源失败

保留可信旧值。电影未评分的 0 或空值不能覆盖有效分数或人数；Steam 0 元可以表示免费，和缺价不是一回事。`index.html` 从相对路径读取两份 JSON，改数据结构前必须同步修改页面。

## 6. 封面

游戏封面框固定为 **460×215**（约 2.14:1），`object-fit: cover`。选图优先 Steam `header.jpg`。不要用 `capsule_616x353`（约 1.74:1）或宽于约 2.35 的套装横幅当主封面。已经核对过的 460×215 图可以放在 `img/`，用 `cover_img` 优先显示。电影海报 2:3，`poster` 可以指向 `img/` 里的本地文件。

候选顺序：`cover_img`、Steam、Nintendo、PlayStation，加载失败再换下一张。刷新价格时不能把已验证的 `cover_img` 盖回不适配的外链。外链必须返回真正的图片；只有一个来源时更要检查。

现有比例不对的外链先留在数据里，由 CSS 裁进 460×215，下次改名单时再换成 `header.jpg`。不要改回「每张图用自己的比例」，也不要改回 16:9。

`ckw()` 仍会给宽于 2.35 的图加上 `.wide`。CSS 对 `.cover.wide` 同样是 `object-fit: cover`，所以超宽横幅是裁切，不是留白。`scripts/test_game_cover.js` 检查这个 class 还在，不要为了「视觉上不再 letterbox」删掉 `ckw()`。

《Dragon's Dogma 2: Dark Arisen》：

- 这是有新剧情 / 新区域的扩展，不是 2024 年本体。
- Steam 套装：`https://store.steampowered.com/sub/1686522/`，`steam_package_apps` 为 `[2054970, 2593290]`（本体和新扩展），套装中国区现价由每日任务刷新。
- 封面是扩展自己的 Steam 头图，`cover_img = "img/game_dd2_dark_arisen.jpg"`，460×215。购买链接和价格不要跟着封面改。

《Fire Emblem: Fortune's Weave》修过封面加载，保留现有优先封面和兜底。没被页面引用的旧本地图片不要顺手清理。

一些 Nintendo CDN 图片实际是 JPEG，但 MIME 为 `application/octet-stream`，图片检查可能误报。

## 7. 当前页面

源码在 `index.html`。下面是已经和用户确认、线上在用的规则。旧版的英文眉题、全大写「RELEASE CALENDAR」刊头、海报墙、白卡片和阴影、彩色平台底、悬停上浮、16:9 游戏封面、游戏 / 电影切换时的横向滑动，都不要恢复。

### 页头

- 左上是小号衬线字标「Release Calendar」，右上是主题开关。
- 月份数字是页面的主视觉，和列表左对齐。按用户要求不显示年份；年份数据仍用于月份选择、跨年判断和倒计时。
- 手机月份数字固定占 `2ch` 宽度（`flex:0 0 2ch`），保留大号衬线和左对齐；切换月份时游戏 / 电影按钮不能跟着数字字形宽度左右移动。
- 「游戏 / 电影」在月份数字旁边，和月份用相同的文字页签与 1px 下划线，无外框和反色底。类别列表只淡入淡出，所以类别下划线直接定位到选中项、不滑动，只保留主题颜色过渡；`aria-pressed` 随切换更新。
- 上月 / 本月 / 下月在右侧细线上，共用一条 1px 下划线（`#tabs > .tabg`），切月时和列表一起以约 0.6 秒滑向选中项。首次加载、恢复偏好和调整屏宽时直接定位下划线，不补播动画。
- 更新时间在细线右端，游戏和电影各用自己 JSON 的 `updated`。
- 两栏共用 `.wrap` 的 `max-width: 860px`。不要再加 `body.view-movie .wrap { max-width: 1040px }`，那条规则会在淡出时把还看得见的游戏列表突然拉宽。

### 字体和颜色

- 字标和桌面月份用 Georgia / Songti 衬线。手机月份用默认齐线数字的 Times New Roman / Times 衬线（`--score-serif`），52px / 700、固定 `2ch` 宽，数字特性 `normal`，避免 Georgia 在部分手机上让 9 显得更大。
- 作品标题：桌面衬线 26px / 700、1.25 行高；手机无衬线 16px / 600、1.4 行高。按实际内容占一行或两行，不预留两行高度。
- 评分用默认齐线数字的 Times New Roman / Times 衬线（`--score-serif`），不要改回 Georgia。
- 无衬线（PingFang SC / 微软雅黑 / Noto Sans SC）用于日期、状态、价格、页签、页脚。
- 浅色底 `#eef0f3`，深色底 `#101114`。主文字 `#1c1d21` / `#f4f5f6`，日期 `#444c59` / `#c5ccd6` 加重，已发布状态 `#606772` / `#a3aab4`。
- 游戏正文默认 6px 间距、手机 4px。游戏和电影的日期、状态统一 13px / 1.5 行高，日期 600、已发布状态 500。日期和状态之间共用「·」，左右各 6px、`--dim` 色、.65 透明度。电影标题到信息行间距 3px。
- 金色用于时间状态：「还有 N 天」「今天 / 明天发售或上映」用 `#8a5200`（深色主题 `#e8b764`）。
- 评分颜色：≥80 绿 `#1d6a43` / `#72c698`，≥60 黄 `#d49d48`（深浅一致，2026-10-13 按用户要求从灰色恢复），<60 红 `#a3333b` / `#ef9398`。
- 平台链接悬停用下划线反馈。评分链接悬停和键盘聚焦只改变颜色、不加下划线，保留绿 / 黄 / 红含义，浅色主题加深、深色主题提亮，0.22 秒过渡。键盘聚焦描边保留。

### 游戏列表

- 通栏细线分隔，没有白底卡片和阴影。圆角只在封面上。
- 封面桌面宽 256px，手机（≤640px）宽 `clamp(108px,32vw,148px)`；比例仍是 460/215，`object-fit: cover`。
- 桌面（≥641px）右侧信息区与封面等高：标题和日期靠上，平台价格用 `margin-top:auto` 对齐封面底部；标题最多自然换行两行。这组规则只在桌面媒体查询里，不影响手机的紧凑间距和触摸区域。
- 平台只显示图标加价格，没有 Steam 紫、PS 蓝、NS 粉色块。无障碍名字仍带平台名。
- 评分和标题同一行，靠右。
- 评分由 `scoreLink()` 拆成每位一个 `.dg`，格子是 `inline-grid`，列宽 `--score-digit-width: 0.56em`。不要改回整段文字加 `min-width: 2ch`，也不要改回 `flex` + `1ch`：手机上的数字不等宽，`1ch` 格子会被字形撑开，十位和个位对不齐。评分的 `font-feature-settings` 保持 `normal`。
- 游戏名用 `gameTitle()` 在显示时处理：有中文就只留中文，去掉英文名和括号里与名字无关的说明（「塞尔达传说 时之笛（2026 重制版）」显示为「塞尔达传说 时之笛」）。纯英文标题保持原样。紧贴中文的罗马数字留下（「侠盗猎车手VI」）。
- 日期行只有「10月2日 · 已发售」这种日期和状态，不显示开发商。
- 手机评分与平台链接的行盒为 24px，用伪元素上下各扩展 10px，保证至少 44×44px 触摸范围；链接 `z-index:3`，高于日期状态文字。平台图标 13px，图标与价格间距 4px，链接横向间距 6px；价格换行时行间距 20px，相邻行的触摸范围不重叠。

### 电影列表

- 同一条 860px 栏里 3 列海报，≤640px 为 2 列。海报 2:3。
- 标题最多两行，要能看全（例如「生化危机：爆发夜」），不要改回单行省略号。
- 评分在标题右侧，桌面 36px、手机 28px，同样用 `.dg` 格子。评分以负的底部外边距退出标题行的高度计算（桌面 -3.5px、手机 -5.6px），避免把日期往下推。手机评分 28px 行盒配合上下各 8px 的伪元素，保持 44px 触摸高度。
- 日期与上映状态同排，字号、字重和「·」与游戏一致。倒计时写成「还有10天」，不加空格。
- 不显示电影类型、导演、地区；这些数据仍保留在 JSON 里。

### 动效、主题与可访问性

- 游戏 / 电影切换约 0.22 秒淡入淡出（`animFade`），并保留当前所选月份（2026-10-13 起，不再重置到本月）。月份切换约 0.6 秒左右滑动（`animSwap`）。
- 主题变色统一用 `--theme-duration: .22s` 和 `ease`，所有自己声明颜色的元素都要同步过渡，只继承颜色的子元素跟随父级。主题旋钮移动约 0.35 秒。保留 `prefers-reduced-motion`。
- iPhone Safari / WebKit 会对继承中的 `color` 叠加过渡，导致衬线字标和标题晚约 0.4～0.6 秒变色。`h1`、`.mh .mn`、`.txt .tline .t` 必须直接取 `var(--txt)`；`.item`、`.pic`、`.tabs` 等只继承文字色的容器不能再做 `color` 过渡。动到主题或字体时，验收必须包含 WebKit 手机宽度的浅→深、深→浅双向切换，只测 Chromium 不够。
- 主题按钮必须是 `position: relative`，否则绝对定位的旋钮会叠到字标上。浅色旋钮是白底琥珀色太阳（`#d18a1d`），夜间旋钮是深灰（`#565661`）加浅蓝灰月亮（`#d6ddf2`）。不要两个主题都用白旋钮。
- 偏好键：主题 `glwTheme`（`dark` / `light`，没存过则跟系统），视图 `glwView`（`game` / `movie`），月份 `glwTab_tabs_month`（存年月如 `2026-10`，不存页码）。
- 隐藏的类别和月份页用 `inert` 和 `aria-hidden="true"` 退出键盘与读屏导航，切换开始即更新，保留原有淡出动画。月份和类别按钮用 `aria-pressed` 表示选择。键盘焦点用 `focus-visible` 描边，不要拿掉。
- 手机（≤640px）月份、类别按钮和平台、评分链接的点击范围至少 44×44px。主题按钮保留原尺寸，用伪元素把触摸高度扩到 45px。检查扩展后的范围有没有重叠或被附近文字挡住。
- 启动时 `#boot` 盖住页面。游戏和电影数据在启动时都会请求并预渲染，任一份到位后 `paint()` 重建共享月份界面，内容画完 `#boot` 才退出。验收时等它消失再看布局。

## 8. 代码入口

```text
release-calendar/
├─ index.html              页面、内联样式、内联 JavaScript
├─ releases.json           游戏清单
├─ movies.json             电影清单
├─ img/                    本地封面和海报，含历史遗留图片（如 music_*.webp）
├─ scripts/
│  ├─ check_data.py        数据结构、日期、月份校验；--images 另查外链图片
│  ├─ test_calendar.py     月份约束和 Steam 套装价格等回归检查
│  ├─ test_month_tabs.js   月份、偏好持久化和隐藏页可访问性检查
│  ├─ test_game_cover.js   封面优先级、图片比例和标题处理检查
│  └─ update_scores.py     现有评分及 Steam 国区价格刷新；--dry-run 不写文件
├─ .github/workflows/
│  ├─ daily-scores.yml     每日数据刷新，实际变化才提交
│  └─ check-images.yml     手动图片检查
├─ .nojekyll               GitHub Pages 静态资源标记
└─ HANDOVER.md             本文
```

`index.html` 的关键函数如下。行号对应 `64957a4`，只作参考，改动后优先按函数名搜索。

| 入口 | 约略行号 | 作用 |
| --- | ---: | --- |
| CSS 变量、`.dark`、媒体查询 | 15–432 | 颜色、字号、间距、动效和手机布局 |
| `refresh()` / `refreshMovies()` | 494 / 875 | 获取 JSON、错误提示与渲染 |
| `moveGlider()` | 508 | 页签下划线定位及移动 |
| `setPageActive()` / `tabbed()` | 519 / 524 | 隐藏页可访问性、三个月页签、共享月份和偏好恢复 |
| `stackFit()` | 654 | 同步容器高度，防止切换时裁切或塌陷 |
| `animSwap()` / `animFade()` | 667 / 676 | 月份滑动、类别淡入淡出 |
| `alignMc()` | 686 | 评分布局对齐 |
| `state`、`paintUp()`、`paint()` | 703 / 707 / 717 | 数据状态、更新时间、两类内容共同渲染 |
| `scoreLink()` | 742 | 把评分拆成固定宽度数字格 |
| `card()` / `gameTitle()` | 747 / 800 | 游戏行和中文标题显示处理 |
| `cf()` / `ckw()` | 812 / 823 | 封面失败兜底和超宽图标记 |
| `mcard()` | 837 | 电影卡片、评分、日期和状态 |
| 文件末尾的视图切换 IIFE | 约 946 起 | 类别选择、偏好保存、下划线和高度处理 |

遗留的 `refreshMusic()` 等函数仍在文件里，但没有任何地方调用，DOM 和可选类别只有游戏、电影；它读取的 `music.json` 已经删除，不要调用或恢复。

测试通过源码边界切出片段单独运行，移动或重构函数时要同步调整测试：

- `scripts/test_month_tabs.js` 切出 `function setPageActive(` 到 `function showCredit(`，依赖自由变量 `PAGE_CLASSES`、`animSwap`、`moveGlider`、`stackFit`、`esc`、`today`、`document`、`localStorage`。
- `scripts/test_game_cover.js` 切出 `function card(` 到 `function firstChar(`。`gameTitle()` 必须留在这一段里；`scoreLink()` 在 `card()` 前面，测试条目没有 `mc`，不会调用它。

## 9. 每日自动化

### 评分和 Steam 现价：`.github/workflows/daily-scores.yml`

计划时间每天 UTC 10:00（北京时间 18:00），也可手动 `workflow_dispatch`。scheduled run 经常晚点，不要向用户承诺每天 18:00 一定更新完。

用 Python 3.12 跑 `scripts/update_scores.py`，前后各跑一次 `check_data.py`。只有 `releases.json` 或 `movies.json` 真有变化才提交并推 `main`，提交说明是「自动更新评分和 Steam 价格」。用仓库 `GITHUB_TOKEN`，不需要私人 token。

脚本行为：

- 只读取现有 `mc_url`、电影 `sid` 和 Steam 链接，遍历全部保留月份，不区分已发售或未发售。不增删作品，不改日期或平台。
- 游戏更新 `mc`，电影更新 `score` 和 `votes`。没有游戏媒体评论数量字段，不要承诺这个功能存在。
- Steam 更新顶层 `steam_price` 和 `plats` 内价格（中国区人民币现价，含折扣）；编号或币种不符、价格未开放、接口失败时保留旧价。套装先核对 `steam_package_apps` 再接受价格。不刷新 PS / Nintendo 价格。
- 豆瓣没有评分或人数时，不用空或 0 覆盖旧值。
- 评分来源请求错误超过计入来源的一半时，整次失败且不写文件。Steam 错误不计入这个门槛；这只保护评分请求，不是所有外部失败的总开关。
- Metacritic 页面打开了但解析不到分数时记为 `unrated`，不算请求错误。页面改版后旧分数可能一直留着、也没有失败报警，要看日志。来源改版时需更新 `update_scores.py`。

不要再做一套每日更新。机器人提交会和人工提交分叉，推送前先 fetch，需要时 merge。

### 图片检查：`.github/workflows/check-images.yml`

只能手动触发（Actions 页面的「Check displayed images」），运行 `check_data.py --images`，不修改内容。图片检测只能发现疑似失效链接，不能代替浏览器里的视觉检查。

## 10. 每月 1 日精选（GPT 负责）

北京时间每月 1 日 09:00 保留上月已发布清单，重新整理本月与下月。这项工作由 GPT 负责。仓库里没有端到端的月度采集程序，也没有月度 Actions，提醒不在仓库里。页面页脚的「每月初自动更新」不能证明调度确实运行。

2026-10-06 曾加过 `.github/workflows/monthly-curate.yml`，用户随即要求回退（`66f63e4` → `0cd00ce`）。任何一方都不要自行恢复，也不要另建第二套写入 `main` 的月度任务。

步骤：

1. 按 §4 的精选规则和已记录决定过滤游戏，排除旧作换平台再发行，然后从商店和豆瓣的实际条目确认日期、地区、平台、价格与详情链接。不能仅凭商店有页面、知名 IP、售价或评分扩大名单，也不能重新加入已暂不收录的边界作品。缺少可核对条目时不要猜测日期或价格。
2. 只保留上月、本月、下月三个 `groups`，按月份升序。上月沿用已发布列表，不重新猜填历史记录；本月与下月按来源重新核对。每条的 `date` 必须与 `year`、`month`、`day` 和所属月份一致。跨年时检查年份切换。PlayStation 的 UTC 时间换成香港 / 北京时间再写。
3. 原有评分保留可信值，再按每日评分来源复核；来源失效不能把有效评分改为空。
4. 按 §6 核对封面。
5. 运行 `python scripts/check_data.py`；网络允许时再运行 `python scripts/check_data.py --images` 或手动触发图片检查。失败项在浏览器里复核，源站可能拦截非浏览器请求。
6. 审阅 JSON 差异，确认没有误删字段，再按 §12 提交、推送并确认线上。

## 11. 本地开发与验证

在仓库根目录运行（本机的 Python 路径和临时目录见 §13）：

```text
python -m http.server 8765 --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8765/`，不要直接双击 HTML。等 `#boot` 消失再看布局，看完关掉服务器进程。

基础检查（四项，每次提交前都要跑）：

```text
python scripts/check_data.py
python scripts/test_calendar.py
node scripts/test_month_tabs.js
node scripts/test_game_cover.js
```

Python 脚本只用标准库，建议 Python 3.12（与 Actions 一致）；Node 检查不需要 npm 或第三方包。

按改动范围追加：

- 图片变化：`python scripts/check_data.py --images`。
- 评分采集变化：`python scripts/update_scores.py --dry-run`，只访问来源并打印差异，不写文件。要实际写入就去掉 `--dry-run`，之后再跑 `check_data.py`，确认差异只涉及评分、人数、Steam 价格和更新时间。
- 这两项都要联网。网络阻断或源站拦截要逐条复核，不要把网络失败当成图片坏了，也不要因此删条目。普通界面调整不需要刷新评分。

样式和交互至少看 1280px 桌面和 390px 手机，必要时补 320px；两个类别、两个主题、三个月份都要看。重点看长标题、未评分、链接点击范围、快速切换、刷新后偏好恢复、页面高度和减弱动画设置。

## 12. 提交与发布

- 只暂存任务相关的文件，不要 `git add .`。
- 推送前 `git fetch origin`，看远端有没有每日机器人或另一位 agent 的新提交；有就 `git merge` 接上，解决冲突后再推。
- 不要强推、`reset --hard`，也不要用旧 JSON 覆盖机器人刚写入的数据。需要旧实现时用 git 历史查看。
- 没有实际变化不做空提交，也不为了留痕改 `updated`。
- 发布算完成的标准：Pages 部署的 commit 就是刚推的那个，并且线上 `index.html`（加查询参数避开缓存）里能看到新内容。只看推送成功或 Actions 绿勾不能说已经上线；没在真实页面上看过，不能说视觉已经验收。

仓库本地 git 配置（不要改用户的全局配置）：`user.name = torge0414`，`user.email = 56673045+torge0414@users.noreply.github.com`，`pull.rebase = false`。

## 13. 本机环境（仅适用于 Torge 的 Windows 电脑）

- 工作仓库：`H:\Release Calendar\release-calendar`，GPT 和 Claude 共用。`C:\Users\Torge\release-calendar` 是旧副本，不在上面工作。
- 外层 `H:\Release Calendar` 不是 Git 仓库，放着本机辅助脚本和检查产物：
  - `qa-safari-serif.cjs`、`qa-view-switch.cjs`、`qa-month-glider.cjs`、`qa-digit-font.cjs` 等是浏览器检查脚本；
  - `score-review/` 是历史截图和测量结果，不能当成当前版本的验收证据；
  - `browser-qa/` 是本机浏览器文件（含 WebKit）；
  - `build-*`、`style-*`、`fix-*`、`publish-*` 等是历史操作脚本，先读再判断用途，不要当成标准构建或发布命令直接运行；
  - `qa-temp/` 是可写临时目录。
- 本机 `python` 指向不可运行的 WindowsApps 别名。可用的运行时：

  ```powershell
  $projectPython = 'C:\Users\Torge\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  Set-Location 'H:\Release Calendar\release-calendar'
  $env:PYTHONUTF8 = '1'
  & $projectPython -m http.server 8765 --bind 127.0.0.1
  ```

- Python 的 `tempfile` 若命中不可写的沙箱临时目录，先把本进程的 `TEMP`、`TMP` 指向 `H:\Release Calendar\qa-temp` 再跑检查，不需要改测试代码或系统全局设置。
- Windows 控制台默认 GBK，跑会打印中文的 Python 时加 `PYTHONUTF8=1`。PowerShell 不支持 `&&` 和 bash heredoc。
- 这台机器到 `github.com:443` 会间歇断开几分钟到二十分钟，`api.github.com` 和 Pages 通常还能访问。推送失败就隔 40 秒以上再试，不要高频连打。`git fetch` 成功但随后的 pull 断了，可以用已有的 `origin/main` 执行 `git merge origin/main --no-edit`。

## 14. 和当前页面对得上的提交

| 提交 | 内容 |
| --- | --- |
| `1b00919` | 改成月份目录式页头；游戏封面统一 460×215；有中文名时只显示中文名。更早的衬线刊头、海报墙、平台色块、悬停上浮都被它替换，不要用旧提交把页面改回去 |
| `7745d52` | 第一次尝试评分按位等宽（flex + `1ch`），手机上无效，不要退回 |
| `1ee509c` | 评分改为按位格子（当时 `0.74em`，2026-10-12 收紧为现在的 `0.56em`） |
| `4e5f39d` | 游戏列表不再显示开发商 |
| `3944245` | 剔除 Hellraiser: Revival |
| `66f63e4` → `0cd00ce` | 月度 Actions 加过，用户要求回退 |
| `250f437` / `25f816a` / `b0f52f5` | 三个月窗口、剔除旧作移植、龙之信条封面和精选口径 |
| `dc7c271` | 月份保持、触摸范围和隐藏导航 |
| `638ab97` | 修复 Safari 主题变色延迟 |
| `feda0e1` | 桌面信息区与封面等高 |
| `91cb65d` | 电影评分移到标题行 |
| `51ac3bd` | 类别切换改用下划线，评分交互改为颜色反馈 |
| `12b65d1` | 类别下划线直接定位，不再滑动 |
| `bb6939a` | 固定手机月份宽度 |
| `a9a7541` | 手机月份改用齐线衬线数字 |
| `64957a4` | 页头不显示年份 |

需要某处的历史原因时，查看对应提交的 diff。

## 15. 安全

- 不索要、不提交密码、Cookie、token，不把第三方登录凭据写进仓库。
- 不绕过验证码，不使用私人 Cookie 抓取。

## 16. 可直接转发给新 agent 的开场说明

> 请参与维护 Release Calendar：https://github.com/torge0414/release-calendar ，线上 https://torge0414.github.io/release-calendar/ 。先读仓库里的 `HANDOVER.md`（唯一的维护、协作与收录说明），再核对实际 HEAD 和远端。
>
> 网站是原生单页加两份 JSON，没有 npm 构建，只维护上月、本月、下月的游戏精选与内地院线电影，音乐已下线。保持当前的月份目录页头、860px 共用栏宽、460×215 游戏封面、齐线衬线评分，以及手机触摸和可访问性规则。不要恢复旧视觉。
>
> GPT 和 Claude 都是项目负责人，谁改动谁负责验收发布；每月精选由 GPT 负责。两位共用 `H:\Release Calendar\release-calendar`，先分清任务和文件，避免同时改 `index.html`。提交前跑四项基础检查，样式改动看真实桌面、手机和两种主题，主题 / 字体改动补 WebKit 双向切换。每日 Actions 会提交评分和 Steam 价格，推送前先 fetch，禁止强推和覆盖新数据。不要自行新建月度任务或扩大清单。
