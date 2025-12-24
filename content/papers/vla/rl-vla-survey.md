# A Survey on Reinforcement Learning of Vision-Language-Action Models for Robotic Manipulation

> 我感觉自己真没必要把早先2年前的文章工作花太多时间在上面（点名ACT和RT-1），花一天时间略过就行。

We begin with preliminaries of RL and VLA and outline the key challenges of their integration (Section II). 
We then analyze core RL-VLA design tradeoffs: action representation, reward design, and transition modeling (Section III), 
followed by insights from online and offline RL paradigms with an emphasis on policy robustness and adaptation (Section IV).
We review deployment frameworks from sim-to-real transfer to direct real-world RL (Section V), 
then summarize benchmarks, evaluation metrics, and existing RL-VLA methods (Section VI). 
Finally, we outline open challenges and promising future research directions (Section VII).


## preliminaries
VLA 是机器人学习的新范式，以端到端框架统一视觉感知、语言理解与动作生成，核心包含视觉编码器、语言编码器和策略解码器，依托预训练 VLM 实现跨任务 / 物体泛化及直观人机交互。其主流通过模仿学习（SFT/BC）训练，依赖大规模遥操作数据集却受限于数据质量与覆盖范围，在领域迁移场景存在短板，因此需结合强化学习（RL）提升适应性与鲁棒性。

