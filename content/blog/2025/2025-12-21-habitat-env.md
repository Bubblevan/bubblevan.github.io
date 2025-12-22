---
slug: 2025-12-21-habitat-env
title: 从头开始配置 Habitat Autodl 环境
authors: [bubblevan]
tags: [habitat, autodl, vnc, environment]
---

## AutoDL + Habitat + VNC + VGLRun

真的没招了...下面的错误层出不穷：
```
GL::Context: cannot retrieve OpenGL version: GL::Renderer::Error::InvalidValue
```

因此咨询学长，考虑根据[AUTODL官方远程GUI文档](https://www.autodl.com/docs/gui/)设置VNC。
```
# 安装基本的依赖包
apt update && apt install -y libglu1-mesa-dev mesa-utils xterm xauth x11-xkb-utils xfonts-base xkb-data libxtst6 libxv1

# 安装libjpeg-turbo和turbovnc
export TURBOVNC_VERSION=2.2.5
export LIBJPEG_VERSION=2.0.90
wget https://autodl-public.ks3-cn-beijing.ksyuncs.com/tool/vnc/libjpeg-turbo-official_${LIBJPEG_VERSION}_amd64.deb
wget https://autodl-public.ks3-cn-beijing.ksyuncs.com/tool/vnc/turbovnc_${TURBOVNC_VERSION}_amd64.deb
dpkg -i libjpeg-turbo-official_${LIBJPEG_VERSION}_amd64.deb
dpkg -i turbovnc_${TURBOVNC_VERSION}_amd64.deb
rm -rf *.deb

# 启动VNC服务端，这一步可能涉及vnc密码配置（注意不是实例的账户密码）。另外如果出现报错xauth未找到，那么使用apt install xauth再安装一次
```
在启动前，需要卸载无头版本：
```bash
pip uninstall habitat-sim -y
conda remove habitat-sim-mutex headless -y

# 安装非无头版本（带渲染支持）
conda install habitat-sim withbullet -c conda-forge -c aihabitat -y
# mamba! /root/miniconda3/bin/mamba install!
# conda config --set ssl_verify false
```
启动！
```
rm -rf /tmp/.X1*  # 如果再次启动，删除上一次的临时文件，否则无法正常启动
USER=root /opt/TurboVNC/bin/vncserver :1 -desktop X -auth /root/.Xauthority -geometry 1920x1080 -depth 24 -rfbwait 120000 -rfbauth /root/.vnc/passwd -fp /usr/share/fonts/X11/misc/,/usr/share/fonts -rfbport 6006

# 检查是否启动，如果有vncserver的进程，证明已经启动
ps -ef | grep vnc
```

接下来cmd里配置SSH转发：
```
ssh -CNg -L 6006:127.0.0.1:6006 root@connect.nmb2.seetacloud.com -p 24413
```
然后设置`export DISPLAY=:1`，随便打开一个VNC Client “连接地址” 栏输入：127.0.0.1:6006（本地被 SSH 隧道代理的端口）；
点击连接，前面你设置的 VNC 密码（不是实例 root 密码）

在这之后我们需要VirtualGL (vglrun)，其拦截了 Habitat 的 OpenGL 渲染请求，重定向到物理 GPU（NVIDIA）上运行，最后再把画面传回 VNC 的虚拟显示器。
```bash
# 下载并安装
wget https://github.com/VirtualGL/virtualgl/releases/download/3.1/virtualgl_3.1_amd64.deb
dpkg -i virtualgl_3.1_amd64.deb

# 安装依赖
apt install -y libegl1-mesa libgl1-mesa-glx libglu1-mesa
```
这之后就可以用它来运行了：
```
vglrun -d :1 python test.py
```

这里会遇到一个非常麻烦的问题：
```bash
Platform::WindowlessEglApplication::tryCreateContext(): unable to find CUDA device 0 among 4 EGL devices in total
```
参考[知乎经验](https://zhuanlan.zhihu.com/p/1959978616382293176)，实际上这个问题在Habitat-lab/TROUBLESHOOTING.md 中提到了。
```bash
# 设置 EGL vendor library（解决 EGL 设备匹配问题）
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
```

接下来因为我是换了一个Autodl实例从头开始跑examples的，这里我们顺便来学习一下[Habitat本身](https://evernorif.github.io/2025/05/07/habitat-%E5%9F%BA%E7%A1%80%E4%BD%BF%E7%94%A8%E8%AE%B0%E5%BD%95/)：

### autodl-tmp/habitat-lab/examples/shortest_path_follower_example.py

这个里面没有`cv2.imshow()`这种弹窗指令，所以逻辑是“静默运行 -> 保存 MP4”。

可以在autodl-tmp/habitat-lab/examples/images/shortest_path_example看到生成的mp4

注意其数据：
```
# 下载测试场景（存放在 habitat-lab/data 下）
python -m habitat_sim.utils.datasets_download --uids habitat_test_scenes --data-path data/
# 下载导航任务数据
python -m habitat_sim.utils.datasets_download --uids habitat_test_pointnav_dataset --data-path data/
```

这个在4090那个容器里也跑起来了。中间报了一个小错误：
```
TypeError: write() got an unexpected keyword argument 'fps'
```
imageio 的 tifffile 插件不支持 fps 参数，问题是 ffmpeg 未安装，导致 imageio 无法使用 ffmpeg 插件写入 MP4，回退到其他插件（如 tifffile）不支持 fps 参数，如果是这样那就很简单了：
```
/root/miniconda3/bin/mamba install -n falcon ffmpeg -c conda-forge -y
conda run -n falcon pip install imageio-ffmpeg
```
解决