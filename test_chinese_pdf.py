"""
中文PDF处理测试脚本
用于测试MERI对中文PDF文档的处理能力
"""
from meri import MERI
import json
import os

def main():
    print("=" * 60)
    print("中文PDF处理测试脚本")
    print("=" * 60)
    
    # 配置路径
    base_path = os.path.dirname(os.path.abspath(__file__))
    pdf_path = input("请输入中文PDF文件路径（或按Enter使用默认路径）: ").strip()
    if not pdf_path:
        pdf_path = os.path.join(base_path, 'data', 'demo_data', 'chinese_document.pdf')
    
    schema_path = input("请输入Schema文件路径（或按Enter使用默认路径）: ").strip()
    if not schema_path:
        schema_path = os.path.join(base_path, 'data', 'demo_data', 'chinese_schema.json')
    
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"错误：找不到 PDF 文件: {pdf_path}")
        print("提示：请将你的中文PDF文件放在指定路径")
        return
    
    if not os.path.exists(schema_path):
        print(f"错误：找不到 Schema 文件: {schema_path}")
        print("提示：请创建中文Schema文件，参考 中文PDF处理指南.md")
        return
    
    print(f"PDF 文件: {pdf_path}")
    print(f"Schema 文件: {schema_path}")
    print()
    
    # 判断PDF类型
    print("判断PDF类型...")
    pdf_type = input("PDF类型：1=文本型（可直接复制文字），2=扫描版（图片格式）[默认1]: ").strip()
    use_ocr = pdf_type == "2"
    
    if use_ocr:
        print("注意：扫描版PDF将启用OCR，处理时间会较长")
    else:
        print("文本型PDF，不需要OCR")
    
    print()
    
    # 加载 JSON Schema
    print("正在加载 JSON Schema...")
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        print("Schema 加载成功")
    except Exception as e:
        print(f"Schema 加载失败: {e}")
        return
    
    # 创建 MERI 实例
    print("\n正在初始化 MERI...")
    try:
        meri = MERI(
            pdf_path=pdf_path,
            model='gpt-4o-mini',  # 对中文支持很好
            model_temp=0.0,
            do_ocr=use_ocr  # 根据PDF类型设置
        )
        print("MERI 初始化成功")
    except Exception as e:
        print(f"MERI 初始化失败: {e}")
        print("提示：请确保已安装所有依赖")
        return
    
    # 转换为中间格式
    print("\n正在转换为中间格式（这可能需要一些时间）...")
    if use_ocr:
        print("OCR处理中，请耐心等待...")
    try:
        meri.to_intermediate()
        print("中间格式转换完成！")
        print(f" 中间格式长度: {len(meri.int_format)} 字符")
        
        # 检查是否包含中文
        sample_text = meri.int_format[:500]
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in sample_text)
        if has_chinese:
            print("   检测到中文字符，文本提取正常")
        else:
            print("    未检测到中文字符，请检查PDF是否为文本型")
    except Exception as e:
        print(f"中间格式转换失败: {e}")
        return
    
    # 可视化布局（可选）
    print("\n正在生成布局可视化...")
    try:
        layout_images = meri.vis_layout()
        print(f"生成了 {len(layout_images)} 页的布局可视化")
    except Exception as e:
        print(f"  布局可视化生成失败（非关键）: {e}")
    
    # 提取参数
    print("\n 正在提取参数（这可能需要一些时间，取决于文档大小和 API 响应速度）...")
    print("   请耐心等待...")
    try:
        populated_schema = meri.run(json.dumps(schema, ensure_ascii=False))
        print(" 参数提取完成！")
    except Exception as e:
        print(f" 参数提取失败: {e}")
        print(" 提示：")
        print("   1. 检查 .env 文件中的 API 密钥是否正确")
        print("   2. 确保有足够的 API 额度")
        print("   3. 检查网络连接")
        return
    
    # 显示结果
    print("\n" + "=" * 60)
    print("提取结果：")
    print("=" * 60)
    print(json.dumps(populated_schema, indent=2, ensure_ascii=False))
    
    # 保存结果到文件
    output_path = os.path.join(base_path, 'output_chinese_result.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(populated_schema, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {output_path}")
    except Exception as e:
        print(f" 保存结果失败: {e}")
    
    # 统计提取结果
    print("\n" + "=" * 60)
    print(" 提取统计：")
    print("=" * 60)
    if 'technicalSpecifications' in populated_schema:
        specs = populated_schema['technicalSpecifications']
        total_params = len(specs)
        found_params = sum(1 for k, v in specs.items() 
                          if v.get('parameter_properties', {}).get('text') not in [None, ''])
        not_found = populated_schema.get('notFoundList', [])
        
        print(f"   总参数数: {total_params}")
        print(f"   成功提取: {found_params}")
        print(f"   未找到: {len(not_found)}")
        if not_found:
            print(f"   未找到的参数: {', '.join(not_found)}")
    
    print("\n" + "=" * 60)
    print(" 测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()

