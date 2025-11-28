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

项目提供了两个截图工具，方便生成高质量的长截图用于分享到社交媒体。

#### 安装依赖

首先确保已安装 Puppeteer（如果尚未安装）：
```bash
npm install
```

如果遇到 Chrome 浏览器未找到的错误，运行：
```bash
npx puppeteer browsers install chrome
```

---

## 功能一：单页面截图工具 (`screenshot.js`)

用于对单个网页进行截图，支持输出完整长图或指定容器区域。

### 使用方法

**基础用法：**
```bash
# 自动生成输出路径（保存到 screenshots/ 目录）
npm run screenshot http://localhost:3000/blog

# 指定输出路径
npm run screenshot http://localhost:3000/blog/2025/11/22/cognav ./screenshots/cognav.png

# 截图文档页面
npm run screenshot http://localhost:3000/docs/self-study/ai/rl ./screenshots/rl-docs.png
```

**高级选项：**
```bash
# 截取指定容器（排除底部 footer）
npm run screenshot http://localhost:3000/blog/2025/11/22/cognav --selector="article" --keep-scale

# 截取 Markdown 内容区域
npm run screenshot http://localhost:3000/blog/2025/11/22/cognav --selector=".markdown" --keep-scale

# 添加自定义边距（默认 20px）
npm run screenshot http://localhost:3000/blog/2025/11/22/cognav --padding=30

# 禁用边距
npm run screenshot http://localhost:3000/blog/2025/11/22/cognav --padding=0
```

### 功能特点

- ✅ **自动排除底部容器**：博客文章页面会自动使用 `article` 选择器，排除底部 footer（个人资料、科研经历、联系方式等）
- ✅ **完整长图**：支持截取整个页面，自动滚动确保懒加载内容都被捕获
- ✅ **指定容器**：可通过 `--selector` 参数指定要截取的容器（如文章、侧边栏等）
- ✅ **高清截图**：默认使用 2x 设备像素比，使用 `--keep-scale` 可保持原始字体大小
- ✅ **自动滚动**：自动滚动页面，确保所有内容都已加载

### 命令行选项

- `--selector=<CSS选择器>`：指定要截取的容器 CSS 选择器（如 `article`、`.markdown`）
- `--keep-scale`：保持原始字体大小，不做缩放
- `--padding=<像素>`：添加白色左右边距（默认 20px，设为 0 禁用）

### 常用选择器

Docusaurus 博客文章常用的容器选择器：
- `article` - 文章容器（推荐，自动排除 footer）
- `.markdown` - Markdown 内容容器
- `main` - 主内容区域
- `[role="main"]` - 主内容区域（语义化）

---

## 功能二：分页截图工具 (`batch-screenshot.js`)

将一个长页面按视口大小分成多张截图，每张图刚好填满屏幕，依次滚动直到文章结束。自动排除底部容器。

### 使用方法

```bash
# 基础用法 - 将一个页面分成多张视口大小的截图
npm run batch-screenshot http://localhost:3000/blog/3d-understand

# 使用相对路径
npm run batch-screenshot /blog/3d-understand

# 自定义输出目录
npm run batch-screenshot /blog/3d-understand --output-dir=./my-screenshots

# 自定义边距
npm run batch-screenshot /blog/3d-understand --padding=30

# 自定义视口大小
npm run batch-screenshot /blog/3d-understand --width=1920 --height=1080
```

### 工作原理

1. 访问指定 URL
2. 自动检测博客文章页面，使用 `article` 选择器排除底部容器
3. 计算页面总高度，按视口高度分成多页
4. 依次滚动页面，每页截取视口大小的截图
5. 生成多张图片：`blog-3d-understand-page-1.png`, `blog-3d-understand-page-2.png`, ...
6. 自动为每张图添加白色左右边距

### 命令行选项

- `--base-url=<url>`：基础 URL（默认：`http://localhost:3000`）
- `--output-dir=<dir>`：输出目录（默认：`./screenshots`）
- `--padding=<像素>`：白色左右边距（默认：20，设为 0 禁用）
- `--selector=<选择器>`：容器选择器（如 `article`，博客文章会自动使用）
- `--keep-scale`：保持原始字体大小
- `--width=<像素>`：视口宽度（默认：1920）
- `--height=<像素>`：视口高度（默认：1080）

### 功能特点

- ✅ **分页截图**：将一个长页面分成多张视口大小的截图
- ✅ **自动排除底部容器**：博客文章页面自动使用 `article` 选择器
- ✅ **智能分页**：根据页面高度自动计算需要多少张截图
- ✅ **自动添加边距**：每张截图自动添加白色左右边距
- ✅ **进度显示**：显示当前截图进度（第 X/总数 张）
- ✅ **文件命名**：自动生成 `page-1.png`, `page-2.png` 等文件名

---

## 注意事项

- 使用前确保 Docusaurus 开发服务器正在运行（`npm run start`），或使用生产环境 URL
- 截图会保存在项目根目录的 `screenshots/` 文件夹中（可自定义）
- 博客文章页面会自动排除底部 footer 容器（个人资料、科研经历、联系方式等）
- 如需截取完整页面（包括 footer），请使用 `--selector` 参数指定其他容器，或不使用选择器

## 使用示例

### 单页面截图示例

```bash
# 截取博客文章长图（自动排除 footer，默认 20px 边距）
npm run screenshot http://localhost:3000/blog/3d-understand

# 截取博客文章长图，指定输出路径
npm run screenshot http://localhost:3000/blog/3d-understand ./screenshots/3d-understand.png

# 截取博客文章长图，自定义边距
npm run screenshot http://localhost:3000/blog/3d-understand --padding=30

# 截取指定容器并保持原始大小
npm run screenshot http://localhost:3000/blog/3d-understand --selector="article" --keep-scale
```

### 分页截图示例

```bash
# 将一个博客文章分成多张视口大小的截图
npm run batch-screenshot http://localhost:3000/blog/3d-understand

# 使用相对路径
npm run batch-screenshot /blog/3d-understand

# 自定义边距和输出目录
npm run batch-screenshot /blog/3d-understand --padding=30 --output-dir=./my-screenshots

# 自定义视口大小
npm run batch-screenshot /blog/3d-understand --width=1920 --height=1080
```

