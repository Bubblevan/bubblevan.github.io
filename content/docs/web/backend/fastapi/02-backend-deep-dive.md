import CollapsibleBlock from '@site/src/components/CollapsibleBlock';

## 1. 初始化项目环境

### 1.1 创建工作目录与虚拟环境

### 1.2 安装依赖

```powershell
pip install fastapi uvicorn[standard] httpx python-dotenv
```

在项目根目录下创建 `requirements.txt`，便于团队成员同步环境：

```plaintext
fastapi
uvicorn[standard]
httpx
python-dotenv
```

## 2. 准备配置与项目结构

1. 新建目录结构：

   ```
   ├── backend/
   │   ├── app.py
   │   └── __init__.py
   ├── .env.example
   └── requirements.txt
   ```

2. 在 `backend/` 目录中放置 FastAPI 应用；`__init__.py` 可以暂时留空。

3. 将敏感配置写入 `.env`（不提交到 Git）：

   ```plaintext
   DIFY_API_KEY=your_dify_api_key_here
   DIFY_BASE_URL=https://api.dify.ai/v1
   ```

   然后复制一份到仓库中的 `env.example`，以便读者了解必填项。

## 3. 创建 FastAPI 实例与中间件

核心应用入口位于 `app.py`，创建 FastAPI 实例并加上所需中间件：

```app.py
app = FastAPI(
    title="学习助手API",
    description="基于Dify的智能学习助手，支持ChatNIO集成",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

<CollapsibleBlock title="FastAPI 元数据与 CORS 中间件详解" defaultExpanded={false}>

- **`title` (`学习助手API`)**：决定 Swagger UI 顶部显示的名称，也会写入自动生成的 OpenAPI 文档。保持语义化命名有助于团队识别环境（例如可在测试环境加 `-staging` 后缀）。
- **`description`**：作为接口文档的项目简介；在团队协作中，简介里可以列出支持的主要能力或依赖，以免使用者误解服务定位。
- **`version` (`1.0.0`)**：用于接口版本管理。升级接口时，可结合语义化版本控制表达兼容性变化；在监控或健康检查中也能快速确认部署版本。
- **`allow_origins=["*"]`**：允许任意来源的前端访问，适合本地开发或内网调试。上线后务必改成具体域名列表，防止被非授权站点调用。
- **`allow_credentials=True`**：保持浏览器能在跨域请求中携带 Cookie/认证信息；如果后端只处理匿名请求，可以关闭以降低风险。
- **`allow_methods=["*"]` 与 `allow_headers=["*"]`**：默认放开所有 HTTP 方法与头信息，避免调试阶段频繁遇到预检失败；生产环境建议改成 `["GET","POST"]` 等最小集合，并只允许必要的自定义头。
- **安全建议**：在生产配置中结合环境变量或独立配置文件控制 CORS 列表，避免代码提交时泄露实际域名；同时配合 API 网关或 WAF 做进一步访问控制。
</CollapsibleBlock>

## 4. 全局配置与数据模型

利用环境变量保存 Dify 的访问凭证，同时定义本项目会用到的 Pydantic 数据模型：

```app.py
# 配置
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")

class ChatMessage(BaseModel):
    message: str
    user_id: str = "default"
    conversation_id: Optional[str] = None
    model: str = "learning-assistant"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class LearningRequest(BaseModel):
    """学习相关请求"""
    question: str
    subject: Optional[str] = None  # 学科：math, physics, chemistry, etc.
    difficulty: Optional[str] = "medium"  # easy, medium, hard
    user_level: Optional[str] = "intermediate"  # beginner, intermediate, advanced
    conversation_id: Optional[str] = None
```

- **默认参数**：`ChatMessage` 预设模型 ID、温度等，让前端即开即用。
- **场景化建模**：`LearningRequest` 聚焦学习问答，覆盖学科、难度、用户水平等维度。

## 5. 封装 Dify 客户端

`DifyClient` 是后端的核心，它负责与 Dify 通信、补齐工作流所需的上下文，并处理重试逻辑。

```app.py
class DifyClient:
    def __init__(self):
        self.api_key = DIFY_API_KEY
        self.base_url = DIFY_BASE_URL
    
    async def send_message(self, message: str, user_id: str = "default", 
                          conversation_id: Optional[str] = None, 
                          inputs: Dict[str, Any] = None):
        """发送消息到Dify"""
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Dify API Key未配置")
        
        url = f"{self.base_url}/chat-messages"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 为DeepResearch工作流提供必需的输入参数
        research_inputs = inputs or {}
        if "Research_Theme" not in research_inputs:
            # 使用NER从消息中提取研究主题
            research_theme = extract_research_theme(message)
            research_inputs["Research_Theme"] = research_theme
            print(f"[NER] 提取的研究主题: {research_theme}")

        payload = {
            "inputs": research_inputs,
            "query": message,
            "response_mode": "blocking",
            "user": user_id,
            "files": []
        }
        
        print(f"[DIFY] 发送的请求参数: {payload}")  # 打印完整请求参数
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        # 添加重试机制
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                print(f"[DIFY] 开始请求 (尝试 {attempt + 1}/{max_retries}): {message[:50]}...")
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    end_time = time.time()
                    print(f"[DIFY] 请求完成，耗时: {(end_time - start_time)*1000:.2f}ms")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"[DIFY] 原始响应: {data}")  # 打印完整响应
                        
                        # 检查Dify API是否返回错误
                        if "error" in data:
                            error_msg = data.get("error", {}).get("message", "未知错误")
                            print(f"[DIFY] API错误: {error_msg}")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Dify API错误: {error_msg}"
                            )
                        elif "answer" not in data:
                            print(f"[DIFY] 响应格式错误: {data}")
                            raise HTTPException(
                                status_code=500,
                                detail="Dify API响应格式错误"
                            )
                        elif not data.get("answer"):
                            print(f"[DIFY] 警告: Dify返回空答案")
                            # 不抛出异常，但记录警告
                        
                        return {
                            "answer": data.get("answer", "未收到回复"),
                            "conversation_id": data.get("conversation_id"),
                            "message_id": data.get("message_id"),
                            "metadata": data.get("metadata", {})
                        }
                    else:
                        error_text = response.text
                        print(f"[DIFY] HTTP错误 {response.status_code}: {error_text}")
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Dify API错误: {error_text}"
                        )
                        
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"[DIFY] 连接失败，{wait_time}秒后重试: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"[DIFY] 所有重试失败: {e}")
                    raise HTTPException(status_code=503, detail="无法连接到Dify服务")
```

- **NER 主题抽取**：`extract_research_theme` 在缺省时自动填充 `Research_Theme`，确保工作流变量完整。
- **异步请求**：`httpx.AsyncClient` + `async/await` 保持高并发性能。
- **指数退避**：对网络波动更加友好，最后一次失败才抛出异常。

`DifyClient` 还提供 `get_conversation_history`，用于在 ChatNIO 中回放历史记录：

```app.py
    async def get_conversation_history(self, conversation_id: str):
        """获取对话历史"""
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Dify API Key未配置")
        
        url = f"{self.base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        params = {
            "conversation_id": conversation_id,
            "first_id": "",
            "limit": 20
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"获取对话历史失败: {response.text}"
                    )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")
```

## 6. 编排 API 端点

服务端暴露了一组围绕 ChatNIO 和学习助手的 REST API。我们按功能分层理解。

### 6.1 基础健康检查

```app.py
@app.get("/")
async def root():
    return {"message": "学习助手API服务运行中", "status": "healthy"}

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "learning-assistant-api",
        "version": "1.0.0"
    }
```

- `/` 提供轻量级握手信息。
- `/health` 返回时间戳与版本号，便于监控系统拉取。

### 6.2 聊天主流程

```app.py
@app.post("/chat")
async def chat_direct(chat_message: ChatMessage):
    """聊天接口 - 直接匹配ChatNIO请求路径"""
    try:
        result = await dify_client.send_message(
            chat_message.message, 
            chat_message.user_id,
            chat_message.conversation_id
        )
        
        return {
            "success": True,
            "message": "",
            "data": {
                "message": result["answer"],
                "keyword": "学习助手",
                "tokens": len(result["answer"]),
                "quota": 0,
                "conversation_id": result["conversation_id"],
                "message_id": result["message_id"]
            }
        }
        
    except HTTPException as e:
        return {
            "success": False,
            "message": e.detail,
            "data": None
        }
```

- 直接复用 `ChatMessage`，返回结构完全对齐 ChatNIO 预期。
- `/api/chat` 只是同一逻辑的别名，保证历史兼容。

### 6.3 学习场景增强

```app.py
@app.post("/api/learning/ask")
async def ask_learning_question(request: LearningRequest):
    """学习问题解答接口"""
    try:
        # 构建学习上下文
        context_message = f"""
        学科: {request.subject or '通用'}
        难度: {request.difficulty}
        用户水平: {request.user_level}
        
        问题: {request.question}
        
        请作为学习助手，提供详细、易懂的解答。
        """
        
        result = await dify_client.send_message(
            context_message,
            f"user_{request.user_level}",
            request.conversation_id,
            inputs={
                "Research_Theme": request.question,  # 使用问题作为研究主题
                "subject": request.subject,
                "difficulty": request.difficulty,
                "user_level": request.user_level
            }
        )
        
        return {
            "success": True,
            "message": "",
            "data": {
                "answer": result["answer"],
                "conversation_id": result["conversation_id"],
                "subject": request.subject,
                "difficulty": request.difficulty,
                "metadata": result["metadata"]
            }
        }
```

- 通过格式化上下文，让 LLM 精准理解用户水平。
- `inputs` 同步传入 Dify 工作流，维持变量一致性。

`/api/learning/study-plan` 则输出多学科学习计划，复用同一 `send_message` 通道。

### 6.4 模型与对话管理

```app.py
@app.get("/api/models")
async def get_models():
    """获取可用模型列表 - ChatNIO需要这个接口"""
    return {
        "success": True,
        "message": "",
        "data": [
            {
                "id": "learning-assistant",
                "name": "学习助手",
                "description": "基于Dify的智能学习助手",
                "provider": "dify",
                "enabled": True
            }
        ]
    }

@app.post("/api/conversation")
async def create_conversation(request: Request):
    """创建对话 - ChatNIO需要"""
    return {
        "success": True,
        "message": "",
        "data": {
            "id": f"conv_{os.urandom(4).hex()}",
            "name": "新对话",
            "message": [],
            "model": "learning-assistant"
        }
    }
```

- ChatNIO 在初始化时会先获取模型列表、创建对话 ID，然后再调用聊天接口。
- `/api/conversation/{conversation_id}` 会走 `get_conversation_history`，把 Dify 返回的历史消息原样回传。

## 7. 依赖注入与身份校验

走到这里，我们已经有了一个能跑起来的学习助手 API，但要想在真实环境中上线，还得考虑「谁」在调用接口。FastAPI 的依赖注入（Dependency Injection, DI）机制就像给服务加上一层“入口守卫”，从而在不破坏核心业务代码的前提下，完成认证与授权。

```app.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # 验证 token 并返回用户信息
    if token == "invalid":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return {"user_id": 1, "name": "包博文"}

@app.get("/me/")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
```

- **入口守卫**：`HTTPBearer` 负责解析来自前端的 `Authorization: Bearer xxx`，我们只需要专注 `token` 的校验逻辑。
- **面向接口编程**：任何需要当前用户信息的端点，都可以通过 `Depends(get_current_user)` 注入，避免在每个路由里重复粘贴验证代码。
- **扩展性**：将来接入 JWT、OAuth2 或者自研 SSO，只要调整 `get_current_user` 即可，业务端点无须改动。

## 8. 数据持久化与 SQLAlchemy 整合

有了用户体系，下一步自然是落地数据。FastAPI 与 SQLAlchemy 是常规搭档，下面这段代码展示了最小可用配置，方便你在实验环境中迅速验证数据流。

```app.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        name=user.name,
        email=user.email,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```

- **轻量起步**：`sqlite` 让我们免去部署数据库的负担，适合 demo 或集成测试。部署时可以无缝切换到 PostgreSQL/MySQL。
- **会话生命周期**：`get_db` 利用 `yield` 在请求结束后自动释放连接，避免连接泄露。
- **模型收口**：定义 `UserResponse`、`UserCreate` 等 Pydantic 模型，既能校验入参，又能控制返回字段，保持 API 的契约清晰。

## 9. 中间件与全局异常处理

当 API 稳步成长，观测性与错误处理就像是给汽车装上仪表盘。通过自定义中间件与异常处理器，我们可以在一处集中记录耗时、拦截错误，并输出一致的响应格式。

```app.py
from fastapi import Request
from fastapi.responses import JSONResponse
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "status_code": exc.status_code}
    )
```

- **性能洞察**：`X-Process-Time` 头部能快速告诉你哪条请求慢了，结合日志平台即可对症下药。
- **统一返回格式**：异常处理器避免了「哪个接口返回了奇怪字段」的尴尬，前端可放心解析。
- **扩展思路**：在企业级项目中，可以继续叠加链路追踪 ID、请求日志、告警埋点，让系统运行状况一目了然。

最后，文件尾部提供 `uvicorn` 启动入口，方便在开发环境直接运行。
