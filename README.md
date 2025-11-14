# Bubblevan
### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run start
```

### 构建生产版本
```bash
npm run build
```

### Python 后端（可选）
```bash
python -m venv .venv
.venv\Scripts\activate  # macOS/Linux 使用 source .venv/bin/activate
pip install -r blog/backend/requirements.txt
python blog/backend/app.py
```

> 如果缺少某些科研检索相关的可选依赖（例如 `scholarly`、`arxiv` 等），FastAPI 应用仍可启动，但部分任务会退化为回退策略。请按需在 `.env` 中配置 `DEEPSEEK_API_KEY`、`SERPAPI_KEY` 等密钥。

