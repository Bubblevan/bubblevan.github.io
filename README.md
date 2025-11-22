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


### 网页长截图生成

项目提供了自动生成长截图的工具，方便分享到社交媒体。

#### 安装依赖

首先安装 Puppeteer（如果尚未安装）：
```bash
npm install
```

#### 使用方法

**单页面截图：**
```bash
# 基础用法（自动生成输出路径）
npm run screenshot http://localhost:3000/blog

# 指定输出路径
npm run screenshot http://localhost:3000/blog/2025/11/22/cognav ./screenshots/cognav.png

# 截图文档页面
npm run screenshot http://localhost:3000/docs/self-study/ai/rl ./screenshots/rl-docs.png
```

**批量截图：**

1. 编辑 `scripts/screenshot-list.json` 配置要截图的页面列表
2. 运行批量截图命令：
```bash
npm run batch-screenshot
```

#### 注意事项

- 使用前确保 Docusaurus 开发服务器正在运行（`npm run start`），或使用生产环境 URL
- 截图会保存在项目根目录的 `screenshots/` 文件夹中
- 截图支持自动滚动，可以捕获整个页面内容
- 默认使用 2x 设备像素比生成高清截图，使用 `--keep-scale` 可保持原始字体大小

#### 常用选择器

Docusaurus 博客文章常用的容器选择器：
- `article` - 文章容器（推荐）
- `.markdown` - Markdown 内容容器
- `main` - 主内容区域
- `[role="main"]` - 主内容区域（语义化）

示例：
```bash
# 截取文章容器（保持原始字体大小）
npm run screenshot https://bubblevan.github.io/blog/2025/11/22/cognav --selector="article" --keep-scale

# 截取 Markdown 内容区域
npm run screenshot https://bubblevan.github.io/blog/2025/11/22/cognav --selector=".markdown" --keep-scale
```

