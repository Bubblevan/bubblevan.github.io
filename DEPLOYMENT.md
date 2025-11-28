# 部署说明

## 本地开发

### 1. 安装依赖
```bash
npm install
```

### 2. 启动开发服务器
```bash
npm run start
```

### 3. 构建生产版本
```bash
npm run build
```

## GitHub Pages 部署

### 1. 构建项目
```bash
npm run build
```

### 2. 部署到 GitHub Pages
```bash
npm run deploy
```

### 3. 配置 GitHub Pages
1. 进入 GitHub 仓库设置
2. 找到 Pages 选项
3. 选择 Source 为 "Deploy from a branch"
4. 选择 Branch 为 "gh-pages"
5. 保存设置

## 自定义域名

如果需要使用自定义域名：

1. 在 `docusaurus.config.ts` 中修改 `url` 字段
2. 在 GitHub Pages 设置中添加自定义域名
3. 在域名提供商处添加 CNAME 记录

## 环境变量

项目使用以下环境变量：
- `GIT_USER` - GitHub 用户名
- `USE_SSH` - 是否使用 SSH 连接

## 故障排除

### 常见问题

1. **构建失败**
   - 检查 Node.js 版本（需要 >= 18.0）
   - 清除缓存：`npm run clear`

2. **部署失败**
   - 检查 GitHub 权限
   - 确认仓库设置正确

3. **样式问题**
   - 清除浏览器缓存
   - 重新构建项目

## 更新内容

修改内容后：
1. 本地测试：`npm run start`
2. 构建项目：`npm run build`
3. 部署更新：`npm run deploy`
