---
title: "Golang"
weight: 2
---

打开Docker Desktop，启动 JupyterLab容器
```bash
docker run -it --rm -p 8888:8888 janpfeifer/gonb_jupyterlab:latest
```
- `-it`：开启交互式终端，能看到Jupyter的输出日志
- `--rm`：容器停止后自动删除，不会在你的电脑上残留垃圾文件
- `-p 8888:8888`：把容器内部的8888端口映射到你电脑的8888端口
- `janpfeifer/gonb_jupyterlab:latest`：官方提供的Go语言Jupyter内核镜像

第一次运行会自动下载镜像（约1GB左右），下载完成后，终端会输出：
```
To access the server, open this file in a browser:
    file:///home/jovyan/.local/share/jupyter/runtime/jpserver-9-open.html
Or copy and paste one of these URLs:
    http://localhost:8888/lab?token=8035fd3ad9e802989ad3a8bcd4a265145d3d803d97681bc1
    http://127.0.0.1:8888/lab?token=8035fd3ad9e802989ad3a8bcd4a265145d3d803d97681bc1
```
**复制完整的带token的链接**（`http://localhost:8888/lab?token=8035fd3ad9e802989ad3a8bcd4a265145d3d803d97681bc1`），这个是连接Jupyter服务器的凭证：
1.  打开VS Code，新建一个后缀为`.ipynb`的笔记本文件
2.  点击VS Code窗口**右上角的"选择内核"按钮**（通常显示"未选择内核"）
3.  在弹出的菜单中选择 **"现有Jupyter服务器"**
4.  粘贴刚才复制的完整带token的链接，按回车
5.  选择 **"Python 3 (ipykernel)"** 作为内核，就可以开始写Go代码了

因为我们加了`--rm`参数，容器停止后会自动删除，下次使用时重新运行那条`docker run`命令即可。
