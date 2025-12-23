---
id: raspberrypi-xiaozhi
title: RaspberryPi 4b 上 部署小智 MCP 服务
weight: 3
---

说实话，前面从头开始手搓一个小智四足桌宠的工作量有点超出我想象的大了，并且弱电焊板子的成果，电路板裸露在外面，我个人感觉作为新年礼物送给小朋友的安全风险有点大，而3D打印一是没有经验，二是不能杜绝安全风险，所以先放一放，闲鱼买了一个成品回来。

如果你不需要小智频繁调用工具生成Action的话，那么开发难度会小很多。暑假的时候宇树的学长学姐被这个小智语音+导航部署在G1上的工作折磨的够呛。

![小智配置概览](/img/raspberrypi-xiaozhi/overview1.png)

可以看到和我们平常调用API请求LLM一样，这里的**人物设定prompt**需要认真改。

然后是**记忆类型**，由于我不想花钱买小智升级功能，所以只有一个记忆体（短期记忆），看演示视频是会存储1000以内对话的记忆。

![语言模型配置](/img/raspberrypi-xiaozhi/language-models.png)

能用的只有一个**qwen3**和一个**deepseek3.1**。

![语音识别配置](/img/raspberrypi-xiaozhi/audio-recognition.png)

**语音识别速度**决定小智会不会在你没说完之前抢答，**语速**和**音调**顾名思义。

![MCP配置](/img/raspberrypi-xiaozhi/mcp.png)

接下来是比较重要的**MCP**，也即我们文章的重心。

首先是[知识库](https://ai.feishu.cn/wiki/QS5ewZHh0iOEI0kdbjncmtY1nFg?from=from_copylink)，现在属于测试期间只能放一个进去，我们这里选择小学英语（因为在撰写文档的同时我妹问我like是不是直接加ing）。其原理我推测跟**RAG**差不多，也可以做一个召回测试。

然后是**MCP**：点击**自定义服务**→**获取MCP接入点**，就能得到一个**wss** 开头的 **WebSocket** 接入点地址。

而小智其实本质上是一个 **"云 - 边" 架构**：
- **端侧设备**是 **"边"**：只负责收语音、发请求、播结果，本身不跑大模型；
- `xiaozhi.me`是 **"云"**：大模型运算、MCP 工具调度都是在云端完成的，端侧设备只是和云端做交互。

比如你需要小智能调用 "随机生成幸运数字" 的工具，就可以写一个 **MCP 工具函数**（`get_lucky_number`），函数里用`random`库生成数字，通过 **MCP 接入点**连到小智后，你问 "帮我生成个 1-100 的幸运数字"，小智就会调用这个工具给你结果。

而这里的这个接入点，是云平台分配的**专属公网地址**（**不能改**）。不是云 / 小智设备连树莓派，而是你的**树莓派 MCP 服务要作为 "客户端"**，**主动连接**这个云的公网 **wss** 地址，相当于把树莓派的工具 **"注册"** 到云端，云端就能调用这些工具了。

因此并不像我一开始想的那样，树莓派要和小智设备在同一局域网，而是**只要能联网，就能直接连这个公网接入点**：

1. 树莓派的 **MCP 服务**→作为**客户端**，主动连接这个`wss://api.xiaozhi.me/mcp/?token=xxx`（**公网地址**）；
2. 云平台识别这个 **token** 对应的智能体，把树莓派的工具加入 **"可调用列表"**；
3. 当小智设备（边侧）发请求到云端，云端会**自动调用**树莓派里的工具，再把结果返回给小智设备。

## 示例代码

以联网搜索为例：

```python
from mcp.client import MCPClient  # 注意是客户端库，不是之前的FastMCP
import logging
import requests

logger = logging.getLogger('mcp_client')
logging.basicConfig(level=logging.INFO)

# 你的云MCP接入点地址（直接用给的wss链接）
MCP_ENDPOINT = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjM3NzM2MCwiYWdlbnRJZCI6MTIzMzYxNCwiZW5kcG9pbnRJZCI6ImFnZW50XzEyMzM2MTQiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzY2NDA3NDY1LCJleHAiOjE3OTc5NjUwNjV9.PCuvcaMVw5lPYksvCVqSFQ1Ll6lysZaA3haB4Xaqnae6VaeGe6jjKfhiU76WSXoQTpaNVxHvSYDRKWwvKlanmw"

# 定义"联网搜索"工具
def web_search(keywords: str) -> dict:
    """用于联网搜索信息，用户问实时内容时调用"""
    try:
        api_key = "你的SerpAPI密钥"
        search_url = f"https://serpapi.com/search?q={keywords}&api_key={api_key}"
        response = requests.get(search_url, timeout=10)
        snippets = [f"{item['title']}：{item['snippet']}" for item in response.json().get("organic_results", [])[:2]]
        return {"success": True, "content": "\n".join(snippets)}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 连接云MCP接入点，并注册工具
if __name__ == "__main__":
    client = MCPClient(endpoint=MCP_ENDPOINT)
    # 把web_search工具注册到云端
    client.register_tool(web_search)
    # 保持连接，等待云端调用
    client.run()
```

这里也有一系列的开源项目如[小智 MCP 集合项目](https://github.com/avxxoo/xiaozhi-mcp)

> **注意**：后续树莓派的配置待更新......