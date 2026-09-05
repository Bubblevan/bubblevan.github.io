https://github.com/Fission-AI/OpenSpec
https://github.com/github/spec-kit
https://github.com/obra/superpowers

这三个项目都聚焦于 **“规格驱动开发”（Spec-Driven Development）**，旨在规范AI编程助手的开发流程，但它们在个人知识库中的定位可以有所区分。

简单来说，我的建议是：
*   **`github/spec-kit`** 和 **`Fission-AI/OpenSpec`**：更适合放在 **`agent orchestration`** 部分。
*   **`obra/superpowers`**：则更适合放在 **`skills`** 部分。

## 1. 📝 各项目简介与归类分析

1.  **`github/spec-kit` (agent orchestration)**
    *   **简介**：这是GitHub官方推出的工具包，提供了一套完整的、可执行的**规格驱动开发流程**。它通过 `/speckit.*` 等一系列命令，引导用户从定义项目原则 (`/speckit.constitution`)、创建规格 (`/speckit.specify`)，到制定计划 (`/speckit.plan`) 和最终执行 (`/speckit.implement`)。
    *   **归类理由**：它更像一个**工作流编排器**。它定义了一个从“想法”到“代码”的完整、结构化的**开发流程**，并提供了命令行工具来驱动这个流程的每个阶段。这符合“orchestration”的定义，即管理和协调一个复杂过程的执行。

2.  **`Fission-AI/OpenSpec` (agent orchestration)**
    *   **简介**：这是一个同样强调规格驱动的开源框架。其核心工作流围绕 `/opsx:propose`、`/opsx:apply` 和 `/opsx:archive` 等命令展开，强调在编写代码前通过“提案（proposal）”和“任务（tasks）”来对齐需求。
    *   **归类理由**：与 `spec-kit` 类似，`OpenSpec` 也定义了一个**端到端的开发流程**。它通过一系列命令引导用户完成从探索、提案到实施和归档的完整周期。因此，它同样更适合归类为一种“orchestration”工具。

3.  **`obra/superpowers` (skills)**
    *   **简介**：这是一个为AI编程代理设计的**技能框架和软件开发方法论**。它提供了一套可组合的“技能（skills）”，如 `brainstorming`、`test-driven-development`、`systematic-debugging` 等。
    *   **归类理由**：它更像一个**技能库或方法论集合**。其核心是提供一系列**独立的、可复用的“技能”**（如TDD、调试、代码审查等），代理可以根据需要调用这些技能来执行特定任务。虽然它也有一个“subagent-driven-development”的流程，但其本质是提供构建模块（技能），而不是编排一个固定的、线性的流程。因此，它更适合放入 `skills` 部分。

## 2. 💎 总结

| 项目 | 核心定位 | 推荐归类 |
| :--- | :--- | :--- |
| **`github/spec-kit`** | 端到端的开发流程编排工具 | **`agent orchestration`** |
| **`Fission-AI/OpenSpec`** | 端到端的开发流程编排框架 | **`agent orchestration`** |
| **`obra/superpowers`** | 可复用的技能与开发方法论集合 | **`skills`** |

简单来说，如果你的知识库是围绕“如何组织和引导AI代理完成复杂任务”来构建的，那么 `spec-kit` 和 `OpenSpec` 是很好的流程案例。而 `Superpowers` 则更像是一本“技能手册”，可以为你的代理提供各种具体的“做事方法”。
