---
id: package-managers
title: 包管理器生态全览
sidebar_label: 包管理器
---

# Python 包管理器生态全览

我刚开始接触 Python 的时候是某个大二暑假自己去跑眼科图片的 CNN 分类，被各种包管理器搞得一头雾水。pip、conda、poetry、uv、mamba... 

为什么会有这么多工具？它们之间有什么区别？我应该用哪个？

其实 pip 走天下就可以了（bushi）

在深入之前，我们先明确一个核心概念：Python 包管理器大致可以分为两大阵营。**PyPI 生态**专注于纯 Python 包的管理，它们基于 pip，只能处理从 PyPI 下载的 Python 包。而 **Conda 生态**则更强大，不仅能管理 Python 包，还能处理 CUDA、C++ 库等非 Python 依赖，是环境管理和包管理的二合一解决方案。

## PyPI 生态：专注 Python 包管理

如果做的是纯 Python 项目，不需要处理 CUDA 或其他系统级依赖，那么 PyPI 生态的工具就足够了。这类工具的核心优势是简单、快速，而且 PyPI 上有超过 400 万个包，几乎能想到的 Python 库都能找到。

### pip：最基础的选择

pip 是 Python 官方内置的包管理器，也是整个 PyPI 生态的基石。几乎所有其他工具最终都会调用 pip 来安装包。pip 的特点就是极简：直接安装、直接卸载，没有多余的功能。

但 pip 的局限性也很明显。它默认会把包安装到全局 Python 环境中，这意味着不同项目可能会因为依赖版本冲突而互相影响。而且 pip 没有锁文件机制，只能手动维护 requirements.txt，无法保证在不同机器上复现完全相同的环境。

如果只是临时安装一个包来测试，或者写一个极简的脚本，pip 完全够用。但对于生产环境或复杂的项目，建议使用更现代的工具。

```bash
# 安装包
pip install requests

# 从 requirements.txt 安装
pip install -r requirements.txt

# 生成 requirements.txt
pip freeze > requirements.txt
```

### pipenv：早期的尝试

pipenv 是早期为了解决「pip + 虚拟环境」痛点而诞生的工具。它把 pip 和 virtualenv 整合在一起，自动创建虚拟环境，并生成 Pipfile 和 Pipfile.lock 来管理依赖。

pipenv 比纯 pip 更规范，它提供了环境隔离和版本锁定功能。但它的依赖解析速度很慢，功能也比较简陋。现在基本上已经被 Poetry 和更新的工具替代了，除非维护的是老项目，否则不推荐使用。

```bash
# 安装 pipenv
pip install pipenv

# 创建虚拟环境并安装依赖
pipenv install requests

# 激活虚拟环境
pipenv shell

# 安装开发依赖
pipenv install pytest --dev
```

### Poetry：现代 Python 项目的标准

Poetry 是专为 Python 项目开发和发布而设计的工具。它不仅管理依赖，还能帮打包和发布到 PyPI。Poetry 的依赖解析能力很强，能很好地解决版本冲突问题，而且完全符合 PEP 标准，使用 pyproject.toml 作为配置文件。

Poetry 的优点是规范、稳定，特别适合需要发布到 PyPI 的库项目。但它对复杂二进制依赖（比如 CUDA）的支持较弱，而且速度不如新一代工具。如果做的是纯 Python 项目，尤其是需要打包发布的库，Poetry 是个不错的选择。

```bash
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 创建新项目
poetry new my-project
cd my-project

# 添加依赖
poetry add requests
poetry add pytest --group dev

# 安装所有依赖
poetry install

# 打包发布
poetry build
poetry publish
```

### Rye：Poetry 的升级版

Rye 是 Poetry 作者开发的继任者，目标是解决 Poetry 的速度和复杂度问题。Rye 整合了 Python 版本管理、虚拟环境、依赖管理和打包功能，是一个真正的「一站式」解决方案。

Rye 最大的亮点是内置了 Python 版本下载功能，不需要手动安装 Python，Rye 会自动帮管理。它的依赖解析速度比 Poetry 更快，而且兼容 pyproject.toml 标准。不过 Rye 的生态还比较新，部分老工具的兼容性可能略差。

如果想要一个功能全面、速度更快的工具，而且不介意使用相对较新的技术，Rye 值得尝试。

```bash
# 安装 Rye
curl -sSf https://rye-up.com/get | bash

# 创建新项目
rye init my-project
cd my-project

# 添加依赖
rye add requests
rye add pytest --dev

# 同步依赖
rye sync

# 运行项目
rye run python main.py
```

### uv：2024 年的新星

uv 是 2024 年爆火的新一代包管理器，用 **Rust** 重写，目标是替代 pip、Poetry 和 Rye。uv 的最大优势就是速度：它的依赖解析速度是毫秒级的，比 Poetry 快 100 倍以上。

uv 完全兼容 pip 的 requirements.txt 和 Poetry 的 pyproject.toml，这意味着可以无缝迁移现有项目。它支持虚拟环境、锁文件、依赖安装更新和打包等所有功能。uv 的缺点就是太新了，极少数边缘场景可能兼容性略差，但这些问题基本可以忽略。

如果做的是纯 Python 项目，我强烈推荐优先考虑 uv。它的速度优势在大型项目中会非常明显，而且使用体验也很棒。

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境
uv venv

# 安装包
uv pip install requests

# 从 requirements.txt 安装
uv pip install -r requirements.txt

# 使用 pyproject.toml（兼容 Poetry）
uv sync
```

## Conda 生态：跨语言环境管理

如果做的是 AI、数据科学或需要 CUDA 的项目，PyPI 生态的工具就不够用了。这时候需要 Conda 生态的工具，它们不仅能管理 Python 包，还能处理 C++ 库、CUDA 驱动等非 Python 依赖。

在深入之前，我们先理清几个概念。Anaconda、Miniconda、Miniforge 是「Conda 发行版」，它们预装了不同组件。Conda 和 Mamba 是「核心工具」，负责实际的包管理和环境管理。Micromamba 则是「精简版」，适合容器和轻量场景。

### Anaconda：一站式数据科学平台

Anaconda 是面向数据科学的完整发行版，预装了 Conda、Python 以及几百个常用的数据科学包，比如 numpy、pandas、tensorflow 等。它的优势是开箱即用，不需要手动安装基础包。

但 Anaconda 的缺点也很明显：体积巨大（GB 级），包含很多可能用不到的包，而且默认使用的源（defaults）更新较慢，部分包可能不是最新版本。Anaconda 适合零基础入门数据科学的新手，但不推荐用于生产环境或容器环境。

```bash
# 创建环境
conda create -n myenv python=3.11

# 激活环境
conda activate myenv

# 安装包
conda install numpy pandas

# 从 environment.yml 创建环境
conda env create -f environment.yml
```

### Miniconda：精简版 Anaconda

Miniconda 是 Anaconda 的瘦身版，只预装 Conda、Python 和基础依赖，没有多余的包。它的体积只有几百 MB，但保留了 Conda 的所有核心功能。

Miniconda 的缺点是默认使用 Anaconda 官方源（defaults），这个源的包更新较慢，而且部分开源包可能缺失。另外，原生 Conda 的求解器是用 Python 写的，解析复杂依赖时速度很慢。Miniconda 适合需要 Conda 但想减少体积的场景，或者维护依赖 Miniconda 的老项目。

```bash
# 创建环境
conda create -n myenv python=3.11

# 安装包（使用 conda-forge 源，更快更全）
conda install -c conda-forge numpy pandas

# 列出所有环境
conda env list
```

### Miniforge：社区版的最佳选择

Miniforge 是社区维护的 Conda 发行版，可以看作是 Miniconda 的改进版。它的默认源是 conda-forge，这是开源社区维护的源，包最全、更新最快。Miniforge 的体积和 Miniconda 相当，而且没有商业许可限制。

Miniforge 现在基本是 Conda 生态的首选发行版，尤其是对于 AI 和跨语言项目。它轻量、源更优、完全开源，几乎没有明显缺点。

```bash
# 创建环境
conda create -n myenv python=3.11

# 安装包（默认使用 conda-forge）
conda install numpy pandas pytorch

# 安装 CUDA 版本的 PyTorch
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

### Conda：核心工具

Conda 是 Conda 生态的核心工具，所有发行版都自带。它既是包管理器，也是环境管理器，能处理 Python、C++、CUDA、Linux 库等非 Python 依赖。

Conda 的环境隔离是全局级的，不同环境的 Python 版本和 CUDA 版本可以完全独立，互不干扰。它提供的都是预编译的二进制包，不需要手动编译，这对 habitat-sim、bullet 这样的复杂库特别友好。

Conda 的主要缺点是原生求解器速度慢。如果需要安装复杂的依赖（比如 habitat-sim），可能需要等很长时间。建议配合 conda-libmamba-solver 使用，或者直接用 Mamba。

```bash
# 创建包含特定 Python 版本的环境
conda create -n myenv python=3.11

# 安装多个包
conda install numpy scipy matplotlib

# 导出环境配置
conda env export > environment.yml

# 从配置文件创建环境
conda env create -f environment.yml
```

### Mamba：Conda 的高速替代

Mamba 是 Conda 的 C++ 重写版，核心解决 Conda 解析慢的问题。Mamba 的命令和 Conda 完全兼容，只需要把 `conda` 换成 `mamba` 即可，求解器速度能提升 10-100 倍。

Mamba 的优点是极速解析、完全兼容 Conda。缺点是它需要依赖 Conda 环境，所以需要先安装 Miniconda 或 Miniforge。如果经常需要安装复杂依赖（比如 habitat-sim、PyTorch+CUDA），Mamba 能大大节省的时间。

```bash
# 安装 Mamba（需要先有 Conda）
conda install mamba -n base -c conda-forge

# 使用 Mamba 创建环境（命令和 Conda 一样）
mamba create -n myenv python=3.11

# 安装包（速度比 Conda 快很多）
mamba install numpy pandas pytorch

# 安装复杂依赖（如 habitat-sim）
mamba install -c conda-forge habitat-sim
```

### Micromamba：极致轻量版

Micromamba 是 Mamba 的超轻量版，没有 Python 依赖，体积极小（MB 级），启动速度很快。它不需要预装 Conda 或 Python，兼容 Mamba 和 Conda 的命令，特别适合容器和嵌入式场景。

Micromamba 的优点是极致轻量、启动快、无依赖。缺点是命令略有差异（比如用 `micromamba create` 而不是 `mamba create`），新手可能需要适应一下。如果在 Docker 容器中工作，或者需要极致轻量的环境，Micromamba 是最佳选择。

```bash
# 安装 Micromamba（Linux/Mac）
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba

# 创建环境
micromamba create -n myenv python=3.11

# 激活环境
micromamba activate myenv

# 安装包
micromamba install numpy pandas
```

### conda-libmamba-solver：Conda 的提速插件

如果不想安装 Mamba，但又想让 Conda 提速，可以使用 conda-libmamba-solver。这是 Conda 官方的求解器插件，把 Mamba 的求解器集成到 Conda 里，让在不改变使用习惯的情况下获得速度提升。

从 Conda 23.10 版本开始，官方已经默认推荐使用 libmamba 求解器。安装和启用都很简单，只需要两行命令。

```bash
# 安装插件
conda install -n base conda-libmamba-solver

# 全局启用
conda config --set solver libmamba

# 之后使用 conda 命令就会自动使用快速求解器
conda install numpy pandas
```

## 系统包管理器：避免混淆

最后提一下系统包管理器，比如 apt（Debian/Ubuntu）、yum/dnf（RHEL/CentOS）、pacman（Arch）。这些工具是 Linux 系统级的包管理器，管理的是全局系统组件，没有环境隔离功能。

系统包管理器装的包是全局生效的，无法解决 Python 项目的版本冲突问题。应该用它们来安装系统工具（比如 git、gcc）。

## 如何选择：按场景选型

如果做的是**纯 Python 项目**，没有 CUDA 或其他非 Python 依赖，优先选择 **uv**。它的速度最快，使用体验最好。如果 uv 在的场景下有问题，可以退而求其次选择 Rye 或 Poetry。

如果做的是**AI 或跨语言项目**，需要 CUDA、habitat-sim、bullet 等依赖，那么 **Miniforge + Mamba** 是最佳组合。Miniforge 提供轻量级的 Conda 环境，Mamba 提供极速的依赖解析。如果需要在容器中使用，可以用 Micromamba 替代。

如果是完全的**新手，刚入门数据科学**，Miniforge 是个好选择，它轻量、开源、源更优。如果觉得手动安装包太麻烦，也可以先用 Anaconda，等熟悉了再迁移到 Miniforge。

如果需要**维护老项目**，而且项目依赖 Miniconda 和 defaults 源，那就继续用 Miniconda，但建议安装 conda-libmamba-solver 来提速。

## 总结：关键差异一览

最后，让我们快速总结一下这些工具的关键差异。

从速度来看，uv 是最快的，其次是 Mamba 和 Micromamba，然后是 Rye 和 Poetry，pipenv 和原生 Conda 比较慢，pip 最慢。

从跨语言支持来看，Conda、Mamba、Micromamba 都能处理非 Python 依赖，而 PyPI 生态的工具（uv、Poetry 等）只能处理 Python 包。

从包源丰富度来看，PyPI（uv/pip 使用）有超过 400 万个包，是最丰富的。conda-forge（Miniforge 默认使用）次之，Anaconda defaults 最少。

从体积来看，Micromamba 只有几 MB，Miniforge 和 Miniconda 是几百 MB，Anaconda 则是 GB 级。

简单来说，纯 Python 项目用 uv，需要 CUDA 或非 Python 依赖用 Miniforge+Mamba，容器环境用 Micromamba，这样选基本不会错。
