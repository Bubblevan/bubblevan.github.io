#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
示例脚本：演示如何使用pdf_to_markdown.py提取PDF图片并生成Markdown

使用方法:
    python pdf_example.py
"""

import os
import sys
import subprocess

def main():
    # 示例PDF文件路径 - 使用项目中已有的PDF文件
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           "static", "pdfs", "数字图像处理教材.pdf")
    
    # 输出Markdown文件路径
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "docs", "undergraduate-notes", "编程基础")
    output_md = os.path.join(output_dir, "pdf_extraction_example.md")
    
    # 图片保存目录
    img_dir = os.path.join(output_dir, "pdf_extraction_example_images")
    
    # 相对路径（用于Markdown中引用图片）
    relative_path = "./pdf_extraction_example_images"
    
    # 构建命令
    cmd = [
        sys.executable,  # 当前Python解释器路径
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_to_markdown.py"),
        pdf_path,
        output_md,
        "--img-dir", img_dir,
        "--img-prefix", "figure",
        "--relative-path", relative_path
    ]
    
    print("执行命令:", " ".join(cmd))
    
    # 执行命令
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("命令执行成功!")
        print(result.stdout)
        
        print(f"\n生成的Markdown文件: {output_md}")
        print(f"提取的图片保存在: {img_dir}")
        
    except subprocess.CalledProcessError as e:
        print("命令执行失败:")
        print(e.stderr)
        return 1
    except Exception as e:
        print(f"发生错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())