---
schema: "bubblevan/v1"
id: "project-yuedong-sports-06"
content_kind: "project"
title: "悦动体育 06：C 端 UniApp 页面与交易流程——页面状态怎样承接真实业务"
date: "2026-09-10"
updated: "2026-09-10"
status: "draft"
visibility: "public"
projects: ["project-yuedong-sports"]
summary: "从 pages.json 和用户点击开始，拆解悦动 C 端 UniApp 的页面生命周期、请求封装、场次矩阵、订单确认、微信支付、查单、凭证、活动报名、约球与个人中心，复盘页面状态如何承接真实业务。"
topics: ["uniapp", "vue3", "javascript", "wechat-mini-program", "frontend", "payment", "booking", "project-review"]
---

# 悦动体育 06：C 端 UniApp 页面与交易流程——页面状态怎样承接真实业务

05 主要处理后端的并发、支付和时间边界。06 转到 C 端，问题变成了：用户点下一个按钮以后，页面怎样知道自己处于哪一步，下一次请求应该带什么参数，服务端返回的状态又该怎样显示出来？

这次我参照 Day02 的阅读方法，从页面行为反推接口。先看用户能看到什么，再去找页面入口、生命周期、请求方法、请求路径、参数和返回字段。这样阅读 yuedong-v2-frontend 时，二十多个 .vue 文件不会变成一张文件名清单，而会被还原成几条可追踪的用户旅程。

![悦动体育 06：C 端用户旅程与系统支撑](/projects/yuedong-sports/yuedong-06-user-journey.png)

本文的主线是场馆预约：

| 用户看到的动作 | 页面 | 需要追踪的状态 |
|---|---|---|
| 从首页进入场馆 | HomePage.vue、BookVenuePage.vue | venueId、场馆详情、位置 |
| 查看日期和场次 | VenueReservation.vue | selectedDate、场次矩阵、格子状态 |
| 选择一个或多个场次 | VenueReservation.vue | selectedRooms、sessionIds、总价 |
| 确认订单并支付 | ConfirmVenue.vue | 须知、会员卡、待支付订单、支付参数 |
| 查看支付结果 | PaymentResult.vue | pending、success、fail |
| 打开订单凭证 | Credential.vue、OrderListPage.vue | orderId、凭证信息、退款入口 |

活动报名、约球和个人中心放在后半部分，用来验证这套页面状态的阅读方法能不能迁移到其他 C 端功能。

> **本篇任务卡**
>
> 以“用户从首页进入场馆，选择场次，创建订单，支付后打开凭证”为唯一主线。读完场馆预约后，再用活动报名、约球和个人中心检查这套阅读方法能否迁移。完成标准不是记住页面文件名，而是能把一次点击还原成：路由参数、请求契约、页面状态、订单 ID 和下一页动作。
>
> - 页面入口可以从 `pages.json` 找到；
> - 页面动作可以对应到请求方法、路径、参数和返回字段；
> - loading、empty、error、pending、success、fail 有不同的显示和恢复动作；
> - 支付结果最终以服务端查单和订单详情为依据。

## 1. 先把 C 端当成一条用户旅程

### pages.json 是页面入口清单

UniApp 页面不是浏览器里任意可以访问的 URL。小程序需要先在 pages.json 注册页面，tabBar.list 再声明底部 Tab 的入口。悦动的四个主入口是首页、活动中心、约球和个人中心：

```json
{
  "tabBar": {
    "custom": true,
    "list": [
      { "pagePath": "pages/HomePage/HomePage", "text": "首页" },
      { "pagePath": "pages/ActivityCenter/ActivityCenter", "text": "活动中心" },
      { "pagePath": "pages/AppointmentPage/AppointmentPage", "text": "约球" },
      { "pagePath": "pages/DashboardPage/DashboardPage", "text": "个人中心" }
    ]
  }
}
```

custom: true 表示底部栏由项目自己的 TabBar.vue 负责渲染。普通页面则继续在 pages 数组中注册，例如 VenueReservation/VenueReservation、ConfirmVenue、PaymentResult、OrderListPage 和活动报名相关页面。

这一步先回答“页面能不能被打开”，还没有回答“页面为什么会跳到那里”。在源码里，页面跳转通常出现在事件处理函数中：

```javascript
const goToBookVenuePage = (venueId) => {
  uni.navigateTo({
    url: '/pages/BookVenuePage/BookVenuePage?venueId=' +
      encodeURIComponent(venueId)
  });
};

const navigateToOrderList = () => {
  uni.navigateTo({
    url: '/pages/OrderList/OrderListPage'
  });
};
```

因此我阅读 C 端时会先把页面分成四类：

| 页面类型 | 悦动里的例子 | 主要职责 |
|---|---|---|
| 入口页 | HomePage、四个 Tab 页面 | 发现内容、检查登录、进入业务 |
| 列表页 | ActivityCenter、AppointmentPage、OrderListPage | 请求集合、筛选、排序、空状态 |
| 详情/选择页 | EventInfo、VenueReservation | 展示一个业务对象，收集选择上下文 |
| 交易/凭证页 | ConfirmVenue、PaymentResult、Credential | 创建订单、确认支付结果、显示可核验信息 |

页面注册顺序不等于业务调用顺序。真正的阅读顺序应该沿着用户动作走：入口页把什么 ID 传给列表或详情页，详情页把什么上下文传给确认页，确认页生成的 orderId 又被哪个页面继续使用。

### onLoad、onMounted 和 onShow 不是同一个时机

`<script setup>` 里的普通 Vue 生命周期和 UniApp 页面生命周期会同时出现。当前项目里可以这样区分：

| 时机 | 适合做什么 | 源码里的使用 |
|---|---|---|
| onLoad(options) | 读取页面参数，初始化 venueId、eventId、orderId | VenueReservation、EventInfo、PaymentResult |
| onMounted() | 组件挂载后加载云端图片或页面初始资源 | HomePage、ActivityCenter、PaymentResult |
| onShow() | 页面重新显示时重新检查会变化的状态 | EventInfo、EventReservation、OrderListPage、DashboardPage |

活动详情页的参数来自路由，首次打开时先拿到 eventId，然后请求活动详情并检查报名状态：

```javascript
onLoad((option) => {
  if (option.eventId) {
    eventId.value = option.eventId;
    fetchEventDetails(eventId.value);
    isFavorite.value = getFavoriteStatus('event', eventId.value);
    checkRegistrationStatus();
  } else {
    error.value = '活动ID缺失';
    isLoading.value = false;
  }
});

onShow(() => {
  if (eventId.value) {
    checkRegistrationStatus();
  }
});
```

onShow 的存在说明页面状态可能在离开期间发生变化。用户从活动详情页进入报名页，支付完成后返回，详情页就不能永远相信第一次加载的 isPaid。订单列表也是一样：从凭证页返回后，列表里的状态可能已经从 pending 变成了 paid 或 refunded。

### 从页面行为反推接口

面对陌生页面，我会先写出一张小表：

| 页面行为 | 先找什么 | 例子 |
|---|---|---|
| 打开页面 | onLoad 参数 | venueId、eventId、orderId |
| 显示列表 | get/post 调用 | GET /venues、GET /events、GET /orders |
| 点击筛选 | refs、computed 和请求参数 | selectedSport、selectedSort |
| 点击提交 | 校验函数和 post 调用 | 场次预约、活动报名 |
| 从支付返回 | onShow、查单和本地标记 | queryWxPayOrder、paidEvents |
| 显示凭证 | 订单详情请求和字段映射 | orderId、场馆、参与人、二维码 |

例如，VenueReservation 的“确认订场”按钮不是直接支付，它先把选择上下文传给 ConfirmVenue：

```javascript
const sessionIds = selectedRooms.value.map(room => room.sessionId);
const dateInfo = selectedDate.value ? {
  date: selectedDate.value.date,
  weekday: selectedDate.value.weekday,
  fullDate: selectedDate.value.fullDate
} : null;
const areaInfo = selectedRooms.value.map(room => room.venue);

uni.navigateTo({
  url: '/pages/VenueReservation/ConfirmVenue' +
    '?sessionIds=' + encodeURIComponent(sessionIds.join(',')) +
    '&venueId=' + encodeURIComponent(venueId.value) +
    '&dateInfo=' + encodeURIComponent(JSON.stringify(dateInfo)) +
    '&areaInfo=' + encodeURIComponent(JSON.stringify(areaInfo)) +
    '&selectedCount=' + selectedRooms.value.length
});
```

这样可以顺着 sessionIds 继续搜索：它在哪里被读取，读取后请求了哪个接口，接口返回的 orderId 在哪里传给支付结果页。这个方法比一开始就打开某个大文件从第一行读起更容易保持方向。

### 先为主流程列一份接口契约

页面行为反推接口之后，还要把关键请求的输入和输出写出来。下面这份表只保留场馆预约主线需要的字段：

| 页面动作 | 方法与路径 | 主要输入 | 页面要拿到什么 |
|---|---|---|---|
| 查看场馆 | `GET /venues/:id` | `venueId` | 场馆名称、类别、地址和营业信息 |
| 查看未来场次 | `GET /sessions/venue/:id` | `startDate`、`endDate`、可选 `category` | session 集合，页面再物化为矩阵 |
| 查询本人预订状态 | `POST /venues/:id/sessions/reservations/status` | 场次或日期范围 | `userReserved`、`reservationId`、`orderStatus` |
| 提交场次预约 | `POST /sessions/reserve` 或容量场次专用路径 | `sessionId` 或批量场次上下文 | 业务 `orderId`、后端计算的 `totalPrice` |
| 创建微信支付 | `POST /payment/wxpay/create` | `orderId`、金额和支付上下文 | `timeStamp`、`nonceStr`、`package`、`signType`、`paySign` |
| 查询支付结果 | `GET /payment/wxpay/query/:id` | 支付订单 ID | 支付状态，页面据此进入 pending、success 或 fail |

这张表把“页面输入”和“后端事实”分开了：`selectedRooms`、行列索引和本地 `pendingOrderId` 是页面状态；`sessionId`、`orderId`、支付订单 ID 和服务端返回的金额才是跨页面继续传递的业务上下文。接口契约越清楚，越不容易把展示字段误当成最终事实。

![悦动体育 06：C 端页面路由地图](/projects/yuedong-sports/yuedong-06-page-route-map.png)

## 2. 页面如何把数据变成可交互状态

### request.js 是 C 端的请求边界

页面调用的不是裸 uni.request，而是 utils/request.js 导出的 get、post、put、patch 和 del。统一请求函数负责拼接基础 URL、添加认证头、展示 loading、判断 HTTP 状态，并把错误转换成页面可以处理的异常。

```javascript
export const request = async (options = {}) => {
  const {
    url,
    method = 'GET',
    data = {},
    header = {},
    showLoading = true,
    showError = true,
    needAuth = false,
    retryCount = 0,
    maxRetries = 2
  } = options;

  const fullUrl = url.startsWith('http')
    ? url
    : CONFIG.API.BASE_URL + url;

  const requestHeaders = {
    'Content-Type': 'application/json',
    ...header
  };

  if (needAuth) {
    const token = uni.getStorageSync('token');
    if (token) {
      requestHeaders.Authorization = 'Bearer ' + token;
    }
  }

  if (showLoading) {
    uni.showLoading({ title: '加载中...' });
  }

  try {
    const response = await uni.request({
      url: fullUrl,
      method,
      data,
      header: requestHeaders
    });

    if (showLoading) {
      uni.hideLoading();
    }

    if (
      response.statusCode >= 200 &&
      response.statusCode < 300 ||
      response.statusCode === 304
    ) {
      return response.data;
    }

    const error = new Error(
      'HTTP ' + response.statusCode + ': ' +
      (response.data && response.data.message || '网络请求失败')
    );
    error.statusCode = response.statusCode;
    error.response = response;
    throw error;
  } catch (error) {
    if (error.statusCode === 401) {
      uni.removeStorageSync('token');
      uni.removeStorageSync('userInfo');
      uni.$emit('tokenExpired');
    }
    throw error;
  }
};
```

这段封装给页面提供了三个稳定入口：

- 页面只需要传相对路径和参数，不需要重复拼接 https://yuedongjump.com/api。
- 需要登录的接口通过 needAuth: true 读取本地 token。
- 网络失败、401、500、502 和业务失败可以进入统一的错误处理，再由页面决定显示重试、登录还是空状态。

它也留下了一个阅读重点：HTTP 状态和业务状态码同时存在。request.js 对部分 401、404、500 响应保留给调用方处理，所以页面不能简单地只判断 Promise 有没有 reject，还要看返回对象里的 statusCode、data 和业务字段。

### config.js 集中维护运行环境和接口路径

utils/config.js 先定义不同环境的 API 地址，再暴露 CONFIG.API.ENDPOINTS：

```javascript
const ENV_CONFIG = {
  local: {
    API_BASE_URL: 'http://localhost:8081/api',
    WEB_BASE_URL: 'http://localhost:8081'
  },
  production: {
    API_BASE_URL: 'https://yuedongjump.com/api',
    WEB_BASE_URL: 'https://yuedongjump.com'
  }
};

export const CONFIG = {
  ENV: currentEnv,
  API: {
    BASE_URL: currentConfig.API_BASE_URL,
    ENDPOINTS: {
      VENUES: '/venues',
      VENUE_DETAIL: (id) => '/venues/' + id,
      VENUE_SESSIONS: (id) => '/sessions/venue/' + id,
      EVENTS: '/events',
      EVENT_DETAIL: (id) => '/events/' + id,
      ORDERS: '/orders',
      ORDER_DETAIL: (id) => '/orders/' + id,
      ORDER_SESSIONS: '/orders/sessions'
    }
  }
};
```

当前配置里，小程序的 develop、trial 和 release 最终都返回 production，local 只保留为手动切换选项。这解释了为什么页面代码可以统一写成：

```javascript
const response = await get(
  CONFIG.API.ENDPOINTS.VENUE_SESSIONS(venueIdInt),
  { startDate, endDate },
  { showLoading: false, showError: true }
);
```

页面不需要知道当前域名，只需要知道资源名称和参数。环境切换集中在配置层，接口路径集中在端点表，页面的业务代码因此更容易被单独阅读。

### loading、empty、error 是三个不同状态

场馆页的模板把三种情况明确分开：

```vue
<view class="empty-container" v-if="isEmptyData && !dataError">
  <text class="empty-title">暂无可用场次</text>
  <button @click="fetchData">刷新</button>
</view>

<view class="error-container" v-if="dataError">
  <text class="error-title">网络连接异常</text>
  <button @click="fetchData">重新加载</button>
</view>

<view v-else-if="!isEmptyData">
  <VenueGrid
    :venues="venues"
    :sessions="sessions"
    :room-status="roomStatus"
    :prices="prices"
  />
</view>
```

接口成功返回空数组，含义是“这次请求成功，但当前没有可展示场次”。网络超时、401 或 500 则代表页面没有拿到可用数据，应该让用户看到错误说明和重试入口。两种情况都可能让列表长度为 0，但处理动作不同：

| 状态 | 数据特征 | 用户动作 | 页面处理 |
|---|---|---|---|
| loading | 请求还没有结束 | 等待 | 显示占位或 loading |
| data | 有可渲染数据 | 浏览、选择 | 渲染列表或矩阵 |
| empty | 请求成功，数组为空 | 换场馆或稍后重试 | 显示空状态 |
| error | 请求失败或未授权 | 登录、重试、联系客服 | 显示错误状态 |

HomePage 对场馆列表失败时也保留了 venuesLoadError 和 retryFetchVenues。ActivityCenter 资源还没有加载完成时显示 loading 占位，筛选后没有活动时显示空状态。页面状态至少应该让用户知道“还在加载”“确实没有”“这次失败了”三者的区别。

### computed 把原始列表转换成显示列表

活动中心和约球页都存在“原始响应不变，显示结果随筛选条件变化”的状态。约球页的搜索只作用于内存中的 cardList：

```javascript
const filteredCardList = computed(() => {
  if (!searchKeyword.value.trim()) {
    return cardList.value;
  }

  const keyword = searchKeyword.value.toLowerCase().trim();

  return cardList.value.filter(card => {
    return (
      card.title?.toLowerCase().includes(keyword) ||
      card.sportName?.toLowerCase().includes(keyword) ||
      card.poster?.name?.toLowerCase().includes(keyword)
    );
  });
});
```

ActivityCenter 还有地区、项目、排序和标签等筛选状态；一部分条件会组合成后端查询参数，一部分条件在前端 computed 中派生。阅读时要分别问两个问题：

- 这个条件改变后，页面只是重新计算数组，还是会再次请求服务端？
- 空状态说明的是“服务端没有数据”，还是“原始数据有，但当前筛选没有命中”？

如果这两个状态混在一起，用户会把“筛选没有结果”误解成“系统没有活动”。前端的 selectedDistrict、selectedSport、selectedSort 和 selectedTag 不是装饰性变量，它们决定了下一次请求或当前渲染的输入。

![悦动体育 06：从用户动作到页面状态](/projects/yuedong-sports/yuedong-06-request-state.png)

## 3. 场馆预约从选场次到确认订单

### 后端场次数组在页面上被物化成矩阵

场馆接口返回的是一组 session 对象，页面最终要渲染成“日期、时间、场地”的二维表格。VenueReservation 先按日期过滤，再构建 timeSlots、venues、sessionMap、roomStatus 和 prices，最后把这些数据传给 VenueGrid：

```vue
<!-- <VenueGrid
  :is-swimming-venue="page.isSwimmingVenue"
  :venues="page.venues"
  :sessions="page.sessions"
  :room-status="page.roomStatus"
  :prices="page.prices"
  :session-map="page.sessionMap"
  @room-select="(timeIndex, venueIndex) =>
handleRoomSelect(timeIndex, venueIndex, pageIndex)"
/> -->
```

加载数据时，页面取今天开始的未来七天：

```javascript
const startDate = dayjs().format('YYYY-MM-DD');
const endDate = dayjs().add(6, 'day').format('YYYY-MM-DD');

const response = await get(
  CONFIG.API.ENDPOINTS.VENUE_SESSIONS(venueIdInt),
  {
    startDate,
    endDate,
    ...(selectedCategory.value
      ? { category: selectedCategory.value }
      : {})
  },
  {
    showLoading: false,
    showError: true
  }
);
```

页面还会通过 POST /venues/:venueId/sessions/reservations/status 查询当前用户在这些场次上的预订状态，把 userReserved、reservationId、orderStatus 等字段合并回 session。这样，“别人已经订了”“我已经订过了”和“接口返回的可用场次”就能在同一张矩阵里呈现。

### a、b、u、s 是页面内部的状态编码

场次矩阵的格子至少有四种含义：

| 编码 | 页面含义 | 能否点击 |
|---|---|---|
| a | available，可选 | 可以 |
| b | blocked，已被占用或不可用 | 不可以 |
| u | user reserved，当前用户已经预订 | 不可以 |
| s | selected，当前页面暂时选中 | 再点一次可以取消 |

handleRoomSelect 先检查页面和行列是否存在，再拦截 b、u、价格为 0 的格子：

```javascript
if (
  page.roomStatus[timeIndex][venueIndex] === 'b' ||
  page.roomStatus[timeIndex][venueIndex] === 'u' ||
  page.prices[timeIndex][venueIndex] === 0
) {
  return;
}

const session = page.sessionMap[timeIndex]?.[venueIndex];
if (!session) {
  return;
}

const room = {
  time: page.sessions.timeSlots[timeIndex],
  venue: page.venues[venueIndex],
  price: page.prices[timeIndex][venueIndex],
  timeIndex,
  venueIndex,
  pageIndex,
  sessionId: session.sessionId,
  courtId: session.courtId,
  timeSlot: session.timeSlot
};
```

点击一次时，selectedRooms 增加一个包含业务 ID 和展示信息的对象，同时把格子改成 s；再次点击时移除对象并恢复成 a。这里的 s 只是前端当前选择，不代表后端已经锁定或已经创建订单。真正提交时，后端还会重新验证场次是否可用。

### selectedRooms 携带提交上下文

页面限制一次最多选择四个场次：

```javascript
if (selectedRooms.value.length >= 4) {
  uni.showToast({
    title: '最多只能选择4个场次',
    icon: 'none'
  });
  return;
}

selectedRooms.value.push(room);
page.roomStatus[timeIndex][venueIndex] = 's';
```

selectedRooms 里同时保存了 sessionId、场地、价格、时间索引和页面索引。索引服务于当前矩阵的撤销操作，sessionId 才是提交给后端的业务标识。用户点击确认时，页面再次生成 sessionIds，把日期和场地信息序列化后放进路由参数。

这解释了为什么不能只在页面里保存一个 selected = true。确认页需要知道提交哪些场次，凭证页需要知道显示哪些场地，页面返回时还需要恢复当前选择的日期。一个 UI 勾选动作，实际携带的是一组跨页面的上下文。

### ConfirmVenue 把选择上下文转换为订单请求

确认页先检查 token、场次数量、会员卡限制和入场须知：

```javascript
const handlePay = async () => {
  if (isProcessing.value) {
    return;
  }

  const token = uni.getStorageSync('token');
  if (!token) {
    uni.showToast({ title: '请先登录', icon: 'none' });
    uni.switchTab({
      url: '/pages/DashboardPage/DashboardPage'
    });
    return;
  }

  if (sessionIds.value.length === 0) {
    uni.showToast({ title: '请选择场次', icon: 'none' });
    return;
  }

  if (!hasReadNotice.value && !pendingOrderId.value) {
    uni.showToast({ title: '请先阅读须知', icon: 'none' });
    return;
  }

  if (pendingOrderId.value) {
    await continuePayment();
    return;
  }
};
```

创建订单时，页面先从场次详情判断是普通场次还是容量场次，再选择相应接口。若容量接口返回“不是容量场次”，代码会回退到普通预约接口：

```javascript
const attemptStandardReserve = async (showError = true) => {
  return post(
    CONFIG.API.ENDPOINTS.SESSIONS_RESERVE,
    buildReservePayload(),
    {
      showLoading: false,
      showError,
      needAuth: true
    }
  );
};

const attemptCapacityReserve = async (showError = true) => {
  return post(
    '/sessions/reserve-capacity/' + sessionIdInt,
    buildCapacityPayload(),
    {
      showLoading: false,
      showError,
      needAuth: true
    }
  );
};

if (isCapacitySession(sessionDetail)) {
  try {
    reserveResponse = await attemptCapacityReserve(false);
  } catch (capacityError) {
    reserveResponse = await attemptStandardReserve(true);
  }
} else {
  reserveResponse = await attemptStandardReserve(true);
}
```

拿到响应后，页面读取 orderId、后端计算的 totalPrice 和会员卡信息。总价不是由路由中的 price 直接决定的；页面展示价是选择时的提示，订单价必须以创建订单响应为准。这样即使会员卡、价格规则或容量规则在服务端发生判断，前端也不会把自己的展示值当成最终金额。

### 会员卡、单场支付和批量支付是三条分支

如果后端返回的 totalPrice 是 0.00，并且带有会员卡信息，C 端直接返回 membership 结果，不弹微信支付：

```javascript
const isMembershipCardReservation =
  backendTotalPrice === '0.00' ||
  backendTotalPrice === 0 ||
  Number(backendTotalPrice) === 0;

const hasMembershipCardInfo =
  membershipCardInfo && membershipCardInfo.cardNumber;

if (isMembershipCardReservation && hasMembershipCardInfo) {
  uni.hideLoading();

  return {
    type: 'membership',
    orderId,
    amount: backendTotalPrice,
    sessionIds: [String(sessionIdInt)],
    membershipCardInfo
  };
}
```

普通订单会把订单 ID、场馆、场次、金额和 trade_type: JSAPI 交给 createWxPayOrder，再把返回的 timeStamp、nonceStr、package、signType 和 paySign 传给 requestWxPayment：

```javascript
const orderPayloadForPayment = {
  orderId,
  venueId: venueId.value,
  sessionIds: [sessionIdInt],
  totalAmount: Number(backendTotalPrice),
  venueName: venueData.value.name || '场馆预订',
  bookingDate: sessionDisplay.bookingDate,
  bookingTime: sessionDisplay.bookingTime,
  trade_type: 'JSAPI'
};

const validation = validatePaymentParams(orderPayloadForPayment);
if (!validation.valid) {
  throw new Error(
    '支付参数验证失败: ' + validation.errors.join(', ')
  );
}

const payOrderResult = await createWxPayOrder(orderPayloadForPayment);

const wxPayParams = {
  timeStamp: payOrderResult.timeStamp,
  nonceStr: payOrderResult.nonceStr,
  package: payOrderResult.package,
  signType: payOrderResult.signType,
  paySign: payOrderResult.paySign
};

await requestWxPayment(wxPayParams);
```

批量预约的前端策略是先为多个 session 逐个创建订单。之后如果需要支付的订单只有一个，就走单笔支付；如果有多个，就调用 createBatchWxPayOrder 合并支付。会员卡订单会被放进 membershipCardOrders，需要支付的订单和不需要支付的订单在页面里被分开处理。

因此“预约成功”不是一个单一页面动作：

| 分支 | 前端动作 | 是否调用 requestWxPayment |
|---|---|---|
| 会员卡零元订单 | 创建订单，直接返回成功结果 | 否 |
| 单个现金订单 | 创建订单，创建 JSAPI 参数，打开支付 | 是 |
| 多个现金订单 | 创建多个业务订单，创建合并支付参数 | 是 |
| 支付弹窗取消 | 保留待支付订单，稍后显示继续支付/取消 | 否，等待下一次操作 |

![悦动体育 06：场馆选择到确认订单](/projects/yuedong-sports/yuedong-06-venue-selection.png)

## 4. 支付结果和订单凭证

### pendingOrderId 让用户从中断处继续支付

用户关闭微信支付弹窗时，业务订单可能已经创建。此时直接重新创建订单会带来重复报名或重复占用，所以 ConfirmVenue 和 EventReservation 都会查询待支付订单。

场馆确认页按当前 session 查询订单：

```javascript
const response = await get(
  CONFIG.API.ENDPOINTS.ORDER_SESSIONS,
  { sessionIds: sessionIds.value.join(',') },
  {
    showLoading: false,
    showError: false,
    needAuth: true
  }
);

const orders = Array.isArray(response.data)
  ? response.data
  : [];

const pendingOrderFound = orders.find(order => {
  if (order.status !== 'pending') {
    return false;
  }

  const money = typeof order.money === 'string'
    ? parseFloat(order.money)
    : order.money;

  return money !== 0;
});

if (pendingOrderFound) {
  pendingOrderId.value = pendingOrderFound.orderId;
  pendingOrder.value = pendingOrderFound;
}
```

模板里只有在 pendingOrderId 存在、待支付操作可见且当前没有处理中时才显示“取消订单”按钮。点击继续支付时，页面使用原来的业务订单 ID调用支付服务；点击取消时，使用 DELETE /orders/:orderId 清掉待支付状态。

支付返回后延迟显示待支付操作，也是一个页面层策略。支付弹窗关闭的瞬间，服务端通知和本地订单查询可能还没有完成，立即把“继续支付”显示出来会造成误导。当前实现使用 1800 毫秒延迟，再结合下一次订单查询决定按钮状态。

### requestPayment success 只是客户端支付流程返回

小程序里的 uni.requestPayment 负责打开微信支付弹窗。调用成功后，页面知道用户完成了客户端支付操作，但这个回调本身不是订单详情接口，也不会替后端完成业务订单、报名记录和凭证数据的更新。

ConfirmVenue 成功后会记录支付订单 ID，再把业务订单 ID 和支付订单 ID 带到结果页：

```javascript
await requestWxPayment(wxPayParams);

const wxOrderId = payOrderResult.orderId;
uni.setStorageSync('wxPaySuccess_' + wxOrderId, true);

return {
  type: 'wechat',
  orderId,
  paymentOrderId: wxOrderId,
  amount: backendTotalPrice,
  bookingDate: sessionDisplay.bookingDate,
  bookingTime: sessionDisplay.bookingTime,
  sessionIds: [String(sessionIdInt)]
};
```

这里至少有两个 ID：

| ID | C 端用途 |
|---|---|
| orderId | 悦动业务订单，凭证页使用它查询订单详情 |
| paymentOrderId | 微信支付订单或项目支付单，支付结果页用它查支付状态 |

这也是 05 中支付协议和 C 端页面必须分开的原因。C 端只负责承接支付 SDK 的参数和结果，后端仍然要通过支付回调、订单查询和业务补偿把最终状态写完整。

### PaymentResult 用查单结果决定显示状态

结果页先把 paymentStatus 设为 pending，再调用 queryWxPayOrder。服务端返回 paid、SUCCESS 或 success 时显示成功，否则在查询失败时读取 wxPaySuccess_<orderId> 作为辅助判断：

```javascript
const checkPaymentResult = async () => {
  paymentStatus.value = 'pending';
  finalAmount.value = parseFloat(amountFromOptions.value).toFixed(2);

  try {
    const result = await queryWxPayOrder(orderId.value);

    if (
      result &&
      (
        result.status === 'paid' ||
        result.status === 'SUCCESS' ||
        result.status === 'success'
      )
    ) {
      paymentStatus.value = 'success';

      const amount = parseFloat(
        result.money || amountFromOptions.value
      );
      finalAmount.value = Number.isNaN(amount)
        ? '0.00'
        : amount.toFixed(2);
    } else if (
      uni.getStorageSync('wxPaySuccess_' + orderId.value)
    ) {
      paymentStatus.value = 'success';
    } else {
      paymentStatus.value = 'fail';
      errorMsg.value = result?.errorMsg || '支付未完成或状态未知';
    }
  } catch (error) {
    if (uni.getStorageSync('wxPaySuccess_' + orderId.value)) {
      paymentStatus.value = 'success';
    } else {
      paymentStatus.value = 'fail';
      errorMsg.value = '查询支付结果失败，请稍后重试';
    }
  }
};
```

页面的三个状态应该这样理解：

| 页面状态 | 触发条件 | 适合显示 |
|---|---|---|
| pending | 正在调用查单 | 查询中图标和等待提示 |
| success | 服务端返回已支付，或查询失败但有本地辅助标记 | 支付成功、查看订单 |
| fail | 查单返回未支付或没有可用辅助信息 | 支付失败、返回重试 |

从可信度上看，页面参数适合做初始展示，本地标记适合帮助恢复，服务端订单查询才适合决定业务状态。当前代码把本地标记作为查询失败时的 fallback，这能改善刚完成支付时的体验，但不能把本地标记扩展成永久的支付证明。

![悦动体育 06：客户端支付回调与服务端订单状态](/projects/yuedong-sports/yuedong-06-payment-result.png)

### Credential 是订单事实的展示投影

支付结果页的“查看订单”会把场馆 ID、session IDs、日期、场地和业务 orderId 传给凭证页：

```javascript
const orderIdForCredential =
  venueOrderId.value || orderId.value;

let url =
  '/pages/VenueReservation/Credential' +
  '?venueId=' + venueId.value +
  '&sessionIds=' +
  encodeURIComponent(sessionIds.value.join(',')) +
  '&dateInfo=' +
  encodeURIComponent(JSON.stringify(dateInfo)) +
  '&areaInfo=' +
  encodeURIComponent(JSON.stringify(areaInfo.value));

if (orderIdForCredential) {
  url += '&orderId=' + encodeURIComponent(orderIdForCredential);
}

if (paymentStatus.value === 'success') {
  url += '&status=paid';
}

uni.navigateTo({ url });
```

凭证页打开后仍然会按 orderId 请求订单详情，再根据订单里的 session、场馆、状态和金额组织展示数据。活动凭证页也采用类似的两步：先查订单，再查活动详情，最后显示参与人和二维码。

```javascript
const orderRes = await get(
  CONFIG.API.ENDPOINTS.ORDER_DETAIL(orderId.value),
  {},
  {
    showLoading: false,
    showError: true
  }
);

if (orderRes.statusCode === 200) {
  orderDetails.value = orderRes.data;
  participants.value = Array.isArray(orderRes.data.participants)
    ? orderRes.data.participants
    : [];

  const eventRes = await get(
    CONFIG.API.ENDPOINTS.EVENT_DETAIL(eventId.value),
    {},
    {
      showLoading: false,
      showError: true
    }
  );

  if (eventRes.statusCode === 200) {
    eventDetails.value = eventRes.data;
  }

  generateQRCode();
}
```

“投影”在这里指页面展示的是订单事实的一种视图。日期、场地、参与人和二维码可以作为可读信息，但真正的查询入口仍然是 orderId。因此从支付结果页跳转凭证时，展示参数可以帮助页面快速显示，凭证页还需要重新读取服务端数据。

### OrderList 先识别订单类型，再决定凭证路由

订单列表同时承接场馆预约和活动报名。当前路由函数优先检查 orderType，再兼容 eventRegs、sessionRegs、根级 venueId 和旧数据结构：

```javascript
const isEventOrder =
  order.orderType === 'event' ||
  (
    Array.isArray(order.eventRegs) &&
    order.eventRegs.length > 0
  ) ||
  !!order.eventId;

if (isEventOrder) {
  const eventId = order.eventRegs?.[0]?.eventId || order.eventId;

  uni.navigateTo({
    url:
      '/pages/VenueReservation/Credential' +
      '?orderId=' + order.orderId +
      '&type=event&eventId=' + eventId
  });

  return;
}

let venueId = null;
let sessionIds = [];

if (order.sessionRegs?.length > 0) {
  venueId = order.sessionRegs[0].session?.venue?.venueId ||
    order.sessionRegs[0].session?.venueId;

  sessionIds = order.sessionRegs
    .map(reg => reg.sessionId || reg.session?.sessionId)
    .filter(Boolean);
}
```

这段代码的复杂度来自历史数据和两类业务共用订单列表。长期看，后端统一返回 orderType、eventId、venueId、sessionIds 和标准化的关联对象，前端路由会更短。当前实现的价值是能够在字段不完全一致时尽量把用户送到正确的凭证页，但它也提醒我：数据结构兼容层应该有明确的退出计划。

## 5. 活动报名、约球和个人中心的共性

### EventInfo 先用状态和容量决定能否报名

活动详情页同时显示活动状态、已报名人数和剩余容量。按钮能否点击不能只看列表页快照，handleConfirm 里还会再次检查登录和 canRegister：

```javascript
const canRegister = () => {
  if (event.value.status !== 'open') {
    return false;
  }

  if (event.value.remainingCapacity <= 0) {
    return false;
  }

  return true;
};

const handleConfirm = () => {
  if (!checkLoginAndShowModal('报名活动')) {
    return;
  }

  if (!canRegister()) {
    uni.showToast({
      title: getButtonText(),
      icon: 'none'
    });
    return;
  }

  uni.navigateTo({
    url:
      '/pages/EventRegistration/EventReservation' +
      '?eventId=' + encodeURIComponent(eventId.value) +
      '&totalCapacity=' + event.value.capacity +
      '&remainingCapacity=' + event.value.remainingCapacity
  });
};
```

页面还在 onShow 中重新检查报名状态。如果本地 paidEvents 里保存了订单 ID，就调用支付查询；如果没有，再从 /orders 找当前活动的订单。这种做法和场馆预约的待支付恢复相似：列表页负责发现，详情页负责再次确认。

### registration_fields 让报名表单由活动数据驱动

不同活动可能需要不同的姓名、性别、手机号、年龄或其他字段。EventReservation 先读取活动返回的 registration_fields，再按 order 排序并初始化 formData：

```javascript
const sortedRegistrationFields = computed(() => {
  if (!registrationFields.value?.fields) {
    return [];
  }

  return [...registrationFields.value.fields].sort((a, b) => {
    const orderA = a.order || 999;
    const orderB = b.order || 999;
    return orderA - orderB;
  });
});

const initFormData = () => {
  if (registrationFields.value?.fields) {
    const data = {};

    registrationFields.value.fields.forEach(field => {
      data[field.id] = field.type === 'checkbox' ? [] : '';
    });

    formData.value = data;
  }
};
```

提交时，页面根据字段类型分别处理必填、长度和数值范围：

```javascript
for (const field of sortedRegistrationFields.value) {
  const value = formData.value[field.id];

  if (field.required) {
    if (field.type === 'checkbox') {
      if (!Array.isArray(value) || value.length === 0) {
        uni.showToast({
          title: '请选择' + field.label,
          icon: 'none'
        });
        return;
      }
    } else if (!value || String(value).trim() === '') {
      uni.showToast({
        title: '请输入' + field.label,
        icon: 'none'
      });
      return;
    }
  }

  if (field.type === 'number' && value !== '') {
    const numValue = Number(value);

    if (Number.isNaN(numValue)) {
      uni.showToast({
        title: field.label + '必须是数字',
        icon: 'none'
      });
      return;
    }
  }
}
```

动态表单减少了为每种活动复制页面的需要。它也带来一个边界：前端校验服务于交互体验，后端仍然要校验字段是否存在、格式是否正确、报名人数是否超出容量。

### companions 把报名人数扩展成参与人集合

报名页面的第一份表单是主要报名人，用户还可以添加 companions。新增参与人时，页面要复用动态字段，并在提交时对每个 companion 执行同样的必填、长度和数值校验。

```javascript
for (let i = 0; i < companions.value.length; i++) {
  const companion = companions.value[i];

  for (const field of sortedRegistrationFields.value) {
    const value = companion[field.id];

    if (
      field.required &&
      (!value ||
        field.type === 'checkbox' &&
        (!Array.isArray(value) || value.length === 0))
    ) {
      uni.showToast({
        title: '请输入他人' + (i + 1) + '的' + field.label,
        icon: 'none'
      });
      return;
    }
  }
}
```

提交的数据最后需要被组织成一个参与人集合，而不是只把主要报名人的字段发给后端。当前页面同时维护 formData 和 companions 两个容器，阅读时要注意它们的字段配置、校验逻辑和提交 payload 是否保持一致。

如果用户在活动报名页已经存在有效报名，页面会拦截重复报名；如果存在 pending 订单，则恢复表单并显示“继续支付”。这说明报名表单不能只当作一张静态表，它还要承接订单状态。

### 约球页把多个筛选条件拆成响应式状态

约球页的交互目标和场馆预约不同：用户浏览的是社交列表，可以按运动类型、是否有空位、是否加入、是否关注和是否由自己发起来筛选。代码将这些条件拆成独立 refs：

```javascript
const selectedTagIndices = ref([]);
const hasSpots = ref(false);
const isJoinedOnly = ref(false);
const isFavoredOnly = ref(false);
const isMyMeetups = ref(false);
const searchKeyword = ref('');

const tagMap = {
  '有空位': null,
  ...SPORT_LABEL_TO_TAG
};
```

页面还有 scroll-view 的 refresher-enabled，用户下拉刷新时重新请求约球列表。搜索词则可以直接作用于 filteredCardList。把每个条件拆开后，模板只关心当前状态，事件函数只修改对应状态，后续再由请求函数或 computed 统一组合。

这套结构可以迁移到其他列表页：把“用户动作”变成 ref，把“显示结果”变成 computed，把“需要服务端参与的条件”变成请求参数。需要留意的是，前端筛选和服务端筛选的边界应该在接口契约中写清楚，不能只靠页面猜测。

### Dashboard 是多个服务结果的聚合视图

个人中心在登录前后是两套模板。登录前显示手机号一键登录；登录后同时展示用户信息、订单日历、收藏场馆、收藏活动和我的约球：

```vue
<view v-if="!isLoggedIn" class="login-container">
  <button
    open-type="getPhoneNumber"
    @getphonenumber="handlePhoneLogin"
  >
    手机号一键登录
  </button>
</view>

<view v-else>
  <UpcomingOrdersCalendar
    :upcoming-orders="upcomingOrders"
    :loading="loadingDashboard"
  />
  <EndedOrdersCalendar
    :calendar-data="calendarData.calendarData"
    :loading="loadingDashboard"
  />
</view>
```

登录状态来自本地 token，但用户资料和 dashboard 数据仍然会重新请求。收藏场馆、收藏活动和我的约球各自有 loading 状态，空数据也分别显示“暂无收藏场馆”“暂无收藏活动”和“暂无约球记录”。

因此 Dashboard 比单个详情页更容易出现局部 loading：订单日历请求成功，不代表收藏场馆请求也完成。页面把多个 service 的结果组合在一个视图中，就需要保留每个区域自己的加载和空状态。

## 6. C 端工程复盘：参数、缓存、刷新和降级

### 路由参数必须同时考虑编码和恢复

场馆预约跨了多个页面，参数里有字符串、数组和对象。当前实现的组合方式是：

```javascript
const sessionIds = selectedRooms.value.map(room => room.sessionId);
const dateInfo = {
  date: selectedDate.value.date,
  weekday: selectedDate.value.weekday,
  fullDate: selectedDate.value.fullDate
};
const areaInfo = selectedRooms.value.map(room => room.venue);

const url =
  '/pages/VenueReservation/ConfirmVenue' +
  '?sessionIds=' + encodeURIComponent(sessionIds.join(',')) +
  '&dateInfo=' + encodeURIComponent(JSON.stringify(dateInfo)) +
  '&areaInfo=' + encodeURIComponent(JSON.stringify(areaInfo));
```

进入页面后再反向解析：

```javascript
onLoad((options) => {
  const decodedSessionIds = decodeURIComponent(
    options.sessionIds || ''
  );

  sessionIds.value = decodedSessionIds
    .split(',')
    .filter(Boolean);

  if (options.dateInfo) {
    initialSelectedDateInfo.value = JSON.parse(
      decodeURIComponent(options.dateInfo)
    );
  }
});
```

这里有三个容易漏掉的点：

- 数组需要约定分隔方式，解析后还要过滤空字符串。
- 对象需要先 JSON.stringify，再 encodeURIComponent；读取时反过来做。
- ID、日期和展示文字都可能包含特殊字符，不能直接拼到 URL。

路由参数越复杂，页面之间的耦合越明显。当前实现保留这些参数是为了让确认页和凭证页快速显示上下文，订单金额和最终状态仍然由服务端数据决定。

### 本地存储只能做辅助事实

项目使用了多组本地存储：

| key | 作用 | 可信边界 |
|---|---|---|
| token | 请求认证 | 过期后由 401 清理 |
| userInfo | 展示个人资料 | 可被用户设备上的旧数据覆盖 |
| wxPaySuccess_<id> | 支付弹窗成功后的辅助标记 | 只能帮助页面恢复，不能单独证明订单已支付 |
| paidEvents | 记录活动订单 ID，帮助详情页查询 | 需要后端订单查询确认 |
| cachedOrders | 订单请求失败时的缓存兜底 | 可能过期，不能替代服务端列表 |

支付结果页的写入很直接：

```javascript
uni.setStorageSync(
  'wxPaySuccess_' + wxOrderId,
  true
);

let paidEvents = uni.getStorageSync('paidEvents') || {};
paidEvents[eventId.value] = {
  orderId,
  payTime: new Date().toISOString(),
  eventName: eventInfo.value.title,
  amount: selectedPrice.value
};
uni.setStorageSync('paidEvents', paidEvents);
```

本地状态最适合做两件事：保存下一次请求需要的 ID，以及在页面刚返回时提供一个临时 UI 提示。它不适合承担库存、支付和报名的最终裁决，因为用户可以清理本地存储，设备之间也不会自动同步。

### onShow 是回到页面后的刷新点

活动详情、活动报名、订单列表和 Dashboard 都在 onShow 中重新检查或加载动态数据：

```javascript
onShow(() => {
  if (eventId.value) {
    checkRegistrationStatus();
  }
});
```

```javascript
onShow(() => {
  if (eventId.value && !isLoading.value) {
    checkPendingOrder(eventId.value);
  }
});
```

```javascript
onShow(() => {
  fetchOrders();
});
```

用户从支付结果页、凭证页或登录页返回时，页面没有重新创建并不意味着数据没有变化。onShow 可以作为“重新获得前台展示机会”的刷新点。它也有成本：如果每次显示都重复请求，复杂页面可能产生闪烁或重复调用，所以下一步应增加请求去重、刷新时间窗口或取消旧请求的策略。

### 云端图片和网络请求都需要降级路径

C 端有一层云端资源管理：页面在 onMounted 中批量获取图片 URL，失败时使用 OSS fallback 或默认图片。PaymentResult 的图片资源加载失败时，也会根据当前状态选择成功、失败或查询中的备用图。

```javascript
try {
  cloudUrls.value = await getCloudResources(resources);
} catch (error) {
  cloudUrls.value = {
    'payment/支付成功.svg':
      'https://yuedong-img.oss-cn-hangzhou.aliyuncs.com/static/支付成功.svg',
    'payment/支付失败.svg':
      'https://yuedong-img.oss-cn-hangzhou.aliyuncs.com/static/支付失败.svg',
    'payment/支付查询中.svg':
      'https://yuedong-img.oss-cn-hangzhou.aliyuncs.com/static/支付查询中.svg'
  };
}
```

业务接口也有对应的降级路径：

| 失败对象 | 当前页面动作 |
|---|---|
| 场馆列表请求失败 | 显示网络错误、重试按钮和联系客服 |
| 场馆接口返回空数组 | 显示暂无可用场次 |
| 未登录请求需要认证的数据 | 清理 token，提示重新登录 |
| 订单请求遇到日期格式错误 | 尝试重新格式化，必要时读取 cachedOrders |
| 图片 URL 无法加载 | 使用云端 fallback、默认图片或占位图 |

资源加载失败和业务数据失败不能显示成同一种错误。图片失败时，页面通常仍然可以展示场馆名称和操作按钮；订单请求失败时，页面可能无法判断用户是否真的支付成功，处理级别不同。

![悦动体育 06：C 端可靠性边界](/projects/yuedong-sports/yuedong-06-client-reliability.png)

### 用状态迁移清单代替只测“页面能打开”

这次复盘后，我会优先手工验证下面这些状态迁移：

| 场景 | 进入状态 | 预期结果 |
|---|---|---|
| 未登录点击订场 | 无 token | 跳转个人中心并提示登录 |
| 场馆接口返回空数组 | isEmptyData = true | 显示空状态，可重新加载 |
| 场馆接口返回 500/502 | dataError = true | 显示错误说明和重试入口 |
| 点击两个可用格子 | roomStatus = a | selectedRooms 增加两个对象，格子变 s |
| 点击已占用格子 | roomStatus = b | 不改变选择 |
| 支付弹窗取消 | pendingOrderId 存在 | 查询待支付订单，显示继续支付/取消 |
| 支付成功但查单延迟 | 本地有辅助标记 | 先给出结果提示，再以订单查询刷新 |
| 从凭证页返回订单列表 | 页面重新显示 | onShow 重新加载订单 |
| 活动报名字段缺失 | 必填字段为空 | 阻止提交并指出字段 |
| 远程图片失败 | @error 触发 | 使用 fallback 或默认图片 |

当前源码没有一组配套的 UniApp 自动化状态测试结果，因此我会把这张表当成下一步测试入口，而不是把“页面能打开”当成完成标准。真正需要补的测试包括：路由参数解析、支付取消后的恢复、支付结果页查单失败、活动重复报名和多个区域同时 loading。

为了让这张清单真正可执行，每次验证至少记录四列：请求路径、输入参数、页面状态、服务端事实。例如“支付弹窗取消”不能只写“页面显示失败”，还要检查 `pendingOrderId` 是否保留、结果页是否再次调用查单、订单详情是否仍然是待支付，以及用户是否可以继续支付或取消订单。

## 7. 面试复盘

面试回答 C 端项目时，我会先用三句话交代主线：用户从 Tab 或首页进入业务页面；页面通过生命周期读取参数、请求数据并维护状态；场馆预约创建订单后，支付结果页通过查单把业务订单 ID 交给凭证页。面试官继续追问时，再从页面状态、接口契约和异常分支展开。

### 页面地图与 UniApp 基础

**Q：这个小程序的页面入口怎么组织？**

A：pages.json 注册所有页面，tabBar.list 声明首页、活动中心、约球和个人中心四个主入口。场馆预约、活动详情、订单列表和凭证页属于通过 uni.navigateTo 进入的普通页面。

**Q：onLoad、onMounted 和 onShow 有什么区别？**

A：onLoad 适合读取路由参数并初始化业务 ID；onMounted 适合组件挂载后的资源加载；onShow 适合页面重新显示时刷新订单、报名或用户状态。

**Q：为什么支付完成后返回活动详情页还要重新查报名状态？**

A：详情页第一次加载时拿到的是一个时间点的快照。支付和报名状态可能在离开页面期间发生变化，所以 onShow 需要重新查询，避免按钮仍然显示为可报名。

**Q：Vue 3 的 ref 和 computed 在这个项目里分别做什么？**

A：ref 保存会变化的原始页面状态，例如 selectedDate、selectedRooms、orderId；computed 根据这些状态派生显示结果，例如约球搜索后的 filteredCardList 或报名字段排序结果。

**Q：UniApp 的 navigateTo 和 switchTab 为什么不能混用？**

A：switchTab 用于切换已经注册在 tabBar 的页面；navigateTo 用于打开普通页面。个人中心和首页是 Tab 页面，确认订单和凭证页是普通页面，调用方式不同。

### 请求封装与页面状态

**Q：为什么要封装 request.js？**

A：它统一处理 BASE_URL、Authorization、loading、HTTP 状态、401 清 token、502 重试和错误提示。页面只关注业务路径、参数和结果状态，避免每个页面重复实现网络基础逻辑。

**Q：needAuth: true 做了什么？**

A：请求工具从 uni.getStorageSync('token') 读取 token，存在时放入 Authorization: Bearer ... 请求头。没有 token 时，页面可以根据业务决定提示登录或继续展示公开数据。

**Q：HTTP 200 是否代表业务一定成功？**

A：不一定。项目的响应里还可能有业务 statusCode、message 和 data。页面需要结合 HTTP 状态和业务对象判断，例如空数组是成功但无数据，订单状态 pending 是成功查询但业务尚未完成。

**Q：为什么空数组不能当成网络错误？**

A：空数组说明请求成功，只是当前筛选条件或日期没有可展示数据；网络错误说明请求没有得到可用响应。两者的用户动作不同，前者可以换日期或场馆，后者应该重试或登录。

**Q：前端筛选和后端筛选怎么区分？**

A：看筛选状态改变后是否重新调用接口。约球搜索的关键词可以由 computed 在内存中过滤；活动中心的一些地区、项目和排序条件会组成请求参数。接口契约应明确每个条件的处理位置。

### 场馆预约与订单

**Q：场馆页为什么要把 session 数组变成矩阵？**

A：UI 是按时间和场地的二维格子展示，后端返回的 session 通常是一维集合。页面构建 timeSlots、venues、sessionMap、roomStatus 和 prices，让 VenueGrid 能按行列渲染和处理点击。

**Q：a、b、u、s 分别是什么？**

A：它们是页面内部的格子状态：a 可选，b 被占用或不可用，u 当前用户已经预订，s 是当前页面暂时选中。s 只说明前端选择，不代表后端已经锁定资源。

**Q：为什么点击场次时要保存 sessionId，不能只保存行列索引？**

A：行列索引只属于当前矩阵，换日期、分页或重新加载后可能失效。sessionId 是后端识别场次的业务 ID，行列索引则只用于当前页面撤销和更新 UI。

**Q：前端显示的价格是不是最终订单金额？**

A：不是。场次选择时的价格只是页面展示和预估，确认页创建订单后读取后端返回的 totalPrice，支付参数也使用后端金额。会员卡、容量规则和价格规则需要由服务端重新判断。

**Q：为什么确认页要先创建订单，再发起支付？**

A：支付需要关联悦动业务订单，订单还要记录场次、用户和金额。先创建订单可以得到业务 orderId，再用它创建支付单；如果用户取消支付，页面可以通过这个订单恢复继续支付或取消。

**Q：会员卡支付为什么不调用 requestPayment？**

A：会员卡抵扣后后端返回零元订单和会员卡信息，前端直接把它作为 membership 结果处理。没有现金支付金额，就不需要打开微信支付弹窗，但订单和会员卡扣次仍然需要服务端完成。

**Q：批量预约怎样处理多个场次？**

A：当前前端先为各场次创建订单，会员卡订单直接归入成功集合，需要现金支付的订单单独收集。需要支付的订单只有一个时走单笔支付，多个时调用批量支付接口。

### 支付结果与凭证

**Q：uni.requestPayment success 后是不是就能把订单改成已支付？**

A：不能。它只代表客户端支付流程返回成功。页面还需要把支付订单 ID 带到结果页，由结果页查询服务端订单；后端还要通过微信通知和自己的业务处理完成最终状态。

**Q：为什么要同时保存 orderId 和 paymentOrderId？**

A：orderId 是悦动业务订单，凭证页通过它查询场馆、场次和参与人；paymentOrderId 是支付侧订单或支付单，结果页用它查询支付状态。两个 ID 的职责不同，混用会导致凭证页查不到业务数据。

**Q：支付结果页为什么有 pending、success、fail 三态？**

A：进入页面时查单还在进行，所以是 pending；服务端返回已支付时是 success；未支付或查单失败且没有辅助信息时是 fail。三态对应不同的图标、提示和按钮。

**Q：本地的 wxPaySuccess_<id> 能不能作为支付凭证？**

A：不能。它只是客户端弹窗返回后的辅助标记，可能帮助页面在服务端查询暂时延迟时给出过渡状态。本地数据可以被清理、过期或只存在于一台设备，最终业务状态仍然应该来自服务端。

**Q：为什么凭证页还要重新请求订单详情？**

A：支付结果页传入的日期、场地和名称是展示上下文，不是完整业务事实。凭证页按 orderId 重新加载订单和关联对象，才能显示当前状态、金额、参与人和退款条件。

**Q：订单列表为什么需要识别活动订单和场馆订单？**

A：两种订单关联的数据不同，活动订单需要 eventId 和活动凭证，场馆订单需要 venueId、sessionIds 和场馆凭证。当前代码优先看 orderType，再兼容 eventRegs、sessionRegs 和历史根级字段。

### 活动、约球和工程复盘

**Q：活动报名为什么要在点击时再次检查容量？**

A：活动列表或详情页的数据可能是之前请求的快照，名额可能在这段时间被其他用户消耗。handleConfirm 再检查 status 和 remainingCapacity，可以减少把已关闭或已满活动提交到后端的情况；最终容量判断仍由后端负责。

**Q：动态报名字段有什么好处？**

A：活动详情返回 registration_fields 后，报名页可以按配置初始化、排序和校验字段，不用为每种活动复制一份页面。它减少了前端页面数量，但要求前后端共同维护字段 ID、类型和校验规则。

**Q：companions 让报名流程增加了什么复杂度？**

A：除了主要报名人，还要维护多个参与人的字段，复用动态字段配置，并对每个人做必填、长度和数值校验。提交时要把它们组织成完整参与人集合，不能只校验第一份表单。

**Q：约球页的筛选为什么拆成多个 ref？**

A：搜索、运动标签、有空位、我加入的、我关注的和我发起的是不同条件，拆开后可以单独修改、清空和组合，列表结果再通过 computed 或请求参数得到。这样比把所有条件塞进一个难以维护的对象更容易追踪。

**Q：个人中心为什么需要多个 loading？**

A：Dashboard 同时加载订单日历、收藏场馆、收藏活动和我的约球。一个接口完成不等于其他区域完成，所以每个区域保留自己的 loading 和 empty 状态，局部失败也不必阻塞整页。

**Q：你会怎样测试这个 C 端交易流程？**

A：先覆盖未登录、空场次、网络失败、重复点击、选择上限、支付取消、支付成功但查单延迟、订单列表返回刷新、活动重复报名和图片加载失败，再检查每个状态是否有用户可执行的下一步。

**Q：这部分项目复盘里你认为还可以改进什么？**

A：一是统一路由参数和订单数据结构，减少 orderType、eventRegs、sessionRegs 的兼容分支；二是把本地缓存明确成辅助状态并加入过期策略；三是为支付取消、查单延迟、重复报名和多区域 loading 增加自动化测试；四是给 onShow 刷新增加请求去重，减少重复加载。

当前 06 的正文已经把 C 端主线从页面入口追到了订单凭证，也把活动报名、约球和个人中心放回了同一套“动作 → 请求 → 状态 → 展示”的框架。下一篇继续进入 B 端管理台，重点会转向运营人员如何配置场馆、场次、活动、订单和权限。
