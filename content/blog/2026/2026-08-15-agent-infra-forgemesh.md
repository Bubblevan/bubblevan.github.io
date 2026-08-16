---
schema: bubblevan/v1
id: blog-20260815-agent-infra-forgemesh
content_kind: blog
title: Agent Infra 参赛复盘：从多 Agent Demo 到可复用的执行基础设施
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 结合 ForgeMesh 的真实实现，记录如何从 AgentTeams 协同、Skill 契约、GuardedPatch、Evidence 和 SLS Adapter 出发，把一个能跑的多 Agent Demo 做成可复现、可验证、可替换的 Agent Infra Workload。
topics: [Agent Infra, AgentTeams, Skill, Software Engineering, GOAI]
projects: [forgemesh]
aliases: []
authors: [bubblevan]
---

# Agent Infra 参赛复盘：从多 Agent Demo 到可复用的执行基础设施

参加 Agent Infra 类比赛，很容易从“先把几个 Agent 接起来”开始：一个 Agent 负责分析，一个 Agent 负责写代码，再找一个 Agent 跑测试。第一版 Demo 往往很快就能动起来，但接下来会遇到一个更难的问题：

> 如果把模型、Agent 框架和提示词换掉，这套系统还剩下什么？

这篇文章不是某个模型的调参教程，也不是一份“多 Agent 数量越多越好”的架构图。我想结合自己在 GOAI 赛道中实现 ForgeMesh 的过程，复盘一条更通用的路线：如何把一个研发故障修复 Demo，逐步做成具有契约、Skill、Workload、Evidence 和 Adapter 接口的 Agent Infra 原型。

文中的代码和测试已经放在 GitHub：[Bubblevan/forgemesh](https://github.com/Bubblevan/forgemesh)。默认环境是 Windows + Docker Desktop + Python 3.12 + uv；不依赖真实云账号也可以跑通核心闭环。

![ForgeMesh Agent Infra 架构：AgentTeams Control Plane 与 Evidence-Mutation-Verification Execution Fabric](/blog/2026/agent-infra-architecture.svg)

## 一、先决定自己要解决的“基础设施问题”

### 1. 不要从“我要做几个 Agent”开始

多 Agent 是实现手段，不是产品定位。真正应该先回答的是：谁负责协同、身份、任务分发和生命周期？哪些动作必须确定性执行，不能交给模型自由发挥？一个 Agent 产出的结果，如何被另一个 Agent 可靠消费？如何证明系统真的修复了问题，而不是生成了一段看起来合理的文本？

我的第一版实现把 ForgeMesh 看成一个多 Agent 编排器，后来发现这会和 AgentTeams 的 Control Plane 重叠。于是我把边界重新划清：

> AgentTeams 管团队、Worker 生命周期、Matrix 和委派；ForgeMesh 管能力绑定、工程状态、受控变更、证据和验证。

这个定位变化很关键。它让“换一个模型”或“换一个 Harness”变成接口替换问题，而不是重写整套工作流。

### 2. 选一个足够小、但能展示闭环的场景

我选的是一个很小的 Python Bug：折扣函数允许 `coupon=None`，但实现直接索引 `coupon["percent"]`，触发 `TypeError`。这个场景有三个优点：根因可以通过源代码和错误日志解释清楚；修改范围可以限制为一个文件、一处 guarded patch；修复后可以用真实 pytest 验证，而不是用模型自评。

这就是仓库里的 `coupon_empty_crash` reference workload。它不追求业务复杂，而追求每一步都有可检查的输入、输出和失败路径。

## 二、把“多 Agent 对话”改造成执行闭环

### 1. Control Plane 和 Execution Fabric 分层

在运行时，AgentTeams 仍然负责 Leader、RCA Worker、Coding Worker 和 Verifier Worker 的协作。但每个 Worker 不直接随意读写主机，而是通过 ForgeMesh 的能力和适配器执行：

```text
AgentTeams Control Plane
        │ task / worker / delegation
        ▼
ForgeMesh Execution Fabric
        │ capability / workspace / policy / artifact
        ▼
Evidence → Guarded Patch → Independent Verification
```

这里有一个很实用的判断标准：如果把 AgentTeams 换掉，底层的 Patch Policy、Artifact Schema 和 Verifier 是否仍然可以复用？如果答案是否定的，说明业务逻辑还没有从编排层里抽出来。

### 2. 三个 Skill 覆盖完整执行链

我没有一开始就设计十几个“未来 Skill”，而是先把真正运行过的三个能力封装出来：

#### `repo-evidence`

只读地采集 Issue、源文件和运行结果，输出带来源的 `EvidenceArtifact` 或 `RCAArtifact`。它必须记录文件路径、行范围、摘录和 SHA-256，不能在取证阶段修改代码。

#### `guarded-patch`

把模型提出的变更收敛成确定性操作。请求中包含目标文件、基础 SHA-256、旧片段和新片段；执行器还会检查允许路径、保护路径、变更预算和上下文是否过期。

#### `verification`

在隔离 workspace 中重新执行 pytest，返回命令、退出码、标准输出、标准错误、变更文件和明确的 `pass`/`fail` 决策。Verifier 不负责“顺手修一下代码”。

这三个 Skill 数量不多，却形成了完整链路：

```text
repo-evidence → guarded-patch → verification
      取证             变更             验收
```

## 三、读 AgentTeams 源码：先看 CRD，再看消息流

如果只是看 AgentTeams 的产品文档，很容易把它理解成“Manager 调几个 Worker”。真正读源码之后，我发现它更接近一个 Kubernetes-native 的协作控制面：Team、Worker、Manager 和 Human 都是有状态资源，Controller 负责把声明式对象落实为 Worker、Matrix Room、共享存储和运行时上下文。

### 1. Team 不是一个 Python list，而是一个带状态的 API 对象

在 `agentteams-controller/api/v1beta1/types.go` 里，Team 的核心结构大致是下面这样（保留了与参赛 Demo 最相关的字段）：

```go
type TeamSpec struct {
    Description    string           `json:"description,omitempty"`
    TeamName       string           `json:"teamName,omitempty"`
    Admin          *TeamAdminSpec   `json:"admin,omitempty"`
    HumanMembers   []TeamMemberSpec `json:"humanMembers,omitempty"`
    WorkerMembers  []TeamWorkerRef  `json:"workerMembers,omitempty"`
    PeerMentions   *bool             `json:"peerMentions,omitempty"`
    ChannelPolicy  *ChannelPolicySpec `json:"channelPolicy,omitempty"`
    HeartbeatEvery string            `json:"heartbeatEvery,omitempty"`
}

type TeamWorkerRef struct {
    Name string `json:"name"`
    Role string `json:"role"` // team_leader or worker
}

type TeamStatus struct {
    Phase          string `json:"phase,omitempty"`
    TeamRoomID     string `json:"teamRoomID,omitempty"`
    LeaderDMRoomID string `json:"leaderDMRoomID,omitempty"`
    LeaderReady    bool   `json:"leaderReady,omitempty"`
    ReadyWorkers   int    `json:"readyWorkers,omitempty"`
    TotalWorkers   int    `json:"totalWorkers,omitempty"`
}
```

这里最值得学习的不是 Go 语法，而是状态建模：`spec` 描述期望的 Team，`status` 描述 Controller 观察到的 Team。`workerMembers` 只保存对已有 Worker CR 的引用；Team 不偷偷复制 Worker 的 runtime、镜像和资源配置。这样 Worker 生命周期和 Team 编排可以分别演进。

这也是我在 ForgeMesh 里把 `ExecutionProfile`、`CapabilityRegistry` 和 `ExecutionJournal` 分开的原因：配置、解析结果、运行事实不能混在一个 prompt 或一个大 JSON 里。

### 2. 用命令创建 Team，背后是 CRD + Reconcile

AgentTeams 的 Team Management Skill 给出的最小命令是：

```bash
agt create team \
  --name forgemesh-demo \
  --leader-name forgemesh-leader \
  --workers forgemesh-rca,forgemesh-coding,forgemesh-verifier \
  --description "RCA to guarded patch to verification"
```

这个命令不是直接启动三个进程。源码路径上的真实顺序更接近：

```text
agt create team
  └─> 写入 Team.spec.workerMembers
        └─> TeamReconciler 校验 Worker 引用和唯一 team_leader
              ├─> 创建 Team Room
              ├─> 创建 Leader DM Room
              ├─> 注入 team/role/room 上下文
              ├─> 配置共享 MinIO 空间
              └─> 聚合 Worker readiness 到 Team.status
```

所以排查 Team 不要只看“容器有没有启动”。我会依次看：

```bash
agt get team forgemesh-demo
agt get workers -o json
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

如果 `Team.status.phase` 还没有进入 `Active`，或者 `readyWorkers < totalWorkers`，这时继续给 Worker 发任务通常只会制造第二个问题。

### 3. Team Leader 是特殊 Worker，不是 Manager 的别名

源码和内置 Skill 都强调一个边界：Team Leader 仍然是一个 Worker container，只是挂载了 `team-leader-agent` 的协同能力；普通 Worker 只和 Leader 沟通，Manager 只和 Leader 沟通。

```text
Global Admin
     │
     ▼
  Manager ───── Leader Room ───── Team Leader
                                  │
                                  ▼
                         Team Room / Matrix
                           ├── RCA Worker
                           ├── Coding Worker
                           └── Verifier Worker
```

这条边界直接影响任务可靠性。Manager 不应该越过 Leader 直接 @mention Coding Worker，否则任务状态、项目 DAG 和完成回报就可能脱离 Team Leader 的协调记录。

在我的 Demo 里，RCA/Coding/Verifier 的职责仍由 ForgeMesh 的 Artifact 和 Policy 契约约束；AgentTeams Leader 负责的是“谁先做、谁等待谁、结果回到哪里”。这就是 Control Plane 与 Execution Fabric 的分工。

### 4. 真正的任务委派不是一条聊天消息

AgentTeams 的 Team Task Delegation 文档把一次委派拆成了可追踪的文件和状态：

```text
Manager receives task
  ├─> shared/tasks/{task-id}/meta.json
  ├─> shared/tasks/{task-id}/spec.md
  ├─> push task directory to MinIO
  ├─> state.json: assigned_to + room_id + delegated_to_team
  └─> @mention Team Leader in Leader Room
```

一个最小的 `meta.json` 可以长这样：

```json
{
  "task_id": "TASK-001",
  "title": "Fix coupon empty crash",
  "assigned_to": "forgemesh-leader",
  "delegated_to_team": "forgemesh-demo",
  "room_id": "!leader-room:matrix.local",
  "status": "assigned"
}
```

Leader 收到任务后再选择 Simple Task Mode 或 Project/DAG Mode。复杂任务的子任务放在 Team 自己的存储空间里，最终由 Leader 聚合成父任务的 `result.md`，再回报 Manager。这个设计让我意识到：协同系统最重要的产物不是聊天记录，而是可恢复的任务状态。

### 5. Matrix 只负责消息传递，不应该承载全部业务状态

AgentTeams 使用 Matrix 作为 Agent 协作通道，但源码里的房间角色和文件同步边界很清楚：消息用于唤醒、委派、状态回报；任务规格、共享文件和结果通过 MinIO/共享文件系统持久化。

因此在 ForgeMesh 中，我没有把 RCA 文本直接塞进 Matrix 消息作为唯一事实，而是写成版本化 Artifact，并在 Journal 中记录 URI：

```python
journal.append(JournalEvent(
    "artifact.ready",
    task_id,
    str(rca_stored.uri),
    {"producer": rca_artifact.producer},
))
```

当 Worker 重启、Matrix 消息重复或模型换掉时，后续步骤仍然可以从 `artifact://TASK-001/rca` 恢复，而不是依赖某一条聊天上下文还在不在。

### 6. Built-in Skill 的本质是运行时可读的操作手册

AgentTeams 的 `manager/agent/skills/` 里，Skill 通常是 `SKILL.md` 加上 scripts/references。它不是编译期插件，而是被 Manager/Worker workspace 加载的操作契约。比如 Team Management Skill 明确规定：

```text
Team = 1 Team Leader + N Workers
Manager → Team Leader
Team Leader → Team Workers
Workers → Team Leader
```

这也是我给 ForgeMesh Skill 增加 `skill.yaml` 的原因：保留 AgentTeams 需要的自然语言说明，同时增加 ForgeMesh 可以校验的版本、能力、输入、输出、权限和失败码。两套 Skill 机制可以组合，但不应该互相冒充。

## 五、Skill 不是 Prompt，而是执行契约

很多项目把 Skill 写成一段“请你这样做”的提示词。对 Infra 来说还不够。我的做法是给每个 Skill 两层描述：`SKILL.md` 给 Agent 阅读的简洁操作说明；`skill.yaml` 给 ForgeMesh 读取的机器契约。

以 `guarded-patch` 为例，manifest 中声明：

```yaml
schema_version: forgemesh.skill/v1
name: guarded-patch
version: 0.2.1
capabilities: [code.edit.guarded]
inputs: [RCAArtifact, PatchProposal, WorkspaceRef]
outputs: [PatchArtifact]
requires: [workspace.write]
policy: {risk: medium, human_approval: false}
failure_codes: [STALE_CONTEXT, PATH_DENIED, PROTECTED_PATH, CHANGE_BUDGET_EXCEEDED]
verification: {downstream: [test.run]}
```

这样评审者可以直接检查：它需要什么、产生什么、依赖什么、权限边界是什么、失败时如何表达、下游如何验证。Skill Registry 还会校验 `SKILL.md`、manifest、references 和 JSON examples 是否完整。

从工程角度看，这比“我们有一个修 Bug 的 Agent”更容易复用。别人可以保留这个契约，把 Python patch executor 换成 Go、Rust 或远程 RPC 实现。

### 1. 真实的 GuardedPatch 代码比概念图更重要

ForgeMesh 里的受控写入入口就是一个普通 Python 函数，但它把关键 gate 集中在写入之前：

```python
def apply_guarded_patch(
    workspace: Path,
    patch: GuardedPatch,
    *,
    allowed_paths: set[str],
    protected_prefixes: tuple[str, ...] = (".github/", "deploy/", ".env"),
) -> dict[str, str]:
    target = patch.target.replace("\\", "/")
    if target not in allowed_paths:
        raise PatchRejectedError(f"target is outside allowed scope: {target}")
    if any(target == prefix.rstrip("/") or target.startswith(prefix)
           for prefix in protected_prefixes):
        raise PatchRejectedError(f"target is protected: {target}")

    source = (workspace / target).read_text(encoding="utf-8")
    if sha256_text(source) != patch.base_sha256:
        raise PatchRejectedError("stale context: recollect repo evidence")
    if patch.old not in source:
        raise PatchRejectedError("patch precondition is absent")

    updated = source.replace(patch.old, patch.new, 1)
    (workspace / target).write_text(updated, encoding="utf-8")
    return {"before_sha256": sha256_text(source),
            "after_sha256": sha256_text(updated)}
```

这段代码有一个我很看重的属性：失败是显式异常，而且发生在写文件之前。模型可以提出 PatchProposal，但不能绕过 `allowed_paths`、`protected_prefixes`、base hash 和 old snippet。Infra 的安全感，来自这种可读的失败语义，而不是来自 prompt 里一句“请谨慎修改”。

### 2. Artifact Envelope 负责把结果变成可消费对象

RCA、Patch 和 Verification 都通过同一个 envelope 进入 Store：

```python
patch_artifact = ArtifactEnvelope(
    artifact_id="patch",
    task_id="TASK-001",
    kind=ArtifactKind.PATCH,
    producer="guarded-coder-hermes",
    payload={
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "changed_files": ["discounts.py"],
        "decision": "applied",
    },
    evidence=(rca_uri, EvidenceURI.parse(
        "workspace://TASK-001/discounts.py")),
)
stored = artifact_store.put(patch_artifact)
print(stored.uri, stored.sha256)
```

这里的 `evidence` 不是一段装饰性文本，而是下游 Verifier 可以继续读取的引用。Artifact Store 写入后返回 URI 和 SHA-256，运行 Journal 只需要记录 URI，不需要复制整段结果到 Matrix 消息。

### 3. Registry 让 Skill 可以被机器发现

我没有用一堆 if/else 把 Skill 名称写死，而是让 Registry 从目录加载 manifest：

```python
registry = SkillRegistry(Path("skills"))

for skill in registry.discover():
    print(skill.name, skill.version, skill.capabilities)

matches = registry.resolve_skill({"code.edit.guarded"})
assert [skill.name for skill in matches] == ["guarded-patch"]
```

这正好对应 AgentTeams 的内置 Skill 机制：`SKILL.md` 负责让 Agent 知道“怎么做”，ForgeMesh Registry 负责让执行层知道“这个能力是什么版本、有什么输入输出、需要什么策略”。

### 4. 测试先写失败边界，再写成功 Demo

例如 SLS adapter 的 real mode 没有 query client 时应该拒绝启动，而不是默默退回 fixture：

```python
def test_real_mode_refuses_unconfigured_client():
    with pytest.raises(SlsAdapterConfigurationError,
                       match="requires a configured"):
        SlsEvidenceAdapter("real")
```

而 fixture mode 要验证真实的 Artifact 结果和脱敏行为：

```python
artifact = SlsEvidenceAdapter("fixture").to_evidence_artifact(
    "TASK-001", request
)

assert artifact.payload["mode"] == "fixture"
assert artifact.payload["record_count"] == 1
assert artifact.payload["records"][0]["authorization"] == "[REDACTED]"
```

测试的重点不是让数字看起来很大，而是把“不应该发生的事情”固定下来：越权路径不能写入、stale context 不能写入、未配置真实云客户端不能假装成功、敏感字段不能进入证据。

## 六、Evidence 是让闭环可信的关键

模型输出的自然语言解释很有价值，但它不能单独作为系统状态。ForgeMesh 给不同阶段的结果统一套上 Artifact Envelope，并通过 Evidence URI 互相引用：

```text
repo://discounts.py#L3-L3
artifact://TASK-001/rca
workspace://TASK-001/discounts.py
test://TASK-001/pytest
```

一个 Patch artifact 引用 RCA，一个 Verification artifact 引用 Patch 和测试结果。这样最终可以回答：这次修改基于哪个版本的源文件？修改了哪些文件，前后 hash 是什么？测试到底执行了什么命令？结果是模型说“应该通过”，还是 pytest 真的返回了 0？

这套 Evidence 链也让 Workload 具备 replay 能力。别人不需要使用我的 Agent，就可以拿同一个 `TASK-001` 和测试仓库验证自己的 Harness。

## 七、把云能力接进来，但不要让 Demo 被云账号绑架

软件研发故障定位不能永远只有本地源代码，线上日志同样重要。我选择接入一个克制的官方云 Skill：阿里云的 [`alibabacloud-sls-query`](https://www.alibabacloud.com/help/zh/sls/sls-query-skill-intelligent-log-query-and-analysis)。它的职责是把自然语言意图转换成 SLS 查询并返回结构化日志结果。

这里最容易踩的坑是：为了证明“用了云 Skill”，把真实账号、网络权限和 CLI 安装全部硬编码进比赛 Demo。我的做法是增加一个 adapter boundary：

```text
official SLS Skill / CLI result
              │
              ▼
      SlsEvidenceAdapter
              │
              ▼
       EvidenceArtifact
```

Adapter 有两种模式：`fixture` 读取仓库中的样例 SLS 返回，脱敏后生成 EvidenceArtifact，CI 和评审现场可以稳定复现；`real` 只接受外部注入的、已经配置好官方 Skill 的 query client，不在 ForgeMesh 中读取或保存 AccessKey。

这不是伪造一个阿里云 Skill，而是把“官方领域能力”和“ForgeMesh 证据规范化”分开。没有云凭据时，仍然可以验证 adapter、artifact 和后续 RCA 流程；有真实环境时，只替换 query client。

## 八、我在实现中踩过的几个坑

### 坑 1：一开始过度关注 Agent 数量

多一个 Agent 不等于多一个能力。真正应该优先设计的是能力契约、权限边界和验证方式。当前三个真实 Skill 比一页 PPT 上的十二个未来 Skill 更可信。

### 坑 2：让模型直接修改工作区

直接把 workspace 交给 Coding Agent，调试时很方便，但无法解释“它到底改了什么”。GuardedPatch 将模型提案和实际写入分开，并要求 base hash、old snippet 和变更预算同时满足。

### 坑 3：验证阶段又让模型自行判断

“看起来修好了”不是验收。独立 Verifier 必须真实执行测试，并把 exit code 和输出写入 artifact。失败就返回 Coding，不要自动吞掉失败。

### 坑 4：为接入云服务而牺牲可复现性

线上依赖应该通过 adapter 注入，fixture 是基础设施项目的测试资产，不是临时 mock。fixture 的 schema、脱敏规则和来源都应该被测试覆盖。

### 坑 5：只开源代码，不说明边界

Infra 项目还需要让别人知道：哪些是自己的代码，哪些是 AgentTeams、模型服务、Docker 或云 Skill 的第三方能力；什么可以复现，什么需要外部账号。仓库现在提供了 Apache-2.0、Third-party Notices、Security Policy 和 reproduction guide。

## 九、从评审标准倒推工程实现

我最后采用了一种很实用的迭代方式：把评分项翻译成仓库里的可检查对象。

| 评审关注点 | 仓库中的对应物 |
|---|---|
| 多 Agent 协同 | AgentTeams Team / Worker / Matrix 任务链 |
| Skill 复用 | `skills/*/SKILL.md` + `skill.yaml` + Registry |
| 工具/云能力接入 | SLS adapter 的 fixture/real 双模式 |
| 安全执行 | allowed paths、protected paths、base SHA、change budget |
| 结果可信 | Artifact Envelope、Evidence URI、Execution Journal |
| 工程质量 | pytest、manifest validator、reference workload |
| 开放性 | Apache-2.0、第三方披露、Adapter/Verifier 接口 |

这比单独准备一张“架构很先进”的图更有效，因为评审者可以沿着代码、测试和运行产物逐项核对。

## 十、如何在本地复现

在 Windows + Docker Desktop 环境下，核心闭环不需要先部署 Cloud Studio：

```powershell
cd D:\MyLab\harness\GOAI\forgemesh-demo
uv sync
uv run pytest
uv run python tools/validate_skills.py
uv run python tools/run_fabric_demo.py
```

预期结果包括：

```text
19 passed
valid alibabacloud-sls-query@0.2.1
valid guarded-patch@0.2.1
Verification: pass
```

运行产物写入被 Git 忽略的 `artifacts/`，其中可以看到 `sls-evidence.json`、RCA、Patch、Verification 和执行 journal。你可以先只运行 Python reference workload，再接入 AgentTeams 的真实 Team；这能显著缩短排错路径。

## 十一、最后的复盘

Agent Infra 的价值不在于“让更多 Agent 同时聊天”，而在于让异构 Agent 能够围绕稳定契约协作：Harness 可以替换；Skill 可以版本化和复用；Evidence 可以重放和审计；Workload 可以作为公共测试题；实现可以在不改变工作流的前提下替换。

如果重新开始，我会更早做三件事：先画清 Control Plane 与 Execution Fabric 的边界；先定义 Artifact/Evidence/Skill 契约；先做一个能真实通过测试的最小 Workload。模型和 Agent 的数量，反而应该放到后面。
