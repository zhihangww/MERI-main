from meri import MERI
import json
import os

def main():
    print("=" * 60)
    print("MERI 项目测试脚本")
    print("=" * 60)
    
    # 使用示例数据
    base_path = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_path, 'data', 'demo_data', 'Alfa Laval LKH.pdf')
    schema_path = os.path.join(base_path, 'data', 'demo_data', 'dummy_schema.json')
    
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
    except Exception as e:
        print(f"Schema 加载失败: {e}")
        return
    
    # 创建 MERI 实例
    print("\n正在初始化 MERI...")
    try:
        meri = MERI(
            pdf_path=pdf_path,
            model='gpt-4o-mini',  # 可以改为 'azure/gpt-4o' 如果使用 Azure
            model_temp=0.0
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
    except Exception as e:
        print(f"中间格式转换失败: {e}")
        return
    
    # 可视化布局（可选）
    print("\n正在生成布局可视化...")
    try:
        layout_images = meri.vis_layout()
        print(f"生成了 {len(layout_images)} 页的布局可视化")
        print("   提示：布局图像已生成，可以在代码中保存或显示")
    except Exception as e:
        print(f"  布局可视化生成失败（非关键）: {e}")
    
    # 提取参数
    print("\n正在提取参数（这可能需要一些时间，取决于文档大小和 API 响应速度）...")
    try:
        populated_schema = meri.run(json.dumps(schema))
        print("参数提取完成！")
    except Exception as e:
        print(f"参数提取失败: {e}")
        print(" 提示：")
        print("   1. 检查 .env 文件中的 API 密钥是否正确")
        print("   2. 确保有足够的 API 额度")
        print("   3. 检查网络连接")
        return
    
    # 显示结果
    print("\n" + "=" * 60)
    print(" 提取结果：")
    print("=" * 60)
    print(json.dumps(populated_schema, indent=2, ensure_ascii=False))
    
    # 保存结果到文件
    output_path = os.path.join(base_path, 'output_result.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(populated_schema, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {output_path}")
    except Exception as e:
        print(f"  保存结果失败: {e}")
    
    print("\n" + "=" * 60)
    print(" 测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()




