#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF图片提取器 - 将PDF中的图片提取并转换为Markdown格式

使用方法:
    python pdf_to_markdown.py input.pdf output.md

依赖:
    pip install PyMuPDF Pillow
"""

import os
import sys
import fitz  # PyMuPDF
import argparse
from PIL import Image
import io
import re
import hashlib
from datetime import datetime


def extract_images_from_pdf(pdf_path, output_folder, image_prefix):
    """
    从PDF文件中提取所有图片
    
    Args:
        pdf_path: PDF文件路径
        output_folder: 图片保存文件夹
        image_prefix: 图片文件名前缀
        
    Returns:
        提取的图片信息列表，每项包含：{"page": 页码, "path": 图片路径, "width": 宽度, "height": 高度}
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 打开PDF文件
    doc = fitz.open(pdf_path)
    image_list = []
    
    # 遍历每一页
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        
        # 获取页面上的图片
        image_list_page = page.get_images(full=True)
        
        # 遍历页面上的每个图片
        for img_index, img in enumerate(image_list_page):
            xref = img[0]  # 图片的xref
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # 使用PIL打开图片以获取尺寸
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            
            # 生成图片文件名
            image_filename = f"{image_prefix}_page{page_index+1}_img{img_index+1}.{image_ext}"
            image_path = os.path.join(output_folder, image_filename)
            
            # 保存图片
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            # 添加到图片列表
            image_list.append({
                "page": page_index + 1,
                "path": image_path,
                "width": width,
                "height": height,
                "filename": image_filename
            })
    
    doc.close()
    return image_list


def generate_markdown(pdf_path, image_list, output_md_path, relative_img_path=""):
    """
    生成包含图片的Markdown文件
    
    Args:
        pdf_path: PDF文件路径
        image_list: 图片信息列表
        output_md_path: 输出的Markdown文件路径
        relative_img_path: Markdown中引用图片的相对路径
    """
    pdf_filename = os.path.basename(pdf_path)
    
    # 按页码分组图片
    images_by_page = {}
    for img in image_list:
        page = img["page"]
        if page not in images_by_page:
            images_by_page[page] = []
        images_by_page[page].append(img)
    
    with open(output_md_path, "w", encoding="utf-8") as md_file:
        # 写入标题
        md_file.write(f"# {os.path.splitext(pdf_filename)[0]}\n\n")
        md_file.write(f"*从 {pdf_filename} 提取的图片*\n\n")
        md_file.write(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # 写入图片内容，按页码组织
        for page in sorted(images_by_page.keys()):
            md_file.write(f"## 第 {page} 页图片\n\n")
            
            # 获取当前页的图片
            page_images = images_by_page[page]
            
            # 根据图片数量决定布局
            if len(page_images) == 1:
                # 单图布局
                img = page_images[0]
                img_path = os.path.join(relative_img_path, os.path.basename(img["path"]))
                md_file.write(f"![图片 {page}.1]({img_path})\n\n")
            
            elif len(page_images) == 2:
                # 两图并排布局
                md_file.write("<div style=\"display: flex; justify-content: space-between;\">\n")
                for i, img in enumerate(page_images):
                    img_path = os.path.join(relative_img_path, os.path.basename(img["path"]))
                    md_file.write(f"  <div style=\"flex: 1; margin: 0 5px;\">\n")
                    md_file.write(f"    <img src=\"{img_path}\" alt=\"图片 {page}.{i+1}\" style=\"width: 100%;\">\n")
                    md_file.write(f"  </div>\n")
                md_file.write("</div>\n\n")
            
            else:
                # 网格布局
                md_file.write("<div style=\"display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;\">\n")
                for i, img in enumerate(page_images):
                    img_path = os.path.join(relative_img_path, os.path.basename(img["path"]))
                    md_file.write(f"  <div>\n")
                    md_file.write(f"    <img src=\"{img_path}\" alt=\"图片 {page}.{i+1}\" style=\"width: 100%;\">\n")
                    md_file.write(f"  </div>\n")
                md_file.write("</div>\n\n")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="从PDF提取图片并生成Markdown")
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("output_md", help="输出的Markdown文件路径")
    parser.add_argument("--img-dir", help="图片保存目录，默认为与Markdown同名的文件夹", default=None)
    parser.add_argument("--img-prefix", help="图片文件名前缀", default="img")
    parser.add_argument("--relative-path", help="Markdown中引用图片的相对路径", default="")
    
    args = parser.parse_args()
    
    # 设置图片保存目录
    if args.img_dir is None:
        img_dir = os.path.splitext(args.output_md)[0] + "_images"
    else:
        img_dir = args.img_dir
    
    try:
        # 提取图片
        print(f"正在从 {args.pdf_path} 提取图片...")
        image_list = extract_images_from_pdf(args.pdf_path, img_dir, args.img_prefix)
        print(f"共提取了 {len(image_list)} 张图片，保存在 {img_dir}")
        
        # 生成Markdown
        print(f"正在生成Markdown文件 {args.output_md}...")
        generate_markdown(args.pdf_path, image_list, args.output_md, args.relative_path)
        print("完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())