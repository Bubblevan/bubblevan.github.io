---
date: 2026-01-09
title: 足式运控综述（3）：本体感知部分初稿
authors: [bubblevan]
tags: []
---

## 1. 历史演进与背景

实现足式机器人在非结构化环境中的自主移动，是其应用于野外勘探、灾难救援等复杂场景的关键。然而，其高维、欠驱动及混合动力系统的本质，使得稳定且敏捷的运动控制成为一个核心挑战。这一挑战不仅在于求解高度非线性的动力学与离散的接触序列，更在于确保系统在模型失配与未知扰动下的动态稳定性。

在这一背景下，“盲走”（Blind Locomotion） ——即仅依赖本体感知信息（如关节编码器、惯性测量单元(IMU)提供的本体状态）而无需任何外感（如视觉、激光雷达）环境反馈的运动控制——构成了足式机器人运动能力的基石与安全底线。尽管视觉等外感感知能为运动规划提供丰富的环境先验，但其固有的感知延迟、数据异步性，以及在极端工况（强光、烟雾、高速运动模糊）下的失效风险，与足式运动控制所需的高实时性（通常在数百赫兹频段）与超高可靠性要求存在根本矛盾。

因此，一个高性能的“盲走”控制器，不仅是应对传感器退化或失效的最后保障，更是任何分层或融合感知-运动架构中不可或缺的、提供稳定底层动态响应的控制基座。

## 2. 模型驱动控制范式的演进
模型驱动控制（Model-driven Control）范式构成了足式机器人盲走控制的理论基石。其核心思想在于，通过对机器人动力学进行不同层次的抽象与建模，并基于模型设计控制器，从而在保证稳定性的前提下实现动态运动。

足式机器人现代控制理论的起点，可追溯至对生物运动机理的工程化简化。Raibert在其开创性工作中提出，复杂的动态平衡问题可被解耦为三个独立的单输入单输出（SISO）控制子问题：跳跃高度、躯体姿态及水平速度控制\cite{raibert1986legged}。它证明了无需求解完整的复杂多体动力学方程，仅通过捕捉关键物理特征（如质心动力学）并设计简单的反馈规则，即可生成并稳定周期性的动态步态。

随着对机器人环境适应能力要求的提高，研究者开始在控制中引入更丰富的物理交互直觉。虚拟模型控制（Virtual Model Control, VMC）是这一方向的代表 [?]。其核心是在机器人本体与期望运动轨迹之间，“虚拟”地构造一组弹簧-阻尼元件。通过计算使虚拟元件达到期望形变所需的力，并将其映射为关节力矩，VMC为控制者提供了一种物理直观的交互语义。例如，Boston Dynamics的BigDog机器人利用此方法，显著提升了在非平整地形（如泥泞、碎石）上的柔顺性与平衡能力。VMC的优势在于将复杂的足端力分配问题，转化为对虚拟元件状态的调控，但其控制性能在很大程度上依赖于虚拟元件参数的人工调谐。

21 世纪 10 年代，计算能力的提升推动了在线优化方法的普及。以 MIT Cheetah 系列 [?]为代表的研究引入了模型预测控制（Model Predictive Control, MPC）框架，在每个控制周期内，基于一个简化的实时动力学模型（如单刚体模型），对未来有限时域的系统状态进行滚动预测，并通过求解一个带约束的优化问题来计算最优的足端接触力序列。
MPC的卓越性能源于其对系统动力学与硬性约束（如摩擦力锥、足端工作空间）的显式处理，从而能在高速运动与抗扰动中实现近乎最优的动态响应。然而，其性能高度耦合于模型精度与预设的接触时序。在面对接触物理参数时变或不确定的环境时，建模误差会导致性能下降，这揭示了纯模型驱动范式在泛化能力上的根本局限。

## 3. 学习驱动的运动控制
模型驱动范式的性能天花板受限于其建模精度。以深度强化学习（Deep Reinforcement Learning, DRL）为代表的数据驱动方法，为解决未建模动力学与环境参数不确定性问题提供了新的范式。其核心在于，不依赖于对世界的显式解析模型，而是通过智能体与环境的交互数据，直接学习从状态到动作的最优映射策略，从而绕过了精确建模的瓶颈。

早期研究主要通过运动模仿（Motion Imitation）框架，将生物运动数据作为先验知识引入奖励函数，引导策略网络习得自然、高效的步态\cite{peng2020learningagileroboticlocomotion}。此类工作证明了DRL能有效处理高维、非线性的连续控制问题。随后，Hwangbo 等人通过构建高精度的执行器模型并结合大规模模拟训练\cite{Hwangbo_2019}，证明了数据驱动的策略在应对复杂扰动时能够展现出超越传统分析方法的鲁棒性。这种鲁棒性并非源于对特定扰动模式的显式编程，而是策略网络从海量数据中隐式学习到的一种广义扰动抑制能力。

针对“盲走”场景下环境参数不可观测的痛点，研究者提出了特权信息学习（Privileged Learning）范式。其核心在于通过“教师-学生”训练架构打破信息瓶颈：在仿真阶段，教师策略通过访问全球信息（如地面摩擦、地形起伏）建立最优行动基准；在部署阶段，学生策略则通过知识蒸馏，学习如何利用历史本体感知序列来隐式表征（Implicit Representation）这些环境特征\cite{Lee_2020}。这一过程实现了从依赖空间感知到依赖时序推断的范式转变，使机器人能够基于本体反馈动态调整其运动策略，从而适应未知地形。

为了进一步缩减 Sim-to-Real 的鸿沟，Kumar 等人提出的快速运动自适应（RMA）框架引入了显式的自适应模块，通过时间卷积网络（TCN）在线估计环境参数的变动\cite{kumar2021rmarapidmotoradaptation}。这种基于时序信息的在线推断机制，极大地提升了机器人对物理属性瞬时的响应精度。在此基础上，DreamWaQ 等工作通过生成式模型引入了“隐式地形想象”，通过预测未来的足端高度变化，将本体感知控制从被动的扰动响应提升到了主动的环境预判高度\cite{nahrendra2023dreamwaqlearningrobustquadrupedal,nahrendra2024obstacleawarequadrupedallocomotionresilient}。

## 4. 算力驱动的演进泛化
数据驱动范式的潜力，其上限由训练数据的规模与多样性决定。近年来，高性能并行仿真技术的突破，使得在超大规模虚拟环境中训练成为可能，这从根本上改变了学习型盲走策略的开发模式，并不断推高其性能边界。

学习型控制器的泛化能力，直接源于其在训练中所见环境的多样性。以Isaac Gym为代表的GPU并行仿真框架，实现了质的飞跃，允许在单卡上同步运行成千上万个物理实例\cite{makoviychuk2021isaacgymhighperformance}。这种高度计算密集型的训练范式允许策略在极广的地形随机化（Domain Randomization）空间内进行探索，从而在极短时间内训练出具有极强泛化能力的“全地形”盲走策略\cite{rudin2022learningwalkminutesusing}。

Miki 等通过循环信念状态编码器与注意力门控，策略能够在外感知可靠时利用高程图高度采样进行地形预判以提升速度，而在遮挡、反光或位姿漂移导致外感知退化时则无缝退化到本体感知主导的控制模式\cite{Miki_2022}。

在此基础上，研究者进一步探索通用策略的能力边界。Margolis 等人开发的 Walk These Ways 架构通过将步态指令参数化，证明了单一神经网络可以在本体感知的反馈下，覆盖从平地奔跑至多种步态切换的通用技能 [?]。

Extreme Parkour 等工作则进一步展示了：即便在缺乏视觉导引的情况下，通过在极端崎岖地形中进行强化学习并结合残差控制，机器人亦能突破动力学极限，完成跳跃、跨越深沟等极具爆发力的动作。这些进展不仅验证了深度强化学习在挖掘硬件潜能方面的优势，也重新定义了本体感知在足式运动中的能力上限 [?]

## Reference
@book{raibert1986legged,
  title     = {Legged Robots That Balance},
  author    = {Raibert, Marc H.},
  year      = {1986},
  publisher = {MIT Press},
  address   = {Cambridge, MA},
  series    = {Artificial Intelligence Series}
}
@misc{kumar2021rmarapidmotoradaptation,
      title={RMA: Rapid Motor Adaptation for Legged Robots}, 
      author={Ashish Kumar and Zipeng Fu and Deepak Pathak and Jitendra Malik},
      year={2021},
      eprint={2107.04034},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2107.04034}, 
}
@misc{peng2020learningagileroboticlocomotion,
      title={Learning Agile Robotic Locomotion Skills by Imitating Animals}, 
      author={Xue Bin Peng and Erwin Coumans and Tingnan Zhang and Tsang-Wei Lee and Jie Tan and Sergey Levine},
      year={2020},
      eprint={2004.00784},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2004.00784}, 
}
@misc{nahrendra2023dreamwaqlearningrobustquadrupedal,
      title={DreamWaQ: Learning Robust Quadrupedal Locomotion With Implicit Terrain Imagination via Deep Reinforcement Learning}, 
      author={I Made Aswin Nahrendra and Byeongho Yu and Hyun Myung},
      year={2023},
      eprint={2301.10602},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2301.10602}, 
}
@misc{nahrendra2024obstacleawarequadrupedallocomotionresilient,
      title={Obstacle-Aware Quadrupedal Locomotion With Resilient Multi-Modal Reinforcement Learning}, 
      author={I Made Aswin Nahrendra and Byeongho Yu and Minho Oh and Dongkyu Lee and Seunghyun Lee and Hyeonwoo Lee and Hyungtae Lim and Hyun Myung},
      year={2024},
      eprint={2409.19709},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2409.19709}, 
}
@article{Hwangbo_2019,
   title={Learning agile and dynamic motor skills for legged robots},
   volume={4},
   ISSN={2470-9476},
   url={http://dx.doi.org/10.1126/scirobotics.aau5872},
   DOI={10.1126/scirobotics.aau5872},
   number={26},
   journal={Science Robotics},
   publisher={American Association for the Advancement of Science (AAAS)},
   author={Hwangbo, Jemin and Lee, Joonho and Dosovitskiy, Alexey and Bellicoso, Dario and Tsounis, Vassilios and Koltun, Vladlen and Hutter, Marco},
   year={2019},
   month=jan 
}
@article{Lee_2020,
   title={Learning quadrupedal locomotion over challenging terrain},
   volume={5},
   ISSN={2470-9476},
   url={http://dx.doi.org/10.1126/scirobotics.abc5986},
   DOI={10.1126/scirobotics.abc5986},
   number={47},
   journal={Science Robotics},
   publisher={American Association for the Advancement of Science (AAAS)},
   author={Lee, Joonho and Hwangbo, Jemin and Wellhausen, Lorenz and Koltun, Vladlen and Hutter, Marco},
   year={2020},
   month=oct 
}
@misc{rudin2022learningwalkminutesusing,
      title={Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning}, 
      author={Nikita Rudin and David Hoeller and Philipp Reist and Marco Hutter},
      year={2022},
      eprint={2109.11978},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2109.11978}, 
}
@article{Miki_2022,
   title={Learning robust perceptive locomotion for quadrupedal robots in the wild},
   volume={7},
   ISSN={2470-9476},
   url={http://dx.doi.org/10.1126/scirobotics.abk2822},
   DOI={10.1126/scirobotics.abk2822},
   number={62},
   journal={Science Robotics},
   publisher={American Association for the Advancement of Science (AAAS)},
   author={Miki, Takahiro and Lee, Joonho and Hwangbo, Jemin and Wellhausen, Lorenz and Koltun, Vladlen and Hutter, Marco},
   year={2022},
   month=jan 
}
@misc{makoviychuk2021isaacgymhighperformance,
      title={Isaac Gym: High Performance GPU-Based Physics Simulation For Robot Learning}, 
      author={Viktor Makoviychuk and Lukasz Wawrzyniak and Yunrong Guo and Michelle Lu and Kier Storey and Miles Macklin and David Hoeller and Nikita Rudin and Arthur Allshire and Ankur Handa and Gavriel State},
      year={2021},
      eprint={2108.10470},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2108.10470}, 
}