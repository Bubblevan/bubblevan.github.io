---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-tokenizer-bpe
content_kind: blog
title: CS336 A1 复盘一：Tokenizer 与 BPE
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 从 Unicode、UTF-8 和预分词开始，复盘 byte-level BPE 的训练、编码、解码与工程边界，并进一步理解 tokenizer 如何影响语言模型的计算效率、上下文长度与多语言能力。
topics: [CS336, Tokenizer, BPE, NLP]
projects: [cs336]
aliases: []
authors: [bubblevan]
--------------------

这是 CS336 A1 baseline 的第一章。

A1 表面上的目标是从零实现一个 BPE tokenizer，接着实现 Transformer、AdamW 和训练循环。但如果把 tokenizer 理解成“在真正的模型之前顺手写掉的文本预处理”，其实会错过 CS336 很重要的一条主线。

2026 年的 Lecture 1 在介绍整个课程时就把 **efficiency** 放在中心位置：语言模型开发是在固定的数据、计算、显存和通信资源下，尽可能训练出更好的模型。tokenization 也是这个资源分配问题的一部分。直接在 raw bytes 上建模当然最干净，词表只有 256 个元素，也不会存在 OOV；问题是序列太长，而今天的 Transformer 对序列长度非常敏感。课程因此直接指出：**raw bytes 很优雅，但对于当前模型架构而言计算效率并不好。**

所以这一章真正要回答的并不只是：

> BPE 是怎么写出来的？

而是另外几个问题：

* 为什么语言模型不能直接方便地处理 Unicode string？
* 为什么 byte tokenizer 虽然完整，却不够高效？
* 为什么 BPE 能在 vocabulary size 和 sequence length 之间做折中？
* pre-tokenization 到底在限制什么？
* 为什么同一套 vocabulary 下，merge 顺序必须严格确定？
* 为什么 tokenizer 会影响 context length、训练成本，甚至不同语言的使用成本？
* 到了 2026 年，我们为什么还在研究“能不能干脆不要 tokenizer”？

把这些问题想清楚之后，A1 里的 `train_bpe`、`encode`、`decode` 和 `encode_iterable` 才不是四个孤立的函数，而是一套完整的 text → model interface。

---

## 1. Tokenizer 到底在模型和文本之间做了什么

语言模型并不直接看到：

```text
The cat sat on the mat.
```

它看到的是类似：

```text
[464, 3797, 3332, 319, 262, 2603, 13]
```

也就是说，真正送进 Transformer 的输入是一个定义在 **有限词表上的整数序列**。

从这一点出发，一个 tokenizer 最基本的 contract 可以写成：

```text
encode: Unicode string -> list[int]
decode: list[int] -> Unicode string
```

CS336 Lecture 1 也正是从这个接口开始定义 tokenizer。

而对于 A1 实现的 byte-level BPE，更完整的数据流实际上是：

```text
Unicode string
    ↓
UTF-8 encoding
    ↓
bytes
    ↓
special-token splitting
    ↓
regex pre-tokenization
    ↓
BPE merge
    ↓
token bytes
    ↓
token IDs
```

解码方向则简单很多：

```text
token IDs
    ↓
vocabulary lookup
    ↓
token bytes
    ↓
concatenate
    ↓
UTF-8 decoding
    ↓
Unicode string
```

这里有一个很容易在第一次实现时忽略的问题：

**token 并不天然对应一个合法的 Unicode 字符。**

例如一个 UTF-8 中文字符可能由三个 bytes 组成，而 BPE vocabulary 完全可能保存其中的一部分 byte sequence。单独 decode 某一个 token 时，它甚至可能只是一个 Unicode 字符编码的前半截。

因此：

```python
tokenizer.decode([token_id])
```

并不保证每个 token 本身都能独立映射成一个完整字符。

OpenAI 的 `tiktoken` 教学实现对此采取的策略就是：

```python
bytes_data.decode("utf-8", errors="replace")
```

即遇到非法 UTF-8 序列时，用 Unicode replacement character `�` 代替。

这也是为什么应该把 tokenizer 的中间表示真正理解成 **bytes**，而不是“字符碎片”。

---

# 2. Unicode、code point 和 UTF-8：为什么先退回 bytes

理解 byte-level BPE，首先要区分三个东西：

```text
字符
Unicode code point
UTF-8 byte sequence
```

例如：

```python
ord("a")
# 97

ord("🌍")
# 127757
```

从 Python `str` 的角度看，`a` 和 `🌍` 都可以被看成一个 Unicode character。

但是编码成 UTF-8 后：

```python
"a".encode("utf-8")
# b'a'

"🌍".encode("utf-8")
# b'\xf0\x9f\x8c\x8d'
```

一个字符到底占多少 bytes 并不固定。

中文通常也是如此：

```python
"你".encode("utf-8")
# b'\xe4\xbd\xa0'
```

这件事会直接影响 tokenizer 的设计。

---

## 2.1 Character tokenizer：看起来最自然，实际上两头吃亏

最直觉的方法是：

```python
ids = [ord(c) for c in text]
```

这样完全不需要 BPE，也天然支持 Unicode。

但 Lecture 1 很快指出了两个问题。

第一，Unicode 的空间非常大。

第二，大部分 code point 极其罕见，因此给每个字符保留一个独立 embedding 是很浪费的。课程把 character tokenizer 形容为几乎是“两头都没占到”：词表很大，同时压缩率又不高。

如果 embedding dimension 是 `d_model`，那么仅输入 embedding 就需要：

[
V \times d_{\text{model}}
]

个参数。

词表 `V` 越大，embedding matrix 和最后的 LM head 都会随之增长。

---

## 2.2 Byte tokenizer：词表问题解决了，序列长度爆炸了

UTF-8 给出了另一个漂亮的方案。

一个 byte 永远只有：

[
2^8 = 256
]

种可能。

于是可以定义：

```text
token 0   = byte 0
token 1   = byte 1
...
token 255 = byte 255
```

任何 Unicode string 都一定可以表示成这些 token。

这意味着：

* vocabulary 固定为 256；
* 永远没有 unknown token；
* 任意语言、emoji、代码甚至奇怪符号都能编码；
* tokenizer 不需要提前“认识”某个字符。

这已经相当漂亮了。

问题是 **compression ratio = 1 byte/token**。

Lecture 1 专门定义了：

[
\text{compression ratio}
========================

\frac{\text{UTF-8 bytes}}{\text{tokens}}
]

compression ratio 越高，相同文本产生的 token 越少。课程进一步指出，序列越短越好，因为标准 self-attention 对序列长度具有二次复杂度。

例如同样一段文本：

```text
4000 bytes
```

如果 byte tokenizer：

```text
≈ 4000 tokens
```

而某个 BPE tokenizer 达到：

```text
4 bytes / token
```

那么：

```text
≈ 1000 tokens
```

单看 attention score matrix：

[
n^2
]

就从：

[
4000^2 = 16,000,000
]

变成：

[
1000^2 = 1,000,000
]

理想化地看，长度缩短 4 倍会让二次项缩小 16 倍。

当然现代 Transformer 的总 FLOPs 并不只有 attention，MLP、projection 等部分也很重要，因此不能简单说“token 少 4 倍，训练就一定快 16 倍”。

但方向非常明确：

> **tokenizer 在决定模型到底需要执行多少次 token-level computation。**

这正是我一开始没有充分意识到的地方。

---

# 3. Word tokenizer 为什么也不是答案

另一个极端是直接按单词切。

例如：

```text
the cat sat on the mat
```

变成：

```text
["the", "cat", "sat", "on", "the", "mat"]
```

它的压缩率很好，而且每个 token 似乎都有明确语言学意义。

但马上遇到 vocabulary explosion：

```text
cat
cats
Cat
CAT
cat-like
cat123
...
```

自然语言中的词形变化、姓名、URL、拼写错误、代码 identifier、数字组合会不断产生新词。

没见过的词怎么办？

经典 word tokenizer 只能引入：

```text
<UNK>
```

于是：

```text
supercalifragilisticexpialidocious
```

和一个完全不同的陌生词，都可能被压成：

```text
<UNK>
```

信息直接丢失。

Lecture 1 因此把 character、byte 和 word tokenizer 都视为不够理想的极端，而 BPE 是一个简单但非常有效的数据驱动 heuristic。

---

# 4. BPE：在 byte 和 word 之间学习一个词表

BPE 原本来自数据压缩领域，后来被引入神经机器翻译，再进入 GPT 系列 tokenizer。CS336 Lecture 1 对它给出的核心直觉非常简单：

> 高频 byte sequence 应该用一个 token 表示，低频 sequence 则允许使用更多 token。

这正好构成 byte tokenizer 和 word tokenizer 的折中。

初始状态：

```text
vocab = 所有 256 个 bytes
```

例如训练语料：

```text
the cat in the hat
```

最初可以想象成：

```text
t h e   c a t   i n   t h e   h a t
```

统计所有相邻 pair：

```text
(t, h)
(h, e)
(e, space)
(space, c)
(c, a)
(a, t)
...
```

假设：

```text
(t, h)
```

最常见，就创建：

```text
th
```

新的 vocabulary item。

然后再次统计。

下一轮可能得到：

```text
(th, e)
```

于是：

```text
th + e -> the
```

随着 merge 不断发生：

```text
bytes
 ↓
常见 byte pairs
 ↓
常见 character fragments
 ↓
subwords
 ↓
完整单词
 ↓
甚至常见的多字符格式片段
```

所以 BPE 并没有真正理解“什么是词根”“什么是后缀”。

如果最终产生：

```text
ing
tion
pre
```

这些看起来很像语言学单位，并不是因为我们把 morphology 教给了 tokenizer，而只是因为这些 byte sequence 在训练语料中出现得足够频繁。

OpenAI 对 BPE 的总结也很贴切：它既能处理训练时没见过的任意文本，又能压缩 byte sequence，同时倾向于让模型反复看到常见 subword。

---

# 5. BPE training：真正学习的是 merge hierarchy

第一次写 BPE 时很容易把结果理解成：

```python
vocab = {...}
```

然后认为训练完成。

实际上仅有 vocabulary 还不够。

BPE 最重要的另一部分是：

```python
merges
```

例如：

```text
1. (t, h)   -> th
2. (th, e)  -> the
3. (i, n)   -> in
4. (a, t)   -> at
...
```

这个顺序描述了 **token 是如何被构造出来的**。

在我的实现里，可以把 tokenizer 参数理解成：

```python
vocab: dict[int, bytes]
merges: list[tuple[bytes, bytes]]
```

或者把 merge rank 显式表示出来。

CS336 Lecture 1 的简化实现也是类似思路：`vocab` 保存 `id -> bytes`，`merges` 则保存两个旧 token 到新 token 的映射。

---

## 5.1 一轮 merge 到底发生什么

一轮 BPE training 可以拆成：

```text
1. 统计所有相邻 token pair
2. 找到频率最高的 pair
3. 创建新的 token
4. 将该 pair 的所有非重叠 occurrence 替换
5. 更新 vocabulary
6. 进入下一轮
```

伪代码：

```python
while len(vocab) < vocab_size:
    pair_counts = count_pairs(corpus)

    best_pair = select_best_pair(pair_counts)

    new_token = concat(best_pair)

    vocab.append(new_token)
    merges.append(best_pair)

    corpus = merge(corpus, best_pair)
```

理论很简单。

真正麻烦的是：

```text
count_pairs(corpus)
```

如果每轮都完整扫描整个 corpus，而 vocab 又需要增加几万次，这个“看起来没什么”的算法很快就会变得极慢。

Lecture 1 故意展示了一个慢版本，然后明确告诉 A1：真正作业里应该避免 encode 时遍历所有无关 merge，并尽量提高 BPE 实现速度。

这也是 A1 第一次把“算法”和“系统实现”放在一起。

---

# 6. 一个很关键的细节：tie-breaking

假设 pair frequency 是：

```text
(b"a", b"b") -> 17
(b"c", b"d") -> 17
```

谁先 merge？

如果随便选，结果并不是只有这一轮不同。

因为第一轮的 merge 会改变 corpus：

```text
token sequence
 ↓
pair statistics
 ↓
下一轮 merge
 ↓
再改变 token sequence
```

因此一个 tie-breaking 差异可能一路传播：

```text
merge #137 不同
→ merge #138 的统计不同
→ merge #139 又不同
→ ...
→ 最终 vocabulary 不同
```

最后：

```text
encode("hello")
```

都有可能得到不同 token IDs。

所以确定性并不是“为了让测试好过”的小细节，而是 tokenizer artifact 可复现性的必要条件。

同一个：

```text
training corpus
vocab_size
special_tokens
pre-tokenizer
```

应该得到同一套：

```text
vocab
merges
token IDs
```

否则后面模型 checkpoint 都失去了清晰含义。

---

# 7. Pre-tokenization：BPE 其实不是在整篇文本上随便 merge

这是我认为 tokenizer 最容易被低估的一部分。

一个最原始的 BPE 完全可以把整篇文档看成 bytes，然后不断统计相邻 pair。

问题是这样会学出一些非常奇怪的 merge。

例如：

```text
dog.
dog!
dog?
```

如果允许无限制跨边界 merge，BPE 可能逐渐把：

```text
dog.
```

直接做成 token，甚至可能学习跨空格、跨词、跨换行的奇怪结构。

GPT 风格 tokenizer 因此在 BPE 之前先做：

```text
pre-tokenization
```

CS336 A1 明确要求使用类似 GPT-2 的 regex pre-tokenization；Lecture 1 也专门把它列为从课堂 toy BPE 到 A1 tokenizer 必须补上的能力。

数据流于是变成：

```text
raw string
    ↓
regex
    ↓
pre-token pieces
    ↓
每一个 piece 独立运行 BPE
```

换句话说：

> **BPE merge 不能跨越 pre-token boundary。**

---

## 7.1 为什么空格经常和后面的词粘在一起

使用 GPT 风格 tokenizer 时，很容易看到：

```text
"hello world"
```

被切成类似：

```text
"hello"
" world"
```

而不是：

```text
"hello"
" "
"world"
```

Lecture 1 甚至特意让学生观察这一现象：同一个 word 出现在字符串开头和中间时，tokenization 可以不同，因为前导空格可能属于 token 的一部分。

例如概念上：

```text
hello
 hello
```

完全可能拥有两个不同 token。

这件事情后来也会影响模型行为。

Prompt 中：

```text
"cat"
```

与：

```text
" cat"
```

对模型而言并不只是“同一个词前面多了个空格”，它们首先就是不同的 token sequence。

---

# 8. Pre-tokenizer 实际上定义了 BPE 可以学习什么

这一点比“正则表达式怎么写”更重要。

如果 pre-tokenizer 把：

```text
don't
```

切成：

```text
don
't
```

那么 BPE 无论训练多少轮，都不可能产生一个跨越这条边界的：

```text
don't
```

token。

同理：

```text
123456789
```

到底能不能整个合并成一个 token，也会被数字对应的 regex pattern 限制。

所以 BPE vocabulary 并不是简单由：

```text
corpus frequency
```

决定。

更准确地说：

[
\text{Vocabulary}
=================

f(\text{corpus},
\text{pre-tokenization},
\text{merge algorithm},
\text{vocab size})
]

这让我开始把 regex 理解成 tokenizer 的一种 **inductive bias**。

它提前告诉算法：

```text
哪些边界可以跨
哪些边界不应该跨
哪些文本应该被当成相似结构
```

所以 tokenizer 并不是完全“语言无关”的统计压缩器。

哪怕主体算法都是 BPE，不同 pre-tokenizer 也能学习出明显不同的 vocabulary。

---

# 9. Special token：不是普通字符串，而是 tokenizer protocol

A1 里 `<|endoftext|>` 很容易被当成：

```text
“一个比较奇怪的人造单词”
```

实际上 special token 最好理解成 tokenizer 和语言模型之间约定的 **控制协议**。

例如：

```text
<|endoftext|>
```

可以告诉模型：

```text
这里不是普通字符序列
这里代表一个文档边界
```

因此它绝对不能再进入普通路径：

```text
<
|
end
of
text
|
>
```

而应该直接变成：

```text
[special_token_id]
```

A1 当前官方 tokenizer tests 专门检查 Unicode、连续 special token、special token 附近的换行以及与 `tiktoken` 行为的一致性。

例如：

```text
hello<|endoftext|><|endoftext|>world
```

需要识别为：

```text
normal text
special token
special token
normal text
```

而不是让 BPE 自己处理这一长串字符。

---

## 9.1 重叠 special token 是一个真正的 parser 问题

A1 还有一个很有意思的测试：

```text
<|endoftext|>
```

以及：

```text
<|endoftext|><|endoftext|>
```

都可能同时被注册为 special token。

那么输入：

```text
<|endoftext|><|endoftext|>
```

到底匹配：

```text
token A + token A
```

还是：

```text
token B
```

不能靠“碰巧 regex 先找到谁”。

官方测试明确要求重叠 special token 能稳定保留。

这说明 special-token handling 本质上已经很像 lexical analysis：

```text
longest / prioritized match
→ hard boundary
→ ordinary tokenizer
```

到了 chat model 和 agent model，这个问题会更加明显，因为 vocabulary 里可能存在大量：

```text
begin-of-message
end-of-message
tool-call
tool-result
reasoning boundary
fim prefix/suffix
```

等控制 token。

所以 tokenizer 不仅定义自然语言表示，也定义模型的部分通信协议。

---

# 10. Encoding：不能把训练算法原样再跑一遍

BPE training 的目标是：

```text
学习 merge priority
```

而 inference-time encoding 的目标是：

```text
按照已经学好的 merge priority
把新字符串切成 token
```

二者不是同一件事。

训练时会统计 corpus frequency。

编码时已经不存在：

```text
count frequency
choose most common pair
```

而是根据 merge rank 决定当前有哪些 pair 可以合并，以及哪个优先。

`tiktoken` 的 educational implementation 就非常清晰：先把一个 pre-token 转为单 byte parts，然后不断找当前所有相邻 pair 中 rank 最优的可 merge pair，直到再也没有合法 merge。

概念上：

```text
bytes
 ↓
检查当前 adjacent pairs
 ↓
找到 rank 最优的 merge
 ↓
合并
 ↓
继续
```

这也是为什么：

```text
vocab
```

和：

```text
merge ranks
```

必须一起保存。

---

# 11. 一个容易混淆的问题：BPE 是 greedy longest match 吗？

不是严格意义上的“直接寻找最长 token”。

假设 vocabulary 里同时存在：

```text
a
b
c
ab
bc
abc
```

不能简单说：

```text
abc 最长
→ 直接输出 abc
```

因为一个 token 是否能够构造出来还取决于 merge hierarchy。

例如：

```text
a + b -> ab
ab + c -> abc
```

和：

```text
b + c -> bc
a + bc -> abc
```

是不同的 merge history。

真正决定 encoding 的是：

```text
merge rank / merge priority
```

而不只是 vocabulary 中“有没有这个 byte string”。

这也是 BPE 和一个普通 trie-based longest-prefix tokenizer 的核心差别。

---

# 12. 为什么 vocabulary size 是一个模型超参数

一开始我会把：

```text
vocab_size = 10K / 32K / 50K / 100K
```

理解成 tokenizer 自己的设置。

其实它会一直传播到 Transformer。

假设 vocabulary size 是 (V)，hidden dimension 是 (d)。

Embedding 参数量：

[
Vd
]

LM head 如果不 weight tying，也大致需要：

[
dV
]

因此 vocab 变大意味着：

```text
+ embedding parameters
+ output projection parameters
+ softmax classes
```

但与此同时 vocab 越大，通常压缩率也越高：

```text
larger vocab
→ longer pieces
→ fewer tokens
→ shorter sequence
```

Lecture 1 正是把它描述成一个 trade-off：提高 vocabulary size 可以提高 compression ratio，但也会让 vocabulary 更稀疏。

于是 tokenizer 设计实际上是在平衡：

```text
小 vocabulary
  ↓
参数少
覆盖稳定
但 sequence 长

大 vocabulary
  ↓
sequence 短
压缩率高
但 embedding / output 更大
稀有 token 更多
```

没有一个脱离模型和数据分布的“最佳 vocab size”。

---

# 13. Compression ratio：A1 之后我会真正开始记录的指标

CS336 Lecture 1 给了一个很简单、但非常实用的指标：

[
\text{compression ratio}
========================

\frac{\text{UTF-8 bytes}}{\text{tokens}}
]

例如：

```text
10 MB UTF-8 corpus
↓ tokenizer
2.5M tokens
```

那么：

```text
≈ 4 bytes/token
```

OpenAI 对其 BPE tokenizer 的概括也是实践中一个 token 平均大约对应数个 bytes，不过具体比例高度依赖语言和文本类型。

因此我训练 TinyStories tokenizer 时，不应该只记录：

```text
training time
peak memory
vocab size
longest token
```

还应该至少补上：

```text
train compression ratio
validation compression ratio
tokens / character
tokens / word
```

如果再进一步，还可以比较：

```text
English prose
Chinese
source code
numbers
URLs
emoji
```

这样才真正能看到自己的 tokenizer 在“偏爱”什么数据。

---

# 14. 多语言模型里的 tokenizer tax

这一点是从 A1 继续往现代 LLM 走时非常值得知道的。

一个 tokenizer 在英文上可能：

```text
1 个词 ≈ 1~2 tokens
```

换成训练数据占比较少、形态更复杂或者 writing system 不同的语言，却可能：

```text
1 个词 ≈ 3~5+ tokens
```

于是同一个语义长度的内容：

```text
English      500 tokens
Language B  1000 tokens
```

会产生一个非常实际的后果。

固定：

```text
context_window = 32K tokens
```

并不意味着所有语言都拥有相同的“自然语言上下文容量”。

token fertility 较高的语言实际能装入的文本更少，同时 API 如果按 token 计费，成本也更高。

近年来多语言 tokenizer 的工作因此经常用 **fertility**：

[
\text{fertility}
================

\frac{\text{number of tokens}}
{\text{number of words}}
]

衡量 fragmentation。

2023 年的工作已经系统指出 tokenizer 会在模型真正执行之前就产生跨语言差异；到 2025—2026 年，这个问题仍在持续被研究，包括 token-count parity、fertility 和 whole-word preservation 等指标。

2026 年还有工作进一步强调一个很直观的问题：

> 在固定 token context 下，高 fertility 语言甚至会直接损失有效上下文长度。

因此“tokenizer 只是预处理”这个说法越来越站不住脚。

它实际上在决定：

```text
谁能更高效地使用模型
什么数据能装进 context
什么语言训练起来更贵
```

---

# 15. BPE 之外：SentencePiece / Unigram 在解决什么

BPE 当然不是唯一方案。

另一个非常经典的体系是 SentencePiece。

SentencePiece 的一个重要思想是：

```text
不要求上游先把句子按单词切好
```

它可以直接在 raw sentences 上学习 subword model，因此更适合构造真正 language-independent 的 preprocessing pipeline。

其中 Unigram LM 和 BPE 的思路也不同。

BPE 是：

```text
从小 vocab 开始
不断 merge
```

而 Unigram 可以粗略理解为：

```text
先有较大的候选 token 集
建立概率模型
逐渐删除贡献较低的 pieces
```

所以：

```text
BPE
```

更像一个确定性的 bottom-up merge procedure；

而：

```text
Unigram
```

天然允许从多个可能 segmentation 中进行概率建模。

这也产生了 **subword regularization** 这条研究线。

---

# 16. 一个固定字符串一定只有一种 tokenization 吗？

普通 deterministic BPE 会给出唯一答案。

例如：

```text
tokenization
```

每次 encode 都是同样的 token sequence。

但从表示学习角度，这并非必然最好。

同一个词理论上可以拆成：

```text
token + ization
tok + en + ization
token + iz + ation
...
```

如果训练时永远只出现一种 segmentation，模型可能过度依赖这一套人工确定的边界。

BPE-Dropout 因此提出：

```text
训练时随机跳过部分合法 merge
```

让同一文本在不同训练 iteration 中产生不同 segmentation；推理时仍使用标准 deterministic BPE。原始工作发现这种 subword regularization 能提高模型对 segmentation/noise 的鲁棒性。

甚至到了 2026 年，仍有研究继续研究在 pretraining 和 fine-tuning 阶段加入 BPE dropout 的效果。

它提醒我一件事：

> tokenizer 输出并不是语言唯一正确的离散表示，只是我们选定的一种表示。

---

# 17. 更前沿的问题：为什么 tokenizer 本身可能最终消失

CS336 Lecture 1 的最后一句其实很值得记住。

课程在总结 tokenization 时说，目前 tokenizer 仍然是模型之外一个独立步骤，但未来可能直接从 bytes 做 end-to-end modeling；理想系统仍然需要让模型在某种 chunk abstraction 上工作，并且这些 chunk 最好是可变的，从而把更多计算放到真正困难的信息上。

这已经非常接近近几年 tokenizer-free 模型的研究方向。

---

## 17.1 为什么直接 byte-level modeling 一直很诱人

byte-level 模型天然解决：

```text
OOV
多语言词表
token boundary artifacts
拼写错误
奇怪 Unicode
代码和结构化数据
```

甚至 tokenizer 本身都不用训练。

问题还是之前那个：

```text
sequence 太长
```

也就是说：

```text
BPE
```

其实是在 model 外部预先做 compression；

而 tokenizer-free 模型需要回答：

> 能不能把“发现有意义 chunk”这件事交给模型自己？

---

## 17.2 Byte Latent Transformer：动态 patch 而不是固定 token

Meta 在 2024 年提出 Byte Latent Transformer（BLT），就是这条路线里一个很有代表性的工作。

BLT 不再使用固定 subword vocabulary，而是直接处理 bytes，然后根据 next-byte entropy 动态决定 patch boundary：

```text
容易预测的区域
→ patch 可以更长

信息密度高、难预测的区域
→ patch 更短
```

昂贵的 global Transformer computation 主要发生在 patch level，而不是每一个 byte 上。

作者在最多 8B 参数、4T training bytes 的 FLOP-controlled 实验中报告，BLT 能在大规模上达到与 tokenization-based LLM 相竞争的性能，同时表现出更好的 robustness 和部分效率优势。

从 A1 的角度看，这件事特别漂亮。

传统 BPE：

```text
corpus statistics
      ↓
提前学习固定 segmentation
      ↓
整个模型生命周期不再改变
```

BLT：

```text
raw bytes
      ↓
根据当前内容的信息复杂度
动态产生 patch
      ↓
模型计算
```

也就是说，BPE 做的是：

```text
static compression
```

而 BLT 在尝试：

```text
dynamic learned abstraction
```

这恰好对应 Lecture 1 留下的两个要求：

```text
模型应该在 chunk 上计算
chunk 应该是 variable
```

所以课程里的那句话不是随口展望，而是已经指向 tokenizer research 的前沿。

---

# 18. 但 2026 年 BPE 也远没有“过时”

看到 BLT 很容易产生另一个误区：

```text
tokenizer-free 出来了
→ BPE 要淘汰了
```

并不是。

现代 subword tokenizer 已经拥有：

```text
成熟训练工具
成熟推理 runtime
极低 tokenization overhead
稳定 serialization
稳定 special-token protocol
成熟 serving ecosystem
```

而 tokenizer-free architecture 要改变的是整个模型 computation unit。

2026 年仍然不断有工作研究：

```text
BPE vocabulary pruning
multilingual vocabulary allocation
pre-tokenization
tokenizer adaptation
fertility
跨 tokenizer knowledge transfer
```

例如 2026 年 8 月出现的 Pruned BPE 工作就重新审视了一个很有意思的问题：标准 BPE 学习过程中会产生许多“为了构造后续 token 而存在”的中间 merge token，但这些 token 未必值得最终暴露给模型，因此可以把 **merge construction** 和 **model-visible vocabulary selection** 分开。

换句话说，即使算法已经三十多年了：

```text
pair frequency
→ merge
→ repeat
```

这件事背后的 vocabulary allocation 问题仍然没有完全解决。

---

# 19. A1 中 `encode_iterable` 为什么值得单独做

普通：

```python
encode(text: str)
```

默认整个文本已经在内存里。

但真正的预训练 corpus 很可能是：

```text
GB
TB
甚至更大
```

显然不能：

```python
text = file.read()
tokenizer.encode(text)
```

再一次性生成几亿 token。

因此 A1 提供：

```python
encode_iterable(iterable)
```

要求输入可以按 chunk 消费，并逐个 yield token。

官方测试甚至给 `encode_iterable` 单独设置了 memory behavior 检查：在 Linux 下将可额外使用的地址空间压到约 1 MB，而普通 `encode` 的对应 memory test 被明确标成 expected failure。

所以这一题测试的不是 generator 语法。

它实际上是在要求：

```text
tokenization algorithm
```

具备真正的：

```text
streaming interface
```

---

## 19.1 Streaming 最大的坑不是 yield，而是 boundary

例如输入 iterable：

```python
[
    "hello <|endo",
    "ftext|> world"
]
```

如果简单：

```python
for chunk in iterable:
    yield from encode(chunk)
```

特殊 token：

```text
<|endoftext|>
```

就被 chunk boundary 拦腰切开了。

类似的问题还可能发生在 regex pre-tokenization boundary。

因此：

```text
streaming tokenizer
```

真正困难的是：

> 我需要保留多少 suffix，才能确定这个 chunk 的末尾已经不可能和下一个 chunk 共同组成一个 tokenization unit？

这本质上是一个 incremental parsing / buffering 问题。

A1 的接口让我第一次比较直观地意识到：

> **API contract 会反过来约束算法设计。**

不是算法写完以后“包一个 generator”就自然变成 streaming system。

---

# 20. 官方 tests 到底在测试什么

当前 A1 repository 的 tokenizer tests 看起来很多，但实际上可以归成几个 contract。官方 2026 课程页面仍将 Assignment 1 定义为从头实现 tokenizer、model architecture 和 optimizer，并强调课程提供 minimal scaffolding、主要靠 unit tests 检查正确性。

### 第一层：可逆性

```text
decode(encode(x)) == x
```

覆盖：

```text
""
"s"
Unicode
English
German
TinyStories
```

官方 tests 中甚至直接拿 GPT-2/tiktoken 的结果作为 reference。

---

### 第二层：BPE compatibility

不仅要求：

```text
roundtrip 成功
```

还要求在给定 GPT-2 vocab / merges 后：

```text
我的 token IDs
==
reference token IDs
```

这比 roundtrip 强得多。

一个 tokenizer 完全可以：

```text
encode A
decode A
```

自洽，但 segmentation 与 GPT-2 不一致。

因此：

```text
correctness
```

不仅是可逆，还包括 merge semantics 完全一致。

---

### 第三层：special token semantics

测试包括：

```text
连续 special tokens
重叠 special tokens
special token 周围 newline
Unicode + special token
```

说明 special token 是整个 tokenizer contract 中的一等公民，而不是最后临时加的字符串 hack。

---

### 第四层：streaming semantics

要求：

```text
encode_iterable(file)
```

最终得到的 token sequence 与一次性 tokenize 整个文本一致，而且 roundtrip 后必须恢复原文件。

---

### 第五层：memory behavior

这是最 CS336 的部分。

```text
结果对
```

并不等于：

```text
实现合格
```

如果为了 tokenize 一个 5 MB 文件：

```text
复制很多份字符串
产生巨大中间 list
一次性 materialize 全部 pre-token
```

即使输出完全正确，仍然没有满足 streaming API 的设计目标。

这也是后续 systems 课程会不断出现的思路：

> **复杂度和资源行为也是 correctness 的一部分。**

---

# 21. 我现在会怎样划分自己的 tokenizer 实现

经过这一轮，我更愿意把代码拆成五个不同责任。

```text
Tokenizer
├── vocabulary
├── special-token parser
├── pre-tokenizer
├── BPE encoder
└── decoder
```

training 则是另外一套 pipeline：

```text
BPETrainer
├── corpus reader
├── special-token splitting
├── pre-token counting
├── pair statistics
├── merge update
└── serialization
```

这样比把所有逻辑塞进：

```python
train_bpe()
encode()
```

更容易理解。

尤其应该明确区分：

```text
training representation
```

和：

```text
inference representation
```

训练时我可能希望保存：

```text
pre-token -> frequency
```

而不是把一个出现一百万次的字符串真的存一百万遍。

encoding 时则只需要：

```text
一个新的 pre-token
+
固定 merge ranks
```

两者的数据结构目标完全不同。

---

# 22. 如果重新实现一次，我最先考虑的性能瓶颈

最 naive 的 BPE trainer 是：

```text
每轮：
    扫描整个 corpus
    统计所有 pair
    找最大 pair
    merge 整个 corpus
```

vocab 如果从：

```text
256
```

训练到：

```text
32K
```

意味着要进行约三万次 merge。

显然反复完整扫描会非常昂贵。

因此性能优化真正可以从：

```text
我为什么在重复计算？
```

开始。

例如思考：

```text
同一个 pre-token 是否出现很多次？
```

如果：

```text
" the"
```

出现 500 万次，就没有必要在内存中保存 500 万份 token sequence。

可以保存：

```text
pretoken[" the"] = 5_000_000
```

然后 pair contribution 乘 frequency。

进一步：

```text
merge 一个 pair
```

只会影响包含该 pair 或邻接它的位置，因此理论上并不需要重新统计全世界。

这就会继续引出：

```text
pair -> occurrence locations
priority queue
incremental count update
linked-list token sequence
```

等数据结构设计。

A1 baseline 未必需要一路写成工业 tokenizer，但这个思考过程很重要：

> 从 `O(n²)` 抱怨“Python 太慢”，和找到到底有哪些 work 被重复做，是完全不同的系统思维。

CS336 自己的 AI guidance 甚至专门拿“我的 BPE 是 O(n²)，怎么优化”作为教学例子，鼓励先定位慢在哪里，而不是直接索要完整优化代码。

---

# 23. A1 的 tokenizer artifact 最后应该留下什么

完成这一部分后，我希望仓库里留下的不只是：

```text
tests passed
```

而是一套之后可以真正用于预训练的数据资产。

至少包括：

```text
1. vocab
2. merges / merge ranks
3. special token configuration
4. encode
5. encode_iterable
6. decode
7. train_bpe
8. serialization / loading
```

然后给两个实际 tokenizer：

```text
TinyStories 10K
OpenWebText 32K
```

留下实验记录：

```text
vocab size
training corpus
training time
peak memory
longest token
compression ratio
tokens / byte
serialization size
```

如果再认真一点，我还想增加：

```text
TinyStories validation compression ratio
OWT validation compression ratio
Chinese sample fertility
code sample fertility
numbers / URL sample
```

这样后面真的开始训练 LM 时，就能回答：

```text
为什么这个模型一个 epoch 有这么多 token？
```

而不是只看到一个莫名其妙的数据集长度。

---

# 24. 从 tokenizer 可以提前看到整个 A1 的结构

写完 BPE 后，我才发现 tokenizer 已经提前出现了后面整个 A1 会不断重复的几个主题。

### 第一，representation matters

同样是文本：

```text
Unicode
bytes
tokens
embeddings
```

换一种表示，计算问题就完全不同。

---

### 第二，efficiency 不是最后再优化

byte tokenizer：

```text
数学上完全正确
工程上非常低效
```

已经告诉我：

> “能表示”只是最低要求。

后面 attention、optimizer、data loader 都会再次遇到同样的问题。

---

### 第三，边界条件往往比主算法难

BPE 主算法：

```text
count
max
merge
```

十几行就能讲完。

真正折磨实现的却是：

```text
Unicode
regex
tie-break
special token
overlap
newline
streaming
serialization
memory
```

后面的 Transformer 也会一样：

```text
矩阵乘法很简单
shape / masking / broadcasting / numerical stability 才容易出错
```

---

### 第四，模型性能从来不只是 architecture

tokenizer 一旦改变：

```text
token count
sequence length
vocabulary size
embedding size
training FLOPs
effective context
```

都会跟着改变。

所以未来比较两个“小模型架构”时，如果 tokenizer 不同，只比较：

```text
validation loss
```

甚至都未必公平。

这是后面自己尝试 mini-Llama、mini-Qwen、mini-DeepSeek 一类 architecture experiment 时必须提前控制的变量。

---

# 25. 我现在怎么理解 BPE

写 A1 之前，我对 BPE 的理解大概只有一句：

> 不断合并出现频率最高的字符对，形成 subword。

现在我更愿意把它理解成：

> **BPE 是一个在固定 vocabulary budget 下，用训练语料统计规律对 byte sequence 做静态压缩的算法。**

它通过：

```text
UTF-8 bytes
+
pre-tokenization inductive bias
+
corpus statistics
+
greedy merge hierarchy
```

构造出模型真正操作的离散计算单位。

它解决的核心矛盾是：

```text
256-byte vocab
    ↓
覆盖完美，但 sequence 太长

word vocab
    ↓
sequence 很短，但 vocabulary 无界/OOV

BPE
    ↓
固定 vocabulary
无 OOV
较高 compression
```

但这只是一个 heuristic，而不是“语言的正确切分方式”。

它也会带来：

```text
pre-tokenization bias
multilingual fertility disparity
固定 segmentation
vocabulary allocation inefficiency
```

等问题。

因此到 2026 年，一边还有大量工作继续改进 BPE 和 multilingual tokenizer，另一边 BLT 等路线已经开始反过来问：

```text
为什么一定要在模型训练前
固定好一套 token boundary？
```

这也是我觉得 CS336 第一章安排 tokenizer 很好的原因。

它看起来只是语言模型最外面的一层，但实际上已经把整门课最重要的思想提前展示出来了：

> **语言模型从来不只是 Transformer 公式。真正的目标，是在有限的数据、计算和内存预算下，设计一套合理的表示和系统，让每一次计算都尽可能值得。**

A1 从 tokenizer 开始，恰好从最底层的表示选择开始。

下一章进入 Transformer 真正接触 token IDs 后的第一步：

```text
token ID
    ↓
Embedding
    ↓
hidden vector
```

也就是最基础的两个参数组件：**Linear 与 Embedding**。

[下一章：Linear / Embedding](/blog/2026/2026-08-15-cs336-a1-linear-embedding/)
