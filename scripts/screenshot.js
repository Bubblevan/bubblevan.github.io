#!/usr/bin/env node
/**
 * Docusaurus 网页长截图生成工具
 * 
 * 使用方法:
 *   npm run screenshot <url> [output-path]
 *   或
 *   node scripts/screenshot.js <url> [output-path]
 * 
 * 示例:
 *   npm run screenshot http://localhost:3000/blog
 *   npm run screenshot http://localhost:3000/docs/intro ./screenshots/intro.png
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function takeScreenshot(url, outputPath, options = {}) {
  const {
    width = 1920,
    height = 1080,
    fullPage = true,
    waitUntil = 'networkidle2',
    delay = 1000,
    quality = 90,
    selector = null, // CSS 选择器，用于指定容器
    keepOriginalScale = false, // 是否保持原始字体大小（不缩放）
  } = options;

  console.log(`正在启动浏览器...`);
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    
    // 设置视口大小
    // 如果 keepOriginalScale 为 true，使用 deviceScaleFactor: 1 保持原始大小
    await page.setViewport({
      width,
      height,
      deviceScaleFactor: keepOriginalScale ? 1 : 2, // 保持原始大小或提高清晰度
    });

    console.log(`正在访问: ${url}`);
    await page.goto(url, {
      waitUntil,
      timeout: 60000, // 60秒超时
    });

    // 等待额外的延迟，确保所有动态内容加载完成
    if (delay > 0) {
      console.log(`等待 ${delay}ms 以确保内容完全加载...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }

    // 如果需要滚动页面，等待滚动完成
    if (fullPage) {
      await autoScroll(page);
    }

    // 确保输出目录存在
    const outputDir = path.dirname(outputPath);
    if (outputDir && !fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    console.log(`正在生成截图: ${outputPath}`);
    
    // 根据文件扩展名确定截图类型
    const ext = path.extname(outputPath).toLowerCase();
    const screenshotType = ext === '.jpg' || ext === '.jpeg' ? 'jpeg' : 'png';
    
    let screenshotOptions = {
      path: outputPath,
      type: screenshotType,
    };
    
    // 只有 JPEG 格式才支持 quality 参数
    if (screenshotType === 'jpeg') {
      screenshotOptions.quality = quality;
    }

    // 如果指定了容器选择器，截取该容器
    if (selector) {
      console.log(`截取容器: ${selector}`);
      const element = await page.$(selector);
      if (!element) {
        throw new Error(`未找到选择器 "${selector}" 对应的元素`);
      }
      
      // 如果选择器指定了，截取该元素（会自动截取到元素结束）
      screenshotOptions = {
        ...screenshotOptions,
        fullPage: false,
      };
      
      await element.screenshot(screenshotOptions);
    } else {
      // 截取整个页面或视口
      screenshotOptions = {
        ...screenshotOptions,
        fullPage,
      };
      await page.screenshot(screenshotOptions);
    }

    console.log(`✅ 截图已保存: ${outputPath}`);
    
    // 获取图片信息
    const stats = fs.statSync(outputPath);
    const fileSizeInMB = (stats.size / (1024 * 1024)).toFixed(2);
    console.log(`📊 文件大小: ${fileSizeInMB} MB`);
    
  } catch (error) {
    console.error('❌ 截图失败:', error.message);
    throw error;
  } finally {
    await browser.close();
  }
}

/**
 * 自动滚动页面，确保懒加载的内容都被加载
 */
async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let totalHeight = 0;
      const distance = 100;
      const timer = setInterval(() => {
        const scrollHeight = document.body.scrollHeight;
        window.scrollBy(0, distance);
        totalHeight += distance;

        if (totalHeight >= scrollHeight) {
          clearInterval(timer);
          // 滚动回顶部
          window.scrollTo(0, 0);
          resolve();
        }
      }, 100);
    });
  });
}

// 命令行参数处理
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('❌ 错误: 请提供 URL');
    console.log('');
    console.log('使用方法:');
    console.log('  npm run screenshot <url> [output-path] [--selector=<css选择器>] [--keep-scale]');
    console.log('');
    console.log('选项:');
    console.log('  --selector=<选择器>  指定要截取的容器 CSS 选择器（如文章容器）');
    console.log('  --keep-scale        保持原始字体大小，不做缩放');
    console.log('');
    console.log('示例:');
    console.log('  # 本地开发环境');
    console.log('  npm run screenshot http://localhost:3000/blog');
    console.log('  npm run screenshot http://localhost:3000/blog/2025/11/22/cognav');
    console.log('');
    console.log('  # 生产环境');
    console.log('  npm run screenshot https://bubblevan.github.io/blog/2025/11/22/cognav');
    console.log('');
    console.log('  # 截取文章容器（保持原始大小）');
    console.log('  npm run screenshot https://bubblevan.github.io/blog/2025/11/22/cognav --selector="article" --keep-scale');
    console.log('  npm run screenshot https://bubblevan.github.io/blog/2025/11/22/cognav --selector=".markdown" --keep-scale');
    console.log('  npm run screenshot https://bubblevan.github.io/blog/2025/11/22/cognav ./screenshots/cognav.png --selector="article" --keep-scale');
    process.exit(1);
  }

  const url = args[0];
  
  // 解析选项参数
  let selector = null;
  let keepOriginalScale = false;
  let outputPath = null;
  
  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--selector=')) {
      selector = arg.split('=')[1];
    } else if (arg === '--keep-scale') {
      keepOriginalScale = true;
    } else if (!arg.startsWith('--')) {
      // 第一个非选项参数作为输出路径
      outputPath = arg;
    }
  }
  
  // 如果没有提供输出路径，根据 URL 自动生成
  if (!outputPath) {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname.replace(/^\//, '').replace(/\/$/, '') || 'index';
    const filename = pathname.replace(/\//g, '-') + '.png';
    outputPath = path.join(process.cwd(), 'screenshots', filename);
  }

  // 如果输出路径是相对路径，转换为绝对路径
  if (!path.isAbsolute(outputPath)) {
    outputPath = path.join(process.cwd(), outputPath);
  }

  try {
    await takeScreenshot(url, outputPath, {
      selector,
      keepOriginalScale,
    });
    process.exit(0);
  } catch (error) {
    console.error('截图生成失败:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { takeScreenshot };

