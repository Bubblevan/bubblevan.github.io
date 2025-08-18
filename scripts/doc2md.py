import pypandoc
import os

def convert_docx_to_md(docx_path, output_folder):
    """
    将 DOCX 文件转换为 Markdown 文件，并提取图片。
    (修正版，确保图片路径正确)

    :param docx_path: 输入的 DOCX 文件路径。
    :param output_folder: 输出文件夹路径。
    """
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    base_filename = os.path.splitext(os.path.basename(docx_path))[0]
    md_filename = f"{base_filename}.md"
    
    # 图片将保存在输出文件夹下的 'media' 子目录中
    media_folder_name = 'media'
    
    # 记录原始工作目录
    original_cwd = os.getcwd()
    
    print(f"开始转换: {docx_path} -> {os.path.join(output_folder, md_filename)}")

    try:
        # --- 关键改动：切换工作目录到输出目录 ---
        os.chdir(output_folder)

        # Pandoc 的额外参数
        # 因为我们已经在输出目录下了，所以 './media' 会被正确解析
        extra_args = [f'--extract-media=./{media_folder_name}']

        # 执行转换
        # 注意：因为我们已经切换了目录，所以 outputfile 只需要文件名即可
        pypandoc.convert_file(
            source_file=docx_path,  # 源文件路径仍然使用绝对或相对调用位置的路径
            to='markdown',
            outputfile=md_filename, # 输出文件现在是相对路径
            extra_args=extra_args,
            encoding='utf-8'
        )
        print(f"转换成功！Markdown 文件保存在: {os.path.join(output_folder, md_filename)}")
        print(f"图片文件保存在: {os.path.join(output_folder, media_folder_name)}")

    except Exception as e:
        print(f"转换失败: {e}")
    finally:
        # --- 关键改动：无论成功与否，都切回原始工作目录 ---
        os.chdir(original_cwd)
        print(f"已恢复工作目录到: {original_cwd}")


# --- 使用示例 ---
if __name__ == "__main__":
    # 你的 docx 文件路径
    input_docx = r'D:\MyLab\大二秋冬\新农科实践-生活园艺\期终论文.docx'
    # 你希望保存 md 文件和图片的文件夹
    output_dir = r'D:\MyLab\大二秋冬\新农科实践-生活园艺'

    # 检查输入文件是否存在
    if not os.path.exists(input_docx):
        print(f"错误: 输入文件 '{input_docx}' 不存在。")
    else:
        convert_docx_to_md(input_docx, output_dir)