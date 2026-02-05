# 技术参数提取与比对平台 - Web界面使用说明

## 快速启动

### Windows 用户
双击运行 `run_web.bat`，浏览器会自动打开。

### 命令行启动
```bash
# 1. 安装依赖（首次使用）
pip install streamlit openpyxl

# 2. 启动应用
streamlit run web_app.py
```

启动后浏览器会自动打开 http://localhost:8501

## 功能说明

### 步骤1：上传PDF文件
- 点击上传区域，选择技术协议PDF文件
- 支持任意大小的PDF文档

### 步骤2：编辑预定义参数列表
- 在文本框中输入需要提取的参数名称
- 每行一个参数
- 可以保存到文件或从文件加载

### 步骤3：编辑规范参数数据库
- 添加规范参数及其要求值
- 设置参数类型（A/B/C/D）
- 可以保存到文件或从文件加载

### 步骤4：提取参数
- 点击"开始提取"按钮
- 系统会自动从PDF中提取指定参数
- 提取完成后可查看结果

### 步骤5：参数比对
- 点击"开始比对"按钮
- 系统会将提取结果与规范库对比
- 分类显示：符合/不符合/未匹配

### 步骤6：导出报告
- 点击"生成Excel报告"
- 下载包含完整比对结果的Excel文件

## 模型配置

在左侧边栏可选择不同的大模型：
- `qwen/qwen3-max` - 阿里云通义千问（默认）
- `openai/gpt-4o` - OpenAI GPT-4o
- `deepseek/deepseek-chat` - DeepSeek
- `azure/gpt-4o` - Azure OpenAI

请确保在 `.env` 文件中配置了对应的 API Key。

## 注意事项

1. **API配置**：使用前请确保已配置正确的API Key
2. **网络连接**：需要能访问对应的API服务
3. **文件保存**：编辑后记得点击"保存到文件"
4. **大文件处理**：大型PDF可能需要较长处理时间

## 打包为独立应用（可选）

如需打包为可分发的独立应用：

```bash
# 安装 pyinstaller
pip install pyinstaller

# 打包（会生成 dist 文件夹）
pyinstaller --onedir --add-data "params_list.txt;." --add-data "spec_database.json;." web_app.py
```

或使用 Streamlit Cloud 部署到云端，用户通过网址即可访问。
