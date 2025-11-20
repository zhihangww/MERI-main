"""
测试脚本：验证模型是否支持多模态功能

此脚本用于测试 Together AI、Groq 或其他模型是否支持 MERI 项目需要的多模态功能：
1. 文本 + 图片（base64 格式）
2. 函数调用（tools）
3. JSON 格式输出（response_format）

使用方法：
1. 在 .env 文件中配置对应的 API Key
2. 修改下面的 model_name 变量
3. 运行：python test_multimodal_support.py
"""

from litellm import completion
import os
from dotenv import load_dotenv
import base64

# 加载环境变量
load_dotenv()

def create_test_image_base64():
    """创建一个简单的测试图片（1x1 红色像素）的 base64 编码"""
    # 创建一个最小的 PNG 图片（1x1 红色像素）
    # 这是一个有效的 PNG 图片的 base64 编码
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return f"data:image/png;base64,{png_base64}"

def test_multimodal_support(model_name):
    """测试模型是否支持多模态功能"""
    
    print("=" * 60)
    print(f"测试模型：{model_name}")
    print("=" * 60)
    
    # 创建测试消息（包含文本和图片）
    test_image = create_test_image_base64()
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请描述这张图片中的内容。如果能看到图片，请回答'我看到了图片'，否则请说明错误原因。"},
                {"type": "image_url", "image_url": {"url": test_image}}
            ]
        }
    ]
    
    print("\n📝 测试 1：多模态支持（文本 + 图片）")
    print("-" * 60)
    
    try:
        response = completion(
            model=model_name,
            messages=messages,
            max_tokens=100,
            temperature=0.0,
        )
        
        print("✅ API 调用成功！")
        print(f"📄 响应内容：{response.choices[0].message.content}")
        
        # 检查响应是否表明看到了图片
        response_text = response.choices[0].message.content.lower()
        if "图片" in response_text or "image" in response_text or "看到" in response_text:
            print("✅ 多模态支持：模型能够处理图片")
            multimodal_supported = True
        else:
            print("⚠️  多模态支持：不确定（请查看响应内容）")
            multimodal_supported = None
            
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        print("❌ 多模态支持：不支持或配置错误")
        multimodal_supported = False
        return multimodal_supported
    
    print("\n📝 测试 2：函数调用支持（tools）")
    print("-" * 60)
    
    # 创建简单的函数调用测试
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称"}
                },
                "required": ["location"]
            }
        }
    }]
    
    text_messages = [
        {"role": "user", "content": "北京今天天气怎么样？"}
    ]
    
    try:
        response = completion(
            model=model_name,
            messages=text_messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=100,
            temperature=0.0,
        )
        
        print("✅ API 调用成功！")
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            print("✅ 函数调用支持：模型支持 tools 参数")
            tools_supported = True
        else:
            print("⚠️  函数调用支持：模型可能不支持或未触发函数调用")
            tools_supported = None
            
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        print("❌ 函数调用支持：不支持或配置错误")
        tools_supported = False
    
    print("\n📝 测试 3：JSON 格式输出支持（response_format）")
    print("-" * 60)
    
    json_messages = [
        {"role": "user", "content": "请以 JSON 格式返回：{\"name\": \"测试\", \"value\": 123}"}
    ]
    
    try:
        response = completion(
            model=model_name,
            messages=json_messages,
            response_format={"type": "json_object"},
            max_tokens=100,
            temperature=0.0,
        )
        
        print("✅ API 调用成功！")
        print(f"📄 响应内容：{response.choices[0].message.content}")
        
        # 尝试解析 JSON
        import json
        try:
            json.loads(response.choices[0].message.content)
            print("✅ JSON 格式输出支持：模型支持 response_format")
            json_supported = True
        except:
            print("⚠️  JSON 格式输出支持：响应不是有效的 JSON（可能通过 prompt 实现）")
            json_supported = None
            
    except Exception as e:
        error_msg = str(e).lower()
        if "response_format" in error_msg or "json" in error_msg:
            print(f"❌ API 调用失败：{e}")
            print("❌ JSON 格式输出支持：不支持 response_format 参数")
            print("💡 提示：可以通过在 prompt 中要求 JSON 格式来替代")
            json_supported = False
        else:
            print(f"❌ API 调用失败：{e}")
            json_supported = False
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"多模态支持（文本+图片）：{'✅ 支持' if multimodal_supported else '❌ 不支持' if multimodal_supported is False else '⚠️  不确定'}")
    print(f"函数调用支持（tools）：{'✅ 支持' if tools_supported else '❌ 不支持' if tools_supported is False else '⚠️  不确定'}")
    print(f"JSON 格式输出支持：{'✅ 支持' if json_supported else '❌ 不支持' if json_supported is False else '⚠️  不确定'}")
    
    print("\n💡 建议：")
    if multimodal_supported:
        print("  ✅ 模型支持多模态，可以用于 MERI 项目")
    else:
        print("  ❌ 模型不支持多模态，无法用于 MERI 项目（需要处理 PDF 中的图片）")
        print("  💡 建议尝试其他模型，如 Hugging Face 的多模态模型")
    
    if not tools_supported:
        print("  ⚠️  模型可能不支持函数调用，MERI 项目可能需要此功能")
    
    if not json_supported:
        print("  ⚠️  模型不支持 response_format，但可以通过 prompt 要求 JSON 格式")
    
    return {
        "multimodal": multimodal_supported,
        "tools": tools_supported,
        "json": json_supported
    }

if __name__ == "__main__":
    # 在这里修改要测试的模型名称
    # 示例：
    # model_name = "together_ai/llava-1.5-7b"
    # model_name = "groq/llama-3.2-11b-vision-preview"
    # model_name = "huggingface/Qwen/Qwen2-VL-2B-Instruct"
    # model_name = "gemini/gemini-1.5-flash"
    
    print("请修改脚本中的 model_name 变量来测试不同的模型")
    print("\n可测试的模型示例：")
    print("  - together_ai/llava-1.5-7b")
    print("  - groq/llama-3.2-11b-vision-preview")
    print("  - huggingface/Qwen/Qwen2-VL-2B-Instruct")
    print("  - gemini/gemini-1.5-flash")
    print()
    
    # 取消下面的注释并修改模型名称来测试
    # model_name = "together_ai/llava-1.5-7b"
    # test_multimodal_support(model_name)




