#!/usr/bin/env node
/**
 * Docusaurus 批量网页长截图生成工具
 * 
 * 使用方法:
 *   npm run batch-screenshot
 *   或
 *   node scripts/batch-screenshot.js
 * 
 * 默认截图列表在 scripts/screenshot-list.json 中配置
 */

const { takeScreenshot } = require('./screenshot');
const path = require('path');
const fs = require('fs');

async function batchScreenshot(configPath) {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  const { baseUrl = 'http://localhost:3000', urls, outputDir = './screenshots' } = config;

  // 确保输出目录存在
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log(`开始批量截图，共 ${urls.length} 个页面...\n`);

  for (let i = 0; i < urls.length; i++) {
    const urlConfig = urls[i];
    const url = typeof urlConfig === 'string' ? urlConfig : urlConfig.url;
    const outputPath = typeof urlConfig === 'string' 
      ? path.join(outputDir, generateFilename(url))
      : urlConfig.output || path.join(outputDir, generateFilename(url));

    const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`;

    console.log(`[${i + 1}/${urls.length}] ${fullUrl}`);
    try {
      await takeScreenshot(fullUrl, outputPath, urlConfig.options || {});
      console.log('');
    } catch (error) {
      console.error(`❌ 截图失败: ${error.message}\n`);
    }
  }

  console.log('✅ 批量截图完成！');
}

function generateFilename(url) {
  const urlObj = new URL(url.startsWith('http') ? url : `http://localhost:3000${url}`);
  const pathname = urlObj.pathname.replace(/^\//, '').replace(/\/$/, '') || 'index';
  return pathname.replace(/\//g, '-') + '.png';
}

// 命令行参数处理
async function main() {
  const args = process.argv.slice(2);
  const configPath = args[0] || path.join(__dirname, 'screenshot-list.json');

  if (!fs.existsSync(configPath)) {
    console.error(`❌ 配置文件不存在: ${configPath}`);
    console.log('');
    console.log('请创建配置文件，或使用:');
    console.log('  node scripts/batch-screenshot.js <config-path>');
    process.exit(1);
  }

  try {
    await batchScreenshot(configPath);
    process.exit(0);
  } catch (error) {
    console.error('批量截图失败:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { batchScreenshot };

