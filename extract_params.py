"""
参数提取工具 - 根据预定义参数列表从PDF中提取参数

功能：
1. 读取预定义的参数列表（params_list.txt）
2. 使用Docling将PDF转换为HTML
3. 调用大模型从文档中提取指定的参数

使用方法：
1. 在 params_list.txt 中填写需要提取的参数名称（每行一个）
2. 修改 PDF_PATH 为目标PDF文件路径
3. 运行脚本：python extract_params.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from docling.document_converter import DocumentConverter
from jinja2 import Template

from meri.utils.llm_utils import complete_chat
from meri.utils.docling_utils import export_to_html


# ============================================================
# 配置区域
# ============================================================

# 待提取的PDF文件路径
PDF_PATH = "data/demo_data/final.pdf"

# 预定义参数列表文件
PARAMS_FILE = "params_list.txt"

# 使用的模型
MODEL = "qwen/qwen3-max"

# 输出目录
OUTPUT_DIR = "output"

# 每个分块的最大字符数（根据模型token限制调整）
MAX_CHARS = 20000

# 每批处理的参数数量（避免参数列表过长）
PARAMS_BATCH_SIZE = 50


# ============================================================
# 提取Prompt
# ============================================================
EXTRACTION_PROMPT = Template("""
你是一个专业的电气设备技术文档参数提取专家。

## 核心任务
从文档中精确提取指定的技术参数。必须仔细阅读文档中的每个表格和段落。

## 需要提取的参数列表（共 {{ params_count }} 个，请逐一查找）
{{ params_list }}

## 文档内容
{{ document }}

## 关键提取规则

### 1. 表格处理（最重要）
- 技术参数通常在表格中，表格第一列是参数名，后面列是数值
- 表格可能有多级表头，如"断路器"下有"分闸时间"、"合闸时间"等子参数
- 仔细识别表格结构，正确关联参数名和数值

### 2. 设备区分（必须严格遵守）
参数列表中的参数名已包含设备名称，必须精确匹配：
- "断路器分闸时间" - 只提取断路器的分闸时间
- "隔离开关分闸时间" - 只提取隔离开关的分闸时间
- "快速接地开关分闸时间" - 只提取快速接地开关的分闸时间
- "检修接地开关机械稳定性" - 只提取检修接地开关的机械稳定性
不同设备的同名参数是不同的参数！

### 3. 语义匹配
文档中的表述可能与列表略有不同，理解语义后匹配：
- "时间参数-分闸时间" → "分闸时间"
- "额定短路开断电流(交流分量)" → "额定短路开断电流交流分量"
- "主回路接触电阻" → "主回路电阻"
- "机械稳定性(次)" → "机械稳定性"

### 4. 数值提取
- 提取完整数值，包括符号：≤28ms、≥10000次、4.8~5.8m/s
- 数值和单位要完整：40kA、3s、1000kg

## 输出格式（严格JSON）
```json
{
    "parameters": [
        {
            "name": "使用参数列表中的原始名称",
            "value": "数值（含符号如≤≥）",
            "unit": "单位",
            "original_text": "文档中的原始表述（含设备名）"
        }
    ],
    "not_found": ["在本段文档中未找到的参数"]
}
```

## 重要提示
1. 逐一检查参数列表中的每个参数，确保不遗漏
2. 表格中的参数尤其要仔细，很多参数都在表格里
3. 如果同一参数在不同设备下有值，只提取与参数名匹配的那个设备的值
4. 只输出JSON，不要有其他内容
""")


class ParamsExtractor:
    """参数提取器"""
    
    def __init__(self, model: str = MODEL):
        self.model = model
        self.converter = DocumentConverter()
        self.params_list = []
    
    def load_params_list(self, params_file: str):
        """加载预定义参数列表"""
        print(f"📂 加载参数列表: {params_file}")
        with open(params_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        self.params_list = [line.strip() for line in lines if line.strip()]
        print(f"  ✓ 加载了 {len(self.params_list)} 个参数")
    
    def _convert_to_html(self, file_path: str) -> str:
        """将文档转换为HTML"""
        print(f"📄 转换文档: {file_path}")
        result = self.converter.convert(file_path)
        html_content = export_to_html(result.document)
        print(f"  ✓ 转换完成，HTML长度: {len(html_content)} 字符")
        return html_content
    
    def _chunk_document(self, html_content: str) -> list:
        """将文档分块"""
        if len(html_content) <= MAX_CHARS:
            return [html_content]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(html_content):
            end_pos = min(current_pos + MAX_CHARS, len(html_content))
            
            if end_pos < len(html_content):
                # 尝试在合适的位置断开
                for tag in ['</table>', '</div>', '</p>', '<br', '\n\n']:
                    find_pos = html_content.rfind(tag, current_pos, end_pos)
                    if find_pos > current_pos + MAX_CHARS // 2:
                        end_pos = find_pos + len(tag)
                        break
            
            chunk = html_content[current_pos:end_pos]
            chunks.append(chunk)
            current_pos = end_pos
        
        print(f"  📦 文档分为 {len(chunks)} 个块")
        return chunks
    
    def _chunk_params(self, params: list) -> list:
        """将参数列表分批"""
        if len(params) <= PARAMS_BATCH_SIZE:
            return [params]
        
        batches = []
        for i in range(0, len(params), PARAMS_BATCH_SIZE):
            batches.append(params[i:i + PARAMS_BATCH_SIZE])
        
        return batches
    
    def _call_llm(self, prompt: str) -> dict:
        """调用大模型"""
        messages = [
            {"role": "system", "content": "你是专业的技术文档参数提取专家。请严格按照要求输出JSON格式。"},
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]
        
        for attempt in range(3):
            try:
                response = complete_chat(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    max_tokens=8192
                )
                
                return json.loads(response)
                
            except json.JSONDecodeError as e:
                if attempt < 2:
                    print(f"    ⚠️ JSON解析失败，重试中...")
                    continue
                # 尝试修复JSON
                return self._try_fix_json(response)
            except Exception as e:
                if attempt < 2:
                    print(f"    ⚠️ 调用失败: {str(e)[:50]}，重试中...")
                    continue
                raise
        
        return {"parameters": [], "not_found": []}
    
    def _try_fix_json(self, response: str) -> dict:
        """尝试修复不完整的JSON"""
        try:
            # 尝试找到最后一个完整的对象
            if '"parameters"' in response:
                # 找到parameters数组的开始
                start = response.find('"parameters"')
                if start > 0:
                    # 尝试补全
                    fixed = response.rstrip()
                    if not fixed.endswith('}'):
                        fixed += '],"not_found":[]}'
                    return json.loads(fixed)
        except:
            pass
        return {"parameters": [], "not_found": []}
    
    def _normalize_name(self, name: str) -> str:
        """标准化参数名，用于匹配"""
        # 移除常见的分隔符和空格
        normalized = name.replace("-", "").replace("－", "").replace("—", "")
        normalized = normalized.replace("(", "").replace(")", "")
        normalized = normalized.replace("（", "").replace("）", "")
        normalized = normalized.replace(" ", "").replace("　", "")
        normalized = normalized.replace("/", "").replace("、", "")
        return normalized.lower()
    
    def _match_param_name(self, extracted_name: str, params_batch: list) -> str:
        """匹配提取的参数名到预定义列表"""
        extracted_norm = self._normalize_name(extracted_name)
        
        # 1. 精确匹配
        for p in params_batch:
            if extracted_name == p:
                return p
        
        # 2. 标准化后精确匹配
        for p in params_batch:
            if self._normalize_name(p) == extracted_norm:
                return p
        
        # 3. 包含匹配（需要设备名也匹配）
        # 提取设备名
        devices = ["断路器", "隔离开关", "快速接地开关", "检修接地开关", "电流互感器", "电压互感器", "避雷器"]
        
        extracted_device = None
        for d in devices:
            if d in extracted_name:
                extracted_device = d
                break
        
        for p in params_batch:
            p_norm = self._normalize_name(p)
            
            # 检查设备是否匹配
            p_device = None
            for d in devices:
                if d in p:
                    p_device = d
                    break
            
            # 如果两者都有设备名，必须匹配
            if extracted_device and p_device:
                if extracted_device != p_device:
                    continue
            
            # 检查参数名核心部分是否匹配
            if extracted_norm in p_norm or p_norm in extracted_norm:
                return p
        
        return None
    
    def _extract_batch(self, html_chunk: str, params_batch: list) -> dict:
        """对一个文档块和一批参数进行提取"""
        params_str = "\n".join([f"- {p}" for p in params_batch])
        
        prompt = EXTRACTION_PROMPT.render(
            params_list=params_str,
            params_count=len(params_batch),
            document=html_chunk
        )
        
        return self._call_llm(prompt)
    
    def extract(self, file_path: str) -> dict:
        """执行提取"""
        print(f"\n{'='*60}")
        print(f"🔍 参数提取（预定义列表模式）")
        print(f"{'='*60}")
        print(f"文件: {file_path}")
        print(f"参数数: {len(self.params_list)}")
        print(f"模型: {self.model}")
        
        # 转换文档
        html_content = self._convert_to_html(file_path)
        
        # 分块
        doc_chunks = self._chunk_document(html_content)
        params_batches = self._chunk_params(self.params_list)
        
        print(f"\n📊 处理计划:")
        print(f"  文档块数: {len(doc_chunks)}")
        print(f"  参数批次: {len(params_batches)}")
        
        # 收集结果
        all_params = {}  # name -> param dict
        found_params = set()
        
        # 对每个文档块，用所有待查参数进行提取
        for chunk_idx, chunk in enumerate(doc_chunks):
            # 计算当前还需要查找的参数
            remaining_params = [p for p in self.params_list if p not in found_params]
            
            if not remaining_params:
                print(f"\n✅ 所有参数已找到，跳过剩余文档块")
                break
            
            print(f"\n🔄 处理文档块 {chunk_idx + 1}/{len(doc_chunks)} (待查参数: {len(remaining_params)})")
            
            # 如果待查参数太多，分批处理
            param_batches = self._chunk_params(remaining_params)
            
            for batch_idx, params_batch in enumerate(param_batches):
                if len(param_batches) > 1:
                    print(f"  📦 参数批次 {batch_idx + 1}/{len(param_batches)}")
                
                try:
                    result = self._extract_batch(chunk, params_batch)
                    
                    # 处理结果
                    chunk_found = 0
                    for param in result.get("parameters", []):
                        if not isinstance(param, dict):
                            continue
                        
                        name = param.get("name", "")
                        value = param.get("value")
                        
                        # 过滤空值
                        if not name or not value or str(value).strip() in ["", "null", "无", "未找到", "N/A", "-"]:
                            continue
                        
                        # 精确匹配预定义列表中的参数
                        matched_name = self._match_param_name(name, params_batch)
                        
                        if matched_name and matched_name not in found_params:
                            param["name"] = matched_name  # 使用标准名称
                            all_params[matched_name] = param
                            found_params.add(matched_name)
                            chunk_found += 1
                    
                    print(f"    ✓ 本批找到 {chunk_found} 个参数")
                    
                except Exception as e:
                    print(f"    ✗ 处理失败: {e}")
        
        # 按预定义顺序整理结果
        ordered_params = []
        not_found = []
        
        for param_name in self.params_list:
            if param_name in all_params:
                ordered_params.append(all_params[param_name])
            else:
                not_found.append(param_name)
        
        # 统计
        print(f"\n{'='*60}")
        print(f"📊 提取结果统计")
        print(f"{'='*60}")
        print(f"  预定义参数:   {len(self.params_list)}")
        print(f"  成功提取:     {len(ordered_params)}")
        print(f"  未找到:       {len(not_found)}")
        
        result = {
            "source_file": file_path,
            "params_file": PARAMS_FILE,
            "extraction_time": datetime.now().isoformat(),
            "model": self.model,
            "statistics": {
                "total_requested": len(self.params_list),
                "found": len(ordered_params),
                "not_found": len(not_found)
            },
            "parameters": ordered_params,
            "not_found": not_found
        }
        
        return result


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print(f"参数提取工具")
    print(f"{'='*60}")
    print(f"PDF文件: {PDF_PATH}")
    print(f"参数列表: {PARAMS_FILE}")
    print(f"模型: {MODEL}")
    
    # 检查文件
    if not os.path.exists(PDF_PATH):
        print(f"\n❌ PDF文件不存在: {PDF_PATH}")
        return
    
    if not os.path.exists(PARAMS_FILE):
        print(f"\n❌ 参数列表文件不存在: {PARAMS_FILE}")
        return
    
    # 创建提取器
    extractor = ParamsExtractor(model=MODEL)
    
    # 加载参数列表
    extractor.load_params_list(PARAMS_FILE)
    
    # 执行提取
    result = extractor.extract(PDF_PATH)
    
    # 保存结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%m_%d_%H%M")
    output_file = os.path.join(OUTPUT_DIR, f"extraction_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 提取结果已保存到: {output_file}")
    
    # 显示部分结果预览
    if result["parameters"]:
        print(f"\n📋 提取结果预览（前10个）:")
        for param in result["parameters"][:10]:
            print(f"  - {param.get('name')}: {param.get('value')}{param.get('unit', '')}")
        if len(result["parameters"]) > 10:
            print(f"  ... 还有 {len(result['parameters']) - 10} 个")
    
    # 显示未找到的参数
    if result["not_found"]:
        print(f"\n⚠️ 未找到的参数 ({len(result['not_found'])}个):")
        for name in result["not_found"][:10]:
            print(f"  - {name}")
        if len(result["not_found"]) > 10:
            print(f"  ... 还有 {len(result['not_found']) - 10} 个")


if __name__ == "__main__":
    main()
