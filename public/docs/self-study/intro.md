# 自学笔记

```mermaid
graph LR
    A[自学笔记] --> B[🤖 AI人工智能]
    A --> C[💻 前端开发]
    A --> D[⚙️ 后端开发]
    A --> E[🗄️ 数据库]
    A --> F[📱 客户端开发]
    A --> G[🤖 具身智能]
    A --> H[🔧 嵌入式系统]
    
    B --> B1[机器学习基础]
    B --> B2[计算机视觉]
    B --> B3[自然语言处理]
    B --> B4[大语言模型]
    B --> B5[强化学习]
    B --> B6[多模态学习]
    B --> B7[图神经网络]
    B --> B8[EGNN]
    B --> B9[图形学]
    
    C --> C1[React]
    C --> C2[Vue.js]
    C --> C3[JavaScript/TypeScript]
    C --> C4[CSS]
    C --> C5[Next.js]
    
    D --> D1[Spring Boot]
    D --> D2[NestJS]
    D --> D3[FastAPI]
    D --> D4[Gin]
    D --> D5[DevOps实践]
    D --> D6[容器化部署]
    D --> D7[K8s集群]
    D --> D8[中间件]
    
    E --> E1[MySQL]
    E --> E2[PostgreSQL]
    E --> E3[MongoDB]
    E --> E4[Milvus]
    E --> E5[ORM框架]
    E --> E6[GORM]
    E --> E7[TypeORM]
    
    F --> F1[UniApp跨平台]
    F --> F2[PyQt桌面应用]
    
    G --> G1[具身智能概述]
    G --> G2[LLM for X]
    G --> G3[视觉语言动作模型]
    G --> G4[视觉语言导航]
    
    H --> H1[嵌入式系统]

    click B1 "./ai/dl" "深度学习笔记"
    click B2 "./ai/cv" "计算机视觉"
    click B3 "./ai/nlp" "自然语言处理"
    click B4 "./ai/llm" "大语言模型"
    click B5 "./ai/rl" "强化学习"
    click B6 "./ai/multimodal" "多模态学习"
    click B7 "./ai/gat" "图神经网络"
    click B8 "./ai/egnn" "EGNN"
    click B9 "./ai/graphics" "图形学"
    
    click C1 "./frontend/react" "React开发"
    click C2 "./frontend/vue" "Vue.js"
    click C3 "./frontend/javascript" "JavaScript/TypeScript"
    click C4 "./frontend/css" "CSS样式"
    click C5 "./frontend/n_xtjs" "Next.js"
    
    click D1 "./backend/springboot" "Spring Boot"
    click D2 "./backend/nestjs" "NestJS"
    click D3 "./backend/fastapi" "FastAPI"
    click D4 "./backend/gin" "Gin框架"
    click D5 "./backend/devops/ci-cd" "DevOps实践"
    click D6 "./backend/devops/docker" "容器化部署"
    click D7 "./backend/devops/k8s" "K8s集群"
    click D8 "./backend/middleware/redis" "中间件"
    
    click E1 "./database/mysql" "MySQL"
    click E2 "./database/postgresql" "PostgreSQL"
    click E3 "./database/mongodb" "MongoDB"
    click E4 "./database/milvus" "向量数据库Milvus"
    click E5 "./database/prisma" "ORM框架"
    click E6 "./database/gorm" "GORM"
    click E7 "./database/typeorm" "TypeORM"
    
    click F1 "./client/uniapp" "UniApp跨平台"
    click F2 "./client/pyqt" "PyQt桌面应用"
    
    click G1 "./embodied/intro" "具身智能概述"
    click G2 "./embodied/llm4x" "LLM for X"
    click G3 "./embodied/vla" "视觉语言动作模型"
    click G4 "./embodied/vln" "视觉语言导航"
    
    click H1 "./embeded/" "嵌入式系统"

    style A fill:#f9f,stroke:#333,stroke-width:4px
    style B fill:#e1f5fe,stroke:#333,stroke-width:2px
    style C fill:#fff3e0,stroke:#333,stroke-width:2px
    style D fill:#f3e5f5,stroke:#333,stroke-width:2px
    style E fill:#e8f5e8,stroke:#333,stroke-width:2px
    style F fill:#fce4ec,stroke:#333,stroke-width:2px
    style G fill:#ffebee,stroke:#333,stroke-width:2px
    style H fill:#f1f8e9,stroke:#333,stroke-width:2px
```