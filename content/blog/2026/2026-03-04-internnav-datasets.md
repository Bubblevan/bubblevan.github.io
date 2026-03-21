---
date: 2026-03-04
title: InternNav数据集构建
authors: [bubblevan]
tags: []
---

## NavPixelGoalDataset
NavPixelGoalDataset 不是随便一个 jsonl 就行，它会**从 LeRobot traj_data 里反推训练样本**：

- 先遍历 `meta/episodes.jsonl`，再读每个 episode 的 parquet。
- parquet 里它期望至少有：
  - `action`（离散动作序列）
  - `pose.<setting>`（某个高度/俯仰设置下的位姿序列）
  - `goal.<setting>`（每步对应的像素目标）
  - `relative_goal_frame_id.<setting>`（像素目标对应的“未来第几帧/多长 horizon”）
- 并且它会把数据拆成三类样本混合训练：
  - pixel goal 样本（能投影出像素目标）
  - turn 样本（当 `relative_goal_frame_id == -1` 时走 turn 分支）
  - stop 样本（终止）
- 同时它强依赖 **两种俯仰视角**（`pitch_1` / `pitch_2`，并读取 lookdown 的 rgb+depth 来生成轨迹相关输入）。

难点不是 LeRobot 格式本身，而是你要补齐/生成这些“导航专用监督”：

* `pose.*`：你要有每帧位姿（仿真真值或 SLAM/VIO）
* `goal.*` + `relative_goal_frame_id.*`：你要为每个时刻选一个**未来 waypoint**，并把它**投影成当前视角的像素坐标**（投影还要考虑相机外参/内参/坐标系约定）
* 以及“看不见目标时的 turn 监督”逻辑（代码里就是 `relative_goal_frame_id == -1` 这种分支）([GitHub][1])

你在另一个数据集代码里也能看到他们投影像素的典型做法：用 `camera_intrinsic` + `camera_extrinsic` 把 3D 目标点变到相机坐标再算 pixel（含坐标轴变换）。
这一步在真实场景/互联网视频里最容易崩（外参误差、深度噪声、坐标系不一致、目标点选择不稳定）。

## LazySupervisedDataset
LazySupervisedDataset 读的是一个 annotation_path（json 或 jsonl），里面每条样本是类似 LLaVA/ShareGPT 风格的 conversations，并且可选带 "image" 或 "video" 字段；代码会统计 token 长度、按需解码视频帧等。
开源方法非常成熟，比如我们造ScanQA得到jsonl数据：
```bash
{"video": "videos/scene0000_00.mp4", "conversations": [{"from": "human", "value": "<video>\nWhat is in the right corner of room by curtains? Answer briefly."}, {"from": "gpt", "value": "brown cabinet with tv sitting in it"}]}
```
1. 采集：只要 RGB（可选再加 depth），按 episode 存视频/帧
2. teacher 生成 label（开源即可）：
   - 仿真：ShortestPathFollower / 经典 planner 输出 next action 或 waypoint
   - 真实：你现有 InternNav baseline 输出 action / pixel-goal 也行（相当于 self-training）
3. 写 annotation.jsonl：每条样本把 instruction 写进 user，把 teacher 输出写进 assistant
这个数据对“提升语言遵循/稳定性/一致性”很有效，而且工程成本低。

ScanQA和SQA3D都是3D场景理解领域著名的问答数据集，但它们的核心任务和设计目标有显著不同。简单来说，ScanQA侧重于物体定位与描述的“场景问答”，而SQA3D侧重于智能体在特定状态下进行推理的“情境问答”。
| 维度 | ScanQA | SQA3D |
| :--- | :--- | :--- |
| **核心任务** | 根据整个3D场景回答文本问题，并定位出问题所描述的**3D物体**。 | 根据文本描述指定的**情境**（如智能体的位置、朝向），回答关于周围环境的问题。 |
| **关键创新** | 首次将**2D图像问答（VQA）任务扩展到3D空间**，使模型能基于完整的3D点云场景进行问答。 | 引入了“**情境**”的概念，要求模型不仅要理解场景，还要理解智能体在场景中的“状态”（位置、视角）。 |
| **输入信息** | - 3D场景（点云）<br>- 自然语言问题 | - 3D场景（点云）<br>- **情境描述（文本）** <br>- 自然语言问题 |
| **输出形式** | - 自然语言答案<br>- 与答案相关的**3D物体边界框** | - 自然语言答案 |
| **数据规模** | - **场景数**：800个（ScanNet场景）<br>- **问答对**：约41,000个 | - **场景数**：650个（ScanNet场景）<br>- **问答对**：约33,400个<br>- **独特情境**：约6,800个 |

- **ScanQA：做“定位式”的3D场景问答**
    ScanQA的任务设计更像是一个“升级版”的3D物体定位。例如，当问题问到“**桌子旁边的蓝色椅子是什么材质？**”时，模型不仅要回答出“**布料**”，还要在3D场景中准确地框出那把“**蓝色椅子**”。它将**问答**与**物体 grounding**紧密结合，要求模型真正理解问题所指的对象。

- **SQA3D：做“沉浸式”的智能体情境推理**
    SQA3D则更侧重于**具身智能**（Embodied AI）的推理。它设想一个智能体置身于场景中，需要先理解自己“**身在何处**”以及“**面朝何方**”。例如，任务会先给定一个情境描述：“**你站在沙发旁边，面对着电视**。”，然后提出问题：“**你左手边有什么家具？**”。模型必须基于这个指定的虚拟位置和朝向，去推理周围的环境，这对空间理解和常识推理的要求更高。

可以说，**ScanQA为3D视觉语言任务奠定了“看图说话+指物”的基础**，而**SQA3D则更进一步，将问题置于一个动态的、以智能体为中心的“情境”中**，更贴近机器人等智能体在真实3D环境中交互和推理的需求。目前，这两个数据集已成为3D视觉语言领域最常用的基准之一，新提出的模型通常会同时在两个数据集上进行评测，以验证其综合性能。

## A0
### 1. 现在算「多轮」吗？

**不算。**  
你这次是 `num_train_epochs=0.01` + `max_steps=100`，只是**短验证**：最多 100 步、约 1% 个 epoch，用来确认流程能跑通，没有做正式多轮训练。
HuggingFace Trainer 里 **`num_train_epochs` 可以是小数**：
- 总步数 = `num_train_epochs × 每个 epoch 的步数`
- **0.01** = 只跑「1% 个 epoch」，总步数约为 1 个完整 epoch 的 1%，适合快速试跑。
- 若同时给了 **`max_steps`**，会**先按步数停**：到 100 步就结束，所以你这回就是严格 100 步。
### 2. 怎么测试训好的 ckpt 能不能做 ScanQA 式 VQA？
目标：用**你保存的 ckpt**（例如 `checkpoints/sft_lazy_only`）加载，输入「视频 + 问题」，看生成答案是否合理。
- **定性测试**：用同一套模型加载方式（和训练时一致），从 ScanQA 的 jsonl 里取几条，每条用「video + question」做一次 `model.generate(...)`，看答案是否在描述场景、是否乱说。
- **定量测试**：对 ScanQA 的 val（若有）全量跑一遍「视频+问题 → 生成答案」，和 GT 比准确率或语义相似度；仓库里没有现成 ScanQA 评测脚本，需要自己写一小段（加载 ckpt + 读 jsonl + generate + 写结果/算分）。

模型加载可参考：`internnav/agent/internvla_n1_agent.py` 或 `scripts/realworld/http_internvla_server.py`，把 `model_name_or_path` 换成你的 `output_dir` 即可。

### 3. 训多轮时：怎么知道 VQA 上去、R2R 不跌？
**做法就是「双轴评估」+ 混训（co-train）：**
| 想看什么 | 怎么做 |
|----------|--------|
| **ScanQA/VQA 能力** | 用同一 ckpt 在 ScanQA（或你的 VQA val）上做「图/视频 + 问题 → 生成答案」，和 GT 比，看训后是否比训前好。 |
| **R2R 导航不跌** | 用仓库里现有 **R2R/Habitat 评测**（如 `scripts/eval/` 下的 VLN 脚本），把模型路径指到你训好的 ckpt，在 R2R val 上跑 **SR、SPL**；训前跑一次记 baseline，训后同 val 再跑，看是否明显掉点。 |
| **为何要 co-train** | 只训 ScanQA 容易忘导航，只训 R2R 没有注入 VQA。**R2R + ScanQA 一起训**就是为了：R2R 拉住导航，ScanQA 注入场景理解，两边平衡。 |

建议：训前在 R2R val 打一次 SR/SPL；训的过程中每隔一两千步在 R2R val 再测，若连续掉就提前停或回退；训后再用同一 ckpt 既测 R2R 又测 ScanQA/VQA。

### 4. 多轮时 max_steps、epochs 等怎么设？
- **epoch 与步数**：要么用 **`max_steps`**（如 5000、10000）控制总长，要么用 **`num_train_epochs`**（如 1.0、3.0）。同时给时，Trainer 会按 **max_steps** 先停。
- **保存与回退**：`--save_strategy "steps" --save_steps 2000 --save_total_limit 3`，方便按 step 做 R2R val 并回退到某个 ckpt。
- **学习率 / 比例**：小学习率（如 2e-5）、R2R 为主（例如 70%～80% 步数来自 R2R），减少导航遗忘。

**示例（多轮混训）：**

```bash
--num_train_epochs 3.0 \
--max_steps 10000 \
--save_strategy "steps" --save_steps 2000 --save_total_limit 3 \
--learning_rate 2e-5
```
其余参数（`--vln_dataset_use`、`--dataset_use`、`--deepspeed`、`--gradient_checkpointing`、`--output_dir` 等）和当前能跑通的那条混训命令保持一致即可。
更细的说明（含测试 ckpt、双轴评估、参数建议）已写在 **`docs/SFT_eval_and_multi_epoch.md`**，之后可以直接查这个文件。

## Q1
那假如我还需要将/root/gpufree-data/SocialNavSUB中的一部分拿来训练呢？我其实有点焦虑，因为我担心cotrain完了这个指标效果不好，于是想着加入我们的VQA Bench，但是我认为：
1、应该加上一个特殊的触发，不能让正常r2r的时候突然输出自然语言出来
2、我打算用SCAND做一个马甲，也就是正在/root/gpufree-data/SCAND里的其中一个样本，研究一下怎么在论文里说我们是怎么从rosbag构造到LazySupervisedDataset的，但是实际因为存储空间限制我们这里就直接用Socialnav-SUB的70%来作为SFT的训练集，而不用我们从SCAND跑通的数据管线
3、我们的全量训练只需要2~3个epoch就可以吗？当然我会视8卡A100的使用时间加钱，但是能省则省嘛

在下面的说明文档里，我们已经通过`num_train_epochs=0.01` + `max_steps=100`**短验证**了最多 100 步、约 1% 个 epoch的流程通跑通，没有做正式多轮训练。最终我们想达到的效果是**「双轴评估」+ 混训（co-train）：**

| 想看什么 | 怎么做 |
|----------|--------|
| **ScanQA/VQA 能力** | 用同一 ckpt 在 ScanQA（或你的 VQA val）上做「图/视频 + 问题 → 生成答案」，和 GT 比，看训后是否比训前好。 |
| **R2R 导航不跌** | 用仓库里现有 **R2R/Habitat 评测**（如 `scripts/eval/` 下的 VLN 脚本），把模型路径指到你训好的 ckpt，在 R2R val 上跑 **SR、SPL**；训前跑一次记 baseline，训后同 val 再跑，看是否明显掉点。 |
| **为何要 co-train** | 只训 ScanQA 容易忘导航，只训 R2R 没有注入 VQA。**R2R + ScanQA 一起训**就是为了：R2R 拉住导航，ScanQA 注入场景理解，两边平衡。 |

一个想法是我已经在训前 R2R val 打一次 SR/SPL 为`{'sucs_all': 0.6432843804359436, 'spls_all': 0.5849772584175172, 'oss_all': 0.7020119428634644, 'nes_all': 4.159605979919434, 'length': 1839}`；训的过程中每隔一两千步在 R2R val 再测，若连续掉就提前停或回退；训后再用同一 ckpt 既测 R2R 又测 ScanQA/VQA。

更细的说明（含测试 ckpt、双轴评估、参数建议）已写在 **`docs/SFT_eval_and_multi_epoch.md`**，之后可以直接查这个文件。

## A1
### 1) 要不要“触发器”，避免 R2R 时输出自然语言？
要，强烈建议做**任务模式触发**（至少在 prompt 层）。

- **训练时**统一加模式前缀：
  - 导航样本：`[MODE: NAV]`（目标输出只允许箭头/动作格式）
  - VQA 样本：`[MODE: VQA]`（目标输出自然语言）
- **推理时**按任务设置 mode；R2R 评测永远用 `NAV`。
- 最稳的是再加一层**解码约束/后处理**（NAV 模式下只接受动作词表），即便模型偶发自然语言也能拦住。

这比“只靠数据自己学会分场景”更稳。

### 2) SocialNav-SUB + SCAND 马甲叙事可行吗？
可行，而且论文里这样写是合理的（只要透明）：

- **方法贡献**：说明你有从 SCAND（rosbag）到 LazySupervisedDataset 的可复用流程（可附 1 个样本/流程图）。
- **训练数据选择**：受存储/算力限制，正式实验采用 `SocialNav-SUB` 的 70% 作为社交 VQA 训练集。
- **不混淆**：明确“SCAND 流水线是可扩展能力验证，主实验数据源是 SocialNav-SUB 子集”。

这样审稿人一般能接受。

### 3) 全量训练 2~3 epoch 够吗？
**很可能够**，但不要只看 epoch，建议看 step + 验证曲线。

你现在有 R2R baseline：
- SR = `0.6433`
- SPL = `0.5850`

建议 guardrail（实用版）：
- 若新 ckpt 相比 baseline：
  - SR 下降超过 **1.5 个百分点**（absolute）或
  - SPL 下降超过 **1.0 个百分点**
  连续两次 eval 都这样，就停/回退。

建议训练节奏：
1. **pilot**：1k~2k steps（先看方向）
2. **main**：再到 5k~10k steps
3. **可选**：若 VQA 还在涨且 R2R 不掉，再继续

> 你担心“训烂”是对的，所以用“早停+回退+双轴评估”比死盯 2~3 epoch 更安全。  
你现在已经能跑 8 卡，直接在混训里加 `socialnav_sub` 即可。  
注意 `%` 是**各数据集自身采样率**，不是全局精确配比。

例如（示例）：
```bash
--vln_dataset_use "r2r_125cm_0_30_vln_ce%30,r2r_60cm_15_15_vln_ce%30" \
--dataset_use "scan_qa%20,socialnav_sub%70"
```

如果你想“VQA 内部以 SocialNav-SUB 为主”，这写法就基本满足你的意图。  
若想更精细控制占比，再用多次重复或调 `%` 做近似配平。

### 你现在最该做的下一步
1. 用 `socialnav_sub%70` 加进混训跑一个 **短程 1k~2k steps**。
2. 在 step 1000/2000 做一次 R2R val（SR/SPL）+ 一次 VQA 抽样评估。
3. 如果 VQA 明显涨、R2R 在 guardrail 内，就继续；否则回退并下调 VQA 比例。  

如果你愿意，我下一条可以直接给你一版“**带 mode 触发文案**”的数据模板（NAV/VQA 两套 prompt），你可以直接用于转换脚本。

## Q2
为我构造数据管线：
1、SCAND /root/gpufree-data/SCAND/ahg2library.bag到lazysupervisedDataset的jsonl
2、Socialnav-SUB到LazySupervisedDataset的jsonl
3、我想默认NAV（不要显式标出），带mode VQA才输出自然语言这样可以吗？

## A2
```bash
(habitat) root@gpufree-container:~/gpufree-data/InternNav# python /root/gpufree-data/InternNav/scripts/dataset_converters/scanqa_to_sft_jsonl.py \
  --input /root/gpufree-share/ScanQA/annotations/ScanQA_v1.0_train_reformat.json \
  --output /root/gpufree-share/ScanQA/annotations/scanqa_train_sft_vqa.jsonl \
  --video_subdir videos \
  --video_suffix .mp4 \
  --vqa_trigger "[MODE: VQA]"
Wrote 25563 lines to /root/gpufree-share/ScanQA/annotations/scanqa_train_sft_vqa.jsonl
Next: 在 data_dict 中设置 scan_qa 的 annotation_path 和 data_path（ScanQA 根目录），然后 --dataset_use scan_qa

python /root/gpufree-data/InternNav/scripts/dataset_converters/socialnav_sub_to_sft_jsonl.py \
  --data_dir /root/gpufree-data/SocialNavSUB/data \
  --output /root/gpufree-data/SocialNavSUB/data/annotations/socialnav_sub_sft_70_vqa.jsonl \
  --max_samples 41 \
  --vqa_trigger "[MODE: VQA]"

cd /root/gpufree-data/InternNav

# 从 DualVLN 加载，只训 S2（R2R + ScanQA + SocialNav-SUB 70%），S1 冻结
bash scripts/train/qwenvl_train/run_cotrain_r2r_scanqa_socialnav.sh
```
