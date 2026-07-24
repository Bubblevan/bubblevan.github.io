---
schema: bubblevan/v1
id: blog-20260721-pytest-intro
content_kind: blog
title: 从 17 个 print 脚本到 pytest：我的第一个测试安全网
date: 2026-07-21
updated: 2026-07-21
status: draft
visibility: public
summary: 把 hi-agent 的 memory 模块从 17 个离散 print 脚本迁移到 pytest，用真实代码解释 pytest 的 fixture、assert、xfail 机制，以及 6 pass + 5 xfail 各自锁住了什么东西
topics: [pytest, testing, python, hi-agent, memory, tdd]
projects: [hi-agent]
aliases: []
authors: [bubblevan]
---

## 0. 之前的测试长什么样

`hi-agent` 的 `memory/` 模块写了一段时间，测试方式是 `test/` 目录下 17 个编号脚本：

```
test/
├── 01-client.py
├── 02-message.py
├── ...
├── 12-working-mem.py
├── 13-memtool.py
├── ...
└── 17-perceptual.py
```

每个脚本的结构大致相同。比如 `test/12-working-memory.py`，打开是这样的：

```python
# test/12-working-memory.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.base import MemoryConfig
from memory.manager import MemoryManager

print("=" * 60)
print("🧪 测试：工作记忆 + MemoryManager")
print("=" * 60)

# 1. 初始化管理器
config = MemoryConfig()
manager = MemoryManager(
    config=config,
    user_id="test_user",
    enable_working=True,
)

# 2. 添加记忆
id1 = manager.add_memory("用户张三是一名Python开发者", importance=0.9)
id2 = manager.add_memory("李四擅长前端开发", importance=0.7)
print(f"✅ 添加了 2 条记忆: {id1[:8]}, {id2[:8]}")

# 3. 检索
results = manager.retrieve_memories("Python开发者", limit=3)
for r in results:
    print(f"  {r.get_summary()}")
```

另一个 `test/13-memtool.py` 更复杂，要初始化 LLM、注册工具、跑完整对话：

```python
# test/13-memtool.py
from dotenv import load_dotenv
from tools.builtin import MemoryTool
from core.llm_client import MyLLMClient
from agents.functioncall_agent import MyFunctionCallAgent

load_dotenv()
llm = MyLLMClient()
memory_tool = MemoryTool(user_id="test_user", enable_working=True)
agent = MyFunctionCallAgent(
    name="记忆助手",
    llm=llm,
    system_prompt="你是一个有记忆能力的AI助手",
    tool_registry=registry,
)
response = agent.run("你好，请记住我是一名Python开发者，我叫小明。")
```

每次想验证 memory 模块有没有被改坏，需要手动跑一遍这些脚本，用眼睛判断输出对不对。改了一行代码后，17 个脚本到底跑没跑、哪个挂了、为什么挂——全靠记忆。

---

## 1. pytest 把"检查"变成了"断言"

pytest 是 Python 的测试框架。它不改变你怎么写验证逻辑——你仍然写 `assert`。它改变的是**测试的组织方式、运行方式和失败报告**。

安装：

```bash
pip install pytest
```

然后一行跑完所有测试：

```bash
pytest
```

它会自动在当前目录及子目录下找到所有 `test_*.py` 或 `*_test.py` 文件，执行里面所有 `test_` 开头的函数，汇总报告。

pytest 跑完的输出是：

```text
tests/unit/test_memory_tool.py ...           [ 27%]
tests/unit/test_memory_manager.py ...        [ 54%]
tests/unit/test_memory_contracts.py xx..xx.  [100%]

6 passed, 5 xfailed, 2 warnings
```

6 个通过了，5 个标记为"已知会失败"（xfail）。每个 `.` 是一个 pass，每个 `x` 是一个 xfail。13 行的输出就概括了 11 个测试的状态。

---

## 2. 第一个测试文件

`tests/unit/test_memory_tool.py` 是测试 `MemoryTool`（memory 模块对外的统一入口）的三个测试。这是最直接的一层——模拟调用 memory tool 时的行为。

```python
from tools.builtin.memory_tool import MemoryTool


def test_memory_tool_add_search_and_stats_use_working_memory(patch_fake_embedder):
    tool = MemoryTool(user_id="user_a", enable_working=True)

    add_result = tool.execute(
        "add",
        content="I write Python services",
        memory_type="working",
        importance=0.6,
    )
    search_result = tool.execute("search", query="Python", limit=3)
    stats_result = tool.execute("stats")

    assert "ID:" in add_result
    assert "I write Python services" in search_result
    assert "working" in stats_result
```

跟之前 `test/12-working-memory.py` 的区别：

**之前**：`print(f"✅ 添加了 3 条记忆")` — 你得盯着屏幕看输出对不对。

**现在**：`assert "I write Python services" in search_result` — 错了 pytest 直接告诉你哪个 assert 失败、实际值是什么。

第二个测试验证边界情况——空输入：

```python
def test_memory_tool_rejects_empty_add_and_search(patch_fake_embedder):
    tool = MemoryTool(user_id="user_a", enable_working=True)

    assert tool.execute("add", content="").startswith("错误")
    assert tool.execute("search", query="").startswith("错误")
    assert tool.manager.memory_types["working"]._items == []
```

空内容不会悄悄存进去，内存列表仍然是空的。三个 assert 在一行输出里一次性验证。

第三个测试检查元数据自动注入——每条记忆都应该带上谁存的、哪个会话：

```python
def test_memory_tool_injects_user_and_session_metadata(patch_fake_embedder):
    tool = MemoryTool(user_id="user_a", enable_working=True)

    tool.execute("add", content="Remember my Python preference")

    item = tool.manager.memory_types["working"]._items[0]
    assert item.metadata["user_id"] == "user_a"
    assert item.metadata["session_id"] == tool.current_session_id
```

---

## 3. fixture：共享的准备逻辑

你注意到每个测试函数都有一个参数 `patch_fake_embedder`。这不是 pytest 内置的东西，是 `conftest.py` 里定义的 **fixture**。

```python
# tests/conftest.py
import pytest


class FakeEmbedder:
    """Small deterministic embedder for memory tests."""
    dimension = 3

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        return [self._vector_for(text) for text in texts]

    def _vector_for(self, text):
        text = text.lower()
        if "python" in text:
            return [1.0, 0.0, 0.0]
        if "coffee" in text or "tea" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def patch_fake_embedder(monkeypatch, fake_embedder):
    monkeypatch.setattr("memory.manager.get_text_embedder", lambda: fake_embedder)
    return fake_embedder
```

`FakeEmbedder` 是一个假向量化工具。它不看语义，只看关键词：`"python"` → `[1,0,0]`，`"coffee"` → `[0,1,0]`，其他 → `[0,0,1]`。

为什么需要假的？真实 embedding 模型要加载几百 MB、每次调用耗时几百毫秒、不同模型的向量维度不同。用假的意味着：测试不依赖外部模型、结果可预测、跑得极快。

两个 fixture 的分工：

- `fake_embedder`：创建一个 FakeEmbedder 实例。
- `patch_fake_embedder`：用 `monkeypatch`（pytest 内置的猴子补丁工具）把 `memory.manager.get_text_embedder` 替换成返回 fake embedder 的函数。这样所有测试里凡是调用 `get_text_embedder()` 的地方，拿到的都是这个假对象。

任何 test 函数只要在参数里写 `patch_fake_embedder`，pytest 就会自动调用这个 fixture，把返回值注入进去。你不用在每个测试开头手动初始化。

对比之前的做法——每个 `test/*.py` 都自己创建 LLM 客户端、加载 `.env`、初始化工具注册表。每次复制粘贴 `sys.path.insert` 和 `load_dotenv()`。改了初始化方式，17 个文件都要改。

---

## 4. 更复杂的测试：TTL 和容量驱逐

`tests/unit/test_memory_manager.py` 测的是 `MemoryManager` 内部逻辑。第一个测试验证 TTL（存活时间）过期：

```python
from datetime import datetime, timedelta
from memory.base import MemoryConfig
from memory.manager import MemoryManager


def test_working_memory_add_search_stats_and_ttl(patch_fake_embedder):
    manager = MemoryManager(
        config=MemoryConfig(working_memory_ttl=1),
        user_id="user_a",
        enable_working=True,
    )
    memory_id = manager.add_memory("Python is my main language", importance=0.7)

    results = manager.retrieve_memories("Python", limit=3)
    stats = manager.get_stats()

    assert [item.id for item in results] == [memory_id]
    assert stats["working"]["count"] == 1

    # 手动把时间拨到 2 分钟前
    manager.memory_types["working"]._items[0].timestamp = (
        datetime.now() - timedelta(minutes=2)
    )
    assert manager.retrieve_memories("Python", limit=3) == []
    assert manager.get_stats()["working"]["count"] == 0
```

测试分两阶段：刚加完能查到 → 手动改时间戳模拟过期 → 查不到了，统计归零。

第二个测试验证容量驱逐——当 working memory 容量只有 2 条时，新来的挤掉 importance 最低的：

```python
def test_working_memory_capacity_evicts_lowest_importance(patch_fake_embedder):
    manager = MemoryManager(
        config=MemoryConfig(working_memory_capacity=2),
        user_id="user_a",
        enable_working=True,
    )

    low_id = manager.add_memory("low value note", importance=0.1)
    kept_id = manager.add_memory("Python project note", importance=0.8)
    new_id = manager.add_memory("coffee preference note", importance=0.5)

    remaining_ids = {item.id for item in manager.memory_types["working"]._items}
    assert low_id not in remaining_ids
    assert remaining_ids == {kept_id, new_id}
```

0.1 那条被挤掉了，0.8 和 0.5 保留。不需要肉眼比对输出。

第三个测试暴露了当前的一个问题——跨 memory type 检索时，排序只看 importance，不看语义相关性：

```python
def test_manager_global_sort_currently_uses_importance_after_module_retrieval(
    patch_fake_embedder,
):
    manager = MemoryManager(user_id="user_a", enable_working=False)
    relevant = MemoryItem(
        id="relevant", content="Python related",
        memory_type="fake", importance=0.2,
    )
    important = MemoryItem(
        id="important", content="Unrelated but important",
        memory_type="fake", importance=0.9,
    )

    class StubMemory:
        def retrieve(self, **kwargs):
            return [relevant, important]

    manager.memory_types["fake"] = StubMemory()

    assert [item.id for item in manager.retrieve_memories("Python", limit=2)] == [
        "important",
        "relevant",
    ]
```

用了一个 `StubMemory`——一个假的 memory type，检索时固定返回两条结果。但 Manager 最后排序时把 `important`（不相关但 importance 高）排到了 `relevant`（相关但 importance 低）前面。这个测试的断言**承认了当前行为**：`assert ... == ["important", "relevant"]`。

函数名里写明了 `_currently_`，下一节会有一条 xfail 标记这个行为是错的。

---

## 5. xfail：把已知 Bug 锁进代码

`xfail` 是 pytest 最有用的机制之一。写法和普通测试完全一样，加一行 `@pytest.mark.xfail`：

```python
@pytest.mark.xfail(reason="Manager currently re-sorts merged results by importance only.")
def test_cross_memory_retrieval_prefers_relevance_over_importance(patch_fake_embedder):
    # ... 一样的 setup ...
    assert manager.retrieve_memories("Python", limit=2)[0].id == "relevant"
```

这个测试的逻辑和上一节的第三个测试**完全一样**，但断言相反：它断言 `relevant` 应该排在最前面。因为当前代码做不到，所以标记 `xfail`。

pytest 跑这条测试时：
- 如果它**失败**了（`"important"` 排在前面）→ 显示 `x`（符合预期）
- 如果某天代码修好了，它**通过**了 → 显示 `X`（unexpected pass），提醒你该去掉 xfail 标记了

`tests/unit/test_memory_contracts.py` 里 5 个 xfail 各自锁住一个已知缺口：

```python
@pytest.mark.xfail(reason="Tenant isolation is only metadata today; CRUD is not enforced.")
def test_user_a_cannot_retrieve_user_b_working_memory(patch_fake_embedder):
    manager_a = MemoryManager(user_id="user_a", enable_working=True)
    manager_b = MemoryManager(user_id="user_b", enable_working=True)

    manager_b.memory_types["working"] = manager_a.memory_types["working"]
    manager_a.add_memory("Alice likes Python", metadata={"user_id": "user_a"})
    manager_b.add_memory("Bob likes coffee", metadata={"user_id": "user_b"})

    results = manager_a.retrieve_memories("coffee", limit=5)
    assert all(item.metadata["user_id"] == "user_a" for item in results)
```

两个用户共享同一个 working memory 底层存储。manager_a 不应该能查到 manager_b 的记忆。当前代码只在 metadata 里标了 `user_id`，但 CRUD 操作没有强制过滤。等修好之后，`results` 应该为空——manager_a 查 `"coffee"` 应该查不到 Bob 的记忆。

另外四个 xfail：

```python
@pytest.mark.xfail(reason="BaseMemory does not define a structured forget contract yet.")
def test_base_memory_requires_forget_contract():
    assert "forget" in BaseMemory.__abstractmethods__
```

`BaseMemory` 是抽象基类，所有 memory type 都继承它。但目前它没有声明 `forget` 是必须实现的抽象方法。这个测试断言 `forget` 应该出现在 `__abstractmethods__` 里——等加了之后就绿了。

```python
@pytest.mark.xfail(reason="Consolidation currently copies source IDs and is not idempotent.")
def test_repeated_consolidation_is_idempotent(patch_fake_embedder):
    manager = MemoryManager(user_id="user_a", enable_working=True, enable_episodic=True)
    manager.add_memory("Important Python memory", importance=0.9)

    first = manager.consolidate_memories()
    second = manager.consolidate_memories()

    assert first == 1
    assert second == 0
```

`consolidate_memories` 把 working memory 的内容归档到 episodic memory。理想情况下执行两次应该只产生一条归档记录（第二次发现已经归档过了就跳过）。当前实现会重复归档。`second == 0` 是预期行为——现在还做不到。

```python
@pytest.mark.xfail(reason="Embedding providers can still return zero vectors on failure.")
def test_embedding_failure_does_not_store_zero_vector(fake_embedder):
    class ZeroEmbedder:
        dimension = 3
        def encode(self, texts):
            return [[0.0, 0.0, 0.0]]

    from memory.types.working import WorkingMemory
    memory = WorkingMemory(MemoryConfig(), ZeroEmbedder())
    memory.add(MemoryItem(content="Python memory", memory_type="working"))

    assert memory._items[0].embedding is None
```

模拟 embedding 模型挂了返回零向量的情况。当前代码照存不误——`embedding` 字段会是 `[0.0, 0.0, 0.0]` 而不是 `None`。修好之后，零向量应该被检测并丢弃。

---

## 6. pytest.ini：4 行配置

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -q
```

- `testpaths = tests`：告诉 pytest 只在这个目录下找测试（不会扫到旧的 `test/` 目录）
- `pythonpath = .`：把项目根目录加入 Python 路径，测试文件里 `from memory.base import ...` 不用手动 `sys.path.insert`
- `addopts = -q`：默认安静模式，少打印无关信息

旧的 `test/*.py` 每个文件开头那两行 `sys.path.insert` 从此不需要了。

---

## 7. 旧的 test/ 目录怎么处理

旧的 17 个 `test/*.py` 脚本仍然保留在仓库里。它们不是 pytest 测试——没有 `test_` 前缀的函数、没有 assert、靠 print 输出人工判断。pytest 的 `testpaths = tests` 配置确保 pytest 不会扫到它们。

这些旧脚本的角色从"测试"变成了"手动 demo"——当你需要快速验证一个想法、或者给新人演示 memory 模块用法时，跑一遍看看输出。回归验证交给 `tests/` 下的 pytest。

---

## 8. 这次运行的结果

```text
tests/unit/test_memory_tool.py ...           [ 27%]
tests/unit/test_memory_manager.py ...        [ 54%]
tests/unit/test_memory_contracts.py xx..xx.  [100%]

6 passed, 5 xfailed, 2 warnings in 0.18s
```

| 文件 | 测试数 | 通过 | xfail |
|------|--------|------|-------|
| `test_memory_tool.py` | 3 | 3 | 0 |
| `test_memory_manager.py` | 3 | 3 | 0 |
| `test_memory_contracts.py` | 5 | 0 | 5 |
| **合计** | **11** | **6** | **5** |

总耗时 0.18 秒。之前手动跑 17 个脚本逐个看输出，至少 5 分钟。

当前仍然需要人工判断的是：旧的 `test/` 目录里那些集成 LLM 的脚本（比如 `test/13-memtool.py` 需要调真实 API），pytest 没有覆盖。这些涉及外部依赖的端到端验证还是手动跑。

下一步是 Commit 2：挑一个 xfail，取消标记，修代码，跑到绿。Codex 建议先修用户隔离那条——它影响面最大、修起来最直接。

---

## 附录：新增文件清单

```
pytest.ini                          ← pytest 配置（4 行）
tests/
├── conftest.py                     ← FakeEmbedder + fixture（31 行）
└── unit/
    ├── test_memory_tool.py         ← MemoryTool 入口测试（36 行，3 pass）
    ├── test_memory_manager.py      ← MemoryManager 逻辑测试（70 行，3 pass）
    └── test_memory_contracts.py    ← 已知缺陷契约（85 行，5 xfail）
```
