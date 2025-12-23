---
date: 2025-12-21
title: 从头开始配置 Habitat Autodl 环境
authors: [bubblevan]
tags: [habitat, autodl, vnc, environment]
---

## AutoDL + Habitat + VNC + VGLRun

### 问题背景

遇到了以下错误，反复出现：

```
GL::Context: cannot retrieve OpenGL version: GL::Renderer::Error::InvalidValue
```

因此咨询学长，考虑根据 [AUTODL 官方远程 GUI 文档](https://www.autodl.com/docs/gui/) 设置 **VNC**。

## 一、安装 VNC 环境

### 1.1 安装基本依赖

```bash
# 安装基本的依赖包
apt update && apt install -y libglu1-mesa-dev mesa-utils xterm xauth x11-xkb-utils xfonts-base xkb-data libxtst6 libxv1
```

### 1.2 安装 TurboVNC

```bash
# 安装 libjpeg-turbo 和 turbovnc
export TURBOVNC_VERSION=2.2.5
export LIBJPEG_VERSION=2.0.90
wget https://autodl-public.ks3-cn-beijing.ksyuncs.com/tool/vnc/libjpeg-turbo-official_${LIBJPEG_VERSION}_amd64.deb
wget https://autodl-public.ks3-cn-beijing.ksyuncs.com/tool/vnc/turbovnc_${TURBOVNC_VERSION}_amd64.deb
dpkg -i libjpeg-turbo-official_${LIBJPEG_VERSION}_amd64.deb
dpkg -i turbovnc_${TURBOVNC_VERSION}_amd64.deb
rm -rf *.deb
```

**注意**：启动 **VNC** 服务端时，这一步可能涉及 **VNC 密码配置**（注意不是实例的账户密码）。另外如果出现报错 `xauth` 未找到，那么使用 `apt install xauth` 再安装一次。

### 1.3 卸载无头版本并安装带渲染支持的版本

在启动前，需要卸载无头版本：

```bash
pip uninstall habitat-sim -y
conda remove habitat-sim-mutex headless -y

# 安装非无头版本（带渲染支持）
conda install habitat-sim withbullet -c conda-forge -c aihabitat -y
# mamba! /root/miniconda3/bin/mamba install!
# conda config --set ssl_verify false
```

### 1.4 启动 VNC 服务端

```bash
rm -rf /tmp/.X1*
# 如果再次启动，删除上一次的临时文件，否则无法正常启动
USER=root /opt/TurboVNC/bin/vncserver :1 -desktop X -auth /root/.Xauthority -geometry 1920x1080 -depth 24 -rfbwait 120000 -rfbauth /root/.vnc/passwd -fp /usr/share/fonts/X11/misc/,/usr/share/fonts -rfbport 6006

# 检查是否启动，如果有 vncserver 的进程，证明已经启动
ps -ef | grep vnc
```

## 二、配置 SSH 隧道和 VNC 客户端

### 2.1 本地 SSH 端口转发

在本地（非 Autodl）**cmd** 里配置 **SSH** 转发：

```bash
# 3090 实例
ssh -CNg -L 6006:127.0.0.1:6006 root@connect.nmb2.seetacloud.com -p 24413

# 4090 实例
ssh -CNg -L 6006:127.0.0.1:6006 root@connect.nmb1.seetacloud.com -p 29490
```

### 2.2 连接 VNC 客户端

1. 设置 `export DISPLAY=:1`
2. 打开任意 **VNC Client**
3. 在"连接地址"栏输入：`127.0.0.1:6006`（本地被 **SSH** 隧道代理的端口）
4. 点击连接，输入前面设置的 **VNC 密码**（不是实例 root 密码）

## 三、安装和配置 VirtualGL

### 3.1 安装 VirtualGL

在这之后我们需要 **VirtualGL (vglrun)**，其拦截了 **Habitat** 的 **OpenGL** 渲染请求，重定向到物理 **GPU（NVIDIA）** 上运行，最后再把画面传回 **VNC** 的虚拟显示器。

```bash
# 下载并安装
wget https://github.com/VirtualGL/virtualgl/releases/download/3.1/virtualgl_3.1_amd64.deb
dpkg -i virtualgl_3.1_amd64.deb

# 安装依赖
apt install -y libegl1-mesa libgl1-mesa-glx libglu1-mesa
```

### 3.2 使用 VirtualGL 运行程序

这之后就可以用它来运行了：

```bash
vglrun -d :1 python test.py
```

### 3.3 解决 EGL 设备匹配问题

这里会遇到一个非常麻烦的问题：

```bash
Platform::WindowlessEglApplication::tryCreateContext(): unable to find CUDA device 0 among 4 EGL devices in total
```

参考[知乎经验](https://zhuanlan.zhihu.com/p/1959978616382293176)，实际上这个问题在 **Habitat-lab/TROUBLESHOOTING.md** 中提到了。

**解决方案**：

```bash
# 设置 EGL vendor library（解决 EGL 设备匹配问题）
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
```
> 建议直接写进`.bashrc`

## 四、运行 Habitat 示例

### 4.1 shortest_path_follower_example.py

接下来因为我是换了一个 **Autodl** 实例从头开始跑 **examples** 的，这里我们顺便来学习一下 [Habitat 本身](https://evernorif.github.io/2025/05/07/habitat-%E5%9F%BA%E7%A1%80%E4%BD%BF%E7%94%A8%E8%AE%B0%E5%BD%95/)：

**文件路径**：`autodl-tmp/habitat-lab/examples/shortest_path_follower_example.py`

这个里面没有 `cv2.imshow()` 这种弹窗指令，所以逻辑是"**静默运行 -> 保存 MP4**"。

可以在 `autodl-tmp/habitat-lab/examples/images/shortest_path_example` 看到生成的 **MP4**。

### 4.2 下载测试数据

注意其数据：

```bash
# 下载测试场景（存放在 habitat-lab/data 下）
python -m habitat_sim.utils.datasets_download --uids habitat_test_scenes --data-path data/

# 下载导航任务数据
python -m habitat_sim.utils.datasets_download --uids habitat_test_pointnav_dataset --data-path data/
```

### 4.3 解决 imageio 错误

这个在 **4090** 那个容器里也跑起来了。中间报了一个小错误：

```
TypeError: write() got an unexpected keyword argument 'fps'
```

**问题分析**：**imageio** 的 **tifffile** 插件不支持 `fps` 参数，问题是 **ffmpeg** 未安装，导致 **imageio** 无法使用 **ffmpeg** 插件写入 **MP4**，回退到其他插件（如 **tifffile**）不支持 `fps` 参数。

**解决方案**：

```bash
/root/miniconda3/bin/mamba install -n falcon ffmpeg -c conda-forge -y
conda run -n falcon pip install imageio-ffmpeg
```

问题解决！
