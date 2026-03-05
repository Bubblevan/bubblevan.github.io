---
title: "InternNav数据集构建"
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