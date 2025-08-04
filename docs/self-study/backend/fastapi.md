# FastAPI 自学笔记

## 学习目标

掌握 FastAPI 框架的核心概念和开发技能，能够使用 FastAPI 构建高性能的 Web API。

## 核心特性

### 高性能
- **基于 Starlette**: 异步 Web 框架
- **Pydantic**: 数据验证和序列化
- **自动文档**: OpenAPI 和 Swagger UI

### 类型提示
- **Python 类型注解**: 完整的类型支持
- **自动验证**: 请求和响应数据验证
- **IDE 支持**: 优秀的开发体验

### 现代化
- **异步支持**: 原生 async/await
- **WebSocket**: 实时通信支持
- **依赖注入**: 灵活的依赖管理

## 学习路径

### 第一阶段：基础语法
1. **基本应用**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="我的 API", version="1.0.0")

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int | None = None

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": "包博文"}

@app.post("/users/")
async def create_user(user: User):
    return user
```

2. **路径参数和查询参数**
```python
from typing import Optional
from fastapi import Query, Path

@app.get("/items/{item_id}")
async def read_item(
    item_id: int = Path(..., title="商品ID", ge=1),
    q: Optional[str] = Query(None, max_length=50),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    return {
        "item_id": item_id,
        "q": q,
        "skip": skip,
        "limit": limit
    }
```

3. **请求体模型**
```python
from pydantic import BaseModel, EmailStr, Field
from typing import List

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    is_active: bool = True

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int
    is_active: bool

    class Config:
        from_attributes = True

@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    # 模拟创建用户
    return UserResponse(
        id=1,
        name=user.name,
        email=user.email,
        age=user.age,
        is_active=user.is_active
    )
```

### 第二阶段：高级特性
1. **依赖注入**
```python
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

2. **数据库集成**
```python
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

3. **中间件和异常处理**
```python
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

### 第三阶段：实战应用
1. **认证和授权**
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
    # 验证用户名和密码
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}
```

2. **WebSocket 支持**
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

## 最佳实践

### 项目结构
```
myapi/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   ├── schemas/
│   ├── api/
│   ├── core/
│   └── utils/
├── tests/
├── requirements.txt
└── README.md
```

### 配置管理
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "FastAPI App"
    database_url: str
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

### 测试
```python
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_create_user():
    user_data = {
        "name": "包博文",
        "email": "test@example.com",
        "age": 25
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    assert response.json()["name"] == user_data["name"]
```

## 学习资源

### 官方文档
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [FastAPI 中文文档](https://fastapi.tiangolo.com/zh/)

### 在线课程
- FastAPI 官方教程
- 慕课网 FastAPI 课程
- 极客时间 FastAPI 专栏

### 实践项目
- RESTful API 开发
- 微服务架构
- 实时聊天应用

## 学习心得

### 学习建议
1. **理解异步**: 深入理解异步编程
2. **类型系统**: 充分利用类型提示
3. **文档驱动**: 重视 API 文档
4. **性能优化**: 关注性能指标

### 常见问题
1. **异步编程**: 理解 async/await
2. **数据库集成**: 选择合适的 ORM
3. **认证授权**: 实现安全的认证机制
4. **部署运维**: 生产环境部署 