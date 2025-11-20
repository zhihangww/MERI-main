# 如何创建自定义 Schema 文件

## 📋 概述

要使用 MERI 从 PDF 中提取技术参数，你需要创建一个符合 JSON Schema 格式的配置文件。我已经为你创建了一个模板文件：`my_custom_schema.json`

## 🔧 修改步骤

### 1. 打开模板文件
打开 `data/demo_data/my_custom_schema.json` 文件

### 2. 修改顶层描述（第 3 行）
```json
"description": "Data sheet for your equipment/product - 请修改此描述"
```
改为你的设备或产品描述，例如：
```json
"description": "Data sheet for Centrifugal Pump Model XYZ-100"
```

### 3. 修改参数定义（第 60-200 行左右）

对于每个参数，你需要修改以下内容：

#### 参数键名（PARAMETER_1, PARAMETER_2 等）
- **命名规则**：使用大写字母和下划线，例如：`MAX_PRESSURE`, `FLOW_RATE`, `MOTOR_POWER`
- **建议**：使用英文，清晰表达参数含义

#### label（标签）
- **作用**：简短的人类可读名称
- **示例**：
  ```json
  "label": "Maximum pressure"
  ```
  或中文：
  ```json
  "label": "最大压力"
  ```

#### description（描述）
- **作用**：详细说明要提取什么信息
- **重要**：描述越详细，提取越准确
- **示例**：
  ```json
  "description": "The maximum operating pressure of the pump, usually specified in bar or MPa. Look for values like 'Max pressure: 10 bar' or 'Maximum pressure 10 bar'."
  ```

#### desiredUnit（期望单位）
- **作用**：指定期望的单位，模型会自动转换
- **示例**：
  - 如果有单位：`"desiredUnit": "bar"`
  - 如果没有单位：`"desiredUnit": ""`
  - 常见单位：`bar`, `MPa`, `kg`, `kW`, `rpm`, `°C`, `mm`, `m³/h` 等

### 4. 删除不需要的参数
如果你只需要 8 个参数，删除 `PARAMETER_9` 和 `PARAMETER_10` 的定义即可。

### 5. 添加更多参数（如果需要超过 10 个）
复制一个参数的定义块，修改键名和内容即可。

## 📝 完整示例

假设你要提取一个泵的参数，修改后的示例：

```json
"MAX_PRESSURE": {
    "label": "Maximum pressure",
    "description": "The maximum operating pressure of the pump, usually specified in bar or MPa. Look for values in the technical specifications table or pressure section.",
    "desiredUnit": "bar",
    "type": "object",
    "properties": {
        "parameter_properties": {"$ref": "#/definitions/parameter_properties"}
    }
},
"FLOW_RATE": {
    "label": "Flow rate",
    "description": "The flow rate capacity of the pump, typically measured in m³/h or L/min. Look for values like 'Flow: 100 m³/h' or 'Capacity: 100 m³/h'.",
    "desiredUnit": "m³/h",
    "type": "object",
    "properties": {
        "parameter_properties": {"$ref": "#/definitions/parameter_properties"}
    }
},
"MOTOR_POWER": {
    "label": "Motor power",
    "description": "The power rating of the motor driving the pump, usually specified in kW or HP. Look for values in the motor specifications section.",
    "desiredUnit": "kW",
    "type": "object",
    "properties": {
        "parameter_properties": {"$ref": "#/definitions/parameter_properties"}
    }
}
```

## ⚠️ 重要注意事项

1. **不要修改 definitions 部分**（第 4-53 行）
   - 这部分定义了数据结构，必须保持不变

2. **不要修改顶层结构**
   - `title`, `technicalSpecifications`, `notFoundList` 这三个字段必须保留
   - `required` 数组也必须包含这三个字段

3. **保持 JSON 格式正确**
   - 确保所有括号、引号、逗号都正确
   - 最后一个参数后面不要有逗号

4. **参数命名建议**
   - 使用大写字母和下划线
   - 使用英文，避免特殊字符
   - 保持简洁但有意义

5. **description 的重要性**
   - 描述越详细，模型提取越准确
   - 可以说明参数在文档中可能出现的格式
   - 可以说明参数所在的章节或表格

## 🚀 使用方法

修改完成后，在 `test_meri.py` 中修改 schema 路径：

```python
schema_path = os.path.join(base_path, 'data', 'demo_data', 'my_custom_schema.json')
```

然后运行脚本即可！

## ✅ 验证 Schema

修改完成后，建议：
1. 使用 JSON 验证工具检查格式是否正确
2. 先用一个简单的参数测试
3. 逐步添加更多参数

## 💡 提示

- **label** 和 **description** 可以用中文，但参数键名（如 `MAX_PRESSURE`）建议用英文
- 如果某个参数在文档中找不到，会自动添加到 `notFoundList` 中
- `desiredUnit` 为空字符串时，模型会保持文档中的原始单位

