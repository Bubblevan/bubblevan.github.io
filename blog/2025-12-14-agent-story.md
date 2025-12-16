---
slug: agent-story
title: XLAB 关于 Agent 的学术讨论
authors: bubblevan
tags: [agent, 学术讨论, llm]
---

## agent 讨论

记录一下 XLAB 里面北美 CS PhD 对于 agent 的学术讨论，我看到这种交流真的是热泪盈眶：

> 再过两年现在的 agent 是不是都会废了  
> 模型自己就可以

> 我觉得 agent 的定义本身就还在演变，很多功能以前的 agent 需要，现在可能就不需要了。但 agent 本身要做的事情应该和模型是区分开的。  
> 现在多模态模型的未来预期是像人脑一样，能接受多模态的输入，能给出思考结果。这个结果不局限于文本，可能是 action（vla），可以是语音，图像（omni model），也可能是一个指令。  
> 而 agent 更多侧重于 action，拿到指令怎么去执行。  
> 过往的 agent 其实不少功能，比如长期记忆，规划，自我反思这些功能其实是之前大模型这几块能力不足的时候的一种过渡方案，之前的大模型不会思考，那我自己搭一个 agent 专门让模型只做思考等等，大模型的长期记忆不行，我要装个记忆模块，我要用 rag 等等。但最近大模型的思考和记忆都在飞速提升，现在的 agent 也不是都需要一个记忆模块了，模型本身能力够用了。不过真的要执行指令，比如说工具调用，图像标注等都需要进一步的操作，这件事大模型本身可能并不会去做。后续 agent 的定义可能也在演变

> 我觉得未来的大模型本身可能是个很强的大脑，他的泛化能力很强，是个全才，但不至于说什么都能做的很好。你要写代码，我要用专门的 code agent，比如 cursor，claude code。你要用到具身智能里，要调用机械臂操控抓取，你要让大模型，vla 输出 action。agent 的概念感觉更偏下游，至少我觉得模型本身再全能，应该也不至于全能到通杀所有领域，只要下游有需求就有专门为下游搭建一个 agent 框架的可能，你模型代码能力再强，能一口气输出再完美的代码，也还是要套个 agent 的壳子才能用的。

> 比如说现在很多技术解决上下文不足的问题，要是之后真的可以把整个代码仓库塞进去，那这些记忆管理之类的 trick 还有意义吗

> 现在模型的上下文长度已经很夸张了（context_length 每年大概翻 30 倍）  
> 但大多 paper 证明自己上下文能力大多就大海捞针说自己几百万上下文还能记住中间的某几个词。  
> 但实际应用上还是效果说话吧，记住了不等于效果好。  
> 比如现在大模型上下文很长，但很明显在对话一段时间后模型回复的质量会有所下降，如果一些记忆 trick 做出来的效果比没用 trick 好就很有意义。  
> claude code 本身也有一个超长下文对话后会主动对上下文做压缩的阶段。  
> 未来考虑到运行几天的 agent 模式，无限上下文是发展趋势甚至说必然结果的话，记忆压缩大概率也还是有必要的。  
> 用人脑对比，人能记住一大堆东西，但为了效率可能不如就记住今天要考试的关键几页内容，别的都忘了，检索效率和回答效果都可能更好。  
> 更好的记忆管理，或者压缩手段哪怕在无限上下文实现了我觉得也还是有意义的，节省成本和提升效果能做到一个就 ok

> 如果把 LLM 视为人类的下位替代的话，那所有人类遇到的记忆问题大模型最终也无法避免？

> 对于普通文本任务上下文压缩有效，但是目前来说遇到代码的话就失灵了……因为具体 code 没法被"总结"

> 这个倒可以稍微引申一下，比如代码这种任务往往希望记忆里存储的是完整的代码信息，这个很难压缩，但除了代码领域同样也有很多需要高精度记忆的任务，这样的类 code 领域的记忆压缩就有很多问题。至少现在 gemini cli 的做法还是挺相对粗暴的，先对历史进行分割，调用大模型分块压缩，summary 总结。压缩用精心设计的 prompt。但这种方法直觉上说想一种暂时的妥协。

> 但是我觉得所谓的 agent 的职能被慢慢统一到上游是可以遇见的吧

> 这个我觉得还是具体问题具体分析吧，我喜欢对比人脑单纯是便于我自己理解现在大模型能做什么不能做什么，然后给一种可能的解释，然后从人的思维角度思考有没什么解决方案。  
> 实际上很多任务 llm 都是人类是上位了。单论记忆问题，llm 可以一分钟记住数万字信息还能复述，人就不太行了。  
> 嗯，我觉得可能 agent 的功能可能也随着 llm 增强而改变，agent 本身这个概念可能也在迭代。之前 llm 不能做的要 agent 做的可能现在 llm 能做了 agent 就不做了，比如说之前 agent 往往有专门的思考模块。

> 那我觉得要你从学术角度看还是从 application 角度看了  
> 而且我觉得所谓的 agent 也不过就是一种加 human prior 的方式

> 所以最后还是要看工程实践  
> 数学/概念上等价的东西不代表实践中是等价的

> 那肯定是的  
> 而且涉及到真的取不取代你还得看发展的多快，旧东西会不会变成历史遗留问题

> 我理解 Agent 是 llm + tools / mcp；私有的 tools/mcp 不可能完全被大模型集成，所以 agent 大概率还是会一直存在的

> agent 和 LLM 定义上最大的区别就是和环境的交互吧，目前而言应该也没有必要让 LLM 往直接绕过 tool 之类的东西直接和环境交互方向发展

> gui agent 算环境交互吗

> gui agent 其实不太涉及到本地环境的操作，更多的是对打开的页面 / 手机的操作  
> 我们组现在在搞的就是 gui agent  
> 目前实测下来基本不用自定义 tools / mcp

> 以后会不会出现面向 AI 的 UI 设计

> gui agent 这个东西其实和爬虫差不多，鉴于目前已有的各种发爬措施，大概率不会有专门面向 gui agent 的服务  
> 更可能的是反 gui agent

> 这你让我想起了造机器人是因为现在环境是为人设计的这个 story

> 我完全不 buy 这个 story

> 合理  
> 前两天豆包那个就被反了

> 一本浓厚 csphd 气息

> 这个 buy story 太典了

> 感觉 gui agent 有点多此一举的味道

> ui 本来就是机器适应人类用的


---

今天做的另一件事情是去autodl里复现falcon，具体可见blog\2025-11-29-falcon.md下半部分，图形学驱动这些真的很难绷的住。再就是今天我疑似罹患流感，晚上昏昏沉沉的，效率不高，RT-1没有看。

## 复盘：3D 视觉仿真与图形渲染基础科普

### 一、Habitat-Sim 是什么？

**Habitat-Sim** 是 Meta（Facebook）开发的 3D 场景仿真器，主要用于训练和评估机器人导航算法。它的核心作用是：

1. **3D 场景渲染**：加载真实的 3D 场景（如 HM3D 数据集中的室内场景），生成机器人"看到"的图像
2. **物理仿真**：模拟机器人的移动、碰撞检测等物理行为
3. **传感器仿真**：模拟 RGB 相机、深度相机、激光雷达等传感器数据
4. **多智能体仿真**：可以同时模拟多个机器人或 NPC（如行人）的行为

**为什么需要图形渲染？**
- 机器人需要通过"视觉"感知环境，这需要从 3D 场景生成 2D 图像
- 即使不显示图像，也需要在 GPU 上渲染以获取传感器数据（RGB、深度图等）
- 这就是为什么即使是无头（headless）模式，也需要 GPU 和图形驱动

### 二、OpenGL、EGL、GLX 是什么？

#### OpenGL（Open Graphics Library）
- **定义**：跨平台的图形渲染 API，用于在 GPU 上绘制 3D 图形
- **作用**：告诉 GPU 如何渲染三角形、纹理、光照等
- **类比**：就像告诉画家"用红色画笔在画布上画一个圆"

#### EGL（Embedded-System Graphics Library）
- **定义**：OpenGL 和底层显示系统之间的接口层
- **作用**：创建 OpenGL 上下文（context），连接 OpenGL 和 GPU 驱动
- **为什么重要**：在服务器上（没有显示器），EGL 是创建 OpenGL 上下文的唯一方式
- **无头模式**：`EGL_PLATFORM=surfaceless` 告诉 EGL "我不需要显示窗口，只需要在内存中渲染"

#### GLX（OpenGL Extension to the X Window System）
- **定义**：Linux 上连接 OpenGL 和 X11 窗口系统的接口
- **作用**：在有显示器的 Linux 系统上创建 OpenGL 上下文
- **服务器场景**：在无头服务器上通常不需要，但 NVIDIA 驱动可能需要它来初始化

#### X11（X Window System）是什么？
- **定义**：Linux/Unix 系统上的图形窗口系统，用于管理窗口、鼠标、键盘等
- **作用**：
  - 提供图形界面基础：窗口管理、事件处理、输入输出
  - 客户端-服务器架构：X Server（显示服务器）和 X Client（应用程序）分离
  - 支持远程显示：可以通过网络在远程机器上显示图形界面
- **为什么服务器上没有 X11？**：
  - 服务器通常没有显示器，不需要窗口系统
  - X11 服务器需要显示器硬件支持
  - 无头服务器不需要图形界面，节省资源
- **与 OpenGL 的关系**：
  - GLX 是 X11 的扩展，用于在 X11 窗口系统中创建 OpenGL 上下文
  - 有显示器时：应用程序 → GLX → X11 → 显示器
  - 无头服务器：无法使用 GLX，必须使用 EGL 的无头模式

### 三、为什么服务器上需要特殊配置？

#### 问题本质
服务器（如 AutoDL）通常：
- **没有显示器**：无法创建传统的窗口来显示图形
- **没有 X11 服务器**：无法使用 GLX 创建 OpenGL 上下文（GLX 依赖 X11）
- **需要 GPU 加速**：仍然需要 GPU 来加速渲染计算

**X11 vs EGL 的区别**：
- **X11 + GLX**：需要显示器，创建可见窗口，适合桌面环境
  - 流程：应用程序 → GLX → X11 Server → 显示器
  - 示例：在本地 Linux 桌面运行图形程序
- **EGL（无头模式）**：不需要显示器，直接在 GPU 内存渲染，适合服务器
  - 流程：应用程序 → EGL → GPU（无窗口）
  - 示例：在服务器上运行 3D 仿真，渲染结果保存为图像或用于计算

#### 解决方案：无头渲染（Headless Rendering）
使用 EGL 的 `surfaceless` 模式：
- 不创建可见窗口
- 直接在 GPU 内存中渲染
- 渲染结果可以保存为图像或用于计算

#### 关键环境变量解释

```bash
# 1. 指定 EGL 平台为无头模式（不需要窗口）
export EGL_PLATFORM=surfaceless

# 2. 强制使用 NVIDIA 的 EGL 实现（而不是 Mesa 软件渲染）
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json

# 3. 指定使用哪个 GPU（多 GPU 系统）
export EGL_DEVICE_ID=0

# 4. 强制加载 NVIDIA 的图形库（确保子进程也使用正确的库）
export LD_PRELOAD="/lib/x86_64-linux-gnu/libEGL_nvidia.so.0:/usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0"
```

**为什么需要 `LD_PRELOAD`？**
- Linux 的动态链接器默认会按顺序查找库文件
- 系统可能有多个 EGL 实现（NVIDIA、Mesa 等）
- `LD_PRELOAD` 强制优先加载指定的库，确保使用 NVIDIA 的硬件加速版本
- 在多进程环境下，子进程也需要继承这个设置


**关于 Mesa vs NVIDIA 冲突的说明**：
- **Mesa** 是开源的 OpenGL/EGL 实现，提供软件渲染（CPU）或通过 DRI（Direct Rendering Infrastructure）使用集成显卡
- **NVIDIA 驱动** 提供专有的硬件加速 OpenGL/EGL 实现，直接使用 NVIDIA GPU
- **冲突原因**：Linux 系统默认会优先加载 Mesa 库（`libEGL.so.1`），但 Mesa 无法访问 NVIDIA GPU，导致无法创建硬件加速的 OpenGL 上下文
- **解决方案**：虽然安装了 Mesa 库解决了 `libEGL.so.1` 缺失的问题，但后续需要通过 `LD_PRELOAD` 和环境变量强制使用 NVIDIA 的 EGL 库（`libEGL_nvidia.so.0`），这样才能利用 GPU 硬件加速

#### EGL/OpenGL 配置（核心难点）

**问题诊断流程**：
1. **检查错误信息**：`GL::Context: cannot retrieve OpenGL version` → EGL 初始化失败
2. **检查 GPU**：`nvidia-smi` 确认 GPU 可用
3. **检查库文件**：确认 NVIDIA EGL 库存在
4. **设置环境变量**：配置 EGL 平台和库路径
5. **多进程问题**：使用 `LD_PRELOAD` 确保子进程继承设置

**调试技巧**：
- 设置 `MAGNUM_LOG=verbose` 和 `HABITAT_SIM_LOG=verbose` 查看详细日志
- 使用最小测试脚本逐步验证每个环节
- 检查日志中的 `found X EGL devices` 确认 GPU 被检测到

#### 配置文件路径问题

**常见问题**：
- 配置文件引用的数据集名称与实际目录不匹配
- 场景数据集的实际目录结构与配置期望不一致

**排查方法**：
1. 检查配置文件中的 `data_path` 和 `scene_id` 路径
2. 使用符号链接统一路径结构
3. 创建最小测试脚本验证路径是否正确

### 五、复现其他 3D 视觉工作的通用检查清单

#### 环境检查
- [ ] GPU 驱动已安装：`nvidia-smi` 能正常显示
- [ ] CUDA 版本匹配：检查项目要求的 CUDA 版本
- [ ] EGL 库已安装：`apt-get install libegl1-mesa`（或使用 NVIDIA 版本）
- [ ] Python 环境正确：conda/venv 环境已激活

#### 图形渲染配置
- [ ] 设置无头模式：`export EGL_PLATFORM=surfaceless`
- [ ] 指定 GPU 设备：`export EGL_DEVICE_ID=0`（多 GPU 时）
- [ ] 强制使用硬件加速：设置 `LD_PRELOAD` 指向 NVIDIA 库
- [ ] 多进程环境：确保子进程继承环境变量

#### 数据集路径
- [ ] 场景数据集路径正确：检查 `scene_datasets/` 目录
- [ ] Episode 数据集路径正确：检查 `datasets/` 目录
- [ ] 配置文件中的路径与实际目录匹配
- [ ] 符号链接正确：使用 `ls -la` 检查符号链接

#### 调试技巧
- [ ] 启用详细日志：设置 `*_LOG=verbose` 环境变量
- [ ] 最小测试：创建简单的测试脚本验证每个组件
- [ ] 逐步排查：先测试 EGL 初始化，再测试场景加载，最后测试完整流程
- [ ] 日志重定向：`> log.txt 2>&1` 保存日志避免终端溢出

### 六、常见错误与解决方案速查

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `GL::Context: cannot retrieve OpenGL version` | EGL 初始化失败 | 设置 `EGL_PLATFORM=surfaceless` 和 `LD_PRELOAD` |
| `malloc_consolidate(): unaligned fastbin chunk detected` | 多进程环境下库加载冲突 | 使用 `LD_PRELOAD` 强制加载 NVIDIA 库 |
| `ImportError: libEGL.so.1` | EGL 库未安装 | `apt-get install libegl1-mesa` |
| `FileNotFoundError: Could not find dataset file` | 数据集路径不匹配 | 检查配置文件中的路径，创建符号链接 |
| `No Stage Attributes exists for requested scene` | 场景文件路径错误 | 检查场景数据集目录结构，创建缺失的符号链接 |




另外又一个优秀的东南大学博主[momo](https://xhslink.com/m/6aPeI4FNFV6)，其主要的笔记是一些SLAMer拓展技术栈Day n系列，我觉得这里的三维重建很有意思。同时他还是智元实习生！

还有这位[laumy的学习笔记](https://www.laumy.tech/)，非常牛逼，包括了一系列比如ROS2实践、ACT算法解析的文章博客。