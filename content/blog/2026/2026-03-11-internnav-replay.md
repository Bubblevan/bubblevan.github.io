---
date: 2026-03-11
title: Replay Benchmark
authors: [bubblevan]
tags: []
---

老板们搁这问"构建一个标准化测试集，这个想法好实现吗？"
感觉我们不在一个频道上
回复：
- 这里的replay是为了测DualVLN的s2在固定输入上的纯推理 latency，即num_history/prompt/max_new_tokens改了以后，速度和输出一致性怎么变，方便后面测如果加KV cache、换backend，模型本身能快多少
- 然后replay_v2是想要去深究一下为什么realworld里S1更少的问题，尽量复现闭环里哪些step真正触发 S2、哪些step只是同一个pixel-goal cycle的延续、当时的prompt、history、conversation到底是什么，或者去模拟realworld proxy/HTTP loopback，把图片编码、请求发送、服务端解码、返回动作加进来，测试看通信和服务化封装到底额外加了多少延时
- 不过对于replay_v2能不能实现这个命题还是要打个问号的，所以不太算是主线

## A1
**先跑闭环**  mini 子集：

```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_mini_cfg.py
```

> 如果想直接用完整 `val_unseen`，但只跑前 8 个 episode：

```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_smoke_cfg.py
```

跑完先看这几个文件：
- [progress.json](/root/backup/InternNav/logs/habitat/test_dual_system_mini/progress.json)
- [runtime_summary_rank0.json](/root/backup/InternNav/logs/habitat/test_dual_system_mini/runtime_summary_rank0.json)
- [manifest_rank0.jsonl](/root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl)

**再跑 replay baseline**
这是当前可用的纯推理基线命令：

```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
export TOKENIZERS_PARALLELISM=false
python -u scripts/eval/tools/benchmark_dualvln_replay.py \
  --manifest /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_summary.json \
  --base-path /root/backup/InternNav/logs \
  --num-history 8 \
  --prompt-variant full \
  --max-new-tokens 128 \
  --verbose-every 20
```

如果你想先做 10 步 sanity check：

```bash
python -u scripts/eval/tools/benchmark_dualvln_replay.py \
  --manifest /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_summary_debug.json \
  --base-path /root/backup/InternNav/logs \
  --num-history 8 \
  --prompt-variant full \
  --max-new-tokens 128 \
  --max-steps 10 \
  --verbose-every 1
```

**然后跑三组 sweep**
统一 runner 的命令是：

```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
export TOKENIZERS_PARALLELISM=false
python scripts/eval/tools/run_replay_benchmark_sweeps.py \
  --manifest /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output-dir /root/backup/InternNav/logs/habitat/test_dual_system_mini/sweeps \
  --base-path /root/backup/InternNav/logs \
  --verbose-every 20
```

它会自动扫：
- `num_history = 8, 4, 2, 0`
- `prompt_variant = full, short, minimal`
- `max_new_tokens = 128, 64, 32, 16`

结果会出在：
- `comparison_num_history.csv`
- `comparison_prompt.csv`
- `comparison_max_new_tokens.csv`
- `comparison_all.json`


## Q2
把 `replay_v2` 所需字段真正加进 [habitat_vln_evaluator.py]吧，尽量复现闭环里的决策上下文，比如哪些 step 真正触发了新的 S2，哪些 step 只是同一个 pixel-goal cycle 的延续，以及当时的 prompt、history、conversation 状态， HTTP loopback也要加上（不用额外造server，client可能需要自己造但尽量复用），原版replay benchmark保留

## A2
`replay_v2` 和 HTTP loopback 都已经加进去了，原版 replay benchmark 保留不动。

关键改动在 [habitat_vln_evaluator.py](/root/backup/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py#L190) 和 [habitat_vln_evaluator.py](/root/backup/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py#L591)。现在重新跑闭环后，会额外生成 `replay_subset_v2/manifest_rank0.jsonl`。每条记录除了旧版的 RGB/depth/lookdown/pose/baseline 外，还会带这些决策级字段：

- `record_id`
- `is_new_s2_decision`
- `is_lookdown_followup`
- `decision_id`
- `decision_step_offset`
- `pixel_goal_cycle_id`
- `cycle_step_offset`
- `action_source`
- `s1_regenerated_this_step`
- `decision_prompt_text`
- `decision_chat_text`
- `decision_input_image_paths`
- `conversation_messages`
- `s2_output_text`
- `s2_generated_token_count`
- `s2_output_kind`
- `s2_output_pixel`
- `s2_action_seq`
- `s1_initial_action_seq`
- `http_loopback` 请求元信息

旧版 `replay_subset` 仍然照常写，所以你现有的 [benchmark_dualvln_replay.py](/root/backup/InternNav/scripts/eval/tools/benchmark_dualvln_replay.py) 不受影响。

HTTP loopback 我做成了独立脚本：[benchmark_dualvln_http_loopback.py](/root/backup/InternNav/scripts/eval/tools/benchmark_dualvln_http_loopback.py#L21)。它不需要额外起 Flask server，而是在本地进程里模拟：

- client 侧 JPEG/PNG 编码
- server 侧解码
- `InternVLAN1AsyncAgent.step(...)`
- `LOOKDOWN -> look_down=True` 二次调用

如果 manifest 里有录下来的 lookdown 图，它还能直接复用。

你现在的使用顺序是：

1. 重新跑 mini 闭环，生成 `replay_subset_v2`
```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_mini_cfg.py
```

2. 跑原版纯推理 replay benchmark
```bash
export TOKENIZERS_PARALLELISM=false
python -u scripts/eval/tools/benchmark_dualvln_replay.py \
  --manifest /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_summary.json \
  --base-path /root/backup/InternNav/logs \
  --num-history 8 \
  --prompt-variant full \
  --max-new-tokens 128 \
  --verbose-every 20
```

3. 跑新的 HTTP loopback benchmark
```bash
export TOKENIZERS_PARALLELISM=false
python -u scripts/eval/tools/benchmark_dualvln_http_loopback.py \
  --manifest /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset_v2/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output /root/backup/InternNav/logs/habitat/test_dual_system_mini/http_loopback_summary.json \
  --base-path /root/backup/InternNav/logs \
  --num-history 8 \
  --plan-step-gap 4 \
  --use-recorded-lookdown \
  --verbose-every 20
```

我只做了 `py_compile` 静态检查，还没有替你实际重跑闭环或完整 benchmark。还有一个边界要说明：`replay_v2` 现在已经能区分“新 S2 决策”和“同一 pixel-goal cycle 的延续”，也保存了 prompt/history/conversation，但 evaluator 里原本就存在少量“提前 continue、不落盘”的分支，所以它已经比旧版严格很多，但还不是数学意义上的 100% 完全重放。

## Q3
每一次你改过文件之后都要记得把新增的字段和命令补写进 2026-3-11 changelog 和 docs，不应该让我每次都提醒
然后replay benchmark也测完了，为我分析结果，同时更新文档
## A3
后续在这个会话里我会把“代码改动 + 新字段 + 新命令 + 结果解释”一起同步到 `2026-3-11` 的 changelog 和相关 docs，不再等你提醒。

这次我分析的是 [replay_summary.json](/root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_summary.json)；当前我没看到新的 `http_loopback_summary.json`，所以还没法分析 loopback 那条链。

这轮结果和之前的判断一致，而且更清楚了。闭环本身在 [runtime_summary_rank0.json](/root/backup/InternNav/logs/habitat/test_dual_system_mini/runtime_summary_rank0.json) 里是健康的：`Success=1.0`、`SPL=0.911`、`Navigation Error=0.916`，平均每步 `wall-clock≈0.508s`，`S2≈0.513s`，`S1≈0.153s`，`pixel_goal_ratio≈0.370`，说明 Habitat 闭环里大小脑切换确实在发生，且模型级瓶颈还是 `S2`。

但离线 replay baseline 明显不是严格重放。它在 [replay_summary.json](/root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_summary.json) 里跑了 `8` 个 episode、`697` 个 step，`cold start≈3.51s`，`GPU peak≈17.5GB`，`total_step p50≈0.860s`，而 `s2_generate p50≈0.860s`，几乎重合，说明这条基线现在主要测到的是 `S2` 纯推理成本。更关键的是，一致性很差：`output_kind_match_rate≈0.298`，`action_match_rate_all≈0.280`，其中 `discrete` 步的一致率还有 `0.803`，但 `pixel_goal` 只有 `0.057`。我又补看了 confusion，结果是 `pixel_goal -> discrete = 477`，`pixel_goal -> pixel_goal = 12`，`discrete -> discrete = 196`，`discrete -> pixel_goal = 12`。所以结论很直接：当前 Level 1 replay 很适合做 `S2` 纯推理优化筛选，但不能直接拿来解释“为什么 realworld 里 S1 少”。

我刚核过，产物已经都在：
- [comparison_num_history.csv](/root/backup/InternNav/logs/habitat/test_dual_system_mini/sweeps/comparison_num_history.csv)
- [comparison_prompt.csv](/root/backup/InternNav/logs/habitat/test_dual_system_mini/sweeps/comparison_prompt.csv)
- [comparison_max_new_tokens.csv](/root/backup/InternNav/logs/habitat/test_dual_system_mini/sweeps/comparison_max_new_tokens.csv)
- [comparison_all.json](/root/backup/InternNav/logs/habitat/test_dual_system_mini/sweeps/comparison_all.json)

更重要的是，这三组结果的解释不是一样的：

- `max_new_tokens` 这组已经基本有结论了。`128 / 64 / 32 / 16` 几乎没差别，因为当前平均生成长度只有 `2.77 tokens`，所以这不是瓶颈。
- prompt 这组也基本有结论。`full / short / minimal` 只有毫秒级差异，说明 prompt 冗余不是主要瓶颈。
- **`num_history` 这组现在不能直接下结论。** 原因是当前 [benchmark_dualvln_replay.py](/root/backup/InternNav/scripts/eval/tools/benchmark_dualvln_replay.py) 会优先使用 manifest 里已经保存的 `history_frame_indices`，所以你传 `--num-history 8/4/2/0`，很可能根本没真正改到输入历史帧。这也是为什么这组结果几乎完全一样。

所以我的更正是：**不用重跑整套 sweep**。现在真正该做的是：
1. 接受 `max_new_tokens` 和 prompt 这两组现有结论。
2. 不接受当前 `num_history` 这组作为最终结论。
3. 如果要继续测 `num_history`，应该先把 benchmark 补一个 `ignore_manifest_history` 或 `force_history_recompute` 开关，然后只重跑 `num_history` 这一组。

改动已经加在：
- [benchmark_dualvln_replay.py](/root/backup/InternNav/scripts/eval/tools/benchmark_dualvln_replay.py)
- [run_replay_benchmark_sweeps.py](/root/backup/InternNav/scripts/eval/tools/run_replay_benchmark_sweeps.py)

现在新增了 `--ignore-manifest-history`，runner 在 `num_history` 组会自动带上它，所以这次会真正按 `--num-history` 重建历史帧，而不是继续复用 manifest 里的 `history_frame_indices`。相关说明我也补进了：
- [technical_trace.md](/root/backup/InternNav/changelog/2026-3-11/technical_trace.md)
- [dualvln_inference_optimization_plan.md](/root/backup/InternNav/docs/dualvln_inference_optimization_plan.md)

直接执行这条命令，不用重跑另外两组：

```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
export TOKENIZERS_PARALLELISM=false
python scripts/eval/tools/run_replay_benchmark_sweeps.py \
  --manifest /root/backup/InternNav/logs/habitat/test_dual_system_mini/replay_subset/manifest_rank0.jsonl \
  --model-path /root/backup/InternNav/checkpoints/InternVLA-N1-DualVLN \
  --output-dir /root/backup/InternNav/logs/habitat/test_dual_system_mini/sweeps \
  --base-path /root/backup/InternNav/logs \
  --groups num_history \
  --verbose-every 20
```

结论先给你：
- `max_new_tokens` 组已经可以视为排除
- prompt 组不是主要瓶颈
- `num_history` 组之前那份结果不可靠，必须用这次修正后的版本再看

你跑完新的 `comparison_num_history.csv` 后，把结果给我，我直接继续帮你分析。
## Q4
跑完了，分析一下结果写到文档里面（/root/backup/InternNav/changelog/2026-3-11/manager_update.txt这个不要忘了，其他的也要写）
## A4
这次重跑后的 `num_history` sweep 是有效的，因为已经启用了 `ignore_manifest_history=True`，真正改到了输入历史帧。核心结论是：

- `num_history=8 -> 4` 是当前最有价值的低风险优化点  
  `total_step p50` 从约 `0.860s` 降到 `0.484s`，几乎减半；`GPU peak` 也从约 `17.5GB` 降到 `16.9GB`。
- `num_history=2` 和 `0` 虽然更快，但开始明显破坏大小脑切换  
  `num_history=2` 时 `s2_latent/s1_generate` 只剩 `1` 次；`num_history=0` 时直接变成 `0`，基本退化成只走 discrete。
- 所以现在最合理的候选不是 `2` 或 `0`，而是 **`num_history=4`**。

我已经把这些分析写进：
- [technical_trace.md](/root/backup/InternNav/changelog/2026-3-11/technical_trace.md)
- [manager_update.txt](/root/backup/InternNav/changelog/2026-3-11/manager_update.txt)
- [dualvln_inference_optimization_plan.md](/root/backup/InternNav/docs/dualvln_inference_optimization_plan.md)

关于下一步：**我不建议立刻先做 KV cache。**  
更合理的顺序是：

1. 先把 `num_history=4` 放回 Habitat 闭环跑一轮。
2. 看 `Success / SPL / Navigation Error / pixel_goal_ratio / avg_s1_steps_per_cycle` 有没有明显退化。
3. 如果闭环稳定，再开始做 `KV cache / backend` 这一类更重的优化。

原因很简单：`num_history=4` 已经是一个“收益很大、实现很便宜、证据很充分”的优化点，应该先吃掉这个确定性收益，再去做更深的系统改造。

一键 runner 已经给你做好了，脚本是 [run_habitat_closed_loop_num_history_sweeps.py](/root/backup/InternNav/scripts/eval/tools/run_habitat_closed_loop_num_history_sweeps.py)。

你现在直接用这两条命令就行。

mini 版闭环 sweep：
```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
python scripts/eval/tools/run_habitat_closed_loop_num_history_sweeps.py \
  --dataset mini \
  --num-history-values 4 2 1 0 \
  --output-root ./logs/habitat/closed_loop_num_history_sweeps \
  --max-eval-episodes 8 \
  --replay-num-episodes 8
  > ./logs/habitat/closed_loop_num_history_sweeps/run_mini_num_history.log 2>&1
```

full 版闭环 sweep：
```bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate habitat
cd /root/backup/InternNav
python scripts/eval/tools/run_habitat_closed_loop_num_history_sweeps.py \
  --dataset full \
  --num-history-values 4 2 1 0 \
  --output-root ./logs/habitat/closed_loop_num_history_sweeps \
  --max-eval-episodes 8 \
  --replay-num-episodes 8
```

如果你要跑 full 且不限制 episode 数量，把：
```bash
--max-eval-episodes 8
```
改成：
```bash
--max-eval-episodes 0
```

输出会在：
- `./logs/habitat/closed_loop_num_history_sweeps/mini/num_history_*`
- `./logs/habitat/closed_loop_num_history_sweeps/full/num_history_*`

跑完还会自动生成：
- `comparison_num_history_closed_loop.csv`

这次新增的 runner 和命令我也已经补写进：
- [technical_trace.md](/root/backup/InternNav/changelog/2026-3-11/technical_trace.md)
- [manager_update.txt](/root/backup/InternNav/changelog/2026-3-11/manager_update.txt)
- [dualvln_inference_optimization_plan.md](/root/backup/InternNav/docs/dualvln_inference_optimization_plan.md)

如果你跑完这组闭环 sweep，把 `comparison_num_history_closed_loop.csv` 和其中 `num_history=4` 的 `runtime_summary_rank0.json` / `result.json` 给我，我就直接帮你判断能不能正式进入 KV cache 阶段。

