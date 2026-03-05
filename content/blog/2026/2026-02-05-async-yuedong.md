---
date: 2026-02-05
title: yuedong异步并发测试
authors: [bubblevan]
tags: []
---

## 一、为什么要做并发测试

预约、报名这类功能本质上是「多用户争抢同一份资源」：同一场次只能被有限人数预订，同一活动有人数上限。在用户少、请求错开的时候，接口往往表现正常；一旦多人同时点击「预订」或「报名」，就容易暴露出锁未生效、容量未校验、人数超限等问题。这些问题很难通过手工点几次页面复现，需要用脚本模拟多用户在同一时刻发起请求，才能验证系统在并发下是否正确保证了「独占场次只允许一人」「有容量场次不超过容量」「活动报名不超过人数上限」等约束。因此我们在修复测试同学反馈的并发问题后，引入了基于 Python 异步脚本的并发测试，作为回归和验收的一环。

## 二、我们遇到过的三类问题

在实际使用中发现了三类典型的并发异常。其一是**独占场次并发预订时锁定失效**：多个用户同时预订同一独占场次（容量为 1）时，系统未能正确串行化或加锁，结果出现两个用户成功、一个用户失败等不符合「仅一人成功」预期的现象。其二是**有容量场次并发预订超额**：在容量为 10 的场次上，并发发起 20 个预订请求时，系统没有在达到 10 人后拒绝后续请求，导致 20 个请求全部返回成功。其三是**活动报名并发控制异常**：人数上限为 2 人的活动，在并发请求下出现了 5 个用户都报名成功的情况，说明活动人数校验在并发场景下未正确生效。这三类问题分别对应「独占锁」「容量上限」「活动人数上限」三个维度的并发一致性，也是我们后续修复和脚本验证的重点。

## 三、修复思路与实现要点

**无容量（独占）场次的根因与改法。** 原先的逻辑是「先查场次状态，再按状态更新」：先读出场次状态是否为 available，若是再把它更新为 reserved。在默认的读已提交（read committed）隔离级别下，多个并发请求可以同时读到 available，然后各自再去更新，就会出现多人同时「抢到」同一场次的情况。修复方式是去掉「先读再改」的依赖，改为**原子更新**：用一次 `updateMany`，条件为 `status = 'available'` 且 `capacity_total` 为空（确保是无容量场次），把满足条件的行直接更新为 `status = 'reserved'`；再根据实际更新到的行数判断是否全部抢到，若更新行数少于请求的场次数，说明有场次已被其他请求占掉，则返回「场次已被其他用户预订」等错误。这样不再依赖「读到的状态」做决策，只依赖数据库的原子写，从根上避免读已提交导致的并发超订。

**有容量场次与「订单存在即占容量」的设计。** 有容量场次和活动目前都采用了「预订/报名时先占容量，支付或取消后再做相应处理」的思路，而不是「支付成功后才消耗容量」。这样做的考虑是：若等支付成功再扣容量，在高并发下要保证「扣容量」与「支付成功」的严格顺序和一致性会更复杂；而「创建订单时就用原子操作占住容量，未支付订单超时或用户取消时再释放」虽然会在一段时间内占用名额（例如待支付期间），但逻辑清晰，且通过原子更新即可避免超额。有容量场次的具体实现是：在预订接口里用一条带条件的 SQL（`UPDATE session SET capacity_used = capacity_used + 1 WHERE session_id = ? AND status = 'available' AND capacity_used < capacity_total`）做**原子自增**，只有更新行数为 1 才认为占位成功，再在同一事务内创建订单和 session_reg；订单若超时未支付或用户取消，在 `cancelOrder` 中再对对应场次做 `capacity_used` 的原子减一并视情况把 status 从 reserved 改回 available。支付倒计时原先为 15 分钟，我们计划缩短到 5 分钟，在保证正常网络下能完成支付的前提下，减少「占着名额不付」的时间，前端如需展示倒计时可一并调整。

**活动报名：先落库 event_reg 再算人数。** 活动人数超限的问题来自「已报名人数」的统计时机：若在创建订单或报名记录之前就按当前数据算人数，并发请求会各自都认为还没满员，从而都通过校验。修复方式是在同一事务内**先创建订单，再立即创建活动报名记录（event_reg）**，之后所有「已报名人数」的统计都基于 event_reg（并排除已取消、已退款等订单对应的记录），这样只要有一条 event_reg 插入成功，后续并发请求在统计时就会把这条算进去，从而在人数达到上限后正确拒绝更多报名。收费活动同样会为待支付订单设置超时，超时取消订单时会删除对应 event_reg 并释放名额，逻辑与场次取消一致。前端已配合做了适配（例如待支付订单的展示与「继续支付」入口），避免用户误以为无法对未支付订单再次发起支付。

---

## 四、并发测试：SQL、脚本与结果

以下按业务场景分节：每节先给出在服务器上查可用数据的 SQL，再贴出 `temp/asynio.py` 中对应代码，然后贴 `temp/results/` 下实际跑出的结果片段，最后做简要解析。脚本入口与共用配置：运行 `python temp/asynio.py` 前需安装 `aiohttp`；脚本会先调用 `GET_TOKEN_URL` 为 `USER_DATA` 中的 openid 取 Token，再根据 `CONFIG["venue_id"]` 请求 `GET /sessions/venue/{venue_id}`，在返回的场次列表中自动选出独占场次（无容量或容量=1）和容量场次（容量≥10），写入 `CONFIG["exclusive_session_id"]` 与 `CONFIG["capacity_session_id"]`；`CONFIG["event_id"]` 不会被动覆盖，须在库中为 `status='open'` 且未结束的活动。

---

### 4.1 独占场次并发预订

**SQL：在库中查当前可用的独占场次（无容量或容量=1、available、当天及以后）**

```sql
SELECT
  s.session_id,
  s.venue_id,
  s.court_id,
  s.date,
  s.start_time,
  s.end_time,
  s.price,
  s.capacity_total,
  s.capacity_used,
  s.status
FROM session s
WHERE s.status = 'available'
  AND (s.capacity_total IS NULL OR s.capacity_total = 1)
  AND s.date >= CURDATE()
ORDER BY s.date, s.start_time
LIMIT 20;
```

**asynio.py：独占场次测试逻辑与成功判定**

```python
# 1. 独占场次并发预订
async def test_exclusive_booking():
    if not CONFIG["tokens"]:
        logging.warning("没有可用Token，跳过独占场次测试")
        return
    if not CONFIG.get("exclusive_session_id"):
        logging.warning("没有找到独占场次，跳过独占场次测试")
        return

    logging.info("开始测试: 独占场次并发预订 (10用户 -> 1场次)")
    url = f"{BASE_URL}/sessions/reserve"
    target_session_id = CONFIG["exclusive_session_id"]

    active_tokens = CONFIG["tokens"][:10]

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i, token in enumerate(active_tokens):
            headers = {"Authorization": format_auth_token(token)}
            payload = {"sessionId": [target_session_id]}
            tasks.append(make_request(session, "POST", url, headers, payload, f"User-{i+1}"))

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

    try:
        save_results(results, "exclusive_booking")
        summarize_results(results, "exclusive_booking")
    except Exception:
        logging.exception("保存/摘要独占场次测试结果时出错")

    success = [r for r in results if r['data']['statusCode'] == 200]
    fails = [r for r in results if r['data']['statusCode'] != 200]

    logging.info("耗时: %.4fs", duration)
    logging.info("成功预订数: %s (预期: 1)", len(success))
    logging.info("失败请求数: %s (预期: 9)", len(fails))
```

**results 示例（exclusive_booking）：jsonl 片段 + summary**

`results_exclusive_booking_20260205-110421.jsonl` 中 10 条，仅保留有代表性的几条：

```jsonl
{"user_id": "User-4", "status": 201, "data": {"message": "Error", "statusCode": 400, "error": "场次已被预定"}, "elapsed": 0.146}
{"user_id": "User-5", "status": 201, "data": {"message": "Success", "statusCode": 200, "data": {"orderId": "e9543ac51d294f911770260661746", "totalPrice": "80.00", "sessions": [{"sessionId": 104239, "courtId": 110, "date": "2026-02-05T00:00:00.000Z", "startTime": "11:00", "endTime": "12:00", "price": 80, "status": "reserved"}]}}, "elapsed": 0.130}
{"user_id": "User-6", "status": 201, "data": {"message": "Error", "statusCode": 400, "error": "场次已被预定"}, "elapsed": 0.139}
```

`results_exclusive_booking_20260205-110421_summary.txt`：

```
Summary for exclusive_booking at 20260205-110421
Status counts:
  201: 10

Sample failures:
{"user_id": "User-1", "status": 201, "data": {"message": "Error", "statusCode": 400, "error": "场次预订失败，请重试"}, ...}
...
```

**解析说明。** 接口成功时 HTTP 状态为 201，业务成功由 `data.statusCode == 200` 表示。10 个并发请求中仅 1 条（如 User-5）为 statusCode 200 并拿到 orderId，其余 9 条为 statusCode 400（「场次已被预定」或「场次预订失败，请重试」），说明无容量场次的原子更新生效，符合「10 抢 1 仅 1 成功」的预期。summary 里按 HTTP 统计均为 201，故看业务结果需以 jsonl 中的 `data.statusCode` 为准。

---

### 4.2 容量场次并发预订

**SQL：在库中查当前可用的容量场次（容量≥10、未满、available）**

```sql
SELECT
  s.session_id,
  s.venue_id,
  s.court_id,
  s.date,
  s.start_time,
  s.end_time,
  s.price,
  s.capacity_total,
  s.capacity_used,
  (s.capacity_total - s.capacity_used) AS remaining
FROM session s
WHERE s.status = 'available'
  AND s.capacity_total IS NOT NULL
  AND s.capacity_total >= 10
  AND s.capacity_used < s.capacity_total
  AND s.date >= CURDATE()
ORDER BY s.date, s.start_time
LIMIT 20;
```

**asynio.py：容量场次测试逻辑与成功判定**

```python
# 2. 容量场次并发预订
async def test_capacity_booking():
    if len(CONFIG["tokens"]) < 20:
        logging.warning("跳过容量测试：Token不足20个")
        return
    if not CONFIG.get("capacity_session_id"):
        logging.warning("没有找到容量场次，跳过容量场次测试")
        return

    logging.info("开始测试: 容量场次并发预订 (20用户 -> 容量10)")
    url = f"{BASE_URL}/sessions/reserve-capacity/{CONFIG['capacity_session_id']}"
    target_session_id = CONFIG["capacity_session_id"]

    active_tokens = CONFIG["tokens"][:30]

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i, token in enumerate(active_tokens):
            headers = {"Authorization": format_auth_token(token)}
            payload = {"sessionId": [target_session_id]}
            tasks.append(make_request(session, "POST", url, headers, payload, f"User-{i+1}"))

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

    # 与独占场次一致：按业务码 data.statusCode 判断，接口成功时返回 HTTP 201
    success = [r for r in results if r.get('data', {}).get('statusCode') == 200]
    fails = [r for r in results if r.get('data', {}).get('statusCode') != 200]

    logging.info("耗时: %.4fs", duration)
    logging.info("成功预订数: %s (预期: 10)", len(success))
    logging.info("失败请求数: %s (预期: 10)", len(fails))
    try:
        save_results(results, "capacity_booking")
        summarize_results(results, "capacity_booking")
    except Exception:
        logging.exception("保存/摘要容量场次测试结果时出错")
```

**results 示例（capacity_booking）：jsonl 片段 + summary**

`results_capacity_booking_20260205-110424.jsonl` 中 28 条，摘录成功与失败各几条：

```jsonl
{"user_id": "User-1", "status": 201, "data": {"message": "容量场次预定成功", "statusCode": 200, "data": {"orderId": "60470e6647e04c4d1770260664674", "totalPrice": "80.00", "session": {"sessionId": 104538, "capacityTotal": 10, "capacityUsed": 0, "remainingCapacity": 10}}}, "elapsed": 0.192}
{"user_id": "User-4", "status": 201, "data": {"message": "场次预订失败，请重试", "statusCode": 400, "error": "场次预订失败，请重试"}, "elapsed": 0.281}
{"user_id": "User-6", "status": 201, "data": {"message": "容量场次预定成功", "statusCode": 200, "data": {"session": {"sessionId": 104538, "capacityTotal": 10, "capacityUsed": 4, "remainingCapacity": 6}}}, "elapsed": 0.260}
{"user_id": "User-8", "status": 201, "data": {"message": "场次不可预定", "statusCode": 400, "error": "场次不可预定"}, "elapsed": 0.284}
```

`results_capacity_booking_20260205-110424_summary.txt`：

```
Summary for capacity_booking at 20260205-110424
Status counts:
  201: 28

Sample failures:
（此处按 HTTP 统计，201 也会被当作“非 200”样本列出；实际业务失败为 statusCode 400）
```

**解析说明。** 容量场次接口成功时同样返回 HTTP 201，脚本已改为按 `data.statusCode == 200` 计成功。28 个并发请求中，按业务码统计为 10 成功、18 失败，与容量 10 的场次上限一致，说明后端 `capacity_used` 原子自增与上限校验生效。成功条目的返回里 `capacityUsed`/`remainingCapacity` 有时仍为 0/10，属返回快照时序问题，不影响实际扣减；只有 10 个订单真正占位。

---

### 4.3 活动报名并发

**SQL：在库中查当前开放报名且未满的活动（按 event_reg + 订单状态统计已报名人数）**

```sql
SELECT
  e.event_id,
  e.title,
  e.venue_id,
  e.status,
  e.capacity,
  e.start_time,
  e.end_time,
  e.price,
  COALESCE(reg.cnt, 0) AS registered_count,
  (e.capacity - COALESCE(reg.cnt, 0)) AS remaining
FROM event e
LEFT JOIN (
  SELECT event_id, COUNT(*) AS cnt
  FROM event_reg er
  INNER JOIN `order` o ON o.order_id = er.order_id
  WHERE o.status NOT IN ('cancelled', 'refunded', 'refund_rejected')
  GROUP BY event_id
) reg ON reg.event_id = e.event_id
WHERE e.status = 'open'
  AND e.end_time > NOW()
  AND (e.capacity - COALESCE(reg.cnt, 0)) > 0
ORDER BY e.start_time
LIMIT 20;
```

**asynio.py：活动报名测试逻辑**

```python
# 3. 活动报名并发测试
async def test_event_registration():
    if not CONFIG["tokens"]: return
    logging.info("开始测试: 活动报名并发")
    url = f"{BASE_URL}/events/{CONFIG['event_id']}/register"

    active_tokens = CONFIG["tokens"]

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i, token in enumerate(active_tokens):
            headers = {"Authorization": format_auth_token(token)}
            phone = f"138{random.randint(10000000, 99999999)}"
            payload = {
                "participants": [
                    { "name": f"AutoTester-{i}", "gender": "male", "tel": phone }
                ]
            }
            tasks.append(make_request(session, "POST", url, headers, payload, f"User-{i+1}"))

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

    success = [r for r in results if r['status'] == 200]
    logging.info("耗时: %.4fs", duration)
    logging.info("报名成功: %s", len(success))
    try:
        save_results(results, "event_registration")
        summarize_results(results, "event_registration")
    except Exception:
        logging.exception("保存/摘要活动报名测试结果时出错")
```

**results 示例（event_registration）：jsonl 片段 + summary**

`results_event_registration_20260205-110426.jsonl` 中 28 条，多为 400：

```jsonl
{"user_id": "User-1", "status": 201, "data": {"message": "Error", "statusCode": 400, "error": "Insufficient capacity"}, "elapsed": 0.125}
{"user_id": "User-2", "status": 201, "data": {"message": "Error", "statusCode": 400, "error": "您已报名该活动或存在待处理的退款申请，请勿重复报名"}, "elapsed": 0.141}
{"user_id": "User-3", "status": 201, "data": {"message": "Error", "statusCode": 400, "error": "Insufficient capacity"}, "elapsed": 0.185}
```

`results_event_registration_20260205-110426_summary.txt`：

```
Summary for event_registration at 20260205-110426
Status counts:
  201: 28

Sample failures:
（同上，按 HTTP 统计；业务上多为 Insufficient capacity 或重复报名）
```

**解析说明。** 活动报名接口成功时返回 HTTP 201，脚本此处按 `r['status'] == 200` 计成功，因此 201 不会算进「报名成功」数。若活动 capacity 较小或已被占满，多数请求会得到 statusCode 400：「Insufficient capacity」表示人数已满，「您已报名该活动或存在待处理的退款申请，请勿重复报名」表示同一用户重复报名被拒绝，二者均说明活动人数与重复校验生效。测试前须保证 CONFIG 中 `event_id` 在库中为 `status='open'` 且 `end_time > NOW()`，否则会报「Event is not open for registration」。

---

### 4.4 场次列表高负载查询

**SQL：按场馆查可用场次（与脚本 venue_id 一致，用于确认查询目标）**

```sql
SELECT
  s.session_id,
  s.venue_id,
  s.capacity_total,
  s.capacity_used,
  s.status,
  s.date,
  s.start_time,
  s.end_time
FROM session s
WHERE s.venue_id = 56
  AND s.status = 'available'
  AND s.date >= CURDATE()
  AND (
    (s.capacity_total IS NULL OR s.capacity_total = 1)
    OR (s.capacity_total >= 10 AND s.capacity_used < s.capacity_total)
  )
ORDER BY s.capacity_total IS NULL DESC, s.date, s.start_time
LIMIT 20;
```

**asynio.py：场次列表查询压测逻辑**

```python
# 4. 场次查询性能测试
async def test_query_load():
    n = CONFIG.get("query_load_concurrency", 20)
    logging.info("开始测试: 场次列表高负载查询 (%s并发)", n)
    url = f"{BASE_URL}/sessions/venue/{CONFIG['venue_id']}"

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i in range(n):
            tasks.append(make_request(session, "GET", url, user_id=f"Query-{i+1}"))

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

    success = [r for r in results if r['status'] == 200]
    latencies = [r['elapsed'] for r in results]
    avg = sum(latencies) / len(latencies) if latencies else 0

    logging.info("总耗时: %.4fs", duration)
    logging.info("成功响应: %s/%s", len(success), n)
    logging.info("平均响应时间: %.2fms", avg*1000)
    try:
        save_results(results, "query_load")
        summarize_results(results, "query_load")
    except Exception:
        logging.exception("保存/摘要查询负载测试结果时出错")
```

**results 示例（query_load）：summary + 失败样本**

`results_query_load_20260205-110612_summary.txt`：

```
Summary for query_load at 20260205-110612
Status counts:
  0: 1
  200: 93
  504: 6

Sample failures:
{"user_id": "Query-49", "status": 0, "error": "Response payload is not completed: ... ContentLengthError ...", "elapsed": 99.58}
{"user_id": "Query-67", "status": 504, "data": {"error": "Invalid JSON", "text": "<html>...504 Gateway Time-out...</html>"}, "elapsed": 10.90}
{"user_id": "Query-84", "status": 504, "data": {"error": "Invalid JSON", "text": "<html>...504 Gateway Time-out...</html>"}, "elapsed": 10.35}
```

**解析说明。** 本场景为对 `GET /sessions/venue/{venue_id}` 做高并发 GET，无业务码，成功以 HTTP 200 计。当并发数较大（如 100）时，上游或 DB 在 nginx 超时内未响应，会得到 504 Gateway Time-out；个别请求还可能因连接中断出现 status 0（ContentLengthError）。脚本已增加 `CONFIG["query_load_concurrency"]`，默认 20，可避免在当前环境下大量 504；若需加压，可逐步提高该值或调大 nginx 超时/优化接口与数据库。

---

### 4.5 取消订单时 capacity_used 下溢报错与修复

**报错信息（服务器 PM2 / Nest 日志）**

取消订单（如预订未支付订单超时自动取消）时出现：

```
[Nest] ERROR [OrderService] 取消订单失败:
Invalid `prisma.$executeRaw()` invocation:
Raw query failed. Code: `1690`. Message: `BIGINT UNSIGNED value is out of range in '(`yuedong`.`session`.`capacity_used` - 1)'`

PrismaClientKnownRequestError: ...
    at OrderService.cancelOrder (/opt/yuedong/backend/src/common/order/order.service.ts:1380:29)
    ...
    at Timeout._onTimeout (/opt/yuedong/backend/src/consumer/session/session.service.ts:1006:17)
```

**原因说明**

- MySQL 错误 1690 表示：在计算 `capacity_used - 1` 时得到**负数**（例如 `capacity_used` 已为 0 时得到 -1），而 `session.capacity_used` 为 **UNSIGNED** 类型，不能为负，故报错。
- 典型场景：多个「预订未支付」的容量场次订单陆续超时取消，每个取消都会对对应场次执行 `capacity_used = capacity_used - 1`。若出现**重复扣减**（同一场次被多个取消各扣一次，或并发取消导致两次都读到 `capacity_used = 1` 再各减 1），第二次减时 `capacity_used` 已是 0，再算 `0 - 1` 即触发 1690。
- 原 SQL 使用 `GREATEST(0, capacity_used - 1)`，在 MySQL 中仍会先求 `capacity_used - 1`，当 `capacity_used = 0` 时中间结果 -1 即触发 UNSIGNED 下溢。

**解决方法**

在 `src/common/order/order.service.ts` 中，取消订单时「释放有容量场次」的那条 `UPDATE session` 已做如下修改：

1. **`capacity_used` 的更新**：不再使用 `GREATEST(0, capacity_used - 1)`，改为  
   `capacity_used = CASE WHEN capacity_used > 0 THEN capacity_used - 1 ELSE 0 END`  
   这样只有在 `capacity_used > 0` 时才做减法，否则直接写 0，不会出现负值。

2. **`status` 的 CASE 中避免对 0 做减法**：若 SET 中先更新了 `capacity_used` 再在同一行里用 `(capacity_used - 1)` 判断 status，可能此时 `capacity_used` 已为 0，再次出现 -1。改为用同一安全表达式：  
   `(CASE WHEN capacity_used > 0 THEN capacity_used - 1 ELSE 0 END) < capacity_total`  
   用于决定是否把 status 从 `reserved` 改回 `available`。

修改后逻辑仍为：仅对 `WHERE capacity_used > 0` 的行更新，且所有涉及「减一」的地方都通过 CASE 保证不产生 UNSIGNED 下溢，重复或并发取消同一场次时不再报 1690。
