"""
测试布局增强功能
验证左右分离的键值对是否被正确合并
"""
from meri import MERI
from meri.utils.html_post_processor import unescape_html_entities
import os

def main():
    print("=" * 60)
    print("布局增强功能测试")
    print("=" * 60)
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 使用您的中文PDF
    pdf_path = os.path.join(base_path, 'data', 'demo_data', 'user_test_sim-scan.pdf')
    
    if not os.path.exists(pdf_path):
        # 尝试其他可能的文件名
        pdf_path = os.path.join(base_path, 'data', 'demo_data', 'user_test4.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"错误：找不到测试PDF文件")
        print(f"  尝试的路径: {pdf_path}")
        return
    
    print(f"\n测试PDF: {pdf_path}")
    print()
    
    # 测试1: 不启用布局增强
    print("测试1: 原始模式（不启用布局增强）")
    print("-" * 60)
    try:
        meri_original = MERI(
            pdf_path=pdf_path,
            model='gpt-4o-mini',
            model_temp=0.0,
            do_ocr=False,
            #ocr_lang="ch_sim",
            enhance_layout=False  # 禁用布局增强
        )
        meri_original.to_intermediate()
        
        # 保存原始结果
        output_path = os.path.join(base_path, 'debug_original_scan.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(meri_original.int_format)
        
        print(f"✓ 原始HTML已保存: {output_path}")
        print(f"  长度: {len(meri_original.int_format)} 字符")
        
        # 检查是否包含分离的模式
        has_list = '<ul className="list_wrapper">' in meri_original.int_format
        has_额定电压 = '额定电压' in meri_original.int_format
        print(f"  包含列表: {has_list}")
        print(f"  包含'额定电压': {has_额定电压}")
        
    except Exception as e:
        print(f"✗ 原始模式测试失败: {e}")
        return
    
    print()
    
    # 测试2: 启用布局增强
    print("测试2: 增强模式（启用布局增强）")
    print("-" * 60)
    try:
        meri_enhanced = MERI(
            pdf_path=pdf_path,
            model='gpt-4o-mini',
            model_temp=0.0,
            do_ocr=False,
            #ocr_lang="ch_sim",
            enhance_layout=True  # 启用布局增强
        )
        meri_enhanced.to_intermediate()
        
        # 保存增强结果（用于显示的版本，反转义HTML实体）
        output_path = os.path.join(base_path, 'debug_enhanced_scan.html')
        display_html = unescape_html_entities(meri_enhanced.int_format)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(display_html)
        
        # 同时保存排序后的版本（用于调试排序功能）
        sorted_path = os.path.join(base_path, 'debug_sorted.html')
        # 注意：这里我们无法直接获取排序后的HTML，因为它在内部处理
        # 所以我们只保存最终版本
        
        print(f"✓ 增强HTML已保存: {output_path}")
        print(f"  长度: {len(meri_enhanced.int_format)} 字符")
        
        # 检查是否包含合并的键值对
        has_merged = 'className="merged_key_value"' in meri_enhanced.int_format
        has_colon_pattern = '额定电压:' in meri_enhanced.int_format or '额定频率:' in meri_enhanced.int_format
        print(f"  包含合并标记: {has_merged}")
        print(f"  包含冒号连接: {has_colon_pattern}")
        
    except Exception as e:
        print(f"✗ 增强模式测试失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print("请对比两个HTML文件：")
    print(f"  1. debug_original.html  - 原始布局")
    print(f"  2. debug_enhanced.html  - 增强布局")


if __name__ == "__main__":
    main()



