# 11. Kubernetes 部署
前面几章我们从 Domain 到 Application 到 Adapter 到 Infrastructure，把 merchant-backend 的代码完整写了一遍。
Domain 层知道什么是商品，Application 层知道怎么编排商品列表和购买流程，Adapter 层暴露 HTTP API，Infrastructure 层连接 MySQL 和 StablePay Gateway。
但代码写完后，它只是一个本地能跑的 Go 程序。要让 AI Agent 在 `https://ai.wenfu.cn/merchant` 上真正买到商品，还需要把它部署到服务器上。

## 11.1 ECS 单机部署
写完了 merchant-backend 的代码，在开发机上 `go run ./cmd/merchant-server`，然后浏览器访问 `http://localhost:8080/health`，看到一个 `{"status":"ok"}`。

但现在只有我的电脑自己能访问。我的电脑没有公网 IP，也没有域名。

### 11.1.1 怎么让外部能访问到我的程序？
- 选项 A：把我的电脑变成服务器（端口映射/内网穿透）
  - 用 `ngrok`、`frp` 等工具把 `localhost:8080` 暴露到公网。
  - 速度慢，校网也不稳定，而且我的电脑不能 7x24 小时开着。
- 选项 B：买一台云服务器（ECS）
  - ECS 是弹性计算服务（Elastic Compute Service）的缩写，说白了就是 **一台放在云厂商机房里、拥有固定公网 IP 的电脑**。我可以在上面部署我的程序，只要它开着，外网就能访问。
因此我们使用公司的阿里云 ECS 实例，它被分配了一个公网 IP 比如 `123.56.78.90`，现在，我可以 `ssh root@123.56.78.90` 登录进去，把编译好的 `merchant-backend` 传上去，运行起来。然后从我的笔记本 `curl http://123.56.78.90:8080/health`，成功了！

但问题又来了：谁记得住 `123.56.78.90` 这个数字？
## 11.1.2 怎么让用户通过域名访问？
我需要告诉全世界：`ai.wenfu.cn` 这个域名指向我的 ECS 公网 IP `123.56.78.90`。这需要在域名注册商（比如阿里云 DNS）里添加一条 **A 记录（Address Record）**。

DNS 就像互联网的电话簿，它会帮用户把域名翻译成 IP。而 A 记录是 DNS 解析体系中最基础的记录类型，作用是将一个域名（如 `ai.wenfu.cn`）直接映射到一个 IPv4 公网地址（如 `123.56.78.90`）。用户在浏览器输入域名时，DNS 系统会通过 A 记录找到对应的服务器 IP，才能建立网络连接。当然有其他类型的记录不过这里我们不做多余讨论。

添加之后，等几分钟生效，我就可以 `curl http://ai.wenfu.cn:8080/health` 了。

但怪的是端口 `8080` 还在 URL 里。普通用户访问 `https://ai.wenfu.cn/merchant` 时，浏览器默认会去 443 端口（HTTPS）或 80 端口（HTTP）。我的程序监听的是 8080，用户必须在网址里写 `:8080`——这太不专业了。

### 11.1.3 怎么隐藏端口让用户访问标准的 80/443？
互联网默认约定了 Web 访问的两个默认端口，用户输入网址时无需手动填写：
- HTTP 明文协议默认使用 80 端口，访问 `http://域名` 时，浏览器默认请求服务器的 80 端口
- HTTPS 加密协议默认使用 443 端口，访问 `https://域名` 时，浏览器默认请求服务器的 443 端口
要实现不带端口号的标准访问，行业内主要有两种方案：

- 选项 A：让我的程序直接监听 80 端口
  - 在 Linux 上，1024 以下的端口属于「特权端口」，只有 root 超级用户才能监听。用 root 权限运行业务程序会带来极大的安全隐患，一旦程序出现漏洞，攻击者可以直接获取服务器最高权限。
  - 80/443 端口通常需要承担加密传输、静态资源分发、多服务路由、流量限流等通用能力。把这些能力全部塞进业务程序里，会让代码臃肿、维护成本陡增，也不符合架构分层的设计原则。
- 选项 B：加一层反向代理，也就是大名鼎鼎的 **Nginx**
  - Nginx 是一个高性能的 Web 服务器，它监听 80 和 443 端口，然后根据请求的路径（比如 `/merchant/`）把请求**转发**给我的程序（`http://127.0.0.1:8080`）。这个过程叫做**反向代理**。

**反向代理的本质** 在于用户不知道背后有几台服务器、是什么端口，他们只知道 `ai.wenfu.cn/merchant`。Nginx 充当门卫，接受所有请求，再按规则发给内部的具体服务。
> 与之相对的是「正向代理」（比如 VPN），它是 **客户端** 的代理，帮客户端访问外部资源；而反向代理是 **服务端** 的代理，帮服务端接收、分发外部请求。
以访问 `http://ai.wenfu.cn/merchant/health` 为例：
1. 用户输入域名，DNS 系统通过 A 记录解析出服务器公网 IP `123.56.78.90`
2. 请求默认发送到服务器的 80 端口，被监听该端口的 Nginx 接收
3. Nginx 匹配到请求路径以 `/merchant/` 开头，按照预设规则，把请求转发给本机运行在 8080 端口的 merchant-backend 服务
4. 业务程序处理完请求，把响应返回给 Nginx，再由 Nginx 统一返回给用户

对应的 Nginx 核心配置示例如下：
```nginx
# 监听 80 端口，接收 ai.wenfu.cn 域名的请求
server {
    listen 80;
    server_name ai.wenfu.cn;

    # 匹配 /merchant/ 开头的所有请求
    location /merchant/ {
        # 转发到本地 8080 端口的业务服务
        proxy_pass http://127.0.0.1:8080/;
    }
}
```
而且 Nginx 能轻松挂上 HTTPS 证书（Let's Encrypt），让我的网站支持加密访问。这是生产环境的基本要求。
> HTTPS = HTTP + SSL/TLS 加密层，是在 HTTP 明文传输的基础上，增加了一层加密传输协议。HTTPS 证书是由权威证书机构（CA）颁发的数字凭证，一方面用来证明网站的真实身份，另一方面实现浏览器与服务器之间的加密传输，防止数据在传输过程中被窃取、篡改。

### 11.1.4 程序怎么保证一直运行？
我在 ECS 上手动运行，但它可能因为 panic、内存不足、系统重启等原因挂掉。我需要一个 **守护进程** 来自动拉起它。

Linux 系统自带 systemd，它可以把我写的程序注册成一个“服务”。我只需要写一个 unit 文件：
```ini
[Service]
ExecStart=/opt/stablepay/merchant-backend
Restart=always
```

然后 `systemctl start merchant-backend`。之后，无论程序崩溃还是机器重启，systemd 都会自动重启它。还可以 `journalctl -u merchant-backend` 看日志。

与此同时在开发时，我的 `config.yaml` 里写的数据库地址是 `localhost:3306`，用户是 `root`，密码是 `123456`。到了 ECS 上，这些都要变——ECS 上的 MySQL 可能在内网另一个 IP，密码也要改。更好的做法：**用环境变量覆盖敏感配置**。

在 systemd service 文件里加上：

```ini
Environment="DB_HOST=10.0.0.10"
Environment="DB_PASSWORD=ProdPass123"
```
然后修改代码，让 `config.yaml` 里的值可以被环境变量覆盖。这样配置文件可以提交到 git，而生产密码只存在于服务器的 systemd 文件中，更安全。

## 11.2 ACK 集群部署
ECS 单机部署虽然简单，但它有几个缺点：
- 扩容困难：流量大了只能换更大的机器（垂直扩展）。
- 单点故障：ECS 宕机了，服务就全挂了。
- 部署不便：每次更新代码要手动登录机器，停止服务，覆盖二进制，再启动。
所以真正生产级的方案是 **ACK（阿里云容器服务 Kubernetes）**。把 merchant-backend 做成容器镜像，交给 K8s 管理。K8s 可以：
- 自动调度到多台服务器（水平扩展）。
- 自动重启失败的 Pod。
- 滚动更新，零停机。
### 11.2.1 单机部署的问题
#### 扩容难
比如说啊，比如说，上线当天，AI Agent 成功买走了第一个 Labubu 公仔。第二天上午 10 点，某 KOL 发了一条视频，瞬间涌入大量 Agent 查询商品。CPU 飙到 100%，响应变慢，用户开始抱怨。

登录 ECS，看了一下 `top`，确实忙不过来了。怎么办？
- 垂直扩容：把 2 核 4G 升级成 4 核 8G。但需要关机重启，停机时间至少 5 分钟。
- 水平扩容：再加一台 ECS，把代码部署上去，前面用 Nginx 做负载均衡。
水平扩容听起来不错，但要手动做很多事：
1. 买一台新 ECS，配置环境（安装 Nginx、Go 运行时？其实不需要，我们用的是静态编译的二进制）。
2. 把 merchant-backend 二进制和配置文件 scp 过去。
3. 同样写 systemd 服务，启动。
4. 修改第一台 ECS 上的 Nginx 配置，把流量分一部分到新机器。
5. 万一其中一台挂了，还要手动摘掉。

**一台机器还好，两台就开始手忙脚乱，十台怎么办？**
#### 程序更新繁琐
晚上我修了一个 bug，需要发布新版本。流程是这样的：
```bash
# 本地交叉编译
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o merchant-backend

# 上传到每台 ECS
scp merchant-backend root@1.2.3.4:/opt/stablepay/
scp merchant-backend root@1.2.3.5:/opt/stablepay/
...

# 登录每台机器，重启 systemd 服务
ssh root@1.2.3.4 systemctl restart merchant-backend
ssh root@1.2.3.5 systemctl restart merchant-backend
...
```

不仅繁琐，而且重启过程中服务会短暂中断。如果 10 台机器一台台重启，整个过程要十几分钟。
#### 资源利用率低
每台 ECS 上只跑了一个 merchant-backend 进程，CPU 和内存利用率可能不到 20%。但为了应对流量高峰，我又不能把机器缩回去。这些闲置资源浪费了钱。
#### 环境不一致
开发环境有同学用的是 macOS，ECS 是 Ubuntu。虽然 Go 交叉编译帮我们解决了二进制兼容，但有些服务（比如 MySQL、Redis）不能在 ECS 上随意安装，需要专门的 DBA 维护。如果每个后端服务都自己搭一套数据库，那简直是灾难。

**我需要一个平台，能帮我解决：**
- 自动化的扩容缩容（水平扩展）
- 滚动更新，零停机
- 提高资源利用率（多个服务混部）
- 统一管理数据库、缓存等有状态服务

这个平台就是 **Kubernetes（K8s）**。
> 可以看一下[Minikube](https://minikube.cn/docs/start/?arch=%2Fwindows%2Fx86-64%2Fstable%2F.exe+download#LoadBalancer)的文档入门。
### 11.2.2 从“部署进程”到“声明期望”
K8s 的核心思想是：**你告诉它“我想要什么”，它负责“怎么做到”。**

在 ECS 上，我得说：
> “登录 1.2.3.4，下载二进制，运行 merchant-backend，再配置 systemd 守护……”

在 K8s 里，我只需要写一个 YAML，声明：
> “我想要 3 个 merchant-backend 副本，每个副本监听 8787 端口，健康检查路径是 /healthz。”

K8s 就会自动在集群的某几台机器上启动 3 个 **Pod**，并且保证始终有 3 个在运行。如果某个 Pod 挂了，它会自动重新创建一个。

这个 YAML 叫做 **Deployment**。
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stablepay-merchant-backend
spec:
  replicas: 3                      # 我要 3 个副本
  selector:
    matchLabels:
      app: merchant-backend
  template:
    metadata:
      labels:
        app: merchant-backend
    spec:
      containers:
      - name: merchant-backend
        image: stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/merchant-backend:latest
        ports:
        - containerPort: 8787
        livenessProbe:             # 存活探针
          httpGet:
            path: /healthz
            port: 8787
```
- **Pod**：K8s 调度的最小单位。一个 Pod 里可以有一个或多个容器（比如 merchant-backend 容器 + 一个 sidecar 日志容器）。
- **Deployment**：管理一组完全相同的 Pod。它负责创建、删除、更新 Pod，并保证 Pod 的数量符合你的要求。
换句话说，我不用手动 `systemctl restart` 了，我只需要改 Deployment 里的镜像版本，K8s 就会自动执行滚动更新：
```bash
kubectl set image deployment/stablepay-merchant-backend \
    merchant-backend=stablepay-registry/merchant-backend:v2 \
    --record
```
K8s 会先启动一个新 Pod，等它健康了，再停掉一个旧 Pod，重复直到全部替换。这个过程 **零停机**。
### 11.2.3 服务发现问题：Pod 会死，但 Service 永存
Pod 是有生命周期的。它可能因为节点宕机、滚动更新、资源不足而被删除重建。每次重建，Pod 的 IP 都会变。

如果我的 API Gateway 需要调用 merchant-backend，它总不能硬编码写死 Pod IP 吧？它需要一个 **固定的访问入口**。

K8s 的解决方案是 **Service**。
```yaml
apiVersion: v1
kind: Service
metadata:
  name: stablepay-merchant-backend
spec:
  selector:
    app: merchant-backend          # 匹配 Deployment 中 Pod 的 label
  ports:
    - port: 8787                   # Service 自己的端口
      targetPort: 8787             # 转发到 Pod 的端口
  type: ClusterIP                  # 集群内部可访问的虚拟 IP
```
Service 会有一个固定的 Cluster IP（比如 `10.96.0.12`）和一个 DNS 名字 `stablepay-merchant-backend.default.svc.cluster.local`。其他 Pod（比如 API Gateway）只需要通过这个 DNS 名字就能访问到 merchant-backend，不用关心后端 Pod 的 IP 怎么变。

**这就是服务发现**——K8s 内置的 DNS 会自动把 Service 名字解析到当前可用的 Pod IP 列表，并做负载均衡。

### 11.2.4 数据持久化问题：Pod 重建了，数据不能丢
之前我也想过用 SQLite 做数据库。在 ECS 上，SQLite 文件是存在硬盘上的，重启机器也不会丢。但在 K8s 里，Pod 重建后，新 Pod 的文件系统是全新镜像，原来的 `/app/data/merchant.db` 就没了。

- kubectl set image → 旧 Pod 被销毁 → 新 Pod 启动 → 
- 新 Pod 的文件系统是全新的镜像层 → /app/data/merchant.db 不存在 →
- Labubu 商品没了，Agent 访问返回空列表
这就是**容器存储的临时性（ephemeral storage）问题**。

Pod 的核心假设是"我可以随时被销毁和重建"。这是 K8s 做滚动更新、自动扩缩容、故障恢复的基础。但如果你的应用在本地文件系统上写数据，数据就会随着 Pod 一起消失。

解决方案是**把数据"挂"到 Pod 外面去**，让 Pod 的生命周期和数据存储分离。

K8s 用两个资源实现这个分离：
- PersistentVolume (PV)     → 真实的存储空间（阿里云盘、AWS EBS、NFS 等）
  - 一个真实的云硬盘（由集群管理员或云供应商自动创建）
- PersistentVolumeClaim (PVC) → Pod 对存储的"需求声明"
  - "我需要一个 1GB 的硬盘，可以读写"

在 merchant-backend 的 yaml 里，表现是这样的：

```yaml
# 1 Pod 的 volumes 字段声明"我要用 merchant-data-pvc 这块存储"
volumes:
  - name: merchant-data
    persistentVolumeClaim:
      claimName: merchant-data-pvc

# 2 Pod 的 volumeMounts 字段声明"我要把它挂到 /app/data"
containers:
  - volumeMounts:
      - name: merchant-data
        mountPath: /app/data

# 3 PVC 的定义在同一个 yaml 里：
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: merchant-data-pvc
  namespace: zheda-agent
spec:
  accessModes:
    - ReadWriteOnce        # 一个 Pod 读写
  resources:
    requests:
      storage: 1Gi         # 要 1GB
```

有了 PVC 之后，Pod 销毁重建的流程变成：
- 旧 Pod 被销毁 → /app/data 目录被卸载（但云硬盘上的数据还在）
- 新 Pod 启动 → PVC 绑定的云硬盘挂载到新 Pod 的 /app/data →
- merchant.db 文件完好无损 → Labubu 商品还在

这样一来，SQLite 文件就存到了云硬盘（PV）上。即使 Pod 被删除重建，新的 Pod 会重新挂载同一块云硬盘，数据完好无损。
- PVC 是你“要一块存储”的声明。
- PV 是实际的云硬盘（由云供应商自动创建）。
- 存储和 Pod 的生命周期是分开的——Pod 没了，PVC 还在，数据还在。

但最终我们还是把 MySQL 单独拆成一个独立的 Pod 运行。数据持久化的核心逻辑和 PVC/PV 底层机制完全不变，但存储的挂载对象从业务 Pod 转移到了专属的 MySQL Pod，数据和业务服务完全解耦，是生产环境的标准分层架构。这个我们就在[上一章](./11-mysql.md)详述吧。

### 11.2.5 对外暴露问题：Ingress 统一网关
Pod 有了，Service 有了，数据也持久化了。可是外网怎么访问我的 `/merchant/api/v1/products`？

在 ECS 时代，我用 Nginx 反向代理，监听 80/443，转发到本地 8080。在 K8s 里，我需要一个类似的“七层路由”组件。
> 网络通信有一套通用的分层标准叫 OSI 七层模型，其中第 7 层是应用层，对应 HTTP、HTTPS 这类携带业务语义的协议。七层负载均衡就是工作在应用层的流量转发能力，它可以读懂 HTTP 请求里的域名、URL 路径、请求头、Cookie 等内容，再根据这些信息把请求转发给不同的后端服务。
> 
> 与之对应的是四层负载均衡，工作在传输层（TCP/UDP），只能根据 IP 地址和端口号做转发，无法识别域名和 URL 路径。ClusterIP 类型 Service，本质就是四层负载均衡，它只能做端口级别的转发，无法实现单入口按路径分流。
这就是 **Ingress**，作用是声明七层路由规则：凡是以 `ai.wenfu.cn/merchant` 开头的请求，都转发到 `stablepay-merchant-backend` 这个 Service。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: stablepay-ingress
spec:
  ingressClassName: alb               # 阿里云的 ALB 作为入口控制器
  rules:
    - host: ai.wenfu.cn
      http:
        paths:
          - path: /merchant
            pathType: Prefix
            backend:
              service:
                name: stablepay-merchant-backend
                port:
                  number: 8787
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: stablepay-api-gateway
                port:
                  number: 8080
```
> pathType: Prefix：路径匹配类型为「前缀匹配」，只要请求的 URL 以 /merchant 开头就会命中这条规则，比如 /merchant/api/v1/products 也能匹配。除此之外还有 Exact（精确匹配，URL 必须完全一致）和 ImplementationSpecific（由具体的 Ingress Controller 自定义匹配逻辑）。
> backend.service：规则匹配成功后，请求最终转发的目标 Service，对应我们之前创建的 ClusterIP 类型的内部服务。
Ingress 像 Nginx 的配置文件，但只定义了 “规则”，它自己不会转发流量。

**Ingress Controller** 是真正干活的程序（比如阿里云的 ALB Ingress Controller 或 Nginx Ingress Controller）。
- 持续监听 Ingress 资源的变化（你 kubectl apply 了新规则，它会实时感知）。
- 根据 Ingress 规则，自动配置底层真正的负载均衡器（比如 Nginx、HAProxy，或者云厂商的 ALB/SLB）。

换句话说：
- **Ingress** = 愿望声明（“我想要这样的路由规则”）
- **Ingress Controller** = 执行器（“我来把规则翻译成底层负载均衡器的配置”）

常见的 Ingress Controller 实现有：
- Nginx Ingress Controller（社区最通用的方案，用 Nginx 做七层代理）
- 阿里云 ALB Ingress Controller（对接阿里云 ALB 负载均衡产品）
- AWS Load Balancer Controller（对接 AWS 的 ELB 负载均衡产品）

#### ALB（Application Load Balancer，应用型负载均衡）
**ALB** 是阿里云提供的托管式**七层负载均衡**云产品。它：
- 自带一个公网域名（比如 `alb-xxxxx.cn-shanghai.alb.aliyuncs.com`），底层对应动态的公网 IP 池，天然具备高可用能力。
- 支持丰富的转发规则：可以根据域名、URL 路径、请求头、Cookie 等维度，把请求转发到不同的后端（后端可以是 ECS 实例，也可以是 K8s 集群内的 Service 或 Pod）。
- 自带 HTTPS 加解密、流量控制、访问控制、监控告警等能力，不用我们自己维护 Nginx 集群。
在我们的 **ACK** 集群里，我们使用 **ALB Ingress Controller**。
> **ACK** 是阿里云容器服务 Kubernetes 版（Alibaba Cloud Container Service for Kubernetes）的缩写，是阿里云提供的托管式 K8s 集群服务。它帮我们维护 K8s 的控制面（Master 节点），同时深度集成了阿里云的存储、网络、负载均衡等云产品，我们只需要专注部署业务即可。

这个 Controller 会自动完成三件事：
1. 在阿里云上自动创建（或更新）一个 ALB 实例。
2. 把 Ingress 里写的 `host` 和 `path` 规则，翻译成 ALB 能识别的转发规则。
3. 打通 ALB 到集群内部的网络链路，把流量转发到对应的 Service。
所以完整的端到端请求链路是：

```text
AI Agent 请求 https://ai.wenfu.cn/merchant/api/v1/products
     ↓ DNS 解析
ai.wenfu.cn 是 CNAME 到 ALB 的域名（例如 alb-xxxxx.aliyuncs.com）
     ↓ 阿里云 ALB
ALB 根据域名和路径，把请求转发到 ACK 集群的某个入口（通常是 NodePort 或 ENI）。
     ↓ 集群内的 ALB Ingress Controller 已提前同步好规则
请求最终到达 Service stablepay-merchant-backend:8787
     ↓ Service 四层负载均衡
转发到某个 merchant-backend Pod
```
这里补充链路中的两个核心概念：
1. **CNAME 记录**
DNS 解析的核心记录类型之一，也叫别名记录。和我们 11.1.2 节讲的 A 记录（域名 → 直接映射 IPv4 地址）不同，CNAME 是把一个域名指向另一个域名，最终由目标域名完成 IP 解析。
比如我们把 `ai.wenfu.cn` 做 CNAME 指向 ALB 的官方域名，好处是：如果 ALB 底层的 IP 发生变更，云厂商会自动更新 ALB 域名的解析，我们自己的业务域名完全不用修改，稳定性和灵活性更高。云厂商的负载均衡、对象存储等服务，普遍都推荐用 CNAME 方式绑定自定义域名。

2. **ENI（弹性网卡，Elastic Network Interface）**
阿里云提供的一种虚拟网卡资源，可以直接挂载到 Pod 上，让 Pod 拥有和集群节点同级别的私网 IP。ALB 可以直接把流量转发到 Pod 的 ENI 网卡，不用经过节点的端口二次转发，相比 NodePort 方式性能更高、延迟更低，是阿里云 ACK 集群的高性能网络方案。
#### `NodePort` 或 `LoadBalancer`
这里我们把 Service 的三种常用类型完整说明，对应不同的使用场景：
- **ClusterIP（默认类型）**：集群内部使用的虚拟 IP，只能在集群内部访问，是服务发现的基础。我们之前讲的 merchant-backend Service 就是这种类型，适合微服务之间的内部调用。

- **NodePort**：在 ClusterIP 的基础上，会在 **每一个集群节点** 上都开放一个相同的高范围端口（默认范围 30000-32767，比如 30087）。用户访问 `http://任意节点IP:30087` 就能打到对应的 Service。
  - 问题：端口号不标准（不是 80/443），且本质是四层转发，不能根据域名/路径区分不同的服务。如果有 10 个微服务，就要开 10 个不同的端口，用户根本记不住，也无法共用 80/443 标准端口。

- **LoadBalancer**：在 NodePort 的基础上，自动对接云厂商的负载均衡器（比如阿里云 SLB），给 Service 分配一个独立的公网 IP。用户访问这个公网 IP 就能直接访问服务。
  - 问题：每个 Service 会单独创建一个云负载均衡器，如果有 10 个微服务，就要买 10 个 LB，成本高且管理复杂，同样无法实现单 IP 多服务的路径分流。

> "你的 merchant-backend 跑在 Pod 里，Service 是 ClusterIP，外网怎么访问？"
你当然可以把 Service 改成 NodePort 或 LoadBalancer：
```yaml
# NodePort 方案：每个节点开一个随机端口
spec:
  type: NodePort
  ports:
    - port: 8787
      nodePort: 30087  # 通过 http://任意节点IP:30087 访问
```
这样做的问题是：
```text
NodePort 方案：
  http://47.96.xxx.xxx:30087/merchant/api/v1/products
  ↑ IP 可能变（节点重启、迁移），端口不标准（30087），且没有 HTTPS

LoadBalancer 方案：
  http://merchant-xxx.aliyun.com:8787/api/v1/products
  ↑ 每个服务一个 LB，成本高，域名管理复杂，HTTPS 证书要自己配

Ingress 方案：
  https://ai.wenfu.cn/merchant/api/v1/products
  ↑ 统一域名、标准端口（443）、证书集中管理、路径路由
```

在我们的 ingress.yaml 里：
```yaml
spec:
  ingressClassName: alb                     # 使用阿里云 ALB（应用型负载均衡）
  rules:
    - host: ai.wenfu.cn                     # 只处理这个域名的请求
      http:
        paths:
          - path: /api                      # 以 /api 开头的请求
            pathType: Prefix                # 前缀匹配
            backend:
              service:
                name: stablepay-api-gateway  # → 发给 api-gateway
                port:
                  number: 8080
          - path: /merchant                 # 以 /merchant 开头的请求
            pathType: Prefix
            backend:
              service:
                name: stablepay-merchant-backend  # → 发给 merchant-backend
                port:
                  number: 8787
```

为什么我们 Service 最终选择 Ingress，就是因为只需要 **一个** 公网负载均衡器（ALB），就能根据域名和路径把流量分给多个 Service。这正是我们需要的——`ai.wenfu.cn/merchant` 走 merchant-backend，`/api` 走 api-gateway，`/` 走前端页面，所有服务共用 80/443 标准端口和同一个公网入口。

#### 路径匹配规则
> "如果 `/merchant` 和 `/merchant/api` 都配置了路由，请求打到哪里？"
这要看 `pathType`：

- **Prefix（前缀匹配）**：
```text
配置 /merchant → 匹配 /merchant、/merchant/、/merchant/api/v1/products、/merchant/healthz

配置 / → 匹配所有请求（默认兜底）
```
- **Exact（精确匹配）**：
```text
配置 /merchant → 只匹配 /merchant，不匹配 /merchant/ 或 /merchant/api
```

**ImplementationSpecific（实现相关）**：
取决于具体的 Ingress Controller 实现，ALB 下等同于 Prefix。

在我们集群中，请求的完整路由链是：
```text
Agent 请求 https://ai.wenfu.cn/merchant/api/v1/products
      ↓ DNS 解析
ai.wenfu.cn → CNAME → ALB 负载均衡器域名
      ↓ ALB（阿里云应用型负载均衡）
看到域名是 ai.wenfu.cn，路径是 /merchant/...
      ↓ Ingress 规则匹配
/merchant - Prefix - service: stablepay-merchant-backend:8787
      ↓ K8s Service
ClusterIP 转发到 Pod（kube-proxy + iptables/ipvs）
      ↓ Pod
merchant-backend 容器收到请求 → Hertz 路由 → /api/v1/products
```

## 11.3 决策链路
### 11.3.1 完整的部署流程
我只是想让 merchant-backend 在 ACK 上跑起来，并且能通过 `https://ai.wenfu.cn/merchant/api/v1/products` 访问商品列表。
这个 **最小目标** 可以拆成五件事。
```
1. 镜像存在：
   merchant-backend 镜像已经构建并推送到 ACR。

2. Pod 能跑：
   ACK 能拉到这个镜像，容器启动，Hertz 监听 8787。

3. Service 能通：
   集群内部能通过 stablepay-merchant-backend:8787 访问 Pod。

4. Ingress 能转发：
   外部访问 https://ai.wenfu.cn/merchant/... 时，ALB Ingress 转发到这个 Service。

5. 数据库能查：
   merchant-backend 能连上 stablepay-mysql，并查到 stablepay_merchant_db.products。
```
先看一下我们的经验之道 `deploy.sh` 做了什么。这个脚本让我们能把 merchant-backend 从本地代码变成线上服务：
```bash
#!/bin/bash
set -euo pipefail

REGISTRY="stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev"
IMAGE_NAME="merchant-backend"
NAMESPACE="zheda-agent"

VERSION="v$(date +%Y%m%d.%H%M%S)"

# 1. 构建 Docker 镜像（Go 多阶段构建）
docker build --platform linux/amd64 -t "${IMAGE_NAME}:${VERSION}" .

# 2. 打 ACR 标签
docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY}/${IMAGE_NAME}:latest"

# 3. 推送到阿里云容器镜像服务
docker push "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
docker push "${REGISTRY}/${IMAGE_NAME}:latest"

# 4. 通知 K8s 更新镜像版本
kubectl set image deployment/stablepay-merchant-backend \
    "merchant-backend=${REGISTRY}/${IMAGE_NAME}:${VERSION}" \
    -n "${NAMESPACE}"

# 5. 等待上线完成
kubectl rollout status deployment/stablepay-merchant-backend -n "${NAMESPACE}"
```
#### 环境名词
这个脚本的流程是：
```
本地代码 → Docker 镜像 → ACR 镜像仓库 → K8s 拉取新镜像 → 滚动更新
```
这次最容易混乱的是三个 **命名空间**：
```
ACK 集群：
  阿里云 Kubernetes 集群本身，由 kubeconfig 指向。

Kubernetes Namespace：
  K8s 集群内部的资源隔离空间，例如 zheda-agent。

ACR Namespace：
  阿里云容器镜像仓库里的命名空间，例如 stablepay-dev。
```
它们名字都像“空间”，但完全不是一回事。

| 概念 | 全称/说明 | 作用 | 典型标识/示例 | 核心特点 |
| ---- | ---- | ---- | ---- | ---- |
| **ACK 集群** | 阿里云容器服务 Kubernetes 版（Alibaba Cloud Container Service for Kubernetes），阿里云托管 K8s 集群 | 定义当前操作**连接到哪一套 Kubernetes 集群环境**，是整套容器编排的运行载体 | 执行命令：<br>`kubectl get pods -n zheda-agent` | 托管式 K8s 服务，`kubectl` 通过 kubeconfig 关联指定 ACK 集群，所有资源操作均在该集群内执行 |
| **Kubernetes Namespace** | K8s 命名空间 | 对集群内资源做**逻辑隔离**，划分独立资源空间 | 标识：`zheda-agent`<br>YAML 配置：<br>`metadata: namespace: zheda-agent` | 1. 集群内资源（Pod/Deployment/Service/Secret 等）归属隔离<br>2. 同命名空间内资源可互相引用，跨命名空间默认无法直接访问<br>3. Secret、ConfigMap 等配置资源仅在当前命名空间内生效 |
| **ACR Namespace** | 阿里云容器镜像仓库命名空间 | 划分镜像仓库的**存储路径**，用于分类、管理容器镜像 | 标识：`stablepay-dev`<br>完整镜像地址：<br>`stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/merchant-backend:latest` | 1. 属于**镜像仓库**体系，和 K8s 命名空间相互独立<br>2. 仅用来组织、归类镜像文件<br>3. 镜像存储位置 与 容器运行的 K8s 命名空间 互不冲突 |

> 第 4 步的 `kubectl set image` 会触发 K8s 的滚动更新——Deployment 会创建一个新 Pod，新 Pod 拉取新版本的镜像，等新 Pod 通过 readinessProbe 后，再销毁旧 Pod。

### 11.3.2 K8S 目录结构
```
D:\MYLAB\STABLEPAY\INFRA-DEPLOYMENT
└─k8s
    │  README.md
    │
    ├─ack
    │  │  README.md
    │  │
    │  ├─apps
    │  │      api-gateway.yaml
    │  │      blockchain-adapter.yaml
    │  │      did-service.yaml
    │  │      merchant-backend.yaml
    │  │      payment-service.yaml
    │  │      query-service.yaml
    │  │      stablepay-docs.yaml
    │  │      stablepay-frontend.yaml
    │  │      verification-service.yaml
    │  │
    │  ├─config
    │  │      blockchain-adapter-config.yaml
    │  │
    │  ├─infra
    │  │      all.yaml
    │  │      rocketmq-topic-init-job.yaml
    │  │
    │  └─platform
    │          ingress.yaml
    │
    └─base
            configmaps.yaml
            infra.yaml
            kustomization.yaml
            mysql-init-job.yaml
            namespace.yaml
            secrets.yaml
            services.yaml
```
对于 `infra-deployment/k8s/base` 和 `infra-deployment/k8s/ack`：
- base：通用基础清单，偏本地、Minikube、开发环境、可复用模板。
- ack：阿里云 ACK 线上环境清单，包含 **ACR 镜像地址、imagePullSecrets、alicloud storageClass、ALB Ingress、zheda-agent namespace**。

所以生产环境优先看 ACK，而对于当前项目，ACK 目录又分成三类：
- **ack/infra**：
  - 基础设施，比如 Namespace、Secret、ConfigMap、MySQL、Redis、RocketMQ、初始化 Job。
  - 频率很少改。除非要改数据库、Redis、RocketMQ、Secret、ConfigMap。

- **ack/apps**：
  - 业务服务，比如 did-service、payment-service、query-service、frontend、merchant-backend。
  - 经常改。每个服务发版时更新自己的 Deployment 镜像。

- **ack/platform**：
  - 平台入口，比如 Ingress、域名、证书、ALB 路由规则。
  - 偶尔改。新增域名路径、证书、Ingress 规则时才改。

#### 一个问题
这是完全依赖 AI vibe 且不经常沉淀指导文档就会出现的问题，也是我决定沉淀这篇文档的初心。
`merchant-backend` 是一个新业务服务，所以我本来应该主要改：
```text
infra-deployment/k8s/ack/apps/merchant-backend.yaml
infra-deployment/k8s/ack/platform/ingress.yaml
merchant/Dockerfile
merchant/deploy.sh
merchant/config/config.go
```
最多补一下 ACK infra 里的数据库初始化逻辑。但是该死的这种 Code CLI不应该直接执行：
```bash
kubectl apply -f infra-deployment/k8s/base/infra.yaml -n zheda-agent
```
这条命令的问题是，它把通用 base 里的基础设施配置强行应用到了线上 namespace `zheda-agent`。结果不是“只为 merchant 建个库”，而是把现有 MySQL、Redis、RocketMQ 的 Deployment 模板也更新了，触发新的 ReplicaSet 和 Pod 创建。

从人的直觉看，我可能以为它只是“帮我把 MySQL 准备好”。

但 Kubernetes 看到的是：
```text
你给了我一份 infra.yaml；
里面声明了 stablepay-mysql、stablepay-redis、stablepay-rocketmq；
我需要让集群里的这些资源变成 YAML 描述的样子。
```
如果这些 Deployment 已经存在，`apply` 就不是新建，而是更新。

Deployment 一旦更新 Pod 模板，就会触发 **滚动更新**：
```
Deployment 模板变化
  ↓
创建新的 ReplicaSet
  ↓
新的 ReplicaSet 创建新 Pod
  ↓
新 Pod 拉镜像、挂 PVC、启动容器
  ↓
新 Pod Ready 后旧 Pod 才会被替换
```
这就是为什么当时我看到新旧 Pod 同时存在：
```bash
stablepay-mysql-665d697689-jltw5      1/1 Running
stablepay-mysql-7f8ff7b5fd-7lfmv      0/1 ContainerCreating
```
它表示：
- 旧 ReplicaSet 的 Pod 还在跑；
- 新 ReplicaSet 的 Pod 因为模板变化被创建；
- 新 Pod 没有 Ready；
- 滚动更新卡住了。

更具体的状态是：
```text
stablepay-mysql-init-f5xql                     0/1 ImagePullBackOff
stablepay-rocketmq-broker-6cf9597d9f-9wsx2     0/1 ImagePullBackOff
stablepay-rocketmq-nameserver-66dbfc99cb-wqfkf 0/1 ImagePullBackOff
```
也就是说，base 清单使用 Docker Hub 公共镜像，比如 `mysql:8.0`、`redis:7-alpine`、`apache/rocketmq:5.3.2`。但 ACK 节点不一定能（划掉，基本可以视为完全不能）稳定访问 Dockerhub。正确做法是我们再把这批基础镜像同步到 ACR，这样 ACK 节点就能把 ACR 当 Dockerhub：
```text
stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/mysql:8.0
stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/redis:7-alpine
stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/rocketmq:5.3.2
```
并且在 Pod spec 里配置：
```yaml
imagePullSecrets:
  - name: acr-secret
```

回滚 Deployment 解决：

```bash
kubectl -n zheda-agent rollout undo deployment/stablepay-mysql
kubectl -n zheda-agent rollout undo deployment/stablepay-redis
kubectl -n zheda-agent rollout undo deployment/stablepay-rocketmq-nameserver
kubectl -n zheda-agent rollout undo deployment/stablepay-rocketmq-broker
```

### 11.3.3 配置不能写死在 config.yaml
本地运行时，`config.yaml` 很方便，但上云以后，很多配置不应该写死在镜像里：
```text
MySQL host
MySQL password
DB name
seed_enabled
public base url
seller address
proof secret
Solana network
USDC mint
```
如果这些都写在 `config.yaml` 里，每次改一个配置都要重新 build 镜像。更合理的是：
```text
镜像内有默认 config.yaml；
K8s Deployment 通过 env 注入线上配置；
程序启动时用 env override 配置文件。
```
所以 merchant-backend 的配置加载需要支持：
```text
文件默认值 + 环境变量覆盖
```
例如 Deployment 里写：
```yaml
env:
  - name: DB_DRIVER
    value: "mysql"
  - name: MYSQL_HOST
    value: "stablepay-mysql"
  - name: MYSQL_DB_NAME
    value: "stablepay_merchant_db"
  - name: DB_SEED_ENABLED
    value: "false"
  - name: MERCHANT_PUBLIC_BASE_URL
    value: "https://ai.wenfu.cn/merchant"
```
敏感信息不要直接写明文，而是从 Secret 读：
```yaml
- name: MYSQL_PASSWORD
  valueFrom:
    secretKeyRef:
      name: stablepay-secrets
      key: mysql-password

- name: MERCHANT_PROOF_SECRET
  valueFrom:
    secretKeyRef:
      name: stablepay-secrets
      key: merchant-proof-secret
```
#### Secret
K8s Secret 解决的问题是：
```text
我需要把密码、私钥、proof secret 交给 Pod；
但不想把它们直接写在 Deployment YAML 里。
```
对于 merchant-backend，至少有这些敏感信息：
```text
MYSQL_PASSWORD
MERCHANT_PROOF_SECRET
STABLEPAY_API_KEY
```
这带来一个新排查点：
```bash
kubectl -n zheda-agent describe pod <merchant-pod>
```
- 如果 Secret key 不存在，Pod 可能直接起不来。
- 如果 env 没生效，应用日志里可能会显示仍然使用默认配置。
这里要注意：
```text
stringData：
  可以直接写明文，K8s 会帮你转成 base64 存储。
data：
  需要自己提供 base64 后的值。
```
- 普通非敏感配置我放在 ConfigMap 或 env 里，敏感配置放在 Secret 里。
- Deployment 通过 valueFrom.secretKeyRef 引用 Secret。
- 这样镜像可以复用，配置可以按环境注入，密钥也不需要写进代码仓库。

所以以后我们排查配置问题，要先看：
```bash
kubectl -n zheda-agent describe pod <pod>
kubectl -n zheda-agent logs deploy/stablepay-merchant-backend --tail=100
kubectl -n zheda-agent exec <pod> -- env
```
如果镜像里没有 `env` 命令，就通过 `kubectl describe pod` 看注入项，或者临时用 debug 容器。

### 11.3.5 checklist
最终正确上线流程应该是：
1. 确认 ACK 基础设施已经存在
   MySQL / Redis / RocketMQ 都 Running，不要重新 apply base infra。

2. 确认 stablepay_merchant_db 存在
   如果不存在，只在现有 MySQL 里建库和授权。

3. 确认 stablepay-secrets 有 merchant-proof-secret
   没有就 patch 一个。

4. 构建 merchant-backend 镜像
   用 Dockerfile 多阶段构建，并推送到 ACR stablepay-dev。

5. apply merchant app YAML
   创建/更新 Deployment 和 Service。

6. set image 或 deploy.sh 更新镜像版本
   等待 rollout status 成功。

7. apply platform ingress
   增加 /merchant 路由到 stablepay-merchant-backend:8787。

8. 从内到外验证
   Pod logs → Service endpoints → port-forward → Ingress curl。

对应命令大概是：
```bash
cd /mnt/d/mylab/stablepay

kubectl -n zheda-agent get pods
kubectl -n zheda-agent get svc stablepay-mysql stablepay-merchant-backend
kubectl -n zheda-agent get secret stablepay-secrets

MERCHANT_PROOF_SECRET=$(openssl rand -hex 32)
kubectl -n zheda-agent patch secret stablepay-secrets --type merge \
  -p "{\"stringData\":{\"merchant-proof-secret\":\"${MERCHANT_PROOF_SECRET}\"}}"

MYSQL_POD=$(kubectl -n zheda-agent get pod -l app=stablepay-mysql \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

kubectl -n zheda-agent exec "$MYSQL_POD" -- mysql -uroot -proot123 -e "
CREATE DATABASE IF NOT EXISTS stablepay_merchant_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'stablepay'@'%' IDENTIFIED BY 'stablepay123';
GRANT ALL PRIVILEGES ON stablepay_merchant_db.* TO 'stablepay'@'%';
FLUSH PRIVILEGES;
"

kubectl apply -f infra-deployment/k8s/ack/apps/merchant-backend.yaml
cd /mnt/d/mylab/stablepay/merchant
bash deploy.sh v20250612
kubectl -n zheda-agent rollout status deployment/stablepay-merchant-backend --timeout=180s
cd /mnt/d/mylab/stablepay
kubectl apply -f infra-deployment/k8s/ack/platform/ingress.yaml
curl --max-time 15 -iLsS https://ai.wenfu.cn/merchant/healthz
curl --max-time 15 -iLsS https://ai.wenfu.cn/merchant/api/v1/products
```
注意：这里没有 `kubectl apply -f infra-deployment/k8s/base/infra.yaml -n zheda-agent`。

这条命令不应该出现在 merchant-backend 的 ACK 上线流程里。

## 11.4 其他排障
### 11.4.1 容器里没curl
尝试：
```bash
kubectl -n zheda-agent exec "$POD" -- curl -sS http://localhost:8080/healthz
```
结果报错：
```text
exec: "curl": executable file not found in $PATH
```
很多生产镜像会故意做得很小，只包含应用二进制和必要证书，不带 curl、bash、vim 这些调试工具。

更好的做法有三个：
#### 方法 1：用 `kubectl logs`
```bash
kubectl -n zheda-agent logs deploy/stablepay-merchant-backend --tail=100
```
这次日志里已经能看到 Hertz 监听：
```text
HTTP server listening on address=[::]:8787
```
这说明应用至少启动了。
#### 方法 2：用端口转发
```bash
kubectl -n zheda-agent port-forward deploy/stablepay-merchant-backend 8787:8787
curl http://127.0.0.1:8787/healthz
curl http://127.0.0.1:8787/merchant/api/v1/products
```
这种方式不依赖容器里有 curl。
#### 方法 3：起一个临时 debug Pod
```bash
kubectl -n zheda-agent run netshoot --rm -it \
  --image=nicolaka/netshoot -- /bin/bash
```
进入后可以访问：
```bash
curl http://stablepay-merchant-backend:8787/healthz
curl http://stablepay-merchant-backend:8787/merchant/api/v1/products
```
这可以验证集群内部 Service 是否通。
### 11.4.2 返回前端 HTML
执行：
```bash
curl -iLsS https://ai.wenfu.cn/merchant
```
返回了前端 HTML。

这说明请求没有进 merchant-backend，而是被前端兜底规则吃掉了。

一般原因有几个：
```text
1. Ingress 里没有 /merchant 规则；
2. /merchant 规则没生效；
3. /merchant 规则顺序或匹配优先级有问题；
4. ALB 规则数量超限，新的规则没有成功下发（我们是这个。Mintlify应该进OSS+CDN那条路）；
5. DNS 指向的不是当前 Ingress 对应的 ALB；
6. 浏览器或 CDN 缓存了前端响应。
```
排查顺序应该是：
```bash
kubectl -n zheda-agent describe ingress stablepay-ingress
kubectl -n zheda-agent get ingress stablepay-ingress -o yaml
kubectl -n zheda-agent get svc stablepay-merchant-backend
kubectl -n zheda-agent get endpoints stablepay-merchant-backend
curl --max-time 15 -iLsS https://ai.wenfu.cn/merchant/api/v1/products
```
`describe ingress` 里出现类似：
```text
quota ... loadbalancer rules ... exceeded
```
就不是后端问题，而是 ALB 规则没有成功应用。

如果 `/merchant/api/v1/products` 最终返回 JSON，就说明链路已经通了：
```text
Ingress → Service → Pod → Hertz → ProductHandler
```
#### 面试所谈
STAR法则进行：现象 → 判断层级 → 查事件 → 定位根因 → 保护数据 → 回滚基础设施 → 最小化上线业务服务。
```
我在把 merchant-backend 部署到阿里云 ACK 时，遇到过一次比较典型的线上排障。

最开始我的目标只是把一个新的 Go + CloudWeGo 商户服务部署到 ACK，
通过 https://ai.wenfu.cn/merchant 暴露给 Agent 调用。
但我误把 base 目录下的 infra.yaml apply 到线上 zheda-agent namespace，
导致现有 MySQL、Redis、RocketMQ 的 Deployment 模板被更新，触发了滚动更新。

排查时我先用 kubectl get pods 看到新旧 Pod 共存：
旧 Pod 还 Running，新 Pod 卡在 ContainerCreating 或 ImagePullBackOff。
然后通过 describe pod 和 events 判断：
ImagePullBackOff 是因为 ACK 节点拉 Docker Hub 镜像超时；
ContainerCreating 是因为 MySQL/Redis 的 RWO PVC 已经被旧 Pod 挂载，新 Pod 无法挂载。

解决时我没有删除 PVC，因为那是生产数据盘。
我选择 rollout undo 回滚基础设施 Deployment，恢复旧 Pod。
随后把部署边界重新拆清楚：
base 保持通用开发清单；
ack/infra 管基础设施；
ack/apps 管业务服务；
ack/platform 管 Ingress。

merchant-backend 自己只走 ack/apps/merchant-backend.yaml，
镜像推送到 ACR stablepay-dev，
K8s 资源部署在 zheda-agent，
通过 stablepay-mysql Service 连接已有 MySQL。
最后给 Ingress 增加 /merchant 前缀路由，实现公网访问。
```
### 11.4.3 排障顺序
被卡住的一个根本原因，是我一开始不知道该从哪里查。
以后遇到 K8s 部署问题，可以按这个顺序：
```bash
第一层：Deployment 有没有创建？
kubectl -n zheda-agent get deploy stablepay-merchant-backend

第二层：Pod 有没有 Ready？
kubectl -n zheda-agent get pod -l app=stablepay-merchant-backend

第三层：Pod 为什么没 Ready？
kubectl -n zheda-agent describe pod <pod>
kubectl -n zheda-agent logs <pod> --tail=100

第四层：Service 有没有选中 Pod？
kubectl -n zheda-agent get svc stablepay-merchant-backend
kubectl -n zheda-agent get endpoints stablepay-merchant-backend

第五层：集群内部能不能访问？
kubectl -n zheda-agent port-forward deploy/stablepay-merchant-backend 8787:8787
curl http://127.0.0.1:8787/healthz

第六层：Ingress 有没有规则？
kubectl -n zheda-agent describe ingress stablepay-ingress
kubectl -n zheda-agent get ingress stablepay-ingress -o yaml

第七层：公网是否真的打到 Ingress？
curl --max-time 15 -iLsS https://ai.wenfu.cn/merchant/api/v1/products
```
## 11.5 面试讲法
### Q1: "你对 Kubernetes 及云原生部署有深入理解，举个实际例子"

```text
我在 StablePay 项目中负责 merchant-backend 的云原生部署。

整个 CI/CD 链路是：
本地开发 → Docker 多阶段构建 → 推送到阿里云 ACR → 
kubectl set image 触发 K8s 滚动更新 → ALB Ingress 暴露服务

在部署过程中我做了几个关键决策：

第一，数据持久化。
Merchant Backend 用 SQLite 作为数据库。
SQLite 是文件型数据库，Pod 重建会丢数据。
所以我引入了 PVC，把 SQLite 文件挂载到阿里云盘上，
保证 Pod 滚动更新后数据不丢失。

第二，路由设计。
服务部署在 https://ai.wenfu.cn 下。
我不想给每个微服务分配独立域名，
所以用 Ingress + 路径前缀路由：
/merchant 前缀路由到 merchant-backend，
/api 前缀路由到 api-gateway。

第三，探活设计。
我用专门的 /healthz 端点做 livenessProbe 和 readinessProbe，
而不是复用业务接口。
这样业务 bug 不会导致 K8s 误判服务死亡。
```

### Q2: "PVC 和 PV 的区别？你用 PVC 遇到过什么问题？"

```text
PV 是存储资源本身，PVC 是对存储资源的需求声明。

我遇到过一个典型问题是 PVC 处于 Pending 状态。
新集群没有配置默认的 StorageClass，PVC 创建后找不到能绑定的 PV。
排查方法是 kubectl describe pvc <name>，看 Events 里的错误信息。
解决方法是配置阿里云 CSI 驱动作为 StorageClass，实现自动创建云硬盘。
```

### Q3: "Ingress 和 Service 的区别？"

```text
Service 是四层（TCP/UDP）负载均衡，工作在 IP:Port 级别。
Ingress 是七层（HTTP/HTTPS）路由规则，工作在 URL 路径和域名级别。

在我们的架构中：
Service：把流量从集群内部转发到 Pod
Ingress：把流量从外部（通过域名 + 路径）路由到正确的 Service

所以 Ingress 不负责转发流量，它只负责告诉 ALB"请求来了怎么路由"。
真正转发流量的是 ALB（阿里云应用型负载均衡器）和 kube-proxy。
```

### Q4: "你们的部署是高可用的吗？如果不是，怎么改进？"

```text
当前阶段 merchant-backend 是单副本部署，原因是 SQLite 不支持多副本并发写入。
如果要求高可用，我有两个改进方向：

短期方案：
配置 PodDisruptionBudget 保证节点维护时至少有一个副本运行。
配置节点反亲和（podAntiAffinity）让 Pod 调度到不同节点上。
SQLite 文件通过阿里云 NAS（网络存储）共享，Pod 可以漂移到其他节点。

长期方案：
把 SQLite 替换为 MySQL，利用 MySQL 的主从复制。
这样可以实现多副本部署，任一 Pod 挂掉不影响服务。
因为 ProductRepository 是接口，切换数据库实现只需要改 Infrastructure 层。
```

### Q5: "镜像版本策略：为什么打 latest 和具体版本两个标签？"

```text
deploy.sh 里打两个标签：
- merchant-backend:latest    → 给 K8s YAML 默认引用
- merchant-backend:v20250612 → 给回滚用

kubectl rollout undo 可以回滚到上一个版本。
但如果没有具体版本号，latest 回滚后无法追踪回滚到哪个版本。
所以我保留两个标签：latest 用于部署，具体版本号用于追溯和回滚。
```
## 11.6 名词附表
### 1. Namespace（命名空间）
- **概念**：K8s 中用于隔离资源的逻辑分区。
- **场景**：`zheda-agent` 和 `stablepay-dev` 两个命名空间。Claude 曾错误地将 `base` 目录下的 YAML 的 namespace 全部改成了 `zheda-agent`，导致部署时误操作了 ACK 线上环境；修正后 `base` 恢复为 `stablepay-dev`，线上 ACK 资源继续使用 `zheda-agent`。

### 2. Pod（容器组）
- **概念**：K8s 调度的最小单元，包含一个或多个容器。
- **场景**：所有运行中的服务（MySQL、Redis、RocketMQ、merchant‑backend 等）都以 Pod 形式存在。我们遇到过多种 Pod 状态：
  - `Running`：正常运行的旧 Pod。
  - `ContainerCreating`：新 Pod 卡在创建阶段（由于 PVC 挂载或镜像拉取问题）。
  - `ImagePullBackOff`：镜像拉取失败（Docker Hub 超时）。

### 3. Deployment（部署）
- **概念**：声明式地管理 Pod 和 ReplicaSet，支持滚动更新与回滚。
- **场景**：所有服务（`stablepay-mysql`、`stablepay-redis`、`stablepay-rocketmq-nameserver`、`stablepay-rocketmq-broker`、`stablepay-merchant-backend`）均由 Deployment 控制。错误地 `apply` 了 `base/infra.yaml` 后，这些 Deployment 的模板被更新，触发了新的 ReplicaSet 创建，导致了问题。

### 4. ReplicaSet（副本集）
- **概念**：Deployment 创建的子对象，负责维护指定数量的 Pod 副本。
- **场景**：新旧 ReplicaSet 共存：旧的 Pod 仍在 `Running`，新的 Pod 因镜像或存储问题卡在 `ContainerCreating`。`rollout undo` 会让 Deployment 回到之前的 ReplicaSet 模板。

### 5. Service（服务）
- **概念**：为一组 Pod 提供稳定的网络访问入口（Cluster IP、DNS）。
- **场景**：`stablepay-mysql`、`stablepay-merchant-backend` 等服务。`merchant‑backend` 通过 Service 名称 `stablepay-mysql` 连接数据库。

### 6. PersistentVolumeClaim（PVC，持久卷声明）
- **概念**：请求持久化存储资源（如云盘），供 Pod 挂载使用。
- **场景**：MySQL 和 Redis 的 62 天前创建的 PVC（如 `mysql-data`），使用 `ReadWriteOnce`（RWO）访问模式。新 Pod 被调度到不同节点时，RWO 卷无法同时挂载到两个节点，导致新 Pod 一直 `ContainerCreating`。**不要删除这些 PVC**，它们包含生产数据。

### 7. StorageClass（存储类）
- **概念**：定义动态存储供应的“类别”，如云盘类型、IOPS 等。
- **场景**：`alicloud-disk-essd` 是阿里云 ACK 环境中使用的 ESSD 云盘 StorageClass，出现在 `base/infra.yaml` 的错误修改中（不应在通用 base 中硬编码 ACK 特有的 StorageClass）。

### 8. Job（一次性任务）
- **概念**：用于执行一次性任务，任务完成后 Pod 会终止。
- **场景**：`stablepay-mysql-init` 是一个 Job，用于初始化数据库（建库、授权）。同样因镜像拉取问题进入 `ImagePullBackOff`。后续改为直接在 MySQL Pod 内执行 SQL 来替代该 Job。

### 9. Secret（密钥）
- **概念**：存储敏感信息，如密码、Token，可以以文件或环境变量形式挂载到 Pod。
- **场景**：
  - `stablepay-secrets`：包含 `mysql-password`、`mysql-root-password`、`hotwallet.json` 等。
  - `merchant-proof-secret`：需要手动 `patch` 到 Secret 中，否则 merchant Pod 会因缺失密钥而创建失败。
  - `imagePullSecrets`：名为 `acr-secret` 的 Secret 用于从阿里云 ACR 私有仓库拉取镜像。

### 10. ConfigMap（配置映射）
- **概念**：存储非敏感配置，同样可以注入到 Pod 中。
- **场景**：`base/configmaps.yaml` 中定义了 `did-config`、`payment-config` 等 ConfigMap，但 merchant 应用本次主要通过文件和环境变量控制配置。

### 11. ImagePullSecrets（镜像拉取密钥）
- **概念**：一种特殊 Secret，用来向私有镜像仓库认证。
- **场景**：ACK 环境使用的 YAML 中 `imagePullSecrets: - name: acr-secret`，允许 Pod 从 ACR（阿里云容器镜像服务）拉取镜像；而错误的 `base/infra.yaml` 使用 Docker Hub 公共镜像，没有拉取密钥，导致超时。

### 12. Ingress（入口控制器）
- **概念**：管理外部 HTTP/HTTPS 流量到集群内服务的路由规则。
- **场景**：`https://ai.wenfu.cn/merchant/...` 的流量通过 Ingress 转发。因此需要在 merchant 代码中添加 `/merchant/healthz` 和 `/merchant/api/v1/...` 路由，以匹配 Ingress 的路径前缀。

### 13. Rollout Undo（回滚）
- **概念**：将 Deployment 回滚到上一个可用的版本（ReplicaSet）。
- **场景**：修复基础设施问题时的第一步：`kubectl rollout undo deployment/stablepay-mysql` 等，让 MySQL/Redis/RocketMQ 回到旧版本的镜像和配置，避免数据丢失。

### 14. 环境变量注入（Env / SecretKeyRef）
- **概念**：通过 `env` 字段直接定义环境变量，或通过 `secretKeyRef` 从 Secret 中读取。
- **场景**：merchant 的 Deployment YAML 中大量使用了环境变量（如 `MYSQL_HOST`、`DB_SEED_ENABLED`），并且通过 `secretKeyRef` 引用了 `stablepay-secrets` 中的 `mysql-user` 和 `mysql-password`。修改后的 `config.go` 会读取这些环境变量并覆盖配置文件中的默认值，从而避免为每个环境修改文件重新构建镜像。

### 15. 健康检查（Liveness & Readiness Probe）
- **概念**：
  - **Liveness Probe**：判定容器是否存活，失败则重启容器。
  - **Readiness Probe**：判定容器是否准备好接收流量，失败则将 Pod 从 Service 端点移除。
- **场景**：merchant Pod 配置了 `httpGet` 探针，路径 `/healthz`，用于自动健康检测。

### 16. 镜像仓库（Image Registry）
- **概念**：存放容器镜像的仓库，如 Docker Hub、阿里云 ACR。
- **场景**：原有基础设施使用了 Docker Hub 的公共镜像（`mysql:8.0`、`redis:7-alpine`、`apache/rocketmq:5.3.2`），在国内 ACK 环境下拉取超时；正确做法是使用上传到 ACR 的镜像（例如 `stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/...`），并且基础镜像（如 Go、Alpine）也改用 ACR 中的镜像。

### 17. RWO 访问模式与 Pod 调度
- **概念**：`ReadWriteOnce` 的卷只能被单个节点上的单个 Pod 挂载为读写。当 Deployment 更新且新 Pod 被调度到不同节点时，旧 Pod 仍占用着该卷，新 Pod 会因无法挂载而一直处于 `ContainerCreating`。
- **场景**：MySQL 和 Redis 的新 Pod 处于 `ContainerCreating`，正是因为这个原因。修复方法是回滚 Deployment，让旧 Pod 保持不变。

### 18. kubectl 常用命令
- **apply**：声明式创建/更新资源。
- **get**：查看资源列表（`pods`, `deploy`, `pvc`）。
- **describe**：查看资源详情和事件。
- **exec**：在容器内执行命令。
- **rollout undo/status**：管理 Deployment 的回滚和更新状态。
- **set image**：直接更新 Deployment 的容器镜像。
- **patch**：部分更新资源（如 Secret）。
- **delete job**：删除一次性任务。

### 19. Ingress（入口）
- **概念**：Kubernetes 中用于管理集群外部 HTTP/HTTPS 流量路由到集群内部 Service 的 API 对象。通过在 Ingress 中定义一组**路由规则（rules）**，可以将不同域名/路径的请求转发到不同的后端 Service。
- **场景**：你的线上环境使用 `stablepay-ingress`，其中包含多条规则。新增 merchant 时需要在 Ingress 中增加一条规则：`path: /merchant` → `backend: stablepay-merchant-backend:8787`。

### 20. Ingress Controller（入口控制器）
- **概念**：真正执行 Ingress 规则、进行流量转发的组件。它不是 Kubernetes 内置的，需要单独部署（如 Nginx Ingress Controller、阿里云 ALB Ingress Controller）。
- **场景**：你的 ACK 集群使用的是**阿里云 ALB Ingress Controller**。你 `kubectl apply` 了 Ingress YAML 后，规则会由该 Controller 同步到真实的阿里云应用型负载均衡（ALB）实例上。

### 21. ALB（应用型负载均衡）与 ALB Ingress Controller
- **概念**：
  - **ALB**：阿里云提供的七层负载均衡产品，支持基于 HTTP/HTTPS 的请求转发。
  - **ALB Ingress Controller**：Kubernetes 的一个控制器，负责监听 Ingress 资源的变化，并自动调用阿里云 API 在对应的 ALB 实例上创建或修改监听规则、转发组等。
- **场景**：
  - 你的 `ingress.yaml` 中声明了 `kubernetes.io/ingress.class: alb`，表明该 Ingress 由 ALB Controller 处理。
  - `kubectl apply` 后，Controller 需要**一段时间同步**到阿里云 ALB。如果同步过程中出现问题（如规则数量超限），即使 Ingress 对象在 K8s 中已更新，ALB 侧也可能未生效。

### 22. Path Type（路径匹配类型）
- **概念**：Ingress 规则中 `pathType` 字段，指定 URL 路径的匹配方式。常见值：
  - `Prefix`：前缀匹配（如 `/merchant` 会匹配 `/merchant`、`/merchant/healthz`、`/merchant/api/v1/products`）。
  - `Exact`：精确匹配。
  - `ImplementationSpecific`：由具体 Ingress Controller 决定匹配方式。
- **场景**：你在 Ingress 中添加的 `/merchant` 规则使用了 `Prefix` 类型，因此所有以 `/merchant` 开头的请求都应被转发到 merchant-backend Service。但前提是**这条规则在 ALB 中排在前端兜底规则 `/` 之前**，否则会被前端规则抢先匹配。

### 23. ALB 规则配额（Rule Quota）
- **概念**：阿里云 ALB 对单个监听器（或实例）可配置的**转发规则数量**有上限，例如标准版默认最多 100 条规则。超出上限后，ALB Controller 无法创建新规则，导致新增的 Ingress path 不生效。
- **场景**：
  - 当 `kubectl apply` 新的 Ingress YAML 后，公网访问 `/merchant` 依然返回前端 HTML。
  - 通过查看 Ingress 事件（`kubectl describe ingress`）发现了关键错误：
    ```
    alb_quota_loadbalancer_rules_num_standard_edition is exceeded (usage 103/100)
    ```
    这表示 ALB 上已有的规则数已达上限，新增的 `/merchant` 规则无法写入 ALB，因此流量仍然被已有的前端 `/` 规则兜底转发。

### 24. Ingress 事件（Events）
- **概念**：Kubernetes 资源（如 Ingress）会记录生命周期中的异常事件，类似于 Pod 的事件。通过 `kubectl describe ingress <name>` 可以看到 Ingress Controller 在处理规则同步时产生的错误或警告。
- **场景**：你在 `describe` 中看到了上述 ALB 配额超限的告警，这是定位 Ingress 规则不生效的直接证据。

### 25. Service 与 Endpoints
- **概念**：
  - **Service**：为一组 Pod 提供统一的网络入口（Cluster IP）。
  - **Endpoints**：Service 自动维护的后端 Pod IP 列表。当 Service 的 selector 匹配到 Ready 的 Pod 时，对应 Pod 的 IP 和端口会被加入 Endpoints。
- **场景**：在排查 Ingress 前，你验证了 `stablepay-merchant-backend` Service 和它的 Endpoints 是否正确指向了 merchant Pod。这两者正常，说明问题不在 Pod 或 Service 本身，而在上层 Ingress 规则。

### 26. Proxy（代理）与网络白名单
- **概念**：由于国内访问 Solana 外网 RPC 会受限，你们在香港搭建了一台代理服务器（`proxy.stablepay.co`），对特定出口 IP 开放白名单，用于转发区块链请求。这不是 K8s 内置概念，但属于微服务架构中外网访问的常见手段。
- **场景**：Pod 所在 VPC 的 NAT 网关出口 IP 为 `116.62.178.52`，已在代理白名单中。应用中需要将 Solana RPC 地址替换为代理地址（如 `https://proxy.stablepay.co/https://api.devnet.solana.com`），确保链上调用不被墙。

### 27. VPC（Virtual Private Cloud，专有网络）
- **概念**：云上隔离的私有网络环境，你可以完全掌控 IP 地址范围、子网划分、路由表和网关。阿里云的 VPC 可以绑定到 ACK 集群。
- **与 K8s 的关系**：
  - ACK 集群必须运行在某个 VPC 内，所有节点（ECS）和 Pod（使用 Flannel/Terway 等 CNI）的 IP 均从 VPC 的子网中分配。
  - VPC 实现了**二层网络隔离**，不同 VPC 默认不互通，保证安全性。
- **场景**：你的 ACK 集群部署在 **`vpc-bp1op2tvahuhr2sf2x003`** 中，所有 Pod 的内网通信都发生在这个 VPC 内。你看到的 `47.99.94.107:6443`（API Server 端点）通常也是一个在 VPC 内的 SLB 或 EIP，因此需要网络可达。

### 28. NAT 网关（Network Address Translation Gateway）
- **概念**：一种将私有 IP 地址转换为公网 IP 地址的网关服务，使无公网 IP 的云资源（如 ECS、Pod）能够主动访问互联网。
- **与 K8s 的关系**：
  - ACK 集群的节点或 Pod 如果位于**私有子网**（没有直接分配公网 IP），它们要下载镜像、访问外部 API 等，就必须通过 NAT 网关转发流量。
  - NAT 网关有一个固定的**出口公网 IP**，外部服务可以通过这个 IP 进行白名单控制。
- **场景**：
  - 你的 VPC **已经配置了 NAT 网关**，出口 IP 为 **`116.62.178.52`**。
  - 这意味着所有从 Pod 发往公网的请求（例如访问 `proxy.stablepay.co`）都会从该 IP 出去。
  - 由于国内访问 Solana RPC 被墙，你在香港部署了一台代理服务器，并**将该出口 IP 加入白名单**，从而允许 Pod 的请求被转发到 `https://api.devnet.solana.com`。

### 29. CNI（容器网络接口）与 Pod 网络
- **概念**：Kubernetes 通过 CNI 插件为 Pod 分配 IP 并实现网络通信。阿里云 ACK 常用 **Terway**（基于阿里云弹性网卡）或 **Flannel**（VxLAN 封装）。
- **关键点**：
  - Pod IP 可能直接来自 VPC 子网（Terway 模式），也可能通过 Overlay 网络隐藏真实 VPC IP。
  - 无论哪种模式，Pod 访问公网的流量最终都会经过节点，然后通过 VPC 的 NAT 网关出去，源 IP 会被替换为 NAT 网关的公网 IP。
- **场景关联**：你不需要在 Pod 内配置代理鉴权，因为所有出口流量已经由 NAT 网关统一转换为 `116.62.178.52`，代理服务器据此放行。

### 30. 公网访问 Ingress 的流量链路
- **从公网到 Pod**：
  ```
  用户 → 域名解析（aliyun SLB/ALB） → ALB 实例（公网） → 通过内网转发到 ACK 节点 → Pod
  ```
  - ALB 实例本身绑定公网 IP，并接入了阿里云的 DDoS 防护等。
  - Ingress 规则在 ALB 上生效，将 `/merchant` 流量转发给 `stablepay-merchant-backend` Service，最终到达 Pod。
  - **NAT 网关不参与这一方向的流量**，只负责 Pod 主动发起的出流量。

### 31. 代理与白名单在 K8s 中的实践
- **代理转发**：在代码或配置中将外部 URL 替换为内部代理地址（如 `https://proxy.stablepay.co/https://api.devnet.solana.com`）。
- **出口 IP 固定**：通过 NAT 网关确保出口 IP 不变，从而在代理侧设置 IP 白名单，避免复杂的证书或 Token 认证。
- **高可用性**：NAT 网关本身是托管服务，会自动容灾，比自建 Squid 代理更稳定。

### 32. OSS（Object Storage Service，对象存储）
- **概念**：一种可无限扩展的、扁平化的文件存储服务，通过 HTTP API 进行文件上传、下载和管理。阿里云的 OSS、AWS 的 S3 等均是典型产品。与传统文件系统不同，它没有目录层级，文件通过“桶（Bucket）+ 对象键（Key）”定位。
- **与 K8s 的关系**：
  - K8s 本身不提供静态资源托管，通常是应用程序（如前端、文档）通过 Service/Ingress 对外暴露，这会占用计算资源和带宽。
  - 将静态文件（HTML、JS、CSS、图片等）迁移到 OSS 后，访问压力从集群内的 Pod 转移到了云存储服务，**Pod 不再需要承载静态资源请求**。
- **优势**：无限存储、高持久性、低成本、自带高可用和备份。

### 33. CDN（Content Delivery Network，内容分发网络）
- **概念**：一种分布式的边缘节点缓存网络，将源站（OSS 或自定义源）的内容缓存到离用户最近的节点，加速访问并降低源站压力。
- **与 OSS 的集成**：通常将 OSS 作为 CDN 的**源站**。用户请求静态资源时，CDN 边缘节点直接返回缓存数据；未缓存时回源到 OSS 获取。例如，阿里云 CDN 可以直接对接 OSS Bucket。
- **与 Ingress/ALB 的区别**：
  - ALB 是七层负载均衡，主要用于动态 API 流量，每个请求最终都可能到达后端 Pod，计算和带宽成本较高。
  - CDN 专门优化静态内容分发，大量流量在边缘节点就被拦截，不需要进入 VPC、NAT、更不占用 ALB 规则配额。
- **场景**：
  - 你的架构中，`stablepay-docs` 等静态文档页面目前通过 Ingress 规则指向一个 Pod 服务，每个文档路径（如 `/settlement`）就占用一条 ALB 规则。如果将这些文档静态化部署到 OSS，并通过 CDN 加速，可以**释放大量 ALB 规则配额**，提升加载速度，同时降低 Pod 资源消耗。

### 34. 前后端分离与动静分离
- **概念**：
  - **前后端分离**：前端静态资源（SPA 应用）与后端 API 服务独立部署、独立域名或路径。
  - **动静分离**：将动态请求（API）和静态请求（前端资源、图片等）分流到不同处理单元，通常静态资源由 CDN/OSS 服务，动态请求由 Ingress → Service → Pod 处理。
- **在当前架构中的应用**：
  - 已有 `stablepay-frontend`（前端 Pod）和 `stablepay-docs`（文档 Pod），它们本质上是**动态托管的静态资源**：Pod 运行一个简单的 HTTP 服务器（如 Nginx）来返回静态文件。
  - 动静分离后，前端和文档的构建产物可以直接上传到 OSS，DNS 或 Ingress 将 `/` 和 `/docs` 的流量直接解析/转发到 CDN，不再经过 ALB → Service → Pod 的链路。
  - 你需要修改前端构建流程：`npm run build` 后，用 `ossutil` 或 CI 插件把 `dist/` 目录同步到 OSS Bucket；同时配置 CDN 域名并更新 Ingress（如果需要保留域名统一）或直接使用 CDN 域名。
