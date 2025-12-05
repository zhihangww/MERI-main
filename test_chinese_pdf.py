"""
中文PDF处理测试脚本
用于测试MERI对中文PDF文档的处理能力
"""
from meri import MERI
import json
import os

def main():
    print("=" * 60)
    print("MERI 中文 PDF 测试脚本")
    print("=" * 60)

    # 使用中文 PDF 和自定义 Schema
    base_path = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_path, 'data', 'demo_data', 'user_test_sim.pdf')
    schema_path = os.path.join(base_path, 'data', 'demo_data', 'table_text_keyvalue.json')

    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"错误：找不到 PDF 文件: {pdf_path}")
        return

    if not os.path.exists(schema_path):
        print(f"错误：找不到 Schema 文件: {schema_path}")
        return

    print(f"PDF 文件: {pdf_path}")
    print(f"Schema 文件: {schema_path}")
    print()

    # 加载 JSON Schema
    print("正在加载 JSON Schema...")
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        print("Schema 加载成功")
        print(f"  参数数量: {len(schema.get('properties', {}).get('technicalSpecifications', {}).get('properties', {}))}")
    except Exception as e:
        print(f"Schema 加载失败: {e}")
        return

    # 创建 MERI 实例
    # 注意：如果是扫描版PDF或文字无法直接提取，请设置 do_ocr=True
    print("\n正在初始化 MERI...")
    print("  已启用布局增强功能（自动合并左右分离的键值对）")
    try:
        meri = MERI(
            pdf_path=pdf_path,
            model='gpt-4o-mini',
            model_temp=0.0,
            do_ocr=False,  # 如果PDF是扫描版，改为True
            enhance_layout=True  # 启用布局增强（默认值）
        )
        print("MERI 初始化成功")
    except Exception as e:
        print(f"MERI 初始化失败: {e}")
        print("提示：请确保已安装所有依赖 (poetry install)")
        return

    # 转换为中间格式
    print("\n正在转换为中间格式（这可能需要一些时间）...")
    try:
        meri.to_intermediate()
        print("中间格式转换完成！")
        print(f"   中间格式长度: {len(meri.int_format)} 字符")
        
        # 可选：保存中间格式用于调试
        debug_path = os.path.join(base_path, 'table_text_keyvalue.html')
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write(meri.int_format)
        print(f"   中间格式已保存到: {debug_path} (用于调试)")
    except Exception as e:
        print(f"中间格式转换失败: {e}")
        return

    # 提取参数
    print("\n正在提取参数（这可能需要一些时间，取决于文档大小和 API 响应速度）...")
    try:
        populated_schema = meri.run(json.dumps(schema, ensure_ascii=False))
        print("参数提取完成！")
    except Exception as e:
        print(f"参数提取失败: {e}")
        print(" 提示：")
        print("   1. 检查 .env 文件中的 API 密钥是否正确")
        print("   2. 确保有足够的 API 额度")
        print("   3. 检查网络连接")
        return

    # 显示提取结果摘要
    print("\n" + "=" * 60)
    print("提取结果摘要")
    print("=" * 60)
    if 'title' in populated_schema:
        print(f"文档标题: {populated_schema.get('title', {}).get('text', '未提取到')}")
    
    tech_specs = populated_schema.get('technicalSpecifications', {})
    found_count = sum(1 for key, val in tech_specs.items() 
                     if isinstance(val, dict) and 'parameter_properties' in val 
                     and val['parameter_properties'].get('value') is not None)
    total_count = len(schema.get('properties', {}).get('technicalSpecifications', {}).get('properties', {}))
    print(f"提取到的参数: {found_count}/{total_count}")
    
    not_found = populated_schema.get('notFoundList', [])
    if not_found:
        print(f"未找到的参数: {', '.join(not_found)}")

    # 保存结果到文件
    output_path = os.path.join(base_path, 'output_chinese.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(populated_schema, f, indent=2, ensure_ascii=False)
        print(f"\n完整结果已保存到: {output_path}")
    except Exception as e:
        print(f"  保存结果失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()