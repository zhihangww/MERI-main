# 中文PDF处理指南

## ✅ 结论：MERI 可以很好地处理中文PDF文档

MERI 项目**完全支持**处理中文PDF文档，并且可以获得与英文文档相似的良好效果。以下是详细说明和优化建议。

## 🔍 技术支撑

### 1. **GPT-4o-mini 对中文的支持**

- ✅ **多语言能力**：GPT-4o-mini 具备强大的多语言处理能力，对中文的理解和生成能力非常出色
- ✅ **上下文理解**：能够理解中文的技术文档、参数描述和上下文关系
- ✅ **语义理解**：能够理解中文的语义，而不仅仅是字面翻译

### 2. **Docling 对中文PDF的支持**

- ✅ **文本提取**：docling 可以正确提取中文PDF中的文本内容
- ✅ **布局识别**：能够识别中文文档的表格、段落、标题等布局元素
- ✅ **OCR支持**：如果PDF是扫描版（图片格式），可以启用OCR功能

### 3. **中间格式处理**

- ✅ **UTF-8编码**：所有文本处理都使用UTF-8编码，完全支持中文字符
- ✅ **HTML格式**：中文内容会被正确转换为HTML中间格式
- ✅ **位置信息**：中文文本的位置信息（bbox）也会被正确保留

## ⚙️ 配置建议

### 1. **OCR设置（重要！）**

根据你的PDF类型，决定是否需要启用OCR：

#### 情况A：文本型PDF（推荐）
如果你的PDF是**文本型PDF**（可以直接复制文字），**不需要**启用OCR：

```python
meri = MERI(
    pdf_path=pdf_path,
    model='gpt-4o-mini',
    do_ocr=False  # 文本型PDF不需要OCR
)
```

#### 情况B：扫描版PDF（图片格式）
如果你的PDF是**扫描版**（无法直接复制文字，是图片格式），**必须**启用OCR：

```python
meri = MERI(
    pdf_path=pdf_path,
    model='gpt-4o-mini',
    do_ocr=True  # 扫描版PDF需要OCR
)
```

**如何判断PDF类型？**
- 文本型：可以在PDF中直接选中和复制文字
- 扫描版：无法选中文字，整个页面是图片

### 2. **模型选择**

对于中文文档，推荐使用以下模型：

```python
# 推荐选项（按优先级）
model='gpt-4o-mini'      # 性价比高，中文支持好
model='gpt-4o'           # 性能更强，中文支持更好
model='azure/gpt-4o'     # 如果使用Azure
```

## 📝 Schema配置优化

### 1. **使用中文描述（强烈推荐）**

在Schema的`label`和`description`中使用中文，可以显著提高提取准确性：

```json
{
  "MAX_PRESSURE": {
    "label": "最大压力",
    "description": "设备的最大工作压力，通常以bar或MPa为单位。在文档中可能表述为'最大压力为X bar'、'最大工作压力：X bar'、'压力范围：X bar'等。提取数值并转换为bar单位。",
    "desiredUnit": "bar"
  },
  "FLOW_RATE": {
    "label": "流量",
    "description": "设备的流量容量，通常以m³/h或L/min为单位。在段落文本中可能表述为'流量为X m³/h'、'流量：X m³/h'、'处理能力X m³/h'等。提取数值。",
    "desiredUnit": "m³/h"
  }
}
```

### 2. **参数键名建议用英文**

虽然`label`和`description`可以用中文，但**参数键名（如`MAX_PRESSURE`）建议使用英文**：

```json
{
  "MAX_PRESSURE": {  // ✅ 键名用英文
    "label": "最大压力",  // ✅ 标签用中文
    "description": "设备的最大工作压力..."  // ✅ 描述用中文
  }
}
```

**原因**：
- JSON键名使用英文更规范
- 便于代码处理和国际化
- 避免编码问题

### 3. **描述中包含中文表述示例**

在`description`中提供中文文档中可能出现的表述方式：

```json
{
  "TEMPERATURE_RANGE": {
    "label": "温度范围",
    "description": "设备的工作温度范围。在文档中可能表述为：'工作温度范围为-10°C至+50°C'、'温度范围：-10°C到+50°C'、'适用温度：-10°C~+50°C'、'工作温度在-10°C和+50°C之间'等。提取最小值和最大值。",
    "desiredUnit": "°C"
  }
}
```

## 🚀 完整使用示例

### 示例1：处理文本型中文PDF

```python
from meri import MERI
import json
import os

# 文件路径
pdf_path = 'path/to/chinese_document.pdf'
schema_path = 'path/to/chinese_schema.json'

# 加载Schema
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = json.load(f)

# 创建MERI实例（文本型PDF，不需要OCR）
meri = MERI(
    pdf_path=pdf_path,
    model='gpt-4o-mini',
    do_ocr=False,  # 文本型PDF
    model_temp=0.0
)

# 转换为中间格式
meri.to_intermediate()

# 提取参数
result = meri.run(json.dumps(schema, ensure_ascii=False))

# 保存结果（使用ensure_ascii=False以正确保存中文）
with open('output_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
```

### 示例2：处理扫描版中文PDF

```python
# 创建MERI实例（扫描版PDF，需要OCR）
meri = MERI(
    pdf_path=pdf_path,
    model='gpt-4o-mini',
    do_ocr=True,  # 扫描版PDF需要OCR
    model_temp=0.0
)
```

### 示例3：中文Schema示例

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "description": "设备技术参数数据表",
  "definitions": {
    "bbox": {
      "type": "array",
      "items": {"type": "number"},
      "minItems": 4,
      "maxItems": 4
    },
    "pageIndex": {
      "description": "参数所在页面的索引",
      "type": "integer"
    },
    "title": {
      "description": "数据表标题，通常是设备名称或型号",
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "bbox": {"$ref": "#/definitions/bbox"},
        "pageIndex": {"$ref": "#/definitions/pageIndex"}
      },
      "required": ["text", "bbox", "pageIndex"]
    },
    "parameter_properties": {
      "type": "object",
      "properties": {
        "value": {"type": "number"},
        "text": {"type": "string"},
        "unit": {"type": "string"},
        "bbox": {"$ref": "#/definitions/bbox"},
        "pageIndex": {"$ref": "#/definitions/pageIndex"}
      },
      "required": ["value", "text", "unit", "bbox", "pageIndex"]
    }
  },
  "type": "object",
  "properties": {
    "title": {
      "$ref": "#/definitions/title"
    },
    "technicalSpecifications": {
      "description": "技术规格参数",
      "type": "object",
      "properties": {
        "MAX_PRESSURE": {
          "label": "最大压力",
          "description": "设备的最大工作压力，通常以bar或MPa为单位。在文档中可能表述为'最大压力为X bar'、'最大工作压力：X bar'、'压力范围：X bar'等。提取数值并转换为bar单位。",
          "desiredUnit": "bar",
          "type": "object",
          "properties": {
            "parameter_properties": {"$ref": "#/definitions/parameter_properties"}
          }
        },
        "FLOW_RATE": {
          "label": "流量",
          "description": "设备的流量容量，通常以m³/h或L/min为单位。在段落文本中可能表述为'流量为X m³/h'、'流量：X m³/h'、'处理能力X m³/h'等。提取数值。",
          "desiredUnit": "m³/h",
          "type": "object",
          "properties": {
            "parameter_properties": {"$ref": "#/definitions/parameter_properties"}
          }
        }
      }
    },
    "notFoundList": {
      "description": "未找到的参数列表",
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["title", "technicalSpecifications", "notFoundList"]
}
```

## ⚠️ 注意事项

### 1. **文件编码**

确保所有文件使用UTF-8编码：

```python
# ✅ 正确：使用UTF-8编码
with open('schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)

with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False)
```

### 2. **JSON输出**

保存结果时使用`ensure_ascii=False`以正确保存中文：

```python
json.dump(result, f, indent=2, ensure_ascii=False)
```

### 3. **OCR性能**

如果启用OCR，处理时间会显著增加：
- 文本型PDF：几秒到几十秒
- 扫描版PDF（OCR）：几分钟到十几分钟（取决于页数）

### 4. **中文单位处理**

注意中文文档中可能使用的中文单位：
- `公斤` → `kg`
- `立方米` → `m³`
- `千瓦` → `kW`
- `转/分` → `rpm`

在`description`中可以说明这些单位转换。

## 🧪 测试建议

### 1. **先用简单参数测试**

选择一个在文档中明确出现的参数进行测试：

```json
{
  "TEST_PARAMETER": {
    "label": "测试参数",
    "description": "这是一个测试参数，在文档第X页明确出现。",
    "desiredUnit": "",
    "type": "object",
    "properties": {
      "parameter_properties": {"$ref": "#/definitions/parameter_properties"}
    }
  }
}
```

### 2. **检查中间格式**

查看中间格式是否正确提取了中文：

```python
meri.to_intermediate()
print(meri.int_format[:1000])  # 查看前1000个字符
```

### 3. **逐步增加参数**

测试成功后，逐步增加更多参数。

### 4. **对比验证**

将提取结果与原始PDF对比，验证准确性。

## 📊 性能对比

| 文档类型 | OCR需求 | 处理速度 | 准确性 |
|---------|---------|---------|--------|
| 文本型中文PDF | 不需要 | 快 | 高 |
| 扫描版中文PDF | 需要 | 慢 | 中等（取决于OCR质量） |
| 混合型PDF | 部分需要 | 中等 | 高 |

## 💡 最佳实践

1. **优先使用文本型PDF**：如果可能，使用文本型PDF而不是扫描版
2. **Schema描述用中文**：在`label`和`description`中使用中文，提高准确性
3. **提供多种表述方式**：在`description`中列出参数可能出现的多种中文表述
4. **测试OCR效果**：如果是扫描版PDF，先测试OCR效果
5. **逐步优化**：从简单参数开始，逐步增加复杂度

## 🎯 总结

- ✅ **MERI完全支持中文PDF处理**
- ✅ **GPT-4o-mini对中文支持很好**
- ✅ **Docling可以正确提取中文内容**
- ✅ **在Schema中使用中文描述可以提高准确性**
- ⚠️ **扫描版PDF需要启用OCR，处理时间较长**
- 💡 **建议：Schema的label和description使用中文，参数键名使用英文**

## 🔗 相关资源

- [如何创建自定义Schema](./new/如何创建自定义Schema.md)
- [从段落文本提取参数的优化指南](./new/从段落文本提取参数的优化指南.md)

