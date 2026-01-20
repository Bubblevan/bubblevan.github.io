---
title: "多模态大模型"
weight: 1
---

2025年10月的[Multimodal large language models: A survey](https://arxiv.org/pdf/2506.10016v1)，主要是从任务和技术两个维度去总结的：
| 领域 | 阶段 | 关键技术与里程碑 |
| :--- | :--- | :--- |
| **1. Text-to-Text (T2T)**<br>MLLM 的基础 | **早期 (2015-2017)** | RNN encoder-decoder（神经机器翻译）→ 注意力机制（2016，动态聚焦输入序列）。 |
| | **突破 (2017-2020)** | Transformer 问世（2017）→ BERT（双向 Transformer，MLM 任务）、GPT-1（Decoder-only，零样本能力）、GPT-2（1.5B 参数，无需标注数据）。 |
| | **规模化 (2020-2025)** | **模型迭代：** GPT-3（175B 参数，少样本推理）、InstructGPT（RLHF 对齐人类偏好）；<br>**效率优化：** MoE 架构（GLaM、Mixtral 8x7B，激活部分参数降本）、Chinchilla（70B 参数，计算最优）；<br>**多模态扩展：** Gemini（文本+图像）、LLaMA 4（MoE+视觉支持）、GPT-4（文本+图像，减少幻觉）。 |
| **2. Text-to-Image (T2I)**<br>从 GAN 到扩散模型 | **早期 (2018-2020)** | GAN 主导（AttnGAN：文本-图像注意力对齐；MirrorGAN：语义重描述）。 |
| | **转型 (2021-2022)** | 扩散模型崛起 → DALL·E（Transformer autoregressive 生成图像 token）、GLIDE（3.5B 参数，支持图像修复）、CLIP（文本-图像对比预训练，奠定跨模态对齐基础）。 |
| | **成熟 (2023-2025)** | **基础模型：** Latent 扩散（Stable Diffusion，降低计算成本）、Imagen（用 LLM 做文本编码器，提升保真度）；<br>**可控性增强：** ControlNet（锁定预训练模型，新增可训练层，支持边缘/深度控制）、DALL·E 3（高质量图像 captioner 优化数据，提升 prompt 跟随能力）；<br>**多任务统一：** Janus（分离语义编码器+视觉 tokenizer）、Janus-Pro（优化训练策略）。 |
| **3. Text-to-Music (T2M)**<br>从波形到高保真音乐 | **早期 (2016-2019)** | WaveNet（卷积模型，生成 raw 波形）、NSynth（WaveNet autoencoder，音乐音符合成）、MusicVAE（层级循环解码器，缓解后验崩溃）。 |
| | **Transformer 时代 (2020-2023)** | MuseNet（MIDI 数据学习音乐模式）、Jukebox（VQ-VAE+Transformer，生成 raw 音频）、MusicGen（单阶段 Transformer，支持旋律控制）。 |
| | **扩散模型突破 (2023-2025)** | **生成能力：** Moûsai（两阶段 latent 扩散，50k 文本-音乐对，实时推理）、MusicLM（280k 小时数据，支持哼唱旋律生成）；<br>**效率与可控性：** Noise2Music（两阶段扩散，合成文本-音频对）、FLUX（端到端训练，低延迟）、Stable Audio Open（开源，多风格生成）。 |
| **4. Text-to-Video (T2V)**<br>时空一致性的挑战 | **早期 (2018-2021)** | GAN 主导（MoCoGAN：分离内容与运动；TiVGAN：T2I 生成首帧，逐步扩展视频）。 |
| | **扩散与 Transformer 融合 (2022-2024)** | **基础架构：** CogVideo（9B 参数，基于 CogView2，多帧率训练）、Make-A-Video（无文本-视频数据，从 T2I 迁移+无监督视频学习）；<br>**长视频能力：** Phenaki（离散视频 token，支持变长视频）、NUWA-XL（“Diffusion over Diffusion”，生成分钟级视频）。 |
| | **近期突破 (2024-2025)** | **前沿模型：** Lumiere（时空 U-Net，单步生成视频，提升连贯性）、VideoPoet（LLM-based，统一文本-视频/图像-视频任务）；<br>**物理规律建模：** Sora（Transformer 处理时空 patch，支持 1 分钟视频，首现涌现能力）、Cosmos（NVIDIA，融合物理模拟，用于机器人/自动驾驶）。 |
| **5. Text-to-Human-Motion (T2HM)**<br>人体运动学的精准匹配 | **早期 (2022)** | TEMOS（VAE+Transformer，生成多候选运动）、T2M-GPT（VQ-VAE 离散化运动，GPT 建模时序）。 |
| | **扩散与多模态控制 (2023-2024)** | **扩散模型：** MotionDiffuse（扩散模型，支持细粒度身体部位控制）、Fg-T2M（层级扩散，捕捉运动细节）；<br>**LLM 融合：** MotionGPT（LLaMA 微调，VQ-VAE 离散运动，支持文本/关键帧输入）、MotionGPT-2（部位感知 tokenization，多任务能力）。 |
| | **对齐人类偏好 (2025)** | MotionRL（多奖励 RL，优化真实感/文本对齐）、LightT2M（轻量模型，近实时生成）。 |
| **6. Text-to-3D-Objects (T2-3D)**<br>跨维度生成的难点 | **早期 (2022)** | 优化驱动 → DreamFusion（用 T2I 扩散模型做 prior，优化 NeRF，无需 3D 数据）、Magic3D（粗-细优化，40 分钟生成高质量 mesh）。 |
| | **效率提升 (2023-2024)** | **直接生成：** Point-E（点云生成，快速低耗）、Shap-E（前馈模型，单步生成 NeRF/mesh）、Instant3D（文本条件+三平面特征图，单步生成）；<br>**材质与光照：** Meta 3D Gen（PBR 材质，支持真实感光照，两阶段：多视图生成→3D 重建）。 |
| | **近期 (2025)** | VolumeDiffusion（体素扩散，平衡几何细节与渲染质量）。 |

| 核心技术 | 定义 | 跨模态应用 | 局限/挑战 |
| :--- | :--- | :--- | :--- |
| **Self-Supervised Learning (SSL)**<br>无标注数据的基础学习 | 通过 “预测输入隐藏部分”（如 masked token）从无标注数据学习，构建模态基础认知。 | - T2T：核心（GPT 系列用 autoregressive 预测下一个 token，学习语法/事实）；<br>- T2I：USP（latent 空间 masked 建模）、MAGE（语义 token masked 建模）；<br>- T2V：Make-A-Video（用无标注视频学习运动）、VITO（视频对比学习，提升视觉鲁棒性）； | T2-3D 因 3D 数据稀缺，SSL 应用极少。 |
| **Mixture of Experts (MoE)**<br>模块化效率提升 | 激活部分 “专家子网络” 处理输入，在不增计算成本的前提下提升模型容量。 | - T2T：GLaM（首次大规模 MoE）、Mixtral 8x7B（Top-2 路由，超 70B dense 模型）、LLaMA 4（16-128 专家，分 “Scout/Maverick/Behemoth” 变体）；<br>- T2I：ERNIE-ViLG 2.0（MoDE，专家负责不同扩散时序）、DiT-MoE（替换 MLP 为 MoE，提升 FID）；<br>- T2V：CogVideoX（专家 Transformer + 自适应 LayerNorm，跨模态融合）； | T2M 因音乐时序连贯性要求高，MoE 应用罕见。 |
| **Reinforcement Learning from Human Feedback (RLHF)**<br>对齐人类偏好 | 通过 “监督微调（SFT）→ 奖励模型（RM）→ 强化学习（如 PPO）” 三阶段，使模型输出匹配人类偏好。 | - T2T：InstructGPT（首用 RLHF）、Sparrow（规则奖励 + 事实 grounding）、CGPO（约束优化，抑制奖励攻击）；<br>- T2I：ImageReward（首个 T2I 奖励模型）、DDPO（扩散模型直接用策略梯度）；<br>- T2V：VideoFeedback（首份 T2V 人类偏好数据集）、VADER（奖励梯度直接反向传播）；<br>- T2-3D：DreamAlign（D-3DPO，LoRA 微调多视图扩散模型）、DreamReward（Reward3D 奖励模型）。 | 无明确局限，是跨模态对齐的核心方案 |
| **Chain-of-Thought (CoT)**<br>推理时结构化思考 | 推理时生成中间步骤，提升多步任务准确性，适用于复杂推理。 | - T2T：Test-Time Preference Optimization（迭代自优化）、Step Back to Leap Forward（回溯纠错）；<br>- 多模态：ReflectionFlow（T2I 生成-反馈-优化循环）、Video-T1（视频生成多阶段推理）、EC-DiT（专家选择路由，动态分配计算）； | 非文本模态 “中间步骤” 难定义（如视觉需用布局/草图表示 “思考”）。 |

但是还是应该从项目入手，这样快一些。
