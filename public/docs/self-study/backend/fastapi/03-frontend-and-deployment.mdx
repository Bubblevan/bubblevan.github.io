
## 1. 前端集成：ChatNIO

[ChatNIO](https://github.com/Deeptrain-Community/chatnio) 是一个 Go 写的开源 WebUI。它支持通过标准 REST 接口与大模型后端通信，非常适合与我们在前面构建的 FastAPI 服务对接。

**集成关键点**：

- **契约对齐**：后端 `ChatMessage`、`LearningRequest` Pydantic 模型已经定义了字段，ChatNIO 只需按以下结构向 `/api/chat` 发送请求：

  ```json
  {
    "message": "请用高中生能理解的方式解释麦克斯韦方程组",
    "user_id": "demo-user",
    "conversation_id": null
  }
  ```

  FastAPI 会调用 `DifyClient.send_message`，透传到 Dify Deep Research 工作流并返回格式化答复。

- **路由映射**：`/chat` 与 `/api/chat` 共用一套业务逻辑，ChatNIO 默认使用后者。初始化时还会请求 `/api/models`、`/api/conversation`，这些端点已在后端实现，可返回模型列表与新对话 ID。
- **会话管理**：ChatNIO 会在后续消息中携带 `conversation_id`。FastAPI 会把它提交给 Dify 并允许 `/api/conversation/{conversation_id}` 读取历史消息，实现 Chat 回放。
- **健康监控**：`/`、`/health` 提供基础握手，适合配置在 ChatNIO 的启动脚本或反向代理健康检查。
- **返回模式**：当前实现采用一次性阻塞返回（`response_mode="blocking"`）。若改为流式 SSE，可参考 FastAPI 的 `StreamingResponse`，同时在 ChatNIO 中启用流式渲染。

## 2. 端到端运行指南

### 步骤一：准备工作

**获取 Dify API 密钥**：

- 登录 Dify 账户。
- 进入 **设置 > API 密钥**，创建一个新的 API 密钥并复制它。
- 同时，记下 Dify API 基础 URL (例如 `https://api.dify.ai/v1`)。

### 步骤二：启动后端服务 (FastAPI)

1. **进入后端目录**，创建虚拟环境并安装依赖：


2. **配置环境变量**：复制 `.env.example` 为 `.env`，填入 Dify 凭证。

   ```text
   DIFY_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   DIFY_BASE_URL=https://api.dify.ai/v1
   ```

3. **启动服务**：开发建议使用 `uvicorn`，便于观察 `DifyClient` 的调试日志。

   ```powershell
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

### 步骤三：启动前端界面 (ChatNIO)

1. **进入 ChatNIO 工程目录**：

   ```powershell
   cd frontend/chatnio
   ```

2. **配置 `.env`**：指向 FastAPI 服务端点，并设定默认模型。

   ```text
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   NEXT_PUBLIC_EDGE_URL=http://localhost:8000/api

   NEXT_PUBLIC_SYSTEM_NAME=学习助手
   NEXT_PUBLIC_ALLOW_REGISTER=false
   NEXT_PUBLIC_ALLOW_PASSWORD_CHANGE=false

   NEXT_PUBLIC_DEFAULT_MODEL=learning-assistant
   ```

3. **安装依赖并启动**：

   ```powershell
   go mod tidy
   go run main.go
   ```

   首次启动会请求后端的 `/api/models`，若能返回 `learning-assistant`，说明前后端契约已打通。

![ChatNIO 后端启动](/img/fastapi/backendGO.png)

### 步骤四：开始使用

完成以上步骤后，就可以在 ChatNIO 界面中与智能学习助手进行对话了，此时后端遵循一个开源的Deep Research工作流。

![ChatNIO 界面展示](/img/fastapi/chatnio.png)



## 启动与本地调试

### 运行服务

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- `--reload` 能在保存时自动重启，适合开发阶段。
- 终端会出现 `[DIFY]`、`[NER]` 等调试日志，便于观察请求耗时与主题抽取情况。
- 若部署到生产，请移除 `--reload`，改用 `gunicorn` + `uvicorn.workers.UvicornWorker`，并通过环境变量配置真实域名和密钥。

### 验证接口

1. 访问 `http://127.0.0.1:8000/docs`，确认 `/chat`、`/api/learning/ask`、`/api/models` 等端点已注册。
2. 使用 `curl` 或 `httpie` 调用 `/api/chat`，确保基础对话流程正常：

   ```powershell
   curl -X POST http://127.0.0.1:8000/api/chat ^
     -H "Content-Type: application/json" ^
     -d "{\"message\":\"如何用积分求解函数 x^2 的面积？\",\"user_id\":\"demo-user\"}"
   ```

3. 测试 `/api/learning/ask`，检查学习上下文字段是否被传入 Dify：

   ```powershell
   curl -X POST http://127.0.0.1:8000/api/learning/ask ^
     -H "Content-Type: application/json" ^
     -d "{\"question\":\"解释热力学第二定律\",\"subject\":\"physics\",\"difficulty\":\"hard\",\"user_level\":\"advanced\"}"
   ```

   返回体中的 `metadata` 字段会包含 Workflow 细节，便于调试。
4. 若缺少密钥或网络异常，FastAPI 会抛出 500 并输出具体错误，日志中也会记录重试情况。



### 第三阶段：实战应用

**认证与配额控制**：当项目需要对 ChatNIO 的访问做权限管理时，可以在 FastAPI 上接入 OAuth2。下面的示例利用 `OAuth2PasswordBearer` 和 JWT 生成访问令牌，你可以替换成真实的用户校验逻辑或对接企业统一认证。

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # TODO: 替换为真实的账号体系
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}
```

**实时推送**：如果希望在前端显示 Dify 工作流的进度或任务状态，可以使用 WebSocket 与客户端保持长连接。

```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
```

### 配置管理

将 Dify API 密钥、数据库连接等敏感信息放入 `.env`，通过 `pydantic-settings` 统一加载，可避免散落在代码中的硬编码。

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "学习助手API"
    database_url: str | None = None
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

### 测试

利用 `TestClient` 可以在不启动服务器的情况下验证接口契约，以下测试覆盖了健康检查与学习问答接口。

```python
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "学习助手API服务运行中",
        "status": "healthy"
    }

@pytest.mark.asyncio
async def test_learning_endpoint(monkeypatch):
    async def mock_send_message(*_args, **_kwargs):
        return {"answer": "OK", "conversation_id": "conv_1", "metadata": {}}
    monkeypatch.setattr(dify_client, "send_message", mock_send_message)

    payload = {"question": "测试题目", "subject": "math"}
    response = client.post("/api/learning/ask", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["answer"] == "OK"
```

## 3. 总结与展望

这个项目本来是我帮朋友写来去打华为某嵌入开发板比赛的，一开始需求是只用对接一个webui，后面发现连后端都没有要自己搓，再后来原来连Workflow和主题都还没定，等我写完距离报名结束只剩下一个晚上了，然后他大手一挥不打了xs

后面还要调docker之类部署到开发板上过于麻烦，这里就不赘述了。