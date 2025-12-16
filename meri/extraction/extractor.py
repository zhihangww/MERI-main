from .iterative_json_completion import (
    IterativeJsonPopulator,
    IterativePopulationStrategies,
)

from meri.intermediate_format.format_handler import BasicFormatHandler
import json

def create_openai_tools_arr(func_name, func_desc, output_schema):


    tools = [{
        "type": "function",
        "function": {
            "name": func_name,
            "description": func_desc,
            "parameters": output_schema
            }
    }]
    return tools


def check_not_found_params(results: dict, schema: dict) -> dict:
    """
    后处理：检查未提取到的参数，添加到 notFoundList
    """
    # 确保 notFoundList 存在
    if 'notFoundList' not in results:
        results['notFoundList'] = []
    
    # 获取 schema 中定义的参数
    tech_specs_schema = schema.get('properties', {}).get('technicalSpecifications', {}).get('properties', {})
    if not tech_specs_schema:
        return results
    
    # 获取实际提取的参数
    tech_specs_result = results.get('technicalSpecifications', {})
    
    # 检查每个参数
    for param_name in tech_specs_schema.keys():
        param_data = tech_specs_result.get(param_name, {})
        param_props = param_data.get('parameter_properties', {}) if param_data else {}
        value = param_props.get('value') if param_props else None
        
        # 如果没有有效值且不在 notFoundList 中
        has_valid_value = value is not None and value != ""
        if not has_valid_value and param_name not in results['notFoundList']:
            results['notFoundList'].append(param_name)
    
    return results


class JsonExtractor:

    def __init__(self, intermediate_format: BasicFormatHandler, chunks_max_characters=450000, chunk_overlap=1, n_rounds=1, model='gpt-4o-mini', model_temp=0.3) -> None:
        
        self.intermediate_format = intermediate_format # markdown or html
        self.model = model

        self.chunks_max_characters = chunks_max_characters
        self.chunk_overlap = chunk_overlap
        self.n_rounds = n_rounds
        self.temp = model_temp

    def populate_schema(self, json_schema_string: str):
        """Populates json file based on provided json_schema

        Args:
            json_schema_string (str): _description_
        """
        chunks = self.intermediate_format.chunk(character_threshold=self.chunks_max_characters, overlap=self.chunk_overlap)
        print(f"Number of chunks: {len(chunks)}")
        content_chunks = [self.intermediate_format.prepare_gpt_message_content(chunk) for chunk in chunks]
        print(f"Number of content chunks: {len(content_chunks)}")
        populator = IterativeJsonPopulator(json_schema_string, IterativePopulationStrategies.SELFSUPERVISED.value, n_rounds=self.n_rounds, model = self.model,
                                           temp=self.temp)
        results = populator.complete(content_chunks)
        
        # 后处理：确保未找到的参数在 notFoundList 中
        schema = json.loads(json_schema_string)
        results = check_not_found_params(results, schema)

        return results