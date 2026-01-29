import tiktoken
from litellm import completion, litellm
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

#litellm.set_verbose=True

# 阿里云 DashScope OpenAI 兼容 API 地址
DASHSCOPE_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def is_qwen_model(model: str) -> bool:
    """检查是否是通义千问模型"""
    return model.startswith("qwen/")

def is_azure_model(model: str) -> bool:
    """检查是否是 Azure OpenAI 模型（LiteLLM 命名约定）"""
    return model.startswith("azure/")

def _get_azure_openai_config() -> tuple[str | None, str | None, str | None]:
    """
    获取 Azure OpenAI 配置。

    兼容两套环境变量：
    1) 本项目新增（避免影响既有环境变量命名）：AZURE_OPENAI_*
    2) LiteLLM 传统命名：AZURE_API_*
    """
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY")
    api_base = (
        os.getenv("AZURE_OPENAI_API_BASE")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
        or os.getenv("AZURE_API_BASE")
    )
    api_version = os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("AZURE_API_VERSION")
    return api_key, api_base, api_version

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def count_messages(messages, encoding_name='o200k_base'):
    """Only count tokens for type text i.e. images are not count

    Args:
        messages (_type_): message array of form [
                                                    {
                                                    "role": "user",
                                                    "content": [{"type": "text", "text": prompt}, ...],
                                                    }
                                                ]
        encoding_name (str, optional): _description_. Defaults to 'o200k_base'.

    Returns:
        _type_: _description_
    """
    count = 0
    for m in messages:
        for m_c in m['content']:
            if m_c['type'] == 'text':
                count += num_tokens_from_string(m_c['text'], encoding_name)
    
    return count

def chat_completion_request(messages, tools=None, tool_choice=None, response_format=None, model="gpt-4o-mini", log_token_usage=False, temp=0.3, top_p=1.0):

    try:
        # 检查是否是通义千问模型
        if is_qwen_model(model):
            # 使用 OpenAI 兼容模式调用阿里云 DashScope
            # 模型名称格式：qwen/qwen-max -> qwen-max
            actual_model = model.replace("qwen/", "")
            api_key = os.getenv("DASHSCOPE_API_KEY")
            
            print(f"[调试] 检测到通义千问模型: {model}")
            print(f"[调试] 实际调用模型: openai/{actual_model}")
            print(f"[调试] API Base: {DASHSCOPE_API_BASE}")
            print(f"[调试] API Key 已设置: {bool(api_key)}")
            
            if not api_key:
                raise ValueError("DASHSCOPE_API_KEY 环境变量未设置，请在 .env 文件中配置")
            
            response = completion(
                model=f"openai/{actual_model}",  # 使用 openai/ 前缀
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                max_tokens=4096,
                temperature=temp,
                api_base=DASHSCOPE_API_BASE,
                api_key=api_key,
            )
            print(f"[调试] 通义千问调用成功!")
        elif is_azure_model(model):
            api_key, api_base, api_version = _get_azure_openai_config()

            if not api_key:
                raise ValueError("Azure OpenAI 未配置 API Key：请设置 AZURE_OPENAI_API_KEY（或兼容的 AZURE_API_KEY）")
            if not api_base:
                raise ValueError("Azure OpenAI 未配置 Endpoint：请设置 AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_BASE（或兼容的 AZURE_API_BASE）")

            response = completion(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                max_tokens=4096,
                temperature=temp,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
            )
        else:
            print(f"[调试] 使用其他模型: {model}")
            # 其他模型（OpenAI、Azure 等）
            response = completion(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                max_tokens=4096,
                temperature=temp,
            )

        if log_token_usage:
            print('Actual Token Usage {}: {}'.format(model, getattr(response, 'usage', 'N/A')))
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        raise  # Re-raise the exception instead of returning it


def complete_chat(model: str, messages: list, temperature: float = 0.3, 
                  response_format: dict = None, max_tokens: int = 8192) -> str:
    """
    简化的聊天补全函数，直接返回文本内容
    
    Args:
        model: 模型名称，如 "qwen/qwen-turbo"
        messages: 消息列表
        temperature: 温度参数
        response_format: 响应格式
        max_tokens: 最大token数
    
    Returns:
        str: 模型返回的文本内容
    """
    try:
        # 检查是否是通义千问模型
        if is_qwen_model(model):
            actual_model = model.replace("qwen/", "")
            api_key = os.getenv("DASHSCOPE_API_KEY")
            
            if not api_key:
                raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
            
            # Qwen 模型 max_tokens 上限是 8192
            max_tokens = min(max_tokens, 8192)
            
            response = completion(
                model=f"openai/{actual_model}",
                messages=messages,
                response_format=response_format,
                max_tokens=max_tokens,
                temperature=temperature,
                api_base=DASHSCOPE_API_BASE,
                api_key=api_key,
            )
        elif is_azure_model(model):
            api_key, api_base, api_version = _get_azure_openai_config()

            if not api_key:
                raise ValueError("Azure OpenAI 未配置 API Key：请设置 AZURE_OPENAI_API_KEY（或兼容的 AZURE_API_KEY）")
            if not api_base:
                raise ValueError("Azure OpenAI 未配置 Endpoint：请设置 AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_BASE（或兼容的 AZURE_API_BASE）")

            response = completion(
                model=model,
                messages=messages,
                response_format=response_format,
                max_tokens=max_tokens,
                temperature=temperature,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
            )
        else:
            response = completion(
                model=model,
                messages=messages,
                response_format=response_format,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"LLM调用失败: {e}")
        raise