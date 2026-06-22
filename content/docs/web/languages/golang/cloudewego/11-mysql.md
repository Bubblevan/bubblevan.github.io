# 10. MySQL 与 Redis
前面几章我一直在写 Merchant Server 自己的代码：Domain、Application、Adapter、Infrastructure。那时候我更关心的是一个服务内部怎么分层，怎么让商品、支付、x402 这些业务逻辑不要混在一起。

但真实项目跑起来以后，很快会遇到另一个问题：
> 后端服务不是孤立运行的。它一定会依赖数据库、缓存、消息队列、外部网关这些基础设施。
在 StablePay 里，MySQL 和 Redis 就是两个最典型的基础设施。
- MySQL 负责保存长期业务数据，比如 DID、支付记录、查询记录、验证记录、商户商品数据。
- Redis 更适合保存短期状态，比如 nonce、幂等键、签名有效期、限流计数、临时缓存等。

> 那我问你，你能回答下面的问题吗？
```text
为什么有些东西进 MySQL，有些东西进 Redis？
为什么本地能连，到了 ACK 里就要改成 stablepay-mysql？
为什么 Pod 重启后数据不能丢？
为什么 selector 改了以后 kubectl apply 会失败？
为什么 did/query Pod 重启时不应该先改代码，而应该先查 MySQL 是否可用？
```

# 第一部分：MVP 手把手最小实现



## 10.1 先不要上云：本地最小 MySQL 是为了解决“长期数据存哪里”



假设我现在有一个最小业务愿望：



> Agent 支付完成后，我想保存一条购买记录。服务重启后，这条记录不能消失。



如果用内存 map：



```go

var purchases = map[string]Purchase{}

```



服务一重启，数据就没了。



所以我需要 MySQL。



最小的一张购买记录表可以这样想：



```sql

CREATE TABLE purchases (

    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    agent_did VARCHAR(255) NOT NULL,

    skill_did VARCHAR(255) NOT NULL,

    amount_minor BIGINT NOT NULL,

    currency VARCHAR(32) NOT NULL,

    tx_hash VARCHAR(255) NOT NULL,

    created_at DATETIME NOT NULL,

    UNIQUE KEY uk_agent_skill (agent_did, skill_did)

);

```



这里字段不是拍脑袋来的，而是被业务逼出来的：



```text

agent_did：

    谁买的。



skill_did：

    买的是哪个商品/技能。



amount_minor：

    付了多少钱，使用 minor units，避免小数精度问题。



currency：

    USDC / USDT 等币种。



tx_hash：

    链上交易证明。



created_at：

    什么时候买的。



uk_agent_skill：

    同一个 Agent 对同一个 Skill 重复购买时，需要幂等判断。

```



本地可以先用 Docker 跑一个 MySQL：



```bash

docker run --name stablepay-mysql-local \

  -e MYSQL_ROOT_PASSWORD=root123 \

  -e MYSQL_DATABASE=stablepay_payment_db \

  -e MYSQL_USER=stablepay \

  -e MYSQL_PASSWORD=stablepay123 \

  -p 3306:3306 \

  -d mysql:8.0

```



然后进入 MySQL：



```bash

docker exec -it stablepay-mysql-local mysql -uroot -proot123

```



创建业务表：



```sql

USE stablepay_payment_db;



CREATE TABLE IF NOT EXISTS purchases (

    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    agent_did VARCHAR(255) NOT NULL,

    skill_did VARCHAR(255) NOT NULL,

    amount_minor BIGINT NOT NULL,

    currency VARCHAR(32) NOT NULL,

    tx_hash VARCHAR(255) NOT NULL,

    created_at DATETIME NOT NULL,

    UNIQUE KEY uk_agent_skill (agent_did, skill_did)

);

```



插入一条测试数据：



```sql

INSERT INTO purchases (

    agent_did,

    skill_did,

    amount_minor,

    currency,

    tx_hash,

    created_at

) VALUES (

    'did:solana:agent111',

    'did:solana:seller111',

    2000000,

    'USDC',

    'fake-tx-hash',

    NOW()

);

```



查询：



```sql

SELECT * FROM purchases;

```



这就是 MySQL 的第一个 MVP：



> 它不是为了“学 SQL”，而是为了证明业务状态可以持久化。



---



## 10.2 Go 后端连接 MySQL 的最小逻辑



本地 MySQL 起起来后，Go 服务要怎么连？



最小 DSN 长这样：



```go

dsn := "stablepay:stablepay123@tcp(127.0.0.1:3306)/stablepay_payment_db?charset=utf8mb4&parseTime=True&loc=Local"

```



这里每一段都有意义：



```text

stablepay:stablepay123

    用户名和密码。



tcp(127.0.0.1:3306)

    本地 MySQL 地址。



stablepay_payment_db

    连接哪个数据库。



charset=utf8mb4

    支持完整 Unicode，包括 emoji。



parseTime=True

    把 MySQL DATETIME 转成 Go 的 time.Time。



loc=Local

    时间按本地时区解析。

```



最小连接代码：



```go

db, err := sql.Open("mysql", dsn)

if err != nil {

    return err

}



ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)

defer cancel()



if err := db.PingContext(ctx); err != nil {

    return err

}

```



这里最重要的不是代码，而是理解：



```text

sql.Open 不一定真的建立连接；

PingContext 才能验证数据库能不能连上；

上线时健康检查最好不要只看服务进程活着，也要看数据库依赖是否可用。

```



这也解释了为什么我们之前写 `/healthz` 时要留一个 `dbReady` 函数。



---



## 10.3 本地最小 Redis 是为了解决“短期状态放哪里”



现在再看 Redis。



假设我有另一个业务愿望：



> Agent 发起支付请求时，我要校验签名 nonce，防止重放攻击。这个 nonce 只需要保存 5 分钟。



如果把 nonce 存 MySQL，可以，但不划算。



因为 nonce 的特点是：



```text

生命周期短；

读写频繁；

过期后自动消失；

不需要复杂 SQL 查询；

通常只关心 key 是否存在。

```



这时 Redis 更合适。



本地跑 Redis：



```bash

docker run --name stablepay-redis-local \

  -p 6379:6379 \

  -d redis:7-alpine redis-server --appendonly yes

```



进入 Redis：



```bash

docker exec -it stablepay-redis-local redis-cli

```



最小操作：



```bash

SET nonce:did:solana:agent111:abc123 1 EX 300

GET nonce:did:solana:agent111:abc123

TTL nonce:did:solana:agent111:abc123

```



这里 `EX 300` 表示 300 秒后自动过期。



这就是 Redis 的第一个 MVP：



> 它不是为了替代 MySQL，而是为了保存短生命周期、高频访问、不值得落长期库的数据。



---



## 10.4 Go 后端连接 Redis 的最小逻辑



用 Go 连接 Redis 时，配置通常是：



```yaml

redis:

  host: stablepay-redis

  port: 6379

  password: ""

  db: 0

  pool_size: 100

  min_idle_conns: 10

```



本地时 host 可以是：



```text

127.0.0.1

```



ACK 内部时 host 应该是：



```text

stablepay-redis

```



这背后是 Kubernetes Service 的作用：Pod 不直接记另一个 Pod 的 IP，而是访问 Service 名称。



伪代码可以这样理解：



```go

rdb := redis.NewClient(&redis.Options{

    Addr: "127.0.0.1:6379",

    DB:   0,

})



ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)

defer cancel()



if err := rdb.Ping(ctx).Err(); err != nil {

    return err

}

```



然后业务里可以做：



```go

key := "nonce:" + agentDID + ":" + nonce

ok, err := rdb.SetNX(ctx, key, "1", 5*time.Minute).Result()

if err != nil {

    return err

}

if !ok {

    return errors.New("nonce already used")

}

```



这里 `SetNX` 的含义是：



```text

如果 key 不存在，就设置成功；

如果 key 已经存在，说明 nonce 被用过，拒绝。

```



这比先 `GET` 再 `SET` 更安全，因为它是原子操作。



---



## 10.5 StablePay 里 MySQL 和 Redis 的本地分工



可以先建立一个简单分工：



```text

MySQL：

    长期保存业务事实。



Redis：

    保存短期状态、缓存、限流、幂等、nonce。

```



在 StablePay 里可以这样对应：



```text

MySQL 适合：

    DID 记录

    支付交易记录

    购买证明

    商品数据

    查询记录

    验证记录



Redis 适合：

    签名 nonce

    幂等键

    支付轮询临时状态

    限流计数

    短期验证码/挑战码

    热点查询缓存

```



最重要的是不要混用：



```text

不能因为 Redis 快，就把必须长期保存的交易记录只放 Redis。

不能因为 MySQL 可靠，就把每分钟高频变化的限流计数都塞 MySQL。

```



面试时可以这样说：



```text

MySQL 保存业务事实，Redis 保存短期状态。

支付成功这种事实必须进 MySQL；

nonce、idempotency key、rate limit 这种短期状态更适合 Redis。

```



---



# 第二部分：八股概念基础知识点



## 10.6 MySQL 是什么？



MySQL 是关系型数据库。



它最适合保存结构化、长期存在、需要事务一致性的业务数据。



关系型数据库的关键词是：



```text

表

行

列

主键

外键

索引

事务

SQL

```



比如支付记录就是典型关系型数据：



```text

一条支付记录有固定字段：

agent_did、skill_did、amount、currency、tx_hash、created_at。

```



这种数据天然适合表结构。



---



## 10.7 Redis 是什么？



Redis 是内存型 key-value 数据库。



它最适合：



```text

快读快写；

短期缓存；

自动过期；

计数器；

分布式锁；

排行榜；

队列辅助结构。

```



Redis 的关键词是：



```text

key-value

TTL

内存

数据结构

原子操作

缓存

持久化

```



Redis 虽然也可以持久化，但它的定位不是替代 MySQL。



在后端面试里，一个经典回答是：



```text

MySQL 是主存储，Redis 是缓存/短期状态。

MySQL 负责正确性，Redis 负责性能和临时状态。

```



这句话不是绝对真理，但对大多数业务系统是一个很好的起点。



---



## 10.8 关系型数据库为什么需要索引？



没有索引时，数据库查一条记录可能需要扫全表。



比如：



```sql

SELECT * FROM purchases WHERE agent_did = ? AND skill_did = ?;

```



如果 purchases 表有几百万行，没有索引就会很慢。



所以需要：



```sql

CREATE UNIQUE INDEX uk_agent_skill ON purchases(agent_did, skill_did);

```



这个索引的意义有两个：



```text

第一，加速查询。

第二，保证同一个 Agent 对同一个 Skill 只有一条购买记录。

```



这就是索引的两种常见作用：



```text

性能优化；

业务约束。

```



不要为了“听起来专业”乱加索引。



索引也有代价：



```text

占用存储空间；

写入时需要维护索引；

索引太多会降低写性能；

错误索引可能完全用不上。

```



所以索引应该从查询路径出发。



---



## 10.9 什么是事务？



事务就是把多步数据库操作当成一个整体。



经典 ACID：



```text

A：Atomicity，原子性，要么全成功，要么全失败。

C：Consistency，一致性，事务前后数据满足约束。

I：Isolation，隔离性，并发事务互不乱影响。

D：Durability，持久性，提交后数据不应该丢。

```



比如支付成功后可能要做：



```text

插入 payment_transactions

插入 purchase_records

更新订单状态

写 verification proof

```



这些操作如果只成功一半，就会出问题。



所以应该放进事务：



```go

tx, err := db.BeginTx(ctx, nil)

if err != nil {

    return err

}



defer tx.Rollback()



// insert transaction

// insert proof

// update status



if err := tx.Commit(); err != nil {

    return err

}

```



事务不是每个地方都要用。

但涉及多个表、多步状态变更、支付资金相关操作时，事务是必须认真考虑的。



---



## 10.10 什么是连接池？



后端服务每次查数据库都新建 TCP 连接会很慢。



所以数据库客户端通常会维护连接池：



```text

max_open_conns：

    最多同时打开多少连接。



max_idle_conns：

    空闲连接保留多少。



conn_max_lifetime：

    连接最多活多久后重建。

```



你们的配置里就有类似：



```yaml

max_open_conns: 100

max_idle_conns: 10

conn_max_lifetime: 3600s

```



理解这个配置很重要。



如果连接池太小：



```text

请求一多，服务会排队等连接。

```



如果连接池太大：



```text

MySQL 会被大量连接压垮。

```



所以连接池不是越大越好。



在 K8s 里尤其要注意：



```text

每个 Pod 都有自己的连接池。

如果一个服务 5 个副本，每个 max_open_conns = 100，

那理论上这个服务最多可能占 500 个 MySQL 连接。

```



这也是为什么扩容 Pod 时要一起考虑数据库承载能力。



---



## 10.11 Redis 为什么快？



Redis 快主要因为：



```text

主要在内存中操作；

单线程事件循环避免大量锁竞争；

数据结构简单高效；

网络协议轻量。

```



但“Redis 快”不等于“Redis 不会出问题”。



Redis 常见问题包括：



```text

大 key；

热 key；

缓存穿透；

缓存击穿；

缓存雪崩；

内存淘汰策略不合理；

持久化配置不合适；

连接数过高。

```



在 StablePay 这种支付系统里，Redis 更应该保守使用：



```text

可以用来做 nonce、幂等、限流；

不要把唯一的支付事实只存在 Redis；

不要把 Redis 当账本。

```



---



## 10.12 Redis 的 AOF 是什么？



你们 ACK Redis 启动参数里有：



```bash

redis-server --appendonly yes

```



这表示开启 AOF。



AOF 可以理解为：



```text

Redis 把写操作追加记录到文件里。

重启时根据这个文件恢复数据。

```



这比完全无持久化更安全。



但也要明白：



```text

Redis 即使开了 AOF，也不应该替代 MySQL 做支付账本。

```



AOF 适合增强 Redis 临时状态的恢复能力。

真正长期、强一致、可审计的支付记录还是应该放 MySQL。



---



## 10.13 Kubernetes 里为什么要用 Service 名称访问 MySQL/Redis？



本地连接 MySQL 用：



```text

127.0.0.1:3306

```



但在 ACK 里，业务 Pod 和 MySQL Pod 不是同一个容器。



如果 payment-service 想连 MySQL，它不能写：



```text

127.0.0.1:3306

```



因为那会连到 payment-service 自己这个 Pod 的 localhost。



它应该写：



```text

stablepay-mysql:3306

```



这是 Kubernetes Service 名称。



Service 的作用是给一组 Pod 一个稳定入口。

Pod IP 会变，但 Service 名称不应该随便变。



Redis 同理：



```text

stablepay-redis:6379

```



这解释了你们配置里为什么是：



```yaml

mysql:

  host: stablepay-mysql



redis:

  host: stablepay-redis

```



不是公网 IP，也不是 localhost。



---



## 10.14 Deployment、Pod、Service、PVC 分别是什么？



以 MySQL 为例：



```text

Deployment：

    告诉 Kubernetes 我要跑一个 MySQL 工作负载。



Pod：

    真正运行 MySQL 容器的最小单位。



Service：

    给 MySQL Pod 一个稳定访问入口 stablepay-mysql:3306。



PVC：

    给 MySQL 的 /var/lib/mysql 提供持久化磁盘。

```



四者关系是：



```text

Deployment 创建 Pod

Pod 运行 mysql 容器

PVC 挂载到 Pod 的 /var/lib/mysql

Service 负责让其他 Pod 找到 MySQL

```



Redis 也是类似：



```text

Deployment 创建 Redis Pod

PVC 挂载到 /data

Service 暴露 stablepay-redis:6379

```



这就是“基础设施作为 Pod 跑在 ACK 里”的最小理解。



---



# 第三部分：ACK 上云排障过程实践



## 10.15 ACK 里 MySQL / Redis 的部署结构



你们当前 ACK infra 里 MySQL 大致是：



```text

Secret：

    stablepay-secrets 保存 MySQL 用户名、密码等敏感信息



PVC：

    mysql-data，20Gi，alicloud-disk-essd



Deployment：

    stablepay-mysql

    image: stablepay-registry.../mysql:8.0

    mountPath: /var/lib/mysql



Service：

    stablepay-mysql:3306



Job：

    stablepay-mysql-init

    等 MySQL ready 后创建多个业务库并授权

```



Redis 大致是：



```text

PVC：

    redis-data，20Gi，alicloud-disk-essd



Deployment：

    stablepay-redis

    image: stablepay-registry.../redis:7-alpine

    args: redis-server --appendonly yes

    mountPath: /data



Service：

    stablepay-redis:6379

```



这里要建立一个最重要的常识：



> Deployment 负责运行进程，Service 负责稳定访问，PVC 负责数据不随 Pod 消失，Secret/ConfigMap 负责配置注入。



排障时不要混在一起看，要一层一层看。



---



## 10.16 第一个排障链路：Pod 起不来，先看状态



先看所有基础设施：



```bash

kubectl -n zheda-agent get pod

kubectl -n zheda-agent get deploy

kubectl -n zheda-agent get svc

kubectl -n zheda-agent get pvc

```



如果只看 MySQL：



```bash

kubectl -n zheda-agent get pod -l app=stablepay-mysql

kubectl -n zheda-agent get deploy stablepay-mysql

kubectl -n zheda-agent get svc stablepay-mysql

kubectl -n zheda-agent get pvc mysql-data

```



如果只看 Redis：



```bash

kubectl -n zheda-agent get pod -l app=stablepay-redis

kubectl -n zheda-agent get deploy stablepay-redis

kubectl -n zheda-agent get svc stablepay-redis

kubectl -n zheda-agent get pvc redis-data

```



先不要急着改 YAML。

先判断是哪一层有问题：



```text

Pod Pending：

    多半是调度、资源、PVC 绑定、镜像拉取问题。



Pod ImagePullBackOff：

    多半是镜像地址、ACR Secret、镜像 tag 问题。



Pod CrashLoopBackOff：

    镜像已经拉下来并启动了，但进程自己崩了。看 logs。



Service 存在但连不上：

    看 selector 是否匹配 Pod label。



PVC Pending：

    看 StorageClass、磁盘配额、可用区。

```



---



## 10.17 第二个排障链路：镜像拉不下来



你们 README 里已经明确提到一个现实问题：



```text

ACK 节点常无法稳定访问 docker.io。

```



所以基础设施镜像最好同步到 ACR。



如果 MySQL/Redis 卡在：



```text

ImagePullBackOff

ErrImagePull

```



先看事件：



```bash

kubectl -n zheda-agent describe pod <mysql-pod-name>

kubectl -n zheda-agent describe pod <redis-pod-name>

```



重点看：



```text

Failed to pull image

pull access denied

unauthorized

i/o timeout

no basic auth credentials

```



如果是 Docker Hub 网络问题，就把镜像推到 ACR。



Redis 示例：



```bash

docker pull redis:7-alpine

docker tag redis:7-alpine stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/redis:7-alpine

docker push stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/redis:7-alpine

```



然后 YAML 里使用：



```yaml

image: stablepay-registry.cn-shanghai.cr.aliyuncs.com/stablepay-dev/redis:7-alpine

imagePullSecrets:

  - name: acr-secret

```



这里有一个很容易混的点：



```text

stablepay-dev 是 ACR 仓库命名空间；

zheda-agent 是 Kubernetes namespace；

acr-secret 是 Kubernetes 里拉镜像用的 Secret。

```



它们不是一个东西。



---



## 10.18 第三个排障链路：Service selector 不匹配



你们之前遇到过旧 selector 的问题，比如旧 Deployment 可能还是：



```yaml

selector:

  matchLabels:

    app: mysql

```



但新 YAML 是：



```yaml

selector:

  matchLabels:

    app: stablepay-mysql

```



Kubernetes 的 Deployment selector 很多情况下是不可变字段。

这意味着你不能随便 `kubectl apply` 改 selector。



如果旧资源还在，就可能出现：



```text

apply 失败；

Service 选不到 Pod；

Service 还指向旧 label；

Pod label 和 Service selector 对不上。

```



排查命令：



```bash

kubectl -n zheda-agent get deploy stablepay-mysql -o yaml | grep -A5 selector

kubectl -n zheda-agent get svc stablepay-mysql -o yaml | grep -A5 selector

kubectl -n zheda-agent get pod --show-labels | grep mysql

```



如果确认是旧 selector 冲突，可以删除旧工作负载和 Service：



```bash

kubectl -n zheda-agent delete deployment stablepay-mysql stablepay-redis --ignore-not-found

kubectl -n zheda-agent delete svc stablepay-mysql stablepay-redis --ignore-not-found

kubectl apply -f k8s/ack/infra/all.yaml

```



注意：



```bash

kubectl -n zheda-agent delete pvc mysql-data redis-data

```



这条要非常谨慎。



删除 PVC 可能意味着删除数据盘，数据会丢。



所以排障时要先删 Deployment / Service，不要上来就删 PVC。



---



## 10.19 第四个排障链路：MySQL Pod Running，但业务 Pod 还是连不上



这种情况非常常见。



第一步，看 Service 是否存在：



```bash

kubectl -n zheda-agent get svc stablepay-mysql

```



应该看到：



```text

stablepay-mysql   ClusterIP   ...   3306/TCP

```



第二步，从业务 Pod 里测试 DNS：



```bash

kubectl -n zheda-agent exec -it deploy/stablepay-payment-service -- sh

```



进入后：



```bash

getent hosts stablepay-mysql

```



如果镜像里没有 `getent`，可以试：



```bash

nslookup stablepay-mysql

```



第三步，测试 TCP 端口：



```bash

nc -vz stablepay-mysql 3306

```



如果业务镜像没有 nc，可以临时起一个调试 Pod：



```bash

kubectl -n zheda-agent run netshoot --rm -it \

  --image=nicolaka/netshoot -- /bin/bash

```



然后在里面测：



```bash

nslookup stablepay-mysql

nc -vz stablepay-mysql 3306

```



这里要区分：



```text

DNS 解析失败：

    Service 名字、namespace、CoreDNS 可能有问题。



DNS 成功但端口不通：

    Service selector、Pod 端口、容器状态可能有问题。



端口通但应用报认证失败：

    用户名、密码、数据库名、权限可能有问题。



认证成功但提示 Unknown database：

    init Job 可能没跑成功，数据库没创建。

```



---



## 10.20 第五个排障链路：MySQL init Job 没成功



你们 infra 里有一个 `stablepay-mysql-init` Job，它做的事情是：



```text

等待 stablepay-mysql 可用；

创建 stablepay_did_db；

创建 stablepay_payment_db；

创建 stablepay_query_db；

创建 stablepay_verification_db；

创建 stablepay_merchant_db；

创建 stablepay 用户并授权。

```



如果 did-service 或 query-service 一直重启，并且日志里出现：



```text

Unknown database

Access denied

connect refused

no such host

```



就要看 init Job。



命令：



```bash

kubectl -n zheda-agent get job stablepay-mysql-init

kubectl -n zheda-agent get pod | grep mysql-init

kubectl -n zheda-agent logs job/stablepay-mysql-init

```



如果 Job 失败，继续 describe：



```bash

kubectl -n zheda-agent describe job stablepay-mysql-init

kubectl -n zheda-agent describe pod <mysql-init-pod-name>

```



这里要分清楚：



```text

init Job 等不到 MySQL：

    可能 MySQL Pod 没 ready，或者 Service 不通。



init Job 能连 MySQL，但 SQL 执行失败：

    可能 root 密码不对，或者权限/语法问题。



init Job 成功，但业务仍然报 Unknown database：

    可能业务配置连的是另一个库名，或者连接到了旧 MySQL/PVC。

```



验证库是否真的创建：



```bash

kubectl -n zheda-agent exec -it deploy/stablepay-mysql -- \

  mysql -uroot -p



SHOW DATABASES;

SELECT user, host FROM mysql.user;

SHOW GRANTS FOR 'stablepay'@'%';

```



---



## 10.21 第六个排障链路：Redis Pod Running，但业务连不上



Redis 排障类似 MySQL，但更简单。



先看 Service：



```bash

kubectl -n zheda-agent get svc stablepay-redis

```



从业务 Pod 测 DNS：



```bash

kubectl -n zheda-agent exec -it deploy/stablepay-payment-service -- sh

nslookup stablepay-redis

```



测端口：



```bash

nc -vz stablepay-redis 6379

```



如果能进入 Redis Pod：



```bash

kubectl -n zheda-agent exec -it deploy/stablepay-redis -- redis-cli ping

```



预期：



```text

PONG

```



再测写入：



```bash

kubectl -n zheda-agent exec -it deploy/stablepay-redis -- \

  redis-cli SET stablepay:test ok EX 60



kubectl -n zheda-agent exec -it deploy/stablepay-redis -- \

  redis-cli GET stablepay:test

```



如果业务报 Redis 连接失败，常见原因：



```text

host 写成 localhost；

Service 名称写错；

namespace 不一致；

Redis Pod 没 ready；

Service selector 不匹配；

网络策略阻断；

密码配置不一致。

```



---



## 10.22 第七个排障链路：PVC 问题



MySQL 和 Redis 都挂了 PVC：



```text

mysql-data -> /var/lib/mysql

redis-data -> /data

```



如果 Pod 一直 Pending，要看 PVC：



```bash

kubectl -n zheda-agent get pvc

kubectl -n zheda-agent describe pvc mysql-data

kubectl -n zheda-agent describe pvc redis-data

```



常见问题：



```text

PVC Pending：

    StorageClass 不存在；

    云盘配额不足；

    可用区不匹配；

    ACK 没有权限创建云盘。



Pod 挂载失败：

    PVC 已绑定到别的节点；

    云盘 attach 失败；

    节点状态异常。



数据异常：

    旧 PVC 里有旧 MySQL 数据目录；

    MySQL 版本或初始化参数变化；

    root 密码改了但旧数据目录里用户密码没变。

```



这里有一个很关键的坑：



> MySQL 第一次初始化时会根据环境变量创建用户和库；但如果 `/var/lib/mysql` 已经有旧数据，环境变量不会重新初始化数据库。



也就是说，如果你改了：



```yaml

MYSQL_ROOT_PASSWORD

MYSQL_DATABASE

MYSQL_USER

MYSQL_PASSWORD

```



但 PVC 里已经有旧数据，MySQL 不会自动按新环境变量重建用户。



这时不要马上删 PVC。

先确认是否可以通过 SQL 修改用户和授权。

只有确认数据可以丢，才考虑删除 PVC 重建。



---



## 10.23 第八个排障链路：业务 Pod 反复重启



README 里已经提醒过：did/query Pod 反复重启时，先查日志，常见原因是连不上 MySQL、库未初始化、配置监听地址等。



命令：



```bash

kubectl -n zheda-agent logs deploy/stablepay-did-service --tail=100

kubectl -n zheda-agent logs deploy/stablepay-query-service --tail=100

```



如果还在重启，想看上一次崩溃日志：



```bash

kubectl -n zheda-agent logs deploy/stablepay-did-service --previous --tail=100

```



然后按错误分类：



```text

no such host stablepay-mysql：

    Service 名称或 DNS 问题。



connect: connection refused：

    MySQL Pod 还没 ready，或者 Service 没指到正确 Pod。



Access denied for user：

    Secret、用户名、密码、授权问题。



Unknown database：

    init Job 没成功，或者库名配置错。



too many connections：

    连接池太大，Pod 副本太多，MySQL 承载不了。



context deadline exceeded：

    网络、DNS、数据库负载、连接池等待都有可能。

```



不要看到 CrashLoopBackOff 就先重启。



正确顺序是：



```text

看 logs

看 describe pod

看依赖 Pod

看 Service

看 PVC

看 Job

再决定改配置还是重建资源

```



---



## 10.24 第九个排障链路：Ingress 不是 MySQL/Redis 的入口



你们的 Ingress 里配置的是 HTTP 路由，比如：



```text

/api -> stablepay-api-gateway

/pay -> stablepay-api-gateway

/verify -> stablepay-api-gateway

/merchant -> stablepay-merchant-backend

/ -> stablepay-frontend

```



这说明 Ingress 负责的是外部 HTTP 流量。



MySQL 和 Redis 不应该通过 Ingress 暴露给公网。



业务 Pod 访问它们应该走集群内 Service：



```text

stablepay-mysql:3306

stablepay-redis:6379

```



这点很重要。



如果你在浏览器里访问不了 MySQL/Redis，不代表它们坏了。

它们本来就不是给浏览器访问的。



面试可以这样讲：



```text

Ingress 管 HTTP 入口；

Service 管集群内服务发现；

MySQL/Redis 这种基础设施只应该暴露 ClusterIP 给内部服务访问，不应该走公网 Ingress。

```



---



## 10.25 本章最终形成的 StablePay 依赖图



可以把当前 ACK 里的基础设施关系画成：



```text

payment-service

  ├── MySQL: stablepay-mysql:3306 / stablepay_payment_db

  ├── Redis: stablepay-redis:6379 / db 0

  ├── RocketMQ: stablepay-rocketmq-nameserver:9876

  ├── did-service: stablepay-did-service:8081

  └── blockchain-adapter: stablepay-blockchain-adapter:8083



did-service

  └── MySQL: stablepay-mysql:3306 / stablepay_did_db



query-service

  └── MySQL: stablepay-mysql:3306 / stablepay_query_db



verification-service

  └── MySQL: stablepay-mysql:3306 / stablepay_verification_db



merchant-backend

  └── MySQL: stablepay-mysql:3306 / stablepay_merchant_db

```



这张图的重点是：



```text

业务服务不直接找 Pod IP。

业务服务找 Service 名称。



数据库不是一个“代码里的变量”。

它在 ACK 里是 Deployment + PVC + Service + Secret + Init Job 的组合。

```



---



## 10.26 面试讲法



如果面试官问：“你们 MySQL 和 Redis 怎么用？”



可以这样回答：



```text

我们把 MySQL 和 Redis 都作为 ACK 内部基础设施来部署。

MySQL 通过 stablepay-mysql Service 暴露 3306，挂载 PVC 到 /var/lib/mysql 保存长期数据；

Redis 通过 stablepay-redis Service 暴露 6379，开启 appendonly yes，并挂载 PVC 到 /data。

业务服务通过 ConfigMap 配置 stablepay-mysql、stablepay-redis 这样的集群内 DNS 名称，而不是写 Pod IP。

```



如果问：“为什么 Redis 不能替代 MySQL？”



可以回答：



```text

MySQL 保存支付记录、DID、proof、商品这些长期业务事实，需要事务、索引和可审计性。

Redis 更适合 nonce、幂等键、限流计数、短期缓存这种临时状态。

即使 Redis 开了 AOF，也不应该把它当支付账本。

```



如果问：“ACK 上 MySQL/Redis 排障怎么做？”



可以回答：



```text

我会先按资源层次排查：

先 get pod/deploy/svc/pvc 看状态；

如果 ImagePullBackOff，看 ACR 镜像和 imagePullSecrets；

如果 Pending，看 PVC 和 StorageClass；

如果 Running 但业务连不上，从业务 Pod 内 nslookup stablepay-mysql / stablepay-redis，再测端口；

如果库不存在或权限错误，看 mysql-init Job 日志；

如果 CrashLoopBackOff，看业务 Pod logs --previous。

```



如果问：“为什么要有 DB init Job？”



可以回答：



```text

因为 MySQL Pod 只负责启动数据库进程，不一定负责创建所有业务库和授权。

我们用一个 Job 等 MySQL ready 后创建 did/payment/query/verification/merchant 等数据库，并给 stablepay 用户授权。

这样 infra 发布后，各业务服务可以直接连接自己的库。

```



---



## 10.27 本章小结



这一章最重要的不是会背 MySQL 和 Redis，而是建立判断链：



```text

长期业务事实

  ↓

MySQL



短期状态、高频计数、自动过期

  ↓

Redis



本地开发

  ↓

localhost + docker run



ACK 内部访问

  ↓

stablepay-mysql / stablepay-redis Service DNS



数据不能随 Pod 消失

  ↓

PVC 挂载 /var/lib/mysql 和 /data



数据库第一次启动需要建库授权

  ↓

mysql-init Job



业务 Pod 重启

  ↓

先查日志，再查 MySQL/Redis/Service/PVC/Job



镜像拉不下来

  ↓

同步 Docker Hub 镜像到 ACR，使用 imagePullSecrets

```



MySQL 和 Redis 不是“两个中间件名词”。

在真实后端项目里，它们是一整套工程能力：



```text

本地开发能力；

业务建模能力；

缓存与幂等能力；

连接池管理能力；

ACK 部署能力；

PVC 持久化能力；

Service 发现能力；

日志排障能力。

```



把这些串起来，才算真正理解了 MySQL 和 Redis 在 StablePay 里的位置。


## 11.7 SQLite + PVC 到 MySQL：不是“哪个高级”，而是不同阶段的取舍



我最早想过用 SQLite。



这很自然。merchant-backend 最开始只是一个商家后端 MVP，商品数据量小，SQLite 不需要额外部署数据库，写起来快。



如果用 SQLite，部署时就会面对：



```text

SQLite 数据是一个文件；

容器重建会丢文件；

所以要用 PVC 把 /app/data 挂到云盘。

```



这时 merchant-backend 自己需要 PVC。



但后面我切到了 MySQL，原因也很自然：



```text

ACK 里已经有 stablepay-mysql；

其他服务也在用 MySQL；

merchant-backend 未来可能需要更多商品、订单、购买记录；

MySQL 更适合多连接、备份、权限管理和长期运维。

```



切到 MySQL 后，merchant-backend 自己就不再需要 SQLite PVC。



它只需要通过 Service 访问现有 MySQL：



```text

stablepay-mysql:3306

```



而商品数据存在：



```text

stablepay_merchant_db.products

```



所以这次看到的 MySQL/Redis PVC，不是 merchant SQLite 的残留，而是线上基础设施的数据盘。



两种阶段可以这样总结：



```text

MVP 本地阶段：

  SQLite + 本地文件

  优点：简单，无需部署数据库

  缺点：不适合多副本和生产运维



MVP 上云过渡阶段：

  SQLite + PVC

  优点：Pod 重建数据不丢

  缺点：单副本、备份麻烦、并发弱



ACK 生产阶段：

  MySQL

  优点：已有基础设施、可备份、可扩展、服务之间统一

  缺点：需要建库、授权、维护连接配置

```

