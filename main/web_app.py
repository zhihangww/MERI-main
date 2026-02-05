"""
技术参数提取与比对平台 - Web界面

基于 Streamlit 构建的可视化操作界面
功能：
1. 上传PDF技术协议文件
2. 编辑预定义参数列表
3. 编辑规范参数数据库
4. 一键提取参数
5. 一键比对参数
6. 导出Excel报告

启动方式：
    streamlit run web_app.py
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from io import BytesIO, StringIO
from contextlib import contextmanager

import streamlit as st

# 导入现有模块（不修改原有代码）
from extract_params import ParamsExtractor
from compare_params import ParamComparator, COMPARE_PROMPT
from export_excel import export_to_excel


# ============================================================
# 进度输出捕获工具
# ============================================================
class StreamlitLogger:
    """捕获 print 输出并显示在 Streamlit 中"""
    
    def __init__(self, status_container, log_container):
        self.status_container = status_container
        self.log_container = log_container
        self.logs = []
        self.original_stdout = sys.stdout
    
    def write(self, text):
        # 同时输出到原始终端
        self.original_stdout.write(text)
        
        # 过滤空行和调试信息
        text = text.strip()
        if text and not text.startswith('[调试]'):
            self.logs.append(text)
            # 保留最近20条日志
            display_logs = self.logs[-20:]
            
            # 更新日志显示
            log_text = "\n".join(display_logs)
            self.log_container.code(log_text, language=None)
            
            # 更新状态（提取关键信息）
            if '处理文档块' in text or '参数批次' in text or '处理第' in text:
                self.status_container.info(f"⏳ {text}")
            elif '找到' in text:
                self.status_container.success(f"✓ {text}")
    
    def flush(self):
        self.original_stdout.flush()


@contextmanager
def capture_output(status_container, log_container):
    """上下文管理器：捕获输出"""
    logger = StreamlitLogger(status_container, log_container)
    old_stdout = sys.stdout
    sys.stdout = logger
    try:
        yield logger
    finally:
        sys.stdout = old_stdout


# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="技术参数提取与比对平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .step-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border-radius: 0.5rem;
        border-left: 4px solid #17a2b8;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 初始化 Session State
# ============================================================
def init_session_state():
    """初始化会话状态"""
    if 'params_list' not in st.session_state:
        # 尝试从文件加载默认参数列表
        if os.path.exists("params_list.txt"):
            with open("params_list.txt", "r", encoding="utf-8") as f:
                st.session_state.params_list = f.read()
        else:
            st.session_state.params_list = ""
    
    if 'spec_database' not in st.session_state:
        # 尝试从文件加载默认规范数据库
        if os.path.exists("spec_database.json"):
            with open("spec_database.json", "r", encoding="utf-8") as f:
                st.session_state.spec_database = json.load(f)
        else:
            st.session_state.spec_database = {
                "description": "规范参数数据库",
                "type_definitions": {
                    "A": "关键参数，不可变更",
                    "B": "变更需提交审核",
                    "C": "可根据情况调整",
                    "D": "通用参数，变更需特殊申请"
                },
                "parameters": []
            }
    
    if 'extraction_result' not in st.session_state:
        st.session_state.extraction_result = None
    
    if 'comparison_result' not in st.session_state:
        st.session_state.comparison_result = None
    
    if 'uploaded_pdf_path' not in st.session_state:
        st.session_state.uploaded_pdf_path = None


# ============================================================
# 侧边栏 - 模型配置
# ============================================================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("### ⚙️ 模型配置")
        
        # 模型提供商选择
        provider = st.selectbox(
            "选择模型提供商",
            ["Azure OpenAI", "阿里云通义千问", "OpenAI", "DeepSeek", "Anthropic"],
            index=0,
            help="选择API服务提供商"
        )
        
        selected_model = ""
        
        # 根据提供商显示不同配置
        if provider == "Azure OpenAI":
            st.markdown("#### Azure OpenAI 配置")
            
            # 从环境变量获取默认值
            default_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            default_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            default_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
            
            azure_api_key = st.text_input(
                "API 密钥",
                value=default_key,
                type="password",
                help="Azure OpenAI 的 API Key",
                key="azure_api_key"
            )
            
            azure_endpoint = st.text_input(
                "终结点 (Endpoint)",
                value=default_endpoint,
                placeholder="https://your-resource.openai.azure.com",
                help="Azure OpenAI 资源的终结点URL",
                key="azure_endpoint"
            )
            
            azure_api_version = st.text_input(
                "API 版本",
                value=default_version,
                help="API版本，如 2024-10-21",
                key="azure_api_version"
            )
            
            azure_deployment = st.text_input(
                "模型部署名称",
                value="gpt-4o",
                placeholder="gpt-4o",
                help="你在Azure中创建的模型部署名称",
                key="azure_deployment"
            )
            
            # 动态设置环境变量
            if azure_api_key:
                os.environ["AZURE_OPENAI_API_KEY"] = azure_api_key
            if azure_endpoint:
                os.environ["AZURE_OPENAI_ENDPOINT"] = azure_endpoint
            if azure_api_version:
                os.environ["AZURE_OPENAI_API_VERSION"] = azure_api_version
            
            selected_model = f"azure/{azure_deployment}"
            
            # 显示当前配置状态
            if azure_api_key and azure_endpoint:
                st.success(f"✓ 已配置: {selected_model}")
            else:
                st.warning("请填写 API 密钥和终结点")
        
        elif provider == "阿里云通义千问":
            st.markdown("#### 通义千问配置")
            
            default_key = os.getenv("DASHSCOPE_API_KEY", "")
            
            dashscope_key = st.text_input(
                "DashScope API Key",
                value=default_key,
                type="password",
                help="阿里云 DashScope API Key",
                key="dashscope_key"
            )
            
            qwen_model = st.selectbox(
                "选择模型",
                ["qwen3-max", "qwen-turbo", "qwen-plus", "qwen-max"],
                index=0,
                key="qwen_model"
            )
            
            if dashscope_key:
                os.environ["DASHSCOPE_API_KEY"] = dashscope_key
                st.success(f"✓ 已配置: qwen/{qwen_model}")
            else:
                st.warning("请填写 API Key")
            
            selected_model = f"qwen/{qwen_model}"
        
        elif provider == "OpenAI":
            st.markdown("#### OpenAI 配置")
            
            default_key = os.getenv("OPENAI_API_KEY", "")
            
            openai_key = st.text_input(
                "OpenAI API Key",
                value=default_key,
                type="password",
                help="OpenAI API Key",
                key="openai_key"
            )
            
            openai_model = st.selectbox(
                "选择模型",
                ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                index=0,
                key="openai_model"
            )
            
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
                st.success(f"✓ 已配置: openai/{openai_model}")
            else:
                st.warning("请填写 API Key")
            
            selected_model = f"openai/{openai_model}"
        
        elif provider == "DeepSeek":
            st.markdown("#### DeepSeek 配置")
            
            default_key = os.getenv("DEEPSEEK_API_KEY", "")
            
            deepseek_key = st.text_input(
                "DeepSeek API Key",
                value=default_key,
                type="password",
                help="DeepSeek API Key",
                key="deepseek_key"
            )
            
            if deepseek_key:
                os.environ["DEEPSEEK_API_KEY"] = deepseek_key
                st.success("✓ 已配置: deepseek/deepseek-chat")
            else:
                st.warning("请填写 API Key")
            
            selected_model = "deepseek/deepseek-chat"
        
        elif provider == "Anthropic":
            st.markdown("#### Anthropic 配置")
            
            default_key = os.getenv("ANTHROPIC_API_KEY", "")
            
            anthropic_key = st.text_input(
                "Anthropic API Key",
                value=default_key,
                type="password",
                help="Anthropic API Key",
                key="anthropic_key"
            )
            
            anthropic_model = st.selectbox(
                "选择模型",
                ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
                index=0,
                key="anthropic_model"
            )
            
            if anthropic_key:
                os.environ["ANTHROPIC_API_KEY"] = anthropic_key
                st.success(f"✓ 已配置: anthropic/{anthropic_model}")
            else:
                st.warning("请填写 API Key")
            
            selected_model = f"anthropic/{anthropic_model}"
        
        st.markdown("---")
        st.markdown("### 📋 操作流程")
        st.markdown("""
        1. **配置API** - 填写模型API信息
        2. **上传PDF** - 上传技术协议文件
        3. **编辑参数列表** - 定义需要提取的参数
        4. **编辑规范库** - 设置规范参数要求
        5. **提取参数** - 从PDF中提取参数
        6. **比对参数** - 与规范库对比
        7. **导出报告** - 下载Excel报告
        """)
        
        st.markdown("---")
        st.markdown("### 📊 当前状态")
        
        # 显示当前状态
        params_count = len([p for p in st.session_state.params_list.split('\n') if p.strip()])
        spec_count = len(st.session_state.spec_database.get("parameters", []))
        
        st.metric("预定义参数数", params_count)
        st.metric("规范库参数数", spec_count)
        
        if st.session_state.extraction_result:
            extracted = len(st.session_state.extraction_result.get("parameters", []))
            st.metric("已提取参数数", extracted)
        
        if st.session_state.comparison_result:
            stats = st.session_state.comparison_result.get("statistics", {})
            col1, col2 = st.columns(2)
            with col1:
                st.metric("符合", stats.get("compliant", 0))
            with col2:
                st.metric("不符合", stats.get("non_compliant", 0))
        
        return selected_model


# ============================================================
# 主页面 - PDF上传
# ============================================================
def render_pdf_upload():
    """渲染PDF上传区域"""
    st.markdown('<p class="step-header">📄 步骤1：上传PDF文件</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "选择技术协议PDF文件",
        type=["pdf"],
        help="支持上传技术协议、设备规格书等PDF文档"
    )
    
    if uploaded_file is not None:
        # 保存上传的文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            st.session_state.uploaded_pdf_path = tmp_file.name
        
        st.success(f"✅ 已上传: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        return True
    
    return st.session_state.uploaded_pdf_path is not None


# ============================================================
# 主页面 - 参数列表编辑
# ============================================================
def render_params_editor():
    """渲染参数列表编辑区域"""
    st.markdown('<p class="step-header">📝 步骤2：编辑预定义参数列表</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.session_state.params_list = st.text_area(
            "参数列表（每行一个参数名称）",
            value=st.session_state.params_list,
            height=200,
            help="输入需要从PDF中提取的参数名称，每行一个"
        )
    
    with col2:
        st.markdown("**快捷操作**")
        
        # 保存到文件
        if st.button("💾 保存到文件", use_container_width=True):
            with open("params_list.txt", "w", encoding="utf-8") as f:
                f.write(st.session_state.params_list)
            st.success("已保存!")
        
        # 从文件加载
        if st.button("📂 从文件加载", use_container_width=True):
            if os.path.exists("params_list.txt"):
                with open("params_list.txt", "r", encoding="utf-8") as f:
                    st.session_state.params_list = f.read()
                st.rerun()
        
        # 统计
        params_count = len([p for p in st.session_state.params_list.split('\n') if p.strip()])
        st.info(f"共 {params_count} 个参数")


# ============================================================
# 主页面 - 规范数据库编辑
# ============================================================
def render_spec_database_editor():
    """渲染规范数据库编辑区域"""
    st.markdown('<p class="step-header">📚 步骤3：编辑规范参数数据库</p>', unsafe_allow_html=True)
    
    # 类型说明
    with st.expander("📖 参数类型说明", expanded=False):
        st.markdown("""
        | 类型 | 说明 |
        |------|------|
        | **A** | 关键参数，不可变更 |
        | **B** | 变更需提交审核 |
        | **C** | 可根据情况调整 |
        | **D** | 通用参数，变更需特殊申请 |
        """)
    
    # 参数列表编辑
    params = st.session_state.spec_database.get("parameters", [])
    
    # 添加新参数
    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
    with col1:
        new_name = st.text_input("参数名称", key="new_param_name", placeholder="例：断路器额定电流")
    with col2:
        new_value = st.text_input("规范值", key="new_param_value", placeholder="例：≤40kA")
    with col3:
        new_type = st.selectbox("类型", ["A", "B", "C", "D"], key="new_param_type")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ 添加", use_container_width=True):
            if new_name and new_value:
                params.append({"name": new_name, "value": new_value, "type": new_type})
                st.session_state.spec_database["parameters"] = params
                st.rerun()
    
    # 显示现有参数（可编辑表格）
    if params:
        st.markdown("**现有规范参数：**")
        
        # 分页显示
        page_size = 10
        total_pages = (len(params) + page_size - 1) // page_size
        
        if 'spec_page' not in st.session_state:
            st.session_state.spec_page = 0
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("⬅️ 上一页") and st.session_state.spec_page > 0:
                st.session_state.spec_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<center>第 {st.session_state.spec_page + 1} / {total_pages} 页</center>", unsafe_allow_html=True)
        with col3:
            if st.button("下一页 ➡️") and st.session_state.spec_page < total_pages - 1:
                st.session_state.spec_page += 1
                st.rerun()
        
        start_idx = st.session_state.spec_page * page_size
        end_idx = min(start_idx + page_size, len(params))
        
        for i in range(start_idx, end_idx):
            param = params[i]
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 0.5, 0.5])
            with col1:
                st.text(param.get("name", ""))
            with col2:
                st.text(param.get("value", ""))
            with col3:
                st.text(param.get("type", "D"))
            with col4:
                if st.button("🗑️", key=f"del_{i}"):
                    params.pop(i)
                    st.session_state.spec_database["parameters"] = params
                    st.rerun()
    
    # 保存/加载按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 保存规范库到文件", use_container_width=True):
            with open("spec_database.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state.spec_database, f, ensure_ascii=False, indent=2)
            st.success("已保存到 spec_database.json")
    
    with col2:
        if st.button("📂 从文件加载规范库", use_container_width=True):
            if os.path.exists("spec_database.json"):
                with open("spec_database.json", "r", encoding="utf-8") as f:
                    st.session_state.spec_database = json.load(f)
                st.rerun()
    
    with col3:
        st.info(f"共 {len(params)} 个规范参数")


# ============================================================
# 主页面 - 参数提取
# ============================================================
def render_extraction(model: str):
    """渲染参数提取区域"""
    st.markdown('<p class="step-header">🔍 步骤4：提取参数</p>', unsafe_allow_html=True)
    
    if not st.session_state.uploaded_pdf_path:
        st.warning("请先上传PDF文件")
        return
    
    params_list = [p.strip() for p in st.session_state.params_list.split('\n') if p.strip()]
    if not params_list:
        st.warning("请先填写预定义参数列表")
        return
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        start_extraction = st.button("🚀 开始提取", type="primary", use_container_width=True)
    
    with col2:
        if st.session_state.extraction_result:
            stats = st.session_state.extraction_result.get("statistics", {})
            st.markdown(f"""
            <div class="success-box">
            <b>提取结果：</b> 找到 {stats.get('found', 0)} 个参数，未找到 {stats.get('not_found', 0)} 个
            </div>
            """, unsafe_allow_html=True)
    
    # 提取逻辑（放在按钮判断外，确保进度显示正常）
    if start_extraction:
        st.markdown("---")
        st.markdown("#### 📊 提取进度")
        
        # 创建进度显示区域
        status_placeholder = st.empty()
        progress_bar = st.progress(0, text="准备中...")
        log_placeholder = st.empty()
        
        status_placeholder.info("⏳ 正在初始化提取器...")
        
        try:
            # 创建提取器
            extractor = ParamsExtractor(model=model)
            extractor.params_list = params_list
            
            status_placeholder.info(f"⏳ 正在转换PDF文档... (模型: {model})")
            progress_bar.progress(10, text="转换PDF文档中...")
            
            # 使用输出捕获执行提取
            with capture_output(status_placeholder, log_placeholder):
                result = extractor.extract(st.session_state.uploaded_pdf_path)
            
            st.session_state.extraction_result = result
            
            progress_bar.progress(100, text="提取完成!")
            status_placeholder.success(f"✅ 提取完成！找到 {len(result.get('parameters', []))} 个参数")
            
            # 延迟刷新以显示结果
            import time
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            progress_bar.progress(100, text="提取失败")
            status_placeholder.error(f"❌ 提取失败: {str(e)}")
            log_placeholder.code(str(e))
    
    # 显示提取结果
    if st.session_state.extraction_result:
        with st.expander("📋 查看提取结果", expanded=True):
            params = st.session_state.extraction_result.get("parameters", [])
            
            if params:
                # 转换为表格显示
                table_data = []
                for p in params:
                    table_data.append({
                        "参数名": p.get("name", ""),
                        "值": p.get("value", ""),
                        "单位": p.get("unit", ""),
                        "原文": p.get("original_text", "")[:50] + "..." if len(p.get("original_text", "")) > 50 else p.get("original_text", "")
                    })
                st.dataframe(table_data, use_container_width=True)
            
            # 显示未找到的参数
            not_found = st.session_state.extraction_result.get("not_found", [])
            if not_found:
                st.warning(f"未提取到的参数 ({len(not_found)}个): {', '.join(not_found[:10])}{'...' if len(not_found) > 10 else ''}")


# ============================================================
# 主页面 - 参数比对
# ============================================================
def render_comparison(model: str):
    """渲染参数比对区域"""
    st.markdown('<p class="step-header">⚖️ 步骤5：参数比对</p>', unsafe_allow_html=True)
    
    if not st.session_state.extraction_result:
        st.warning("请先完成参数提取")
        return
    
    spec_params = st.session_state.spec_database.get("parameters", [])
    if not spec_params:
        st.warning("请先填写规范参数数据库")
        return
    
    # 显示当前比对信息
    extracted_count = len(st.session_state.extraction_result.get("parameters", []))
    st.info(f"📋 将使用 **{extracted_count}** 个已提取参数与 **{len(spec_params)}** 个规范参数进行比对")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        start_comparison = st.button("🔄 开始比对", type="primary", use_container_width=True)
    
    with col2:
        if st.session_state.comparison_result:
            stats = st.session_state.comparison_result.get("statistics", {})
            st.markdown(f"""
            <div class="info-box">
            <b>比对结果：</b> 符合 {stats.get('compliant', 0)} | 不符合 {stats.get('non_compliant', 0)} | 未匹配 {stats.get('no_match', 0)}
            </div>
            """, unsafe_allow_html=True)
    
    # 比对逻辑
    if start_comparison:
        st.markdown("---")
        st.markdown("#### 📊 比对进度")
        
        # 创建进度显示区域
        status_placeholder = st.empty()
        progress_bar = st.progress(0, text="准备中...")
        log_placeholder = st.empty()
        
        status_placeholder.info(f"⏳ 正在初始化比对器... (模型: {model})")
        progress_bar.progress(10, text="初始化中...")
        
        try:
            # 创建比对器
            comparator = ParamComparator(model=model)
            comparator.spec_params = spec_params
            
            status_placeholder.info("⏳ 正在进行语义匹配比对...")
            progress_bar.progress(20, text="比对中...")
            
            # 使用输出捕获执行比对
            with capture_output(status_placeholder, log_placeholder):
                result = comparator.compare(st.session_state.extraction_result)
            
            st.session_state.comparison_result = result
            
            stats = result.get("statistics", {})
            progress_bar.progress(100, text="比对完成!")
            status_placeholder.success(f"✅ 比对完成！符合 {stats.get('compliant', 0)} 个，不符合 {stats.get('non_compliant', 0)} 个")
            
            # 延迟刷新以显示结果
            import time
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            progress_bar.progress(100, text="比对失败")
            status_placeholder.error(f"❌ 比对失败: {str(e)}")
            log_placeholder.code(str(e))
    
    # 显示比对结果
    if st.session_state.comparison_result:
        tab1, tab2, tab3, tab4 = st.tabs(["✅ 符合规范", "❌ 不符合规范", "❓ 未匹配", "📊 统计"])
        
        with tab1:
            compliant = st.session_state.comparison_result.get("compliant_params", [])
            if compliant:
                table_data = [{
                    "用户参数": p.get("user_param_name", ""),
                    "用户值": p.get("user_value", ""),
                    "规范参数": p.get("matched_spec_name", ""),
                    "规范值": p.get("spec_value", ""),
                    "类型": p.get("param_type", "")
                } for p in compliant]
                st.dataframe(table_data, use_container_width=True)
            else:
                st.info("没有符合规范的参数")
        
        with tab2:
            non_compliant = st.session_state.comparison_result.get("non_compliant_params", [])
            if non_compliant:
                table_data = [{
                    "用户参数": p.get("user_param_name", ""),
                    "用户值": p.get("user_value", ""),
                    "规范参数": p.get("matched_spec_name", ""),
                    "规范值": p.get("spec_value", ""),
                    "类型": p.get("param_type", "")
                } for p in non_compliant]
                st.dataframe(table_data, use_container_width=True)
            else:
                st.success("没有不符合规范的参数")
        
        with tab3:
            no_match = st.session_state.comparison_result.get("no_match_params", [])
            if no_match:
                table_data = [{
                    "用户参数": p.get("user_param_name", ""),
                    "用户值": p.get("user_value", "")
                } for p in no_match]
                st.dataframe(table_data, use_container_width=True)
            else:
                st.info("所有参数都已匹配到规范")
        
        with tab4:
            stats = st.session_state.comparison_result.get("statistics", {})
            type_stats = st.session_state.comparison_result.get("type_statistics", {})
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("符合规范", stats.get("compliant", 0))
            with col2:
                st.metric("不符合规范", stats.get("non_compliant", 0))
            with col3:
                st.metric("未匹配", stats.get("no_match", 0))
            with col4:
                st.metric("无法判断", stats.get("uncertain", 0))
            
            st.markdown("**按类型统计：**")
            for ptype in ["A", "B", "C", "D"]:
                data = type_stats.get(ptype, {})
                st.write(f"- **{ptype}类**: 符合 {data.get('compliant', 0)}, 不符合 {data.get('non_compliant', 0)}")


# ============================================================
# 主页面 - 导出报告
# ============================================================
def render_export():
    """渲染导出报告区域"""
    st.markdown('<p class="step-header">📥 步骤6：导出Excel报告</p>', unsafe_allow_html=True)
    
    if not st.session_state.comparison_result:
        st.warning("请先完成参数比对")
        return
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("📊 生成Excel报告", type="primary", use_container_width=True):
            with st.spinner("正在生成报告..."):
                try:
                    # 生成临时文件
                    timestamp = datetime.now().strftime("%m_%d_%H%M")
                    output_path = os.path.join(tempfile.gettempdir(), f"report_{timestamp}.xlsx")
                    
                    # 导出Excel
                    export_to_excel(
                        st.session_state.comparison_result,
                        st.session_state.extraction_result,
                        output_path
                    )
                    
                    # 读取文件用于下载
                    with open(output_path, "rb") as f:
                        excel_data = f.read()
                    
                    st.session_state.excel_data = excel_data
                    st.session_state.excel_filename = f"参数比对报告_{timestamp}.xlsx"
                    st.success("✅ 报告生成成功！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"生成报告失败: {str(e)}")
    
    with col2:
        if 'excel_data' in st.session_state and st.session_state.excel_data:
            st.download_button(
                label="⬇️ 下载Excel报告",
                data=st.session_state.excel_data,
                file_name=st.session_state.excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# ============================================================
# 主函数
# ============================================================
def main():
    """主函数"""
    # 初始化
    init_session_state()
    
    # 标题
    st.markdown('<p class="main-header">📊 技术参数提取与比对平台</p>', unsafe_allow_html=True)
    st.markdown("基于大语言模型的PDF技术协议参数自动提取与规范符合性检查工具")
    st.markdown("---")
    
    # 侧边栏
    selected_model = render_sidebar()
    
    # 主内容区 - 使用标签页组织
    tab1, tab2, tab3 = st.tabs(["📄 文件上传与提取", "📚 规范数据库", "📊 比对与导出"])
    
    with tab1:
        render_pdf_upload()
        st.markdown("---")
        render_params_editor()
        st.markdown("---")
        render_extraction(selected_model)
    
    with tab2:
        render_spec_database_editor()
    
    with tab3:
        render_comparison(selected_model)
        st.markdown("---")
        render_export()


if __name__ == "__main__":
    main()
