"""
参数匹配对比工具

功能：使用大模型将提取的参数与规范数据库进行语义匹配对比

使用方法：
1. 在 spec_database.json 中填写规范参数数据
2. 设置 EXTRACTION_RESULT 为提取结果文件路径
3. 运行脚本：python compare_params.py
"""

import json
import os
from datetime import datetime
from jinja2 import Template

from meri.utils.llm_utils import complete_chat


# ============================================================
# 配置区域
# ============================================================

# 提取结果文件路径（修改为实际文件名）
EXTRACTION_RESULT = "output/ex_azure_01_28_1057.json"

# 规范数据库文件路径
SPEC_DATABASE = "spec_database.json"

# 使用的模型
MODEL = "azure/gpt-4.1"

# 输出目录
OUTPUT_DIR = "output"

# 每批处理的参数数量（可根据实际情况调整）
BATCH_SIZE = 20


# ============================================================
# 匹配对比Prompt
# ============================================================
COMPARE_PROMPT = Template("""
你是一个专业的电气设备技术参数匹配对比专家。

## 核心任务
对于每个用户参数，在规范数据库中查找对应的规范要求，并判断用户参数值是否符合规范。

## 规范数据库（共 {{ spec_count }} 个参数）
格式: [类型] 参数名: 规范值
类型说明: A=关键参数不可变更, B=变更需审核, C=可调整, D=通用参数变更需特殊申请
{{ spec_params }}

## 用户提取的参数（本批 {{ user_count }} 个，需要逐一匹配）
{{ user_params }}

## 匹配规则

### 1. 语义匹配（参数名不要求完全相同）
- "断路器时间参数-分闸时间" = "断路器分闸时间"（同一参数）
- "断路器额定短路开断电流交流分量" = "断路器额定短路开断电流-交流分量"（同一参数）
- "隔离开关主回路接触电阻" = "隔离开关主回路电阻"（同一参数）

### 2. 设备必须匹配
- "断路器分闸时间" ≠ "隔离开关分闸时间"（不同设备）
- "快速接地开关额定短时耐受电流" ≠ "检修接地开关额定短时耐受电流"（不同设备）

### 3. 数值判断规则

#### 3.1 带符号的规范值（直接按符号判断）
- 规范"≤25ms"，用户"20ms" → 符合（20 ≤ 25）
- 规范"≤25ms"，用户"30ms" → 不符合（30 > 25）
- 规范"≥10000次"，用户"10000次" → 符合（10000 ≥ 10000）
- 规范"4.8~5.8m/s"，用户"5.2m/s" → 符合（在范围内）

#### 3.2 能力型参数（电流、电压、耐受值等）
对于以下类型的参数，规范值代表设备的最大能力/额定值：
- 额定电流、短路电流、耐受电流、关合电流、开断电流等
- 额定电压、耐受电压、冲击耐压等
- 峰值耐受电流、短时耐受电流等
- 机械寿命是特殊的能力型参数，用户值比规范值小或者等于才能实现，如果用户值 ≥ 规范值则不符合，否则符合
                          
**判断逻辑**：用户要求值 ≤ 规范值 → 合规；用户要求值 > 规范值 → 不合规；不论大于还是小于，均视为带有边界值，即大于5000就视为大于等于5000。
- 规范"40kA"，用户"40kA" → 符合（等于设备能力）
- 规范"40kA"，用户"35kA" → 符合（在设备能力范围内）
- 规范"40kA"，用户"50kA" → 不符合（超出设备能力）
- 规范"106kA"，用户"100kA" → 符合（在设备能力范围内）
- 规范"600kV"，用户"550kV" → 符合（在设备能力范围内）
- 规范"600kV"，用户"650kV" → 不符合（超出设备能力）
- 规范"机械寿命≥2000次"，用户"5000次" → 不符合
- 规范"机械寿命≥5000次"，用户"3000次" → 符合

#### 3.3 精确匹配型参数
对于断口数、操作顺序、电源电压等参数，需要精确匹配或兼容匹配

### 4. 未匹配情况
如果用户参数在规范数据库中找不到对应项，则 matched_spec_name 为 null

## 输出格式（严格JSON，只包含以下6个字段）
```json
{
    "results": [
        {
            "user_param_name": "用户参数名称",
            "user_value": "用户参数值",
            "matched_spec_name": "匹配到的规范参数名（未找到则为null）",
            "spec_value": "规范要求值（未找到则为null）",
            "param_type": "参数类型A/B/C/D（未找到则为null）",
            "is_compliant": true/false/null
        }
    ]
}
```

## 重要提示
1. 对每个用户参数都必须输出一条记录
2. is_compliant: true=符合规范, false=不符合规范, null=未找到匹配或无法判断
3. param_type: 从规范数据库中获取该参数的类型（A/B/C/D），如未匹配到则为null
4. 只输出上述6个字段，不要添加其他字段
5. 只输出JSON，不要输出其他内容
""")


class ParamComparator:
    """参数对比器"""
    
    def __init__(self, model: str = MODEL):
        self.model = model
        self.spec_params = []
    
    def load_spec_database(self, db_path: str):
        """加载规范数据库"""
        print(f"📂 加载规范数据库: {db_path}")
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.spec_params = data.get("parameters", [])
        print(f"  ✓ 加载了 {len(self.spec_params)} 个规范参数")
    
    def load_extraction_result(self, result_path: str) -> dict:
        """加载提取结果"""
        print(f"📂 加载提取结果: {result_path}")
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  ✓ 加载了 {len(data.get('parameters', []))} 个提取参数")
        return data
    
    def _format_spec_params(self) -> str:
        """格式化规范参数列表（包含类型信息）"""
        lines = []
        for p in self.spec_params:
            param_type = p.get('type', '')
            if param_type:
                lines.append(f"- [{param_type}] {p.get('name')}: {p.get('value')}")
            else:
                lines.append(f"- {p.get('name')}: {p.get('value')}")
        return "\n".join(lines)
    
    def _get_spec_type(self, spec_name: str) -> str:
        """根据规范参数名获取其类型"""
        for p in self.spec_params:
            if p.get('name') == spec_name:
                return p.get('type', '')
        return ''
    
    def _format_user_params(self, params: list) -> str:
        """格式化用户参数列表"""
        lines = []
        for p in params:
            # 用户参数可能有unit字段也可能没有，兼容处理
            value = p.get('value', '')
            unit = p.get('unit', '')
            if unit and not str(value).endswith(unit):
                value = f"{value}{unit}"
            lines.append(f"- {p.get('name')}: {value}")
        return "\n".join(lines)
    
    def _call_llm(self, prompt: str) -> dict:
        """调用大模型"""
        messages = [
            {"role": "system", "content": "你是专业的技术参数匹配对比专家。请输出规范的JSON格式。"},
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
                
            except json.JSONDecodeError:
                if attempt < 2:
                    print(f"    ⚠️ JSON解析失败，重试中...")
                    continue
                raise
            except Exception as e:
                if attempt < 2:
                    print(f"    ⚠️ 调用失败: {str(e)[:50]}，重试中...")
                    continue
                raise
        
        return {"results": []}
    
    def _compare_batch(self, user_params_batch: list) -> list:
        """对一批参数进行匹配对比"""
        spec_str = self._format_spec_params()
        user_str = self._format_user_params(user_params_batch)
        
        prompt = COMPARE_PROMPT.render(
            spec_params=spec_str,
            spec_count=len(self.spec_params),
            user_params=user_str,
            user_count=len(user_params_batch)
        )
        
        result = self._call_llm(prompt)
        return result.get("results", [])
    
    def compare(self, extraction_result: dict) -> dict:
        """执行对比"""
        print(f"\n{'='*60}")
        print(f"🔍 参数匹配对比（大模型语义匹配）")
        print(f"{'='*60}")
        
        user_params = extraction_result.get("parameters", [])
        print(f"待匹配参数数: {len(user_params)}")
        print(f"规范参数数: {len(self.spec_params)}")
        
        all_results = []
        
        # 分批处理
        total_batches = (len(user_params) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n📦 分 {total_batches} 批处理...")
        
        for i in range(0, len(user_params), BATCH_SIZE):
            batch = user_params[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            print(f"\n  🔄 处理第 {batch_num}/{total_batches} 批 ({len(batch)} 个参数)...")
            
            try:
                results = self._compare_batch(batch)
                all_results.extend(results)
                
                # 统计本批结果
                compliant = sum(1 for r in results if r.get("is_compliant") == True)
                non_compliant = sum(1 for r in results if r.get("is_compliant") == False)
                no_match = sum(1 for r in results if r.get("matched_spec_name") is None)
                
                print(f"    ✓ 符合:{compliant} 不符合:{non_compliant} 未匹配:{no_match}")
                
            except Exception as e:
                print(f"    ✗ 处理失败: {e}")
        
        # 汇总统计
        total = len(all_results)
        compliant_count = sum(1 for r in all_results if r.get("is_compliant") == True)
        non_compliant_count = sum(1 for r in all_results if r.get("is_compliant") == False)
        no_match_count = sum(1 for r in all_results if r.get("matched_spec_name") is None)
        uncertain_count = total - compliant_count - non_compliant_count - no_match_count
        
        print(f"\n{'='*60}")
        print(f"📊 对比结果统计")
        print(f"{'='*60}")
        print(f"  总参数数:     {total}")
        print(f"  ✓ 符合规范:   {compliant_count}")
        print(f"  ✗ 不符合:     {non_compliant_count}")
        print(f"  - 未匹配规范: {no_match_count}")
        print(f"  ? 无法判断:   {uncertain_count}")
        
        # 按类型统计不符合的参数
        type_stats = {"A": 0, "B": 0, "C": 0, "D": 0}
        for r in all_results:
            if r.get("is_compliant") == False:
                ptype = r.get("param_type", "")
                if ptype in type_stats:
                    type_stats[ptype] += 1
        
        if non_compliant_count > 0:
            print(f"\n  不符合参数按类型统计:")
            print(f"    A类(关键):   {type_stats['A']}")
            print(f"    B类(需审核): {type_stats['B']}")
            print(f"    C类(可调):   {type_stats['C']}")
            print(f"    D类(通用):   {type_stats['D']}")
        
        # 分类结果
        compliant_params = [r for r in all_results if r.get("is_compliant") == True]
        non_compliant_params = [r for r in all_results if r.get("is_compliant") == False]
        no_match_params = [r for r in all_results if r.get("matched_spec_name") is None]
        uncertain_params = [r for r in all_results if r.get("is_compliant") is None and r.get("matched_spec_name") is not None]
        
        # 按类型统计
        type_statistics = {
            "A": {"compliant": 0, "non_compliant": 0},
            "B": {"compliant": 0, "non_compliant": 0},
            "C": {"compliant": 0, "non_compliant": 0},
            "D": {"compliant": 0, "non_compliant": 0}
        }
        for r in all_results:
            ptype = r.get("param_type", "")
            if ptype in type_statistics:
                if r.get("is_compliant") == True:
                    type_statistics[ptype]["compliant"] += 1
                elif r.get("is_compliant") == False:
                    type_statistics[ptype]["non_compliant"] += 1
        
        result = {
            "extraction_file": EXTRACTION_RESULT,
            "spec_database": SPEC_DATABASE,
            "compare_time": datetime.now().isoformat(),
            "model": self.model,
            "statistics": {
                "total": total,
                "compliant": compliant_count,
                "non_compliant": non_compliant_count,
                "no_match": no_match_count,
                "uncertain": uncertain_count
            },
            "type_statistics": type_statistics,
            "type_definitions": {
                "A": "关键参数，不可变更",
                "B": "变更需提交审核",
                "C": "可根据情况调整",
                "D": "通用参数，变更需特殊申请"
            },
            "compliant_params": compliant_params,
            "non_compliant_params": non_compliant_params,
            "no_match_params": no_match_params,
            "uncertain_params": uncertain_params,
            "all_results": all_results
        }
        
        return result


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print(f"参数匹配对比工具")
    print(f"{'='*60}")
    print(f"提取结果: {EXTRACTION_RESULT}")
    print(f"规范数据库: {SPEC_DATABASE}")
    print(f"使用模型: {MODEL}")
    
    # 检查文件
    if not os.path.exists(EXTRACTION_RESULT):
        print(f"\n❌ 提取结果文件不存在: {EXTRACTION_RESULT}")
        print(f"请先运行 extract_params.py 或修改 EXTRACTION_RESULT 路径")
        return
    
    if not os.path.exists(SPEC_DATABASE):
        print(f"\n❌ 规范数据库文件不存在: {SPEC_DATABASE}")
        print(f"请先创建并填写 spec_database.json")
        return
    
    # 创建对比器
    comparator = ParamComparator(model=MODEL)
    
    # 加载数据
    comparator.load_spec_database(SPEC_DATABASE)
    extraction_result = comparator.load_extraction_result(EXTRACTION_RESULT)
    
    # 执行对比
    result = comparator.compare(extraction_result)
    
    # 保存结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%m_%d_%H%M")
    output_file = os.path.join(OUTPUT_DIR, f"com_azure_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 对比结果已保存到: {output_file}")
    
    # 显示符合规范的参数
    if result["compliant_params"]:
        print(f"\n✅ 符合规范的参数 ({len(result['compliant_params'])}个):")
        for item in result["compliant_params"][:8]:
            ptype = item.get('param_type', '')
            type_str = f"[{ptype}]" if ptype else ""
            print(f"  - {type_str} {item.get('user_param_name')}")
            print(f"    用户值: {item.get('user_value')} | 规范值: {item.get('spec_value')}")
        if len(result["compliant_params"]) > 8:
            print(f"  ... 还有 {len(result['compliant_params']) - 8} 个")
    
    # 显示不符合规范的参数
    if result["non_compliant_params"]:
        print(f"\n⚠️ 不符合规范的参数 ({len(result['non_compliant_params'])}个):")
        for item in result["non_compliant_params"]:
            ptype = item.get('param_type', '')
            type_str = f"[{ptype}类]" if ptype else ""
            print(f"  - {type_str} {item.get('user_param_name')}")
            print(f"    用户值: {item.get('user_value')} | 规范值: {item.get('spec_value')}")
    
    # 显示未匹配到规范的参数
    if result["no_match_params"]:
        print(f"\n📋 未匹配到规范的参数 ({len(result['no_match_params'])}个):")
        for item in result["no_match_params"][:15]:
            print(f"  - {item.get('user_param_name')}: {item.get('user_value')}")
        if len(result["no_match_params"]) > 15:
            print(f"  ... 还有 {len(result['no_match_params']) - 15} 个")


if __name__ == "__main__":
    main()
