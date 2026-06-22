---
date: 2026-06-03
title: 文档站部署踩坑笔记：从 404 到子路径、中文 403
authors: [bubblevan]
tags: []
---

> 场景：在 `ai.wenfu.cn` 同域部署两个静态前端——`stablepay-frontend`（`/`）与 Mintlify 文档（`/docs/`）。  
> 本文把排障过程沉淀为可复用的认知，面向对 Nginx、K8s、Mintlify、kubectl 尚不熟悉的自己。

## 1. 先建立「请求怎么走」的全景图

```text
浏览器 https://ai.wenfu.cn/docs/
    ↓
阿里云 ALB Ingress（ingress.yaml，按 path 最长/规则顺序匹配）
    ↓
Service stablepay-docs:80  或  stablepay-frontend:80
    ↓
Pod 内 Nginx（容器 80 端口）
    ↓
磁盘上的静态文件 /usr/share/nginx/html/...
```

**三个层次，三个「路由表」**——改错一层，表象会像「缓存」「Mintlify 坏了」，其实是另一层在拦你：

| 层次 | 谁决定 | 典型问题 |
|------|--------|----------|
| Ingress | `ingress.yaml` 的 `paths` | `/quickstart` 落到 frontend，文档侧边栏点穿 |
| Nginx | `nginx.conf` 的 `location` | `/docs/zh/` 403、alias 死循环 |
| 构建产物 | Dockerfile + `mintlify export` | `docs` 是文件不是目录 → 404 Not a directory |

排障时**从上到下核对**：浏览器 Network → Ingress 规则 → Pod 内 `curl localhost` → 容器内 `ls` 文件树。

### 1.1 什么是 Ingress

Ingress 是 Kubernetes 集群的「入口控制器」，负责将集群外部的 HTTP/HTTPS 请求转发到集群内部的 Service。可以把 Ingress 理解为一套转发规则：当请求到达集群时，Ingress Controller（例如阿里云 ACK 使用的 ALB Ingress Controller）检查请求的域名和路径，然后决定把这个请求交给哪个 Service 处理。

在阿里云 ACK 环境中，Ingress 资源通过 YAML 文件定义，提交后由 ALB Ingress Controller 自动在阿里云负载均衡（ALB）上创建对应的转发规则。因此，修改 `ingress.yaml` 后必须执行 `kubectl apply`，否则负载均衡层面的规则不会更新。

### 1.2 Ingress 的路径匹配机制

Ingress 的路径匹配遵循两个核心原则：**最长前缀匹配** 和 **规则顺序匹配**。

- **最长前缀匹配**：当多个 path 规则都可以匹配一个请求时，匹配路径最长的那个规则生效。例如，请求路径 `/docs/zh/`，规则中有 `path: /docs` 和 `path: /docs/zh`，则后者匹配更长，优先使用。
- **规则顺序匹配**：当没有明确的长短关系时（例如两个规则都是 `path: /api`，但指向不同 Service），按 Ingress YAML 中规则的书写顺序匹配，先写先匹配。

还有一个重要概念：`pathType`。Kubernetes Ingress 支持三种路径匹配类型：

- **Prefix**：前缀匹配。`path: /docs` 匹配 `/docs`、`/docs/`、`/docs/zh/` 等所有以该前缀开头的路径。这是最常用的类型。
- **Exact**：精确匹配。`path: /docs` 只匹配 `/docs`，不匹配 `/docs/` 或 `/docs/zh`。
- **ImplementationSpecific**：由具体的 Ingress Controller 决定匹配方式。ALB Ingress Controller 对此类型的处理与 Prefix 类似。

在一个同域部署两个应用（前端主站和文档站）的场景中，路径规则的设计需要特别小心。以本项目为例，Mintlify 生成的页面里有大量以根路径 `/` 开头的链接，比如侧边栏的 `/quickstart`、语言切换的 `/zh`、Next.js 加载 chunk 的 `/_next/static/...`。这些路径本身没有 `/docs` 前缀，因此 Ingress 必须为它们单独声明规则，指向文档站的 Service。否则，这些请求会被末尾的 `path: /` 规则捕获，交给前端主站处理，导致 404 或返回前端 HTML，使 JS 解析失败。

### 1.3 什么是 Service

Service 是 Kubernetes 中将一组 Pod 抽象为一个稳定网络入口的资源。Pod 的 IP 会随着重启、重新调度而变化，但 Service 提供一个固定的集群内 IP（ClusterIP）和 DNS 名称。在上述流程中，Ingress 将请求转发给 Service，Service 再根据 `selector` 标签将请求负载均衡到匹配的 Pod。Service 本身不做路径判断，它只是一个「流量中转站」。

### 1.4 请求在 Pod 内如何到达 Nginx

请求被 Service 转发到 Pod 后，进入 Pod 内部的网络命名空间。Pod 内运行着 Nginx 容器，监听 80 端口。Nginx 收到请求后，开始进行它自己的路径匹配——这就是下一层路由。从这个角度看，一个完整的请求经过了两次路径匹配：第一次是 Ingress 决定去哪个 Service，第二次是 Nginx 决定去磁盘上哪个文件。两层必须协调一致，缺一不可。

## 2. 核心知识点

### 2.1 Mintlify `export` 产出的是 ZIP，不是文件夹

```dockerfile
# 常见误解
RUN npx mintlify export --output ./_site
COPY --from=builder /app/_site /usr/share/nginx/html/docs
# → _site 是 ~16MB 的 zip 文件，COPY 后变成名为 docs 的「单文件」
```

```dockerfile
# 正确
RUN npx mintlify export --output ./_site.zip \
    && unzip -q ./_site.zip -d ./_site \
    && test -f ./_site/index.html
COPY --from=builder /app/_site/ /usr/share/nginx/html/docs/
```

**日志指纹**：`"/usr/share/nginx/html/docs/index.html" is not found (20: Not a directory)`  
→ `docs` 是文件，不是目录。

**教训**：读 CLI 帮助——`mint export --output` 默认是 `export.zip`，不是目录名。

### 2.2 同域子路径：Mintlify 按「站点根」生成路径

离线导出后，HTML/JS 里默认是：

- `/_next/static/...`
- `/quickstart`
- `/zh`（语言切换）

我们挂在 `https://ai.wenfu.cn/docs/`，但应用「以为」自己在 `https://ai.wenfu.cn/`。

所以需要**两套补救**（缺一不可）：

1. **构建期**：只改 HTML 的链接；JS 只改 `/_next/`、`/_mintlify/` 等资源前缀，**不要**在 JS 里批量替换站内路由。
2. **运行期**：Nginx + Ingress 把根路径请求「兜」到 docs 服务（`/_next`、`/quickstart`、`/zh` 等）。

官方子路径方案也是反向代理/重写，见 [Mintlify: Host docs at a /docs subpath](https://www.mintlify.com/docs/deploy/docs-subpath)。

#### 2.2.1 为什么 HTML 和 JS 的替换策略不同

HTML 文件是服务端在构建阶段产出的纯文本，其内容由开发者控制。在 HTML 中，链接以 `href="/quickstart"` 或 `src="/_next/static/..."` 的形式明文存在。因为结构固定，所以可以用脚本安全地做字符串替换，将站内链接加上 `/docs` 前缀。

JavaScript 文件则完全不同。现代前端构建工具（Webpack、Turbopack 等）会将代码压缩成紧凑的单行或几行，变量名被缩短为单个字母，所有字符串被集中放在一个字符串表中。在这样的文件中，字符 `/` 会出现在无数位置：正则表达式、JSON 字符串、路径拼接逻辑、React Router 的路由定义等等。如果用一个简单的 `sed` 替换将 `/` 全部改成 `/docs/`，这些与路径无关的 `/` 也会被替换，导致 JS 语法错误或运行时逻辑错误，整个应用直接崩溃——这就是为什么 JS 的替换范围必须严格限制在 `/_next/`、`/_mintlify/` 这类明确是资源路径的字符串上，且通常只在构建工具链中通过环境变量（如 Next.js 的 `basePath` 配置）来实现，而不是事后用 sed 修改。

### 2.3 致命坑：对 `.js` 做 `sed` 替换 `"/"` → `"/docs/"`

症状：

- `/docs/` **先正常闪一下**，然后 **Error 500 / Connection closed**
- Nginx 日志仍是 **200**（HTML 已返回）
- 控制台：`f486afc314643ce1.js` / `cbb16a3954e7bd60.js` 报错

原因：压缩后的 webpack chunk 里有海量 `"/"` 字符串。把路由 `/` 的替换规则用在 `.js` 上，等于**整包 JS 语法/字符串表被破坏**，React hydration 失败。

**正确分工**：

| 文件类型 | 可改什么 | 禁止什么 |
|----------|----------|----------|
| `.html` | `href`、`/_next/`、站内 `/quickstart` → `/docs/quickstart` | — |
| `.js` | 仅 `/_next/`、`/_mintlify/` 等资源路径 | 不要用 `"/"`、`"/zh"` 等路由级替换 |

这是「一改就好」的关键分水岭：**404/403 像服务器问题，500+Connection closed 像 JS 被改坏**。

### 2.4 Nginx：`alias` + `try_files` 回退 = 内部重定向死循环

#### 2.4.1 Nginx 的 `location` 是什么

`location` 是 Nginx 配置中的核心指令，定义「当请求 URI 匹配某个模式时，应该执行哪些操作」。一个 `server` 块内可以有多个 `location`，Nginx 按照一套固定的优先级规则选择执行哪一个。

匹配优先级从高到低是：

1. **精确匹配**（`=`）：`location = /docs`，完全相等才匹配。
2. **前缀匹配 + 优先前缀**（`^~`）：`location ^~ /_next/`，匹配以 `/ _next/` 开头的请求；`^~` 表示一旦匹配成功就不再检查正则。
3. **正则匹配**（`~` 或 `~*`）：`location ~ \.(js|css)$`，按正则表达式匹配；区分大小写用 `~`，不区分用 `~*`。
4. **普通前缀匹配**（无修饰符）：`location /docs/`，匹配以 `/docs/` 开头的请求。

当请求到达时，Nginx 会先扫描所有精确匹配和带 `^~` 的前缀匹配，如果命中就直接使用。如果没有命中，Nginx 会记住匹配到的最长前缀规则，然后按顺序检查正则匹配，第一个正则匹配到就使用。如果没有任何正则匹配到，最终使用之前记住的那个最长前缀规则。

#### 2.4.2 `root` 与 `alias` 的区别

这是 Nginx 中最容易混淆的两个指令，但在静态文件服务中极其关键。

- **`root`**：将 `location` 匹配到的 URI 路径**拼接**在 `root` 指定的目录后面，组成最终的磁盘路径。例如配置 `root /usr/share/nginx/html;` 和 `location /docs/`，请求 `/docs/zh/index.html` 的实际磁盘路径是 `/usr/share/nginx/html/docs/zh/index.html`。也就是说，请求路径中的 `/docs/` 部分会被保留在文件系统路径中。
- **`alias`**：将 `location` 匹配到的部分**替换**为 `alias` 指定的路径。例如配置 `alias /var/data/;` 和 `location /docs/`，请求 `/docs/zh/index.html` 的实际路径是 `/var/data/zh/index.html`。注意，此时请求路径中的 `/docs/` 被去掉了，换成 `/var/data/`。

在本项目中，静态文件的实际存储位置是 `/usr/share/nginx/html/docs/` 目录。由于请求路径恰好也是以 `/docs/` 开头，所以 **`root` 是最自然、最不容易出错的选择**——请求路径和磁盘路径的结构完全一致。

使用 `alias` 的常见场景是：希望将某个 URL 路径映射到磁盘上完全不同的位置。例如，如果文档文件实际存放在 `/var/static-content/` 下，但希望用 `/docs/` 这个 URL 来访问，就需要 `alias /var/static-content/;`。

`alias` 有一个容易被忽视的规则：如果 `location` 以 `/` 结尾，`alias` 也必须以 `/` 结尾；如果 `location` 不以 `/` 结尾，`alias` 也不能以 `/` 结尾。两者必须成对一致。例如 `location /docs/` 配 `alias /data/docs/` 是正确的，`location /docs/` 配 `alias /data/docs` 会导致路径拼接错误，Nginx 会将文件路径错拼为 `/data/docszh/index.html`（中间缺少斜杠分隔）。

#### 2.4.3 `try_files` 的工作原理

`try_files` 是 Nginx 提供的一个按顺序检查文件或目录是否存在的指令。它的语法是：

```nginx
try_files file1 file2 ... uri;
```

Nginx 会按从左到右的顺序，在磁盘上检查 `root`（或 `alias`）对应的路径下是否存在 `file1`、`file2`……，找到第一个存在的文件就立即返回。如果所有列出的文件都不存在，就执行最后一次指定的 `uri`——这个 `uri` 会引发一次**内部重定向**，Nginx 用它作为新的请求 URI，重新走一遍 `location` 匹配流程。

**内部重定向**意味着 Nginx 不会给客户端返回 302 或 301，而是在服务器内部重新处理一个新的 URI。因此，新 URI 会再次进入 `location` 匹配，这可能导致循环。典型的循环场景是：`try_files` 的最后一个回退 URI 与当前 `location` 匹配的是同一规则。例如：

```nginx
location /docs/ {
    alias /usr/share/nginx/html/docs/;
    try_files $uri $uri/ /docs/index.html;
}
```

此时如果 `$uri` 和 `$uri/` 都不存在，Nginx 会以 `/docs/index.html` 为新的请求 URI，重新进入 `location` 匹配。`/docs/index.html` 以 `/docs/` 开头，再次命中这个 `location`，`try_files` 里的 `/docs/index.html` 又被用作回退 URI——如此无限循环，最终 Nginx 返回 500 Internal Server Error。

#### 2.4.4 本项目的正确写法：`named location` 回退

为了避免循环，本项目采用了 `named location`。`named location` 是以 `@` 开头的特殊 `location`，它不会被常规请求路径匹配到，只能通过 `try_files` 的最后一个参数来显式跳转进入。因为它是单向的、不可被路径匹配自然进入，所以不会引发循环。

当前 `nginx.conf` 中的文档 SPA 回退配置如下：

```nginx
location /docs/ {
    try_files $uri $uri/ @docs_spa;
}

location @docs_spa {
    rewrite ^ /docs/index.html break;
}
```

这里的逻辑是：对于 `/docs/` 下的请求，Nginx 先在磁盘上检查对应的文件（`$uri`）或目录下的索引文件（`$uri/`）；如果都不存在，就进入 `@docs_spa`，用 `rewrite ... break` 将请求 URI 重写为 `/docs/index.html` 并直接在当前上下文处理，而不会产生新的内部重定向。

`rewrite ... break` 和 `rewrite ... last` 的区别很重要：

- **`break`**：重写 URI 后，在当前 `location` 上下文里继续处理，不再重新匹配 `location`。适合回退到 SPA 入口文件这类「到此为止」的场景。
- **`last`**：重写 URI 后，以新 URI 为起点，重新走一遍所有 `location` 的匹配流程。适合需要让新 URI 被其他 `location` 规则处理的场景，比如将 `/_next/` 改写成 `/docs/_next/` 后，让它进入 `/docs/` 的 `location` 处理静态文件。

### 2.5 Nginx：目录存在但没有 `index.html` → 403

中文切换访问 `/docs/zh/`：

```text
directory index of "/usr/share/nginx/html/docs/zh/" is forbidden
GET /docs/zh/ HTTP/1.1" 403
```

导出结构里中文首页是 **`zh/index/index.html`**（`docs.json` 里页面 id 为 `zh/index`），**不是** `zh/index.html`。

`try_files $uri $uri/` 发现 `zh/` 是目录 → 找 `zh/index.html` → 没有 → 默认禁止目录列表 → **403**（不会落到 `@docs_spa`）。

**修复**：精确匹配 + 内部 rewrite（保留 `?_rsc=` 查询参数）：

```nginx
location = /docs/zh/ {
    rewrite ^ /docs/zh/index/ last;
}
```

**教训**：静态站点的 URL ≠ 磁盘路径；Mintlify/Next 习惯「每页一个目录 + index.html」。

#### 2.5.1 为什么目录没有 `index.html` 会导致 403

Nginx 的默认行为是：当请求一个以 `/` 结尾的路径（如 `/docs/zh/`）时，`try_files $uri/` 会让 Nginx 检查这个目录是否存在。如果存在，Nginx 会尝试返回该目录下的**索引文件**。默认的索引文件由 `index` 指令定义（本项目配置的是 `index index.html;`），意味着 Nginx 会依次查找 `index.html`。

如果 `/usr/share/nginx/html/docs/zh/` 目录里没有 `index.html`，Nginx 就无法返回默认索引文件。此时 Nginx 的下一个默认行为是**生成目录列表**（显示该目录下所有文件的列表），但出于安全考虑，现代 Nginx 默认禁用了目录列表功能（`autoindex off`），于是直接返回 403 Forbidden。

这意味着 `try_files $uri/` 在目录存在但缺少 `index.html` 的情况下并不会触发回退——`$uri/` 这个检查项已经「成功」了（目录存在），Nginx 不会再继续执行 `@docs_spa` 回退。

#### 2.5.2 如何排查磁盘路径问题

在容器内直接查看文件结构是最可靠的方式，不受 Nginx 配置或 Ingress 规则的任何干扰：

```bash
kubectl exec -n zheda-agent deploy/stablepay-docs -- ls -la /usr/share/nginx/html/docs/zh/
```

这个命令的输出会精确显示 `zh/` 目录下有哪些文件和子目录。如果输出中只有 `index/` 子目录，而没有 `index.html` 文件，就说明中文首页确实不在预期的位置，需要用精确的 `location` 规则做 rewrite。

### 2.6 K8s Ingress：路径是「谁先匹配、指到哪个 Service」

`ingress.yaml` 里**最后**的 `path: /` 会吃掉所有未单独声明的前缀。

必须为文档独占（示例）：

- `/docs`
- `/_next`、`/_mintlify`、`/logo`、`/favicons`
- `/quickstart`、`/api-reference`、`/zh`、…

否则：

- 侧边栏 → `https://ai.wenfu.cn/quickstart` → **frontend** 的 SPA → 空白或错页
- `/_next/...` → frontend 返回 `index.html` → JS 把 HTML 当脚本解析 → **Connection closed**

**`curl -I` 返回 200 不代表路由正确**——frontend 的 SPA 对任意路径也可能 200+`index.html`。

#### 2.6.1 ALB Ingress 的路径规则详解

阿里云 ACK 的 ALB Ingress Controller 在处理路径时，遵循以下规则：

- 路径匹配基于 HTTP 请求的完整路径（path），不包括查询参数（query string）。
- 同一个域名下，多个 path 规则按**最长前缀优先**的原则进行匹配。
- `path: /` 是一个特殊的前缀，它匹配所有路径。因此，在 Ingress YAML 的 `rules` 列表中，`path: /` 必须放在最后，否则它会把所有请求都拦截，后续更精确的规则永远不会被匹配到。
- ALB Ingress 支持 `pathType: Prefix`、`Exact` 和 `ImplementationSpecific`。在生产环境中，大多数场景使用 `Prefix` 类型即可覆盖。

#### 2.6.2 同域多应用的 Ingress 设计模式

当两个应用共享同一个域名时，Ingress 的路径规则设计必须采用「白名单 + 兜底」的模式：

1. 列出文档站需要独占的所有路径前缀，为每个前缀创建指向 `stablepay-docs` Service 的规则。
2. 将 `path: /` 作为最后一条规则，指向 `stablepay-frontend` Service，兜底所有未被上述规则匹配的请求。

对于 Mintlify 这类生成大量绝对路径（以 `/` 开头的链接）的静态站点，构建产物本身不会知道自己被挂载在 `/docs/` 子路径下。因此，`/_next/`、`/quickstart`、`/zh` 等路径必须像 `/docs/` 本身一样，被显式地添加到 Ingress 规则中。如果漏掉任何一个，对应的请求就会落到前端主站，导致 404 或 JS 解析错误。

#### 2.6.3 验证 Ingress 路由是否生效

验证 Ingress 路由不能用简单的 `curl -I` 检查 HTTP 状态码。前端主站的 SPA 可能对任意路径都返回 200 和 `index.html`，状态码本身不能说明请求到了正确的应用。

更可靠的验证方式是检查**响应体的内容特征**：

```bash
# 检查 /_next/ 路径是否返回 JS 内容而非 HTML
curl -s https://ai.wenfu.cn/_next/static/chunks/xxx.js | head -1
# 正确的响应应该是 JavaScript 代码，如果返回 <!DOCTYPE html> 则说明路由错误

# 检查 /quickstart 是否返回文档页而非前端 SPA
curl -s https://ai.wenfu.cn/quickstart | grep -o '<title>.*</title>'
# 对比预期标题，判断是前端还是文档站返回的
```

另外，确认 Ingress 的修改已在 ALB 层面生效，可以查看 Ingress 资源的状态和 ALB 控制台对应的转发规则：

```bash
kubectl describe ingress -n zheda-agent <ingress-name>
```

输出中会显示 ALB 实例 ID 和当前生效的转发规则列表。如果刚修改了 `ingress.yaml` 并执行了 `kubectl apply`，ALB Ingress Controller 通常需要几十秒到一两分钟来同步规则到 ALB 实例。

### 2.7 Frontend 缓存：旧版 UI 不一定是「没部署成功」

Vite 构建：

- `index.html` → 引用 `/assets/index-xxxxx.js`（hash 随构建变）
- Nginx 曾对 `.js` 设长期 `immutable` 缓存

若 **`index.html` 可被浏览器缓存**，会一直指向**旧 hash** 的 JS → 看起来像发版失败。

**策略**：

- `index.html` / SPA 路由：`Cache-Control: no-cache`
- `/assets/*`：长期缓存 + hash 文件名

**验证**（比肉眼看页面可靠）：

```bash
kubectl exec -n zheda-agent deploy/stablepay-frontend -- \
  grep -o '/assets/[^"]*' /usr/share/nginx/html/index.html | head -1
curl -s https://ai.wenfu.cn/ | grep -o '/assets/[^"]*' | head -1
# 两边 hash 一致 → 集群已是新版，浏览器硬刷新即可
```

#### 2.7.1 浏览器缓存与 Nginx 缓存控制的协作

HTTP 缓存是一个「逐级协商」的机制。Nginx 通过 `Cache-Control` 响应头告诉浏览器（以及中间的 CDN、代理服务器）如何处理响应内容。关键的指令包括：

- **`no-cache`**：浏览器可以缓存，但每次使用前必须向服务器验证内容是否有更新（通过 `If-None-Match` 或 `If-Modified-Since` 请求头）。服务器返回 304 Not Modified 时，浏览器使用本地缓存。
- **`no-store`**：完全不缓存，每次必须重新请求。
- **`public, max-age=31536000, immutable`**：告诉浏览器和中间代理，这个资源可以缓存一年，且在缓存有效期内内容永不改变（`immutable`）。这适用于文件名中包含内容哈希的资源（如 `index-abc123.js`），因为内容改变时文件名也会改变，所以旧缓存永远不会被错误使用。

对于 SPA 应用，`index.html` 是一个特殊文件：它的文件名不变，但内容会随着每次构建而改变（引用的 JS/CSS 文件名中的 hash 变了）。因此，`index.html` 不能使用长期缓存，否则浏览器在缓存有效期内不会向服务器请求新的 `index.html`，自然也就不知道 JS 文件已经更新，继续加载旧版本的 JS chunk。如果旧版 JS 已被删除（容器重建后），页面就会出现资源 404 错误。

本项目中 `nginx.conf` 对静态资源使用了 `expires 1y; add_header Cache-Control "public, immutable";`，这是正确的，因为文件名已经包含 hash。但必须确保 `index.html` 没有被同一规则缓存。在配置中，这个保护依赖于 `location /` 的精确匹配将 `index.html` 的缓存策略与 `/assets/` 分开处理。

#### 2.7.2 前端缓存问题的排查方法论

部署新版本后，如果页面看起来仍是旧版，按以下顺序排查：

1. 浏览器端：打开开发者工具 → Network 面板 → 勾选 "Disable cache"，硬刷新（Ctrl+Shift+R）。如果页面恢复正常，问题在浏览器缓存。
2. CDN 端：如果使用了 CDN，通过 CDN 控制台检查缓存刷新状态，或使用 `curl -H "Host: ai.wenfu.cn" http://<CDN节点IP>/` 绕过 CDN 直接验证源站。
3. 服务端：用上文 2.7 节的命令对比 Pod 内文件和公网响应的 asset hash，确认源站内容确实已更新。
4. Nginx 配置：检查 `nginx.conf` 中是否对 `index.html` 设置了长期缓存的 `Cache-Control` 头。如果存在，修复配置并重建 Pod。

### 2.8 日志与现象对照表

| 现象 | 优先怀疑 |
|------|----------|
| 404 + `Not a directory` | `docs` 是 zip 文件未解压 |
| 先正常后 500 + Connection closed | JS 被 sed 改坏；或 `/_next` 打到 frontend |
| 403 + `directory index ... forbidden` | 目录无 `index.html`（如 `/docs/zh/`） |
| 点击侧边栏到根路径 `/quickstart` | Ingress/nginx 未把根路径指到 docs |
| 发版后仍旧 UI | `index.html` 缓存；对比 Pod 与公网 asset hash |
| `?_rsc=` 请求 301 | 尽量用 `rewrite ... last` 保留 query，避免丢参数的 301 |

## 3. kubectl 最小排障命令集

```bash
# Pod 是否在跑、用的什么镜像
kubectl get pods -n zheda-agent -l app=stablepay-docs
kubectl describe pod -n zheda-agent -l app=stablepay-docs | grep -E 'Image:|State:'

# 容器内日志（Nginx access/error）
kubectl logs -n zheda-agent deployment/stablepay-docs --tail=50

# 集群内直接打服务（绕过 Ingress）
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n zheda-agent -- \
  curl -sI http://stablepay-docs.zheda-agent.svc.cluster.local/docs/

# 看容器里文件是否真是「目录 + index.html」
kubectl exec -n zheda-agent deploy/stablepay-docs -- \
  ls -la /usr/share/nginx/html/docs/ | head
kubectl exec -n zheda-agent deploy/stablepay-docs -- \
  ls -la /usr/share/nginx/html/docs/zh/

# 滚动发布是否完成
kubectl rollout status deployment/stablepay-docs -n zheda-agent
kubectl rollout undo deployment/stablepay-docs -n zheda-agent   # 回滚
```

### 3.1 kubectl 核心概念速查

对于不熟悉 Kubernetes 的使用者，以下是最常用的几个资源类型和对应操作：

- **Pod**：Kubernetes 中最小的部署单元，一个 Pod 里可以有一个或多个容器。`kubectl get pods` 查看所有 Pod 及其状态。`Running` 是正常状态，`CrashLoopBackOff` 表示容器反复崩溃重启，`ImagePullBackOff` 表示镜像拉取失败。
- **Deployment**：管理 Pod 的副本数、镜像版本和更新策略。`kubectl get deployment` 查看 Deployment 的期望副本数和当前就绪副本数。滚动更新通过修改 Deployment 的镜像版本触发，Kubernetes 会逐步替换旧的 Pod 为新的 Pod。
- **Service**：为 Pod 提供稳定的网络入口，通过标签选择器（selector）将流量转发到匹配的 Pod。`kubectl get service` 查看 Service 的 ClusterIP 和端口映射。
- **Ingress**：管理外部 HTTP/HTTPS 访问的规则，将流量按域名和路径转发到不同的 Service。`kubectl get ingress` 查看 Ingress 的规则和状态。

在上述排障命令中，`-n zheda-agent` 指定命名空间（namespace）。命名空间是 Kubernetes 中隔离资源的逻辑分区，不同命名空间的资源互相不可见。如果不指定 `-n`，kubectl 默认操作 `default` 命名空间。

## 4. 推荐部署顺序（文档站）

```bash
cd stablepayAI-documentation
./deploy.sh v1.0.x

kubectl apply -f ../infra-deployment/k8s/ack/platform/ingress.yaml   # 改过 path 时必须
kubectl rollout status deployment/stablepay-docs -n zheda-agent

# 验证
curl -sI https://ai.wenfu.cn/docs/ | head -5
curl -sI https://ai.wenfu.cn/docs/zh/ | head -5
curl -sI https://ai.wenfu.cn/docs/_next/static/chunks/xxx.js | head -3   # 任选一个 chunk
```

浏览器：**无痕**或 **Ctrl+Shift+R**，避免旧 `index.html` 干扰判断。

### 4.1 为什么修改 Ingress 后必须单独 apply

`deploy.sh` 脚本通常只负责构建镜像、推送镜像和更新 Deployment 的镜像版本。Ingress 资源与 Deployment 是独立的 Kubernetes 资源，更新 Deployment 不会自动触发 Ingress 的变更。因此，如果本次部署涉及新的 URL 路径（例如新增了 `/new-page`），或者修改了已有路径的指向，必须显式执行 `kubectl apply -f ingress.yaml`，否则 Ingress 规则保持在旧版本，新路径仍然无法正确访问。

## 5. 架构取舍（以后可升级）

| 方案 | 优点 | 缺点 |
|------|------|------|
| 同域 `/docs/`（当前） | 一个域名、品牌统一 | Ingress/nginx/构建脚本都要维护路径表 |
| 子域 `docs.ai.wenfu.cn` | Mintlify 原生根路径，几乎不用 sed | 多一条 DNS + 证书 |
| Mintlify 托管 + 反向代理 | 省离线 export | 依赖外网、非纯静态 |

### 5.1 三种方案的流量路径对比

- **同域 `/docs/` 方案**（当前）：所有请求进入同一个域名，Ingress 根据路径分流，Nginx 负责子路径的 rewrite。优点是品牌统一（所有服务共享同一个域名），SEO 受益（子路径被搜索引擎视为同一站点的不同部分）。代价是配置复杂，每新增一个文档站顶层路径都需要同时修改 Ingress 和 Nginx 规则。
- **子域方案**：文档站独立部署在 `docs.ai.wenfu.cn`，无需任何路径前缀的修改。Mintlify 构建产物可以直接使用根路径部署，省去所有 `sed` 操作和 Nginx rewrite 规则。代价是需要额外的 DNS 记录和 TLS 证书，同时跨域资源共享（CORS）和 Cookie 共享可能需要额外配置。
- **托管 + 反向代理方案**：文档站由 Mintlify 托管，自己的 Nginx 或 Ingress 将 `/docs/` 的请求反向代理到 Mintlify 的服务器。好处是免去离线导出流程，坏处是依赖外部服务可用性，且页面加载速度受外部服务响应时间影响。

## 6. 相关仓库文件索引

| 文件 | 作用 |
|------|------|
| `stablepayAI-documentation/Dockerfile` | export → unzip → prefix 脚本 → nginx |
| `stablepayAI-documentation/scripts/prefix-docs-paths.sh` | 子路径前缀（HTML/JS 分工） |
| `stablepayAI-documentation/nginx.conf` | 容器内路由、zh 重写、SPA 回退 |
| `infra-deployment/k8s/ack/platform/ingress.yaml` | ALB 路径 → Service |
| `stablepay-frontend/deploy/nginx.conf` | 主站 SPA + 缓存策略 |

### 6.1 各文件在请求链路中的角色

从请求进入集群到返回响应的全链路中，各文件的职责如下：

1. **`ingress.yaml`**：请求的第一道入口。在 ALB 层面决定请求去哪个 Service。当文件修改后，ALB Ingress Controller 需要时间同步规则到 ALB 实例。
2. **`stablepayAI-documentation/nginx.conf`**：文档站 Pod 内部的第二道路由。负责将 `/docs/` 下的请求映射到磁盘文件，处理 SPA 回退，以及对 `/zh`、`/_next` 等特殊路径进行 rewrite。
3. **`stablepayAI-documentation/Dockerfile`**：定义文档站镜像的构建过程。负责调用 Mintlify 导出、解压产物、执行路径前缀脚本、复制 Nginx 配置文件。
4. **`prefix-docs-paths.sh`**：在构建期修改 HTML 和 JS 中的路径，使 Mintlify 的绝对路径适配 `/docs/` 子路径。这个脚本在镜像构建时执行一次，产物固化在镜像中。
5. **`stablepay-frontend/deploy/nginx.conf`**：主站 Pod 内部的 Nginx 配置。处理前端 SPA 的请求，配置静态资源缓存策略。需确保 `index.html` 不被长期缓存。

## 7. 一句话总结

> **子路径静态站 = 构建产物路径 + Nginx 文件树 + Ingress 三分路由必须一致；**  
> **Mintlify/Next 的 500 常在浏览器里，不在 Nginx 状态码里；**  
> **改 minified JS 比改 nginx 危险一个数量级。**

把「请求路径 → 哪台 Service → 磁盘哪个文件」画出来，比反复改 `alias` 更有效。


## 8. Skills
### 适用场景
- Mintlify `mintlify export` 离线包 + Nginx 容器
- 同域挂载 `/docs/` 子路径
- ACK + ALB Ingress 多路径分流
- Vite/React 主站与文档站共存

### 排障决策树
```
页面问题？
├─ Nginx/Pod 日志有 404 + "Not a directory"
│  └─ 检查 export 是否 unzip；docs 必须是目录
├─ 日志 403 + "directory index ... forbidden"
│  └─ ls 该目录是否有 index.html；Mintlify 可能在子目录如 zh/index/
├─ 日志 200 但浏览器 Error 500 / Connection closed
│  └─ 禁止对 .js 做路由级 sed；检查 /_next 是否打到 frontend
├─ 点击侧边栏跳到 /quickstart（无 /docs）
│  └─ ingress.yaml + nginx 补根路径到 stablepay-docs
└─ 主站发版后仍旧版
   └─ 对比 Pod 与公网 index.html 中 /assets/ hash；index.html 需 no-cache
```
### 发版检查清单
#### 文档站 `stablepayAI-documentation`
- [ ] `Dockerfile`：`export --output ./_site.zip` → `unzip` → `test -f ./_site/index.html`
- [ ] `prefix-docs-paths.sh`：**仅 HTML** 改站内链；**JS 只改** `/_next/`、`/_mintlify/`
- [ ] `./deploy.sh <版本>` 且 `kubectl set image` 版本一致
- [ ] 若改过路径：`kubectl apply -f infra-deployment/k8s/ack/platform/ingress.yaml`
- [ ] `kubectl rollout status deployment/stablepay-docs -n zheda-agent`
- [ ] `curl -sI https://ai.wenfu.cn/docs/` → 200
- [ ] `curl -sI https://ai.wenfu.cn/docs/zh/` → 200（非 403）
- [ ] 无痕打开 `/docs/`，切换中文、点 Quickstart

#### 主站 `stablepay-frontend`
- [ ] `deploy/nginx.conf`：`index.html` no-cache，`/assets/` 长缓存
- [ ] `./deploy.sh` 后对比 Pod/公网 `grep /assets/` hash

### 禁止操作
1. **不要** `mintlify export --output ./_site` 后直接 COPY 到 `html/docs`（会得到 zip 单文件）
2. **不要** 在 `.js` 里 `sed` 替换 `"/"`、`"/zh"` 等路由字符串
3. **不要** `alias` + `try_files ... /docs/index.html` 回退（易内部重定向循环）
4. **不要** 仅靠 `curl -I /quickstart` 200 判断文档路由（可能是 frontend SPA）
5. **不要** 改 ingress 后只滚 Pod、不 `kubectl apply ingress.yaml`

### 关键命令模板
```bash
NS=zheda-agent
kubectl logs -n $NS deployment/stablepay-docs --tail=40
kubectl exec -n $NS deploy/stablepay-docs -- ls -la /usr/share/nginx/html/docs/zh/
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n $NS -- \
  curl -sI http://stablepay-docs.$NS.svc.cluster.local/docs/zh/
```

### 新增文档页时

1. `docs.json` 增加页面 → 重新 `./deploy.sh`
2. 若是**新的顶层路径**（如 `/new-page`）：
   - `ingress.yaml` 增加 `path: /new-page` → `stablepay-docs`
   - `nginx.conf` 根路径 rewrite 正则中增加 `new-page`
3. 中文首页类路径：确认磁盘上是否有 `index.html`，否则加 `location =` rewrite
