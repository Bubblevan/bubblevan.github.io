---
schema: bubblevan/v1
id: papers-agent-search
content_kind: paper
title: Search Agent 论文
date: 2026-09-06
status: published
visibility: public
summary: Search Agent、Deep Research Agent 与 Agentic RL 相关论文阅读记录。
topics: [search-agent, deep-research, reinforcement-learning, web-agent]
aliases: []
authors: [bubblevan]
---

找到了，就是你之前粘的那份 **《有，而且我刚按 2026-09-15 重新扫了一遍。你现在这 8 篇已经覆盖了 Search Agent 第一阶段的主干……》**。我帮你把里面的“Search Agent 图景”复述一下。

## 你原有的 8 篇：第一阶段主干

```text
Search-R1 / Search-o1 / WebThinker
        ↓
DeepResearcher / DR-Tulu
        ↓
CW-GRPO / Context Interference
        ↓
Evolving Rollouts
```

这份判断是：这 8 篇已经覆盖了 Search Agent 第一阶段的主干，但 **2026 年 3–8 月又长出了几条新主线**。

## 到 2026 年 9 月，更完整的路线图

```text
                       Search Agent
                            │
       ┌────────────────────┼──────────────────────┐
       │                    │                      │
   数据 / 探索          RL / Credit           环境 / 系统
       │                    │                      │
 SearchArt              CW-GRPO              SearchGym
 SearchMaster           CriticSearch         MemSearcher
 HiExp                  InfoFlow             Table-as-Search
       │                    │
       └─────────────┬──────┘
                     │
              Long-horizon Search
                     │
       ┌─────────────┼─────────────┐
       │             │             │
   Retriever       Memory       Search Policy
   Agentic-R     MemSearch-o1      KbPO
                                 AutoSearch
                     │
                 Multimodal
                     │
 MMSearch-R1 → VSearcher → OpenSearch-VL
                     ↓
             ProMMSearchAgent
             LMM-Searcher
```

## 这份图景的核心意思

Search Agent 已经不只是“RL 训练搜索”这一条线了，而是分成了三块：

1. **数据 / 探索**：怎么造题、怎么造长轨迹、怎么自进化  
   - SearchArt  
   - SearchMaster  
   - HiExp  

2. **RL / Credit**：怎么把轨迹奖励分配到每一步  
   - CW-GRPO  
   - CriticSearch  
   - InfoFlow  

3. **环境 / 系统**：怎么让搜索环境可复现、可训练、成本可控  
   - SearchGym  
   - MemSearcher  
   - Table-as-Search  

这三块最后汇入 **Long-horizon Search**，再往下分成：

- Retriever：Agentic-R  
- Memory：MemSearch-o1  
- Search Policy：KbPO、AutoSearch  

然后再进入 **Multimodal**：

```text
MMSearch-R1 → VSearcher → OpenSearch-VL → ProMMSearchAgent / LMM-Searcher
```

## 第一优先级：建议立刻补的 6 篇

1. SearchMaster  
2. SearchArt  
3. SearchGym  
4. CriticSearch  
5. OpenSearch-VL  
6. MMSearch-R1  

其中对 `TraceSearch-R1` 最对味的是：

- **SearchMaster**：自出题、自搜索、自验证、自训练，解决自生成数据的作弊问题  
- **SearchArt**：工业规模制造 long-horizon search / research tasks  
- **SearchGym**：可验证知识图谱 + 对齐语料，解决环境保真度  
- **CriticSearch**：retrospective critic 做 turn-level credit assignment  
- **OpenSearch-VL**：多模态搜索的完整开放 recipe，含 Fatal-Aware GRPO  
- **MMSearch-R1**：模型什么时候该搜、什么时候该信自己

## 第二优先级

- InfoFlow：reward density optimization  
- Agentic-R：retriever 也随 Agent 一起进化  
- MemSearcher：compact memory + multi-context GRPO  
- KbPO：knowledge boundary aware policy optimization  
- AutoSearch：搜多少轮才够，惩罚 over-search

## 多模态线

```text
MMSearch-R1
→ VSearcher
→ OpenSearch-VL
→ ProMMSearchAgent
→ LMM-Searcher
```

重点：

- MMSearch-R1：on-demand image/text search  
- VSearcher：long-horizon multimodal web search  
- OpenSearch-VL：active perception + search + full SFT/RL recipe  
- ProMMSearchAgent：Sim-to-Real + process-oriented reward  
- LMM-Searcher：100-turn multimodal search + file-based visual memory

## 安全方向

2026 年 8 月还有一条 **Search Agent Security**：

- Breadcrumbing Search Agents  
- 攻击的是连续多轮搜索的 observation channel  
- 从单网页 prompt injection 升级为 trajectory-level evidence poisoning

## 数据资源

**UltraData-SFT-Agent-2609**：

- 483,661 条 trajectory  
- Search-Agent 子集 **20,000 条**  
- 中英文 Web Search、multi-hop QA、retrieval planning、Web information acquisition

## 建议的目录扩展

```text
search/
├── _index.md
├── foundations/
│   ├── search-o1.md
│   ├── search-r1.md
│   ├── webthinker.md
│   ├── deepresearcher.md
│   └── dr-tulu.md
├── credit/
│   ├── cw-grpo.md
│   ├── criticsearch.md
│   └── infoflow.md
├── data/
│   ├── evolving-rollouts.md
│   ├── searchart.md
│   └── searchmaster.md
├── environment/
│   └── searchgym.md
├── retrieval/
│   ├── agentic-r.md
│   ├── autosearch.md
│   └── kbpo.md
├── context/
│   ├── context-interference.md
│   └── memsearcher.md
└── multimodal/
    ├── mmsearch-r1.md
    └── opensearch-vl.md
```

## 最后给的阅读序列

```text
Search-R1
  ↓
SearchGym
  ↓
SearchMaster / SearchArt
  ↓
CW-GRPO
  ├──────────────┐
  ↓              ↓
CriticSearch   InfoFlow
  └──────┬───────┘
         ↓
   TraceSearch-R1
   Fatal-aware × Contribution
         ↓
     Agentic-R
         ↓
    MMSearch-R1
         ↓
   OpenSearch-VL
         ↓
 Multimodal TraceSearch
```

如果只选 5 篇必读，那份图景里的顺序是：

1. SearchMaster  
2. SearchGym  
3. CriticSearch  
4. MMSearch-R1  
5. OpenSearch-VL  

第 6 篇才是 SearchArt。

一句话总结：这份图景把 Search Agent 从“Search-R1 那条 RL 主线”扩展成了 **数据 / Credit / 环境 / 长程 / 多模态 / 安全** 六块，并建议你围绕 `TraceSearch-R1` 按“环境 → 数据 → credit → 多模态”的顺序补，而不是无脑横向堆论文。