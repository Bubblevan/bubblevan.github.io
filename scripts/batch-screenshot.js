#!/usr/bin/env node
/**
 * Docusaurus 分页截图工具 - 将单个页面按视口大小分成多张图
 * 
 * 使用方法:
 *   npm run batch-screenshot <url> [选项]
 *   npm run batch-screenshot http://localhost:3000/blog/3d-understand
 *   npm run batch-screenshot http://localhost:3000/blog/3d-understand --output-dir=./screenshots --padding=20
 * 
 * 功能: 将一个长页面分成多张视口大小的截图，每张图刚好填满屏幕
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

/**
 * 分页截图：将一个页面按视口大小分成多张图
 */
async function takeBatchScreenshots(url, options = {}) {
  const {
    width = 1920,
    height = 1080,
    waitUntil = 'networkidle2',
    delay = 1000,
    padding = 20,
    selector = null, // CSS 选择器，用于指定容器
    keepOriginalScale = false,
    outputDir = './screenshots',
    baseUrl = 'http://localhost:3000',
  } = options;

  // 构建完整 URL
  const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`;
  
  // 生成基础文件名
  const baseFilename = generateFilename(url, baseUrl).replace('.png', '');
  
  // 确保输出目录存在
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log(`正在启动浏览器...`);
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    
    // 设置视口大小
    await page.setViewport({
      width,
      height,
      deviceScaleFactor: keepOriginalScale ? 1 : 2,
    });

    console.log(`正在访问: ${fullUrl}`);
    await page.goto(fullUrl, {
      waitUntil,
      timeout: 60000,
    });

    // 等待内容加载
    if (delay > 0) {
      console.log(`等待 ${delay}ms 以确保内容完全加载...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }

    // 检测是否是博客文章页面，自动使用 article 选择器
    const isBlogPost = await page.evaluate(() => {
      const pathname = window.location.pathname;
      return pathname.startsWith('/blog/') && 
             pathname !== '/blog' && 
             !pathname.match(/^\/blog\/page\/\d+$/);
    });

    let finalSelector = selector;
    if (isBlogPost && !selector) {
      const articleExists = await page.$('article');
      if (articleExists) {
        finalSelector = 'article';
        console.log('检测到博客文章页面，自动使用 article 选择器排除底部容器');
      }
    }

    // 获取元素位置和高度信息
    const elementInfo = await page.evaluate((sel) => {
      if (sel) {
        const element = document.querySelector(sel);
        if (element) {
          const rect = element.getBoundingClientRect();
          return {
            top: rect.top + window.scrollY,
            height: element.scrollHeight,
            exists: true
          };
        }
      }
      return {
        top: 0,
        height: document.body.scrollHeight,
        exists: false
      };
    }, finalSelector);

    if (finalSelector && !elementInfo.exists) {
      throw new Error(`未找到选择器 "${finalSelector}" 对应的元素`);
    }

    const contentHeight = elementInfo.height;
    const contentTop = elementInfo.top;
    const viewportHeight = height;
    const totalPages = Math.ceil(contentHeight / viewportHeight);

    console.log(`\n内容总高度: ${contentHeight}px`);
    console.log(`视口高度: ${viewportHeight}px`);
    console.log(`将生成 ${totalPages} 张截图\n`);

    const screenshots = [];

    // 滚动并截图每一页
    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      // 计算需要滚动到的位置（相对于页面顶部）
      const scrollY = contentTop + (pageNum - 1) * viewportHeight;
      
      // 滚动页面到指定位置
      await page.evaluate((y) => {
        window.scrollTo(0, y);
      }, scrollY);

      // 等待滚动完成
      await new Promise(resolve => setTimeout(resolve, 300));

      // 生成输出路径
      const outputPath = path.join(outputDir, `${baseFilename}-page-${pageNum}.png`);

      console.log(`[${pageNum}/${totalPages}] 正在截图: ${outputPath} (滚动位置: ${scrollY}px)`);

      // 根据文件扩展名确定截图类型
      const ext = path.extname(outputPath).toLowerCase();
      const screenshotType = ext === '.jpg' || ext === '.jpeg' ? 'jpeg' : 'png';
      
      let screenshotOptions = {
        path: outputPath,
        type: screenshotType,
        fullPage: false, // 只截取视口大小，不截取整个页面
      };
      
      if (screenshotType === 'jpeg') {
        screenshotOptions.quality = 90;
      }

      // 始终使用 page.screenshot() 来确保只截取视口
      await page.screenshot(screenshotOptions);

      // 添加边距
      if (padding && padding > 0) {
        const tempPath = outputPath + '.tmp';
        fs.renameSync(outputPath, tempPath);
        
        await sharp(tempPath)
          .extend({
            top: 0,
            bottom: 0,
            left: padding,
            right: padding,
            background: { r: 255, g: 255, b: 255, alpha: 1 }
          })
          .toFile(outputPath);
        
        fs.unlinkSync(tempPath);
      }

      const stats = fs.statSync(outputPath);
      const fileSizeInMB = (stats.size / (1024 * 1024)).toFixed(2);
      console.log(`✅ 已保存 (${fileSizeInMB} MB)\n`);

      screenshots.push(outputPath);
    }

    console.log(`✅ 分页截图完成！共生成 ${screenshots.length} 张图片`);
    return screenshots;

  } catch (error) {
    console.error('❌ 截图失败:', error.message);
    throw error;
  } finally {
    await browser.close();
  }
}

function generateFilename(url, baseUrl = 'http://localhost:3000') {
  try {
    // 如果是完整 URL，直接解析
    if (url.startsWith('http://') || url.startsWith('https://')) {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname.replace(/^\//, '').replace(/\/$/, '') || 'index';
      return pathname.replace(/\//g, '-') + '.png';
    }
    // 如果是相对路径，使用 baseUrl 构建完整 URL
    const fullUrl = url.startsWith('/') ? `${baseUrl}${url}` : `${baseUrl}/${url}`;
    const urlObj = new URL(fullUrl);
    const pathname = urlObj.pathname.replace(/^\//, '').replace(/\/$/, '') || 'index';
    return pathname.replace(/\//g, '-') + '.png';
  } catch (error) {
    // 如果 URL 解析失败，使用简单的文件名生成
    const safeName = url.replace(/[^a-zA-Z0-9]/g, '-').replace(/-+/g, '-');
    return (safeName || 'screenshot') + '.png';
  }
}

// 命令行参数处理
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('❌ 错误: 请提供 URL');
    console.log('');
    console.log('使用方法:');
    console.log('  npm run batch-screenshot <url> [选项]');
    console.log('');
    console.log('选项:');
    console.log('  --base-url=<url>        基础 URL（默认: http://localhost:3000）');
    console.log('  --output-dir=<dir>     输出目录（默认: ./screenshots）');
    console.log('  --padding=<像素>       白色左右边距（默认: 20）');
    console.log('  --selector=<选择器>    容器选择器（如 article，博客文章会自动使用）');
    console.log('  --keep-scale           保持原始字体大小');
    console.log('  --width=<像素>         视口宽度（默认: 1920）');
    console.log('  --height=<像素>        视口高度（默认: 1080）');
    console.log('');
    console.log('示例:');
    console.log('  npm run batch-screenshot http://localhost:3000/blog/3d-understand');
    console.log('  npm run batch-screenshot /blog/3d-understand --padding=30');
    console.log('  npm run batch-screenshot /blog/3d-understand --output-dir=./my-screenshots');
    process.exit(1);
  }

  // 解析参数
  const options = {};
  let url = null;

  for (const arg of args) {
    if (arg.startsWith('--base-url=')) {
      options.baseUrl = arg.split('=')[1];
    } else if (arg.startsWith('--output-dir=')) {
      options.outputDir = arg.split('=')[1];
    } else if (arg.startsWith('--padding=')) {
      options.padding = parseInt(arg.split('=')[1]) || 0;
    } else if (arg.startsWith('--selector=')) {
      options.selector = arg.split('=')[1];
    } else if (arg.startsWith('--width=')) {
      options.width = parseInt(arg.split('=')[1]) || 1920;
    } else if (arg.startsWith('--height=')) {
      options.height = parseInt(arg.split('=')[1]) || 1080;
    } else if (arg === '--keep-scale') {
      options.keepOriginalScale = true;
    } else if (!arg.startsWith('--')) {
      // 第一个非选项参数作为 URL
      if (!url) {
        url = arg;
      }
    }
  }

  if (!url) {
    console.error('❌ 错误: 请提供 URL');
    process.exit(1);
  }

  try {
    await takeBatchScreenshots(url, options);
    process.exit(0);
  } catch (error) {
    console.error('分页截图失败:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { takeBatchScreenshots };

