---
date: 2026-03-10
title: InternNav L20测试
authors: [bubblevan]
tags: []
---

首先仿照[隔壁](./2026-03-10-remote-proxy.md)的配置，在远程服务器上配置codex，然后之后打算是以问答的形式来记录自己的实验过程。

## Q1
https://huggingface.co/datasets/InternRobotics/InternData-N1/tree/main/vln_ce/traj_data/r2r
这个里面我想跑通一个mini的vln_ce r2r的情景，因为df -h的不够多空间，而traj_data都非常大（还要解压），我的项目放在/root/backup/InternNav，数据理论上应该放在/root/backup/InternNav/data/vln_ce。
我不跑训练，只跑评估。你可以看一看目前的闭环可不可以跑其中的一点点子数据集。我们必须从下面的main branch里选而不能在v0.1-mini分支上，因为后者不包含深度图等更新；我们已经有了部署conda环境internnav和运行habitat的habitat环境。
```bash
(base) root@iZuf6fncnfdmvnrvlwsp6dZ:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
tmpfs            13G  1.2M   13G   1% /run
/dev/nvme0n1p3  197G  118G   71G  63% /
tmpfs            62G     0   62G   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
/dev/nvme0n1p2  197M  6.1M  191M   4% /boot/efi
tmpfs            13G   80K   13G   1% /run/user/0
tmpfs            13G  4.0K   13G   1% /run/user/1000
```

`./hfd.sh InternRobotics/InternData-N1 --dataset --include "vln_ce/traj_data/r2r/**"`
| 文件名 | 大小 |
|--------|------|
| 17DRP5sb8fy.tar.gz | 1.54 GB |
| 1LXtFkjw3qL.tar.gz | 4.36 GB |
| 1pXnuDYAj8r.tar.gz | 8.92 GB |
| 29hnd4uzFmX.tar.gz | 4.65 GB |
| 2n8kARJN3HM.tar.gz | 8.34 GB |
| 5LpN3gDmAk7.tar.gz | 6.3 GB |
| 5q7pvUzZiYa.tar.gz | 3.84 GB |
| 759xd9YjKW5.tar.gz | 9.1 GB |
| 7y3sRwLe3Va.tar.gz | 4.64 GB |
| 82sE5b5pLXE.tar.gz | 5.47 GB |
| 8WUmhLawc2A.tar.gz | 8.96 GB |
| B6ByNegPMKs.tar.gz | 4.94 GB |
| D7G3Y4RVNrH.tar.gz | 1.17 GB |
| D7N2EKCX4Sj.tar.gz | 8.77 GB |
| E9uDoFAP3SH.tar.gz | 12.7 GB |
| EDJbREhghzL.tar.gz | 8.07 GB |
| GdvgFV5R1Z5.tar.gz | 685 MB |
| HxpKQynjfin.tar.gz | 359 MB |
| JF19kD82Mey.tar.gz | 1.97 GB |
| JeFG25nYj2p.tar.gz | 6.94 GB |
| JmbYfDe2QKZ.tar.gz | 7.43 GB |
| PX4nDJXEHrG.tar.gz | 6.59 GB |
| Pm6F8kyY3z2.tar.gz | 692 MB |
| PuKPg4mmafe.tar.gz | 3.05 GB |
| S9hNv5qa7GM.tar.gz | 6.63 GB |
| SN83YJsR3w2.tar.gz | 8 GB |
| ULsKaCPVFJR.tar.gz | 5.32 GB |
| Uxmj2M2itWa.tar.gz | 6.49 GB |
| V2XKFyX4ASd.tar.gz | 7 GB |
| VFuaQ6m2Qom.tar.gz | 4.14 GB |
| VLzqgDo317F.tar.gz | 8.05 GB |
| VVfe2KiqLaN.tar.gz | 2.92 GB |
| Vvot9Ly1tCj.tar.gz | 8.29 GB |
| VzqfbhrpDEA.tar.gz | 5.87 GB |
| XcA2TqTSSAj.tar.gz | 429 MB |
| YmJkqBEsHnH.tar.gz | 236 MB |
| ZMojNkEp431.tar.gz | 9.45 GB |
| aayBHfsNo7d.tar.gz | 4.21 GB |
| ac26ZMwG7aT.tar.gz | 9.6 GB |
| b8cTxDM8gDG.tar.gz | 4.68 GB |
| cV4RVeZvu5T.tar.gz | 3.81 GB |
| dhjEzFoUFzH.tar.gz | 1.91 GB |
| e9zR4mvMWw7.tar.gz | 3.79 GB |
| gTV8FGcVJC9.tar.gz | 7.47 GB |
| gZ6f7yhEvPG.tar.gz | 69.2 MB |
| i5noydFURQK.tar.gz | 4.4 GB |
| jh4fc5c5qoQ.tar.gz | 4.13 GB |
| kEZ7cmS4wCh.tar.gz | 5.73 GB |
| mJXqzFtmKg4.tar.gz | 6.58 GB |
| p5wJjkQkbXX.tar.gz | 8.46 GB |
| pRbA3pwrgk9.tar.gz | 3.78 GB |
| qoiz87JEwZ2.tar.gz | 6 GB |
| r1Q1Z4BcV1o.tar.gz | 8.41 GB |
| r47D5H71a5s.tar.gz | 7.96 GB |
| rPc6DW4iMge.tar.gz | 4.97 GB |
| s8pcmisQ38h.tar.gz | 2.99 GB |
| sKLMLpTHeUy.tar.gz | 5.77 GB |
| sT4fr6TAbpF.tar.gz | 6.04 GB |
| uNb9QFRL6hY.tar.gz | 3.64 GB |
| ur6pFq6Qu1A.tar.gz | 7.23 GB |
| vyrNrziPKCB.tar.gz | 10.1 GB |

DualVLN的输出和指标类似：
```bash
Eval Epoch 0 Rank 0: 67%|████████████████████████████████████████████████████████████████████████████████████████▉ | 1230/1839 [14:20:01<3:57:09, 23.37s/it][12:56:34.541086] scene_episode Z6MFQCViBuw_1659 success: 1.0, spl: 0.915552915929419, os: 1.0, ne: 0.06489334255456924 [12:56:36.474658] episode start Go down the path on the left towards the large dining room. Enter and go down the red carpet on the right side of the room, stopping at the door leading into another room. [12:56:36.700972] step_id: 0 output text: ↓ [12:56:36.701063] actions [5] [12:56:36.701105] step_id 0 action 5 [12:56:37.242942] step_id: 0 output text: 303 186 [12:56:37.935475] predicted goal [186, 303] [12:56:37.935538] step_id 0 action 3 [12:56:38.039915] step_id 1 action 3 [12:56:38.147404] step_id 2 action 3 [12:56:38.259146] step_id 3 action 1 [12:56:38.624357] local_actions [1, 1, 2, 1] [12:56:38.624416] step_id 4 action 1 [12:56:38.726116] step_id 5 action 1 [12:56:38.838516] step_id 6 action 2 [12:56:38.954433] step_id 7 action 1 [12:56:39.327402] local_actions [2, 1, 1, 2] [12:56:40.001080] step_id: 9 output text: ←← [12:56:40.001175] actions [2, 2] [12:56:40.001218] step_id 9 action 2 [12:56:40.113763] step_id 10 action 2 [12:56:41.012306] step_id: 11 output text: ↓ [12:56:41.012415] actions [5] [12:56:41.012456] step_id 11 action 5 [12:56:42.518175] step_id: 11 output text: 190 188 [12:56:43.615070] predicted goal [188, 190] [12:56:43.615151] step_id 11 action 1 [12:56:43.727561] step_id 12 action 2 [12:56:43.843558] step_id 13 action 1 [12:56:43.957890] step_id 14 action 1 [12:56:44.295122] local_actions [1, 1, 2, 1] [12:56:44.295199] step_id 15 action 1 [12:56:44.407580] step_id 16 action 1 [12:56:44.525595] step_id 17 action 2 [12:56:44.644094] step_id 18 action 1 [12:56:45.008275] local_actions [1, 1, 1, 1] [12:56:45.794590] step_id: 20 output text: ↓ [12:56:45.794689] actions [5] [12:56:45.794732] step_id 20 action 5 [12:56:47.261735] step_id: 20 output text: 340 178 [12:56:48.264287] predicted goal [178, 340] [12:56:48.264363] step_id 20 action 1 [12:56:48.380687] step_id 21 action 1 [12:56:48.497173] step_id 22 action 3 [12:56:48.613465] step_id 23 action 1 [12:56:48.947505] local_actions [1, 1, 2, 1] [12:56:48.947570] step_id 24 action 1 [12:56:49.053366] step_id 25 action 1 [12:56:49.161661] step_id 26 action 2 [12:56:49.277904] step_id 27 action 1 [12:56:49.640776] local_actions [1, 1, 1, 1] [12:56:50.549755] step_id: 29 output text: ↓ [12:56:50.549844] actions [5] [12:56:50.549884] step_id 29 action 5 [12:56:51.814697] step_id: 29 output text: 326 170 [12:56:52.895622] predicted goal [170, 326] [12:56:52.895699] step_id 29 action 1 [12:56:53.013051] step_id 30 action 1 [12:56:53.130480] step_id 31 action 1 [12:56:53.240816] step_id 32 action 1 [12:56:53.564363] local_actions [1, 1, 1, 1] [12:56:53.564429] step_id 33 action 1 [12:56:53.668916] step_id 34 action 1 [12:56:53.771155] step_id 35 action 1 [12:56:53.878551] step_id 36 action 1 [12:56:54.252163] local_actions [1, 1, 1, 1] [12:56:55.200071] step_id: 38 output text: ↓ [12:56:55.200173] actions [5] [12:56:55.200216] step_id 38 action 5 [12:56:56.362000] step_id: 38 output text: 461 192 [12:56:57.602518] predicted goal [192, 461] [12:56:57.602590] step_id 38 action 1 [12:56:57.720162] step_id 39 action 1 [12:56:57.838709] step_id 40 action 1 [12:56:57.951833] step_id 41 action 3 [12:56:58.288404] local_actions [1, 1, 3, 1] [12:56:58.288465] step_id 42 action 1 [12:56:58.392835] step_id 43 action 1 [12:56:58.496285] step_id 44 action 3 [12:56:58.599396] step_id 45 action 1 [12:56:58.964277] local_actions [1, 1, 1, 1] [12:56:59.750044] step_id: 47 output text: ↓ [12:56:59.750138] actions [5] [12:56:59.750180] step_id 47 action 5 [12:57:01.110274] step_id: 47 output text: 378 182 [12:57:02.199320] predicted goal [182, 378] [12:57:02.199384] step_id 47 action 1 [12:57:02.300812] step_id 48 action 3 [12:57:02.400004] step_id 49 action 1 [12:57:02.500297] step_id 50 action 1 [12:57:02.817614] local_actions [1, 1, 1, 1] [12:57:02.817672] step_id 51 action 1 [12:57:02.917863] step_id 52 action 1 [12:57:03.017076] step_id 53 action 1 [12:57:03.116799] step_id 54 action 1 [12:57:03.433189] local_actions [1, 1, 2, 1] [12:57:04.056655] step_id: 56 output text: ↓ [12:57:04.056751] actions [5] [12:57:04.056791] step_id 56 action 5 [12:57:05.104714] step_id: 56 output text: 153 200 [12:57:06.171620] predicted goal [200, 153] [12:57:06.171693] step_id 56 action 1 [12:57:06.277197] step_id 57 action 1 [12:57:06.389925] step_id 58 action 1 [12:57:06.506230] step_id 59 action 2 [12:57:06.850964] local_actions [1, 2, 1, 1] [12:57:06.851045] step_id 60 action 1 [12:57:06.964593] step_id 61 action 2 [12:57:07.079851] step_id 62 action 1 [12:57:07.198388] step_id 63 action 1 [12:57:07.567827] local_actions [1, 1, 1, 1] [12:57:08.303806] step_id: 65 output text: ↓ [12:57:08.303896] actions [5] [12:57:08.303940] step_id 65 action 5 [12:57:09.710926] step_id: 65 output text: 258 167 [12:57:10.791876] predicted goal [167, 258] [12:57:10.791951] step_id 65 action 1 [12:57:10.909473] step_id 66 action 1 [12:57:11.023748] step_id 67 action 2 [12:57:11.130843] step_id 68 action 1 [12:57:11.481141] local_actions [1, 1, 1, 3] [12:57:11.481203] step_id 69 action 1 [12:57:11.598766] step_id 70 action 1 [12:57:11.712944] step_id 71 action 1 [12:57:11.826639] step_id 72 action 3 [12:57:12.156299] local_actions [1, 1, 2, 1] [12:57:12.925022] step_id: 74 output text: ↓ [12:57:12.925116] actions [5] [12:57:12.925158] step_id 74 action 5 [12:57:14.435768] step_id: 74 output text: 273 158 [12:57:15.453423] predicted goal [158, 273] [12:57:15.453499] step_id 74 action 1 [12:57:15.565128] step_id 75 action 1 [12:57:15.681188] step_id 76 action 1 [12:57:15.797470] step_id 77 action 2 [12:57:16.131290] local_actions [1, 1, 1, 3] [12:57:16.131362] step_id 78 action 1 [12:57:16.246393] step_id 79 action 1 [12:57:16.362671] step_id 80 action 1 [12:57:16.476910] step_id 81 action 3 [12:57:16.841838] local_actions [1, 2, 1, 3] [12:57:17.504574] step_id: 83 output text: ↓ [12:57:17.504670] actions [5] [12:57:17.504711] step_id 83 action 5 [12:57:19.062974] step_id: 83 output text: 270 180 [12:57:20.139053] predicted goal [180, 270] [12:57:20.139135] step_id 83 action 1 [12:57:20.250935] step_id 84 action 1 [12:57:20.369112] step_id 85 action 2 [12:57:20.485345] step_id 86 action 1 [12:57:20.814544] local_actions [1, 1, 3, 1] [12:57:20.814600] step_id 87 action 1 [12:57:20.915530] step_id 88 action 1 [12:57:21.014032] step_id 89 action 3 [12:57:21.114450] step_id 90 action 1 [12:57:21.430977] local_actions [1, 2, 1, 3] [12:57:22.052870] step_id: 92 output text: STOP [12:57:22.052962] actions [0] [12:57:22.053003] step_id 92 action 0 ... [00:14:27.035234] {'sucs_all': 0.6432843804359436, 'spls_all': 0.5849772584175172, 'oss_all': 0.7020119428634644, 'nes_all': 4.159605979919434, 'length': 1839}
```
另外我需要你在以上指标的基础上，在跑 habitat_dual_system_cfg.py，额外记录： 
Success / SPL / Oracle Success / Navigation Error
每个 episode 的总 wall-clock 时间
平均每步 wall-clock 时间
每个 episode 的 S2 调用次数
STOP 比例、pixel_goal 比例等行为统计

同时，生成一个 Habitat replay 子集：随机选取 20~100 个 episode，在每个决策步保存：
episode_id, instruction, step_id
RGB 原始图、depth 图、pose 信息
历史帧索引（因为 num_history=8）
baseline 输出（动作、pixel_goal 等）
这个 replay 子集将用于 L20 离线压测，保证输入固定可比。

因为我们运行scripts/realworld的真机部署的时候延迟很大，有400ms，我们怀疑是很多时候System2都在输出离散动作，而没有输出pixel goal使其进入System1从而完成大小脑循环。但是现在我没有Unitree Go2实机了，所以我只能在服务器上用Habitat仿真去拆解 DualVLN 的耗时分布，找出瓶颈是 S2 还是 S1，还是交互开销。目前暂时想出来的方法是（如果你研究代码之后发现更好的你也可以补充）在 internnav/agent/internvla_n1_agent.py 的 step() 中插入计时点：
should_infer_s2() 判断是否触发 S2
policy.s2_step(...) 耗时
根据输出类型分支：
如果直接返回离散动作，则无 S1
如果返回 latent，则 policy.s1_step_latent(...) 耗时，并统计连续执行步数
收集整个 episode 的统计数据（S2 调用次数、S1 平均执行步数、各模块耗时）。
意义：回答“到底是不是 S2 拖慢？双系统交接是否发生？”为后续优化方向提供依据。

最后在replay 子集跑 DualVLN 原始版本（注意：这里是直接用 DualVLN checkpoint 在离线模式下推理，但不依赖 Habitat 环境——即用保存的观测喂给模型，只测推理部分）。记录：
冷启动加载时间
warm latency (p50/p95/max)
tokens per second
生成长度
GPU 峰值显存
输出与 baseline 的一致性（动作或 pixel_goal 误差）
这步得到的是“DualVLN 在 L20 上的纯推理基线”。

这之后是打算在 L20 上，对 DualVLN 应用 单一优化变量（例如量化 INT8、启用 KV cache、或换推理后端），重复周三的离线评测。
比较延迟、显存、输出一致性，挑选出收益最大的优化方向。然后放回去Habitat跑闭环评测，看功能指标（Success/SPL 等）是否退化。

## A1
评估居然不用`traj_data`吗？那我得把rxr和scalevln给下下来（先不慌）
跑完 `python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_mini_cfg.py` 后可以在 `logs/habitat/test_dual_system_mini` 下看到：
- progress.json：每个 episode 的功能指标 + 耗时/行为统计
- runtime_rank0.jsonl / runtime_summary_rank0.json：模块级耗时汇总
- replay_subset/manifest_rank0.jsonl：离线 replay 清单
这是只有8个Episode做smoke test的mini版本，既然不依赖traj_data那还可以跑全量评估：`python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_smoke_cfg.py`

## Q2
评估`python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_mini_cfg.py` 后 `/root/backup/InternNav/logs_example/habitat/test_dual_system_mini` 得到的结果。除了常规还要看一下延时等信息是否和之前realworld的推测一样
并把你刚刚两轮对话做出的修改写进/root/backup/InternNav/changelog/2026-3-10中，要详细一点。写两个文件，一个是技术一点的描述对哪些代码文件做出的哪些修改（方便我日后Traceback），一个是给老板看的我今天做了啥进展是什么，下一步计划是什么（后面这个想象你在写Word而不是Markdown，比如不要用太多无序列表之类的，然后段落式尽量描述的好一些，把整体思路体现出来，然后说明我们3-10做的是目前的哪一个环节） 
然后看看下一步我们要做什么实验去跑，KV Cache优化还是量化之类的

## A2
得到了`/root/backup/InternNav/changelog/2026-3-10`下的两版文件
从 result.json 和 runtime_summary_rank0.json 看，8 个 episode 的功能指标是 Success=0.875、SPL=0.775、Oracle Success=0.875、Navigation Error=1.023。延时上，平均每步 wall-clock 约 0.509s，S2 单次平均约 0.520s，S1 单次平均约 0.153s。这说明模型侧的主瓶颈确实是 S2，不是 S1。同时，pixel_goal_ratio 约 0.375，discrete_ratio 约 0.625，也就是 S2 更常直接输出离散动作，而不是把控制权交给 S1。这一点和我对真机高延迟的怀疑是一致的。
但另一个同样重要的结论是：不是“根本没进 S1”。从 runtime_rank0.jsonl 看，8 个 episode 里总 S2 调用是 178，总 S1 调用是 185，而且每次进入 S1 后平均可连续执行大约 8.6 步。所以更准确的判断是：S1 在发生，但 S2 仍占主导，而且闭环总延迟不只来自模型。把 S2 generate + S2 latent + S1 generate 全部加起来，也只占总 wall-clock 的大约 38%，剩下六成左右是在 Habitat 交互、look-down 取帧、预处理和 Python 侧流程上消耗掉的。

## Q3
1、继续把离线 replay benchmark 脚本补强成一版更适合 L20 对比实验的结果格式
2、为我解释一下代码的架构，比如说整体大小脑的框架，就放在/docs里吧，我还是不太明白，你带着我过一遍数据流在代码里是怎么做的，比如输入的数据包含哪些，然后分别是怎么在Internnav代码里进去的，模型s2和s1的step等等
3、为我构思一下KV cache / 推理后端 应该如何去优化
4、更新/root/backup/InternNav/changelog/2026-3-10的两个文档，在你所做的新修改内容的基础上，你需要额外加对指标的解释，比如wall-clock老板可能不知道是什么，然后要在那个txt文件里一方面解释指标的含义，一方面要列出具体的数据

## A3

> 其中前4个是必填
```bash
cd /root/backup/InternNav
export TOKENIZERS_PARALLELISM=false
python -u scripts/eval/tools/benchmark_dualvln_replay.py \
  --manifest /root/backup/InternNav/logs_example/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output /root/backup/InternNav/logs_example/habitat/test_dual_system_mini/replay_summary_debug.json \
  --base-path /root/backup/InternNav/logs_example \
  --max-steps 10 \
  --verbose-every 1
```
因为出现了卡死的问题，所以这里先跑上面没问题了再跑全量：
```bash
python -u scripts/eval/tools/benchmark_dualvln_replay.py \
  --manifest /root/backup/InternNav/logs_example/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output /root/backup/InternNav/logs_example/habitat/test_dual_system_mini/replay_summary.json \
  --base-path /root/backup/InternNav/logs_example \
  --verbose-every 20
```

先用现在这版 replay benchmark 在 L20 上跑一轮原始 DualVLN 基线。
1. 第一优先级做 num_history / prompt 长度 / max_new_tokens 缩减实验。
2. 第二优先级做 KV cache 和 S2-only 推理后端 实验。
3. 第三优先级再做量化，并始终用 replay 一致性先筛一轮，再放回 Habitat 闭环。

