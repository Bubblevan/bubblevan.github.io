---
date: 2025-12-12
title: 全文献检索工具方案设计
authors: [bubblevan]
tags: [paper-agent, literature-review, arxiv, dblp, semantic-scholar, cvf, crawler, open-review]
---

科研paper读着实在是不得劲。独立研究者有着自己的一套**taste**，正如杨振宁先生所说，这种taste是可以通过**大量的喂养培养出来的**——但是这有一点**太厚积薄发了**，看着zotero里面贫瘠的二十多篇论文，我打算做一个全文献检索的工具。

首先想到的当然是**ArXiv提供的官方库**，但是养taste的话，**顶会中稿+开源的才有用**，普通的preprint属于垃圾食品，然而**arXiv API 本身并没有一个专门的 strict 字段来筛选"是否被会议录用"**，完全依赖于作者手动更新 metadata 中的 comment。

## 方案一：DBLP + Semantic Scholar + ArXiv

所以我想到了下面这样的产品流：

### DBLP（作为"权威判官"）

- **作用：** 只负责提供**"真·录用名单"**
- **优势：** DBLP 是计算机领域的**"户籍科"**，它的数据是**人工校对的**，只有真正被 CVPR 录用的论文才会出现在 `conf/cvpr/2025` 列表里
- **解决痛点：** 解决了 arXiv 上作者**"自吹自擂"或"撒谎"**的问题（比如有的作者被拒稿了也敢写 Accepted）

### Semantic Scholar（作为"连接器"）

- **作用：** 负责把 DBLP 的会议论文标题，映射到 **arXiv ID**
- **优势：** DBLP 的会议条目和 arXiv 条目通常是独立的（两条记录）。Semantic Scholar 构建了**巨大的图谱**，它能识别出"这篇 CVPR 论文其实就是那篇 arXiv 预印本"，并提供 `externalIds` 字段
- **解决痛点：** 解决了 **DBLP 不直接提供 PDF 下载链接**，以及 DBLP 和 arXiv 割裂的问题

### ArXiv（作为"内容仓库"）

- **作用：** 负责下载
- **优势：** 一旦知道了 arXiv ID，用 Python 的 **arxiv 库下载 PDF 或源码是最稳定、最合规的**
- **解决痛点：** Semantic Scholar 的 API 有时会**限流**或不直接提供 PDF 文件流

### 存在的问题

DBLP 的标题有时候会把句号放在最后，或者包含特殊字符。Semantic Scholar 的搜索能力很强，通常能模糊匹配，但偶尔也会因为特殊符号对不上。代码里做一点简单的 `strip()` 清洗很有必要，但这不是最大的问题。

**Semantic Scholar 和 DBLP 都有频率限制**。如果名单有几千篇，一定要加 `time.sleep(1)` 或者使用 **API Key**（Semantic Scholar 申请 Key 后并发度更高），但是这导致了一个非常大的问题：**调用Semantic Scholar太久了**

## 方案二：直接爬取 CVF

所以接下来又想了第二条路：直接爬取 **CVF (Computer Vision Foundation)** 的官方 **Open Access 仓库**。

**CVPR、ICCV、WACV** 的所有论文（包括 Supplemental Material）都全量、免费托管在这里，它就是**简单的静态 HTML 页面**，没有复杂的反爬机制，**没有 API 限流**，直接 `requests` 请求一次就能拿到几千篇论文的列表，通过暴力爬虫直接访问 CVPR 2022 的"所有论文"页面，瞬间解析出所有论文的标题和 PDF 下载链接，并保存为 CSV 文件。

然而没有投过paper的本科生被这个数量吓晕了：

![](/blog/2025/cvpr.png)

- CVPR 2020: ~**1,467** 篇
- CVPR 2021: ~**1,660** 篇
- CVPR 2022: **2,074** 篇
- CVPR 2023: ~**2,359** 篇
- CVPR 2024: ~**2,719** 篇

实在是太疯狂了。如果你一天读 5 篇，读完这一年的会，明年的会都开完了。

## 各顶会的处理方法

这里还是继续完善离线方法，前面**CVF的方法只适用于3个**：

- **ECCV：** 虽然不属于 CVF，但 **ECVA 的网站结构和 CVF 惊人的相似**
- **ICLR 和 CoRL：** 最优雅的方法不是爬网页，而是使用 **OpenReview 的官方 Python 库**
- **ICRA, IROS（机器人双雄）：** 是最麻烦的两个。因为它们版权属于 **IEEE**；**IEEE Xplore 有很强的反爬**，且下载 PDF 需要**学校 IP 验证**
- **NeurIPS & RSS：** 非常良心，**历史归档都在静态网页上，HTML 结构十年不变**

所以对于双雄，只能用**DBLP的方法**，然后用Arxiv库交叉验证。

根据经验，机器人领域（Robotics）的 **ArXiv 覆盖率大约在 60% - 80%**。剩下 **20%** 的文章，作者可能根本没传 ArXiv，或者传了但是标题改得面目全非（比如从 "A Fast Method..." 改成了 "FastMethod:..."）。

计算机视觉顶会有严格的**“奇偶年份”**规律？！这里修正了我的爬取ICCV和ECCV的方法


