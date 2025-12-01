"""
HTML后处理工具
用于处理PDF转HTML后的布局问题，特别是左右分离的键值对
"""
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict
import html as html_module


def extract_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """从bbox字符串提取坐标
    
    Args:
        bbox_str: 格式如 "[113.09, 263.28, 181.42, 276.89]"
    
    Returns:
        (x1, y1, x2, y2) 坐标元组
    """
    try:
        bbox_str = bbox_str.strip('[]')
        coords = [float(x.strip()) for x in bbox_str.split(',')]
        return tuple(coords)
    except:
        return (0, 0, 0, 0)


def is_vertically_aligned(bbox1: Tuple[float, float, float, float],
                          bbox2: Tuple[float, float, float, float],
                          tolerance: float = 15.0) -> bool:
    """判断两个bbox是否垂直对齐（y坐标接近）
    
    Args:
        bbox1: 第一个bbox (x1, y1, x2, y2)
        bbox2: 第二个bbox (x1, y1, x2, y2)
        tolerance: y坐标差异容忍度（像素）
    
    Returns:
        如果两个bbox在同一水平线上返回True
    """
    _, y1_1, _, y1_2 = bbox1
    _, y2_1, _, y2_2 = bbox2
    
    # 计算中心y坐标
    center_y1 = (y1_1 + y1_2) / 2
    center_y2 = (y2_1 + y2_2) / 2
    
    return abs(center_y1 - center_y2) < tolerance


def is_right_of(bbox1: Tuple[float, float, float, float],
                bbox2: Tuple[float, float, float, float],
                min_gap: float = 50.0) -> bool:
    """判断bbox2是否在bbox1的右侧
    
    Args:
        bbox1: 左侧bbox (x1, y1, x2, y2)
        bbox2: 右侧bbox (x1, y1, x2, y2)
        min_gap: 最小间隔（像素）
    
    Returns:
        如果bbox2在bbox1右侧且有适当间隔返回True
    """
    x1_1, _, x1_2, _ = bbox1
    x2_1, _, _, _ = bbox2
    
    # bbox2的左边界应该在bbox1的右边界之后
    return x2_1 - x1_2 > min_gap


def sort_html_by_position(html_str: str, y_group_threshold: float = 5.0) -> str:
    """按照阅读顺序排序HTML元素（从上到下，从左到右）
    
    关键：
    1. 先拆散<ul>，把每个<li>当作独立元素
    2. 按页码分组（page_index）
    3. 每页内按y坐标分组（差异<5像素认为同一行）
    4. 同一行内按x坐标排序（从左到右）
    
    Args:
        html_str: 原始HTML字符串
        y_group_threshold: y坐标差异小于此值认为是同一行（默认5像素）
    
    Returns:
        排序后的HTML字符串
    """
    parts = html_str.split('\n\n')
    
    # 解析每个部分，提取位置信息
    elements_by_page = {}  # {page_index: [elements]}
    elements_without_pos = []  # 没有位置信息的元素
    
    for part in parts:
        if not part.strip():
            continue
        
        try:
            # 检查是否是<ul>容器
            if '<ul className="list_wrapper">' in part and '</ul>' in part:
                # 拆散<ul>，提取每个<li>作为独立元素
                root = ET.fromstring(part)
                for li in root.findall('.//li'):
                    bbox_str = li.get('bbox')
                    page_index = li.get('page_index')
                    
                    if bbox_str and page_index:
                        bbox = extract_bbox(bbox_str)
                        x1, y1, _, y2 = bbox
                        page_idx = int(page_index)
                        
                        if page_idx not in elements_by_page:
                            elements_by_page[page_idx] = []
                        
                        # 将<li>转换为字符串
                        li_html = ET.tostring(li, encoding='unicode')
                        elements_by_page[page_idx].append({
                            'html': li_html,
                            'x': x1,
                            'y': y1,
                            'bbox': bbox,
                            'type': 'li'
                        })
                    else:
                        # <li>没有位置信息，保留
                        elements_without_pos.append(ET.tostring(li, encoding='unicode'))
                continue  # 处理完这个<ul>，跳到下一个part
            
            # 尝试从HTML中提取bbox和page_index
            root = ET.fromstring(part)
            bbox_str = root.get('bbox')
            page_index = root.get('page_index')
            
            if bbox_str and page_index:
                bbox = extract_bbox(bbox_str)
                x1, y1, _, y2 = bbox
                page_idx = int(page_index)
                
                if page_idx not in elements_by_page:
                    elements_by_page[page_idx] = []
                
                elements_by_page[page_idx].append({
                    'html': part,
                    'x': x1,
                    'y': y1,
                    'bbox': bbox,
                    'type': root.tag
                })
            else:
                # 没有位置信息的元素
                elements_without_pos.append(part)
        except Exception as e:
            # 解析失败的元素
            elements_without_pos.append(part)
    
    # 对每一页单独排序，保持页面顺序
    all_sorted_parts = []
    
    # 先放没有位置信息的元素
    all_sorted_parts.extend(elements_without_pos)
    
    # 然后按页码顺序处理每一页
    for page_idx in sorted(elements_by_page.keys()):
        page_elements = elements_by_page[page_idx]
        
        # 先按y坐标粗略排序
        page_elements.sort(key=lambda e: e['y'])
        
        # 然后按y分组，组内按x排序
        sorted_page_elements = []
        current_group = []
        last_y = -1
        
        for elem in page_elements:
            if not current_group:
                # 第一个元素
                current_group = [elem]
                last_y = elem['y']
            elif abs(elem['y'] - last_y) < y_group_threshold:
                # 同一行（y差异<5像素）
                current_group.append(elem)
            else:
                # 新的一行，先处理当前组
                current_group.sort(key=lambda e: e['x'])
                sorted_page_elements.extend(current_group)
                # 开始新组
                current_group = [elem]
                last_y = elem['y']
        
        # 处理最后一组
        if current_group:
            current_group.sort(key=lambda e: e['x'])
            sorted_page_elements.extend(current_group)
        
        # 把这一页的排序结果添加到总结果中
        all_sorted_parts.extend([e['html'] for e in sorted_page_elements])
    
    return '\n\n'.join(all_sorted_parts)


def merge_aligned_key_values_sequential(html_str: str,
                                       y_first_match_tolerance: float = 5.0,
                                       y_subsequent_tolerance: float = 60.0,
                                       x_subsequent_tolerance: float = 60.0) -> str:
    """基于正确排序的HTML，按顺序合并键值对
    
    算法：
    1. HTML已按阅读顺序排列（从上到下，从左到右）
    2. 遍历元素，遇到<li>记录为"当前参数"
    3. 遇到<div>时：
       - 首次匹配：y接近当前参数(<5px) 且 x在右侧 → 匹配
       - 后续匹配：y在上一个值下方 且 x对齐 → 匹配
    4. 遇到新的<li>时，完成当前参数，开始新参数
    
    Args:
        html_str: 已排序的HTML字符串
        y_first_match_tolerance: 首次匹配的y容差（默认5px，严格同行）
        y_subsequent_tolerance: 后续匹配的y容差（默认60px）
        x_subsequent_tolerance: 后续匹配的x容差（默认60px）
    
    Returns:
        合并后的HTML字符串
    """
    import html as html_module
    
    parts = [p.strip() for p in html_str.split('\n\n') if p.strip()]
    
    result_parts = []
    current_param = None  # {'text': str, 'bbox': tuple, 'page_index': str, 'values': []}
    
    for part in parts:
        try:
            root = ET.fromstring(part)
            tag = root.tag
            bbox_str = root.get('bbox')
            page_index = root.get('page_index')
            text = root.text or ''
            
            if not bbox_str or not page_index:
                # 没有位置信息，直接输出
                result_parts.append(part)
                continue
            
            bbox = extract_bbox(bbox_str)
            
            if tag == 'li':
                # 遇到新的参数，先完成当前参数
                if current_param and current_param['values']:
                    # 输出合并后的参数
                    merged_text = current_param['text'] + ": " + "; ".join([v['text'] for v in current_param['values']])
                    merged_bbox_str = str(list(current_param['bbox']))
                    result_parts.append(
                        f'<div className="merged_key_value" bbox="{merged_bbox_str}" page_index="{current_param["page_index"]}">{html_module.escape(merged_text)}</div>'
                    )
                elif current_param:
                    # 参数没有匹配到值，保留原样
                    result_parts.append(
                        f'<li bbox="{str(list(current_param["bbox"]))}" page_index="{current_param["page_index"]}" className="listitem_wrapper">{html_module.escape(current_param["text"])}</li>'
                    )
                
                # 开始新参数
                current_param = {
                    'text': text,
                    'bbox': bbox,
                    'page_index': page_index,
                    'values': []
                }
            
            elif tag == 'div':
                div_x, div_y1, _, div_y2 = bbox
                div_y_center = (div_y1 + div_y2) / 2
                
                matched = False
                
                # 尝试匹配到当前参数
                if current_param and current_param['page_index'] == page_index:
                    param_x1, param_y1, param_x2, param_y2 = current_param['bbox']
                    param_y_center = (param_y1 + param_y2) / 2
                    
                    # 首次匹配：参数还没有值，且div在同一行右侧
                    if len(current_param['values']) == 0:
                        # 检查：y接近，x在右侧
                        y_diff = abs(div_y_center - param_y_center)
                        x_is_right = div_x > param_x2 + 50  # div在参数右侧至少50px
                        
                        if y_diff < y_first_match_tolerance and x_is_right:
                            current_param['values'].append({'text': text, 'bbox': bbox})
                            matched = True
                    
                    # 后续匹配：参数已有值，检查是否在最后一个值下方
                    elif len(current_param['values']) > 0:
                        last_value = current_param['values'][-1]
                        last_x1, last_y1, last_x2, last_y2 = last_value['bbox']
                        
                        # 检查：y在下方，x对齐
                        y_distance = div_y1 - last_y2
                        x_distance = abs(div_x - last_x1)
                        
                        if 0 <= y_distance < y_subsequent_tolerance and x_distance < x_subsequent_tolerance:
                            current_param['values'].append({'text': text, 'bbox': bbox})
                            matched = True
                
                # 如果没匹配到，作为独立元素输出
                if not matched:
                    result_parts.append(part)
            
            else:
                # 其他标签（h1, h2等），先完成当前参数
                if current_param and current_param['values']:
                    merged_text = current_param['text'] + ": " + "; ".join([v['text'] for v in current_param['values']])
                    merged_bbox_str = str(list(current_param['bbox']))
                    result_parts.append(
                        f'<div className="merged_key_value" bbox="{merged_bbox_str}" page_index="{current_param["page_index"]}">{html_module.escape(merged_text)}</div>'
                    )
                elif current_param:
                    result_parts.append(
                        f'<li bbox="{str(list(current_param["bbox"]))}" page_index="{current_param["page_index"]}" className="listitem_wrapper">{html_module.escape(current_param["text"])}</li>'
                    )
                current_param = None
                
                # 输出当前标签
                result_parts.append(part)
        
        except Exception as e:
            # 解析失败，直接输出
            result_parts.append(part)
    
    # 处理最后一个参数
    if current_param and current_param['values']:
        merged_text = current_param['text'] + ": " + "; ".join([v['text'] for v in current_param['values']])
        merged_bbox_str = str(list(current_param['bbox']))
        result_parts.append(
            f'<div className="merged_key_value" bbox="{merged_bbox_str}" page_index="{current_param["page_index"]}">{html_module.escape(merged_text)}</div>'
        )
    elif current_param:
        result_parts.append(
            f'<li bbox="{str(list(current_param["bbox"]))}" page_index="{current_param["page_index"]}" className="listitem_wrapper">{html_module.escape(current_param["text"])}</li>'
        )
    
    return '\n\n'.join(result_parts)


def merge_aligned_key_values(html_str: str, 
                            x_threshold: float = 300.0,
                            y_tolerance: float = 15.0) -> str:
    """合并垂直对齐的键值对
    
    处理这种情况：
    <li>(1) 额定电压</li>     在x<200位置
    <div>145kV</div>           在x>300位置，y坐标接近
    
    转换为：
    <div>(1) 额定电压: 145kV</div>
    
    Args:
        html_str: 原始HTML字符串
        x_threshold: 用于区分左右两侧的x坐标阈值
        y_tolerance: y坐标对齐容忍度
    
    Returns:
        处理后的HTML字符串
    """
    # 注意：html_str应该已经在enhance_html_for_extraction中排序过了
    parts = html_str.split('\n\n')
    processed_parts = []
    i = 0
    
    while i < len(parts):
        part = parts[i].strip()
        
        if not part:
            i += 1
            continue
        
        # 检查是否是列表
        if '<ul className="list_wrapper">' in part and '</ul>' in part:
            # 提取列表项
            try:
                root = ET.fromstring(part)
                list_items = []
                
                for li in root.findall('.//li'):
                    bbox_str = li.get('bbox', '[0,0,0,0]')
                    page_index = li.get('page_index', '0')
                    text = li.text or ''
                    bbox = extract_bbox(bbox_str)
                    
                    list_items.append({
                        'text': text,
                        'bbox': bbox,
                        'page_index': page_index,
                        'matched': False,
                        'values': []  # 支持多个值
                    })
                
                # 尝试在后续的div中找到匹配的值
                matched_any = False
                values_to_remove = []
                
                # 收集所有后续的div（按顺序）
                all_divs = []
                j = i + 1
                while j < len(parts) and j < i + 20:
                    next_part = parts[j].strip()
                    if next_part.startswith('<div className="text_wrapper"'):
                        try:
                            div_root = ET.fromstring(next_part)
                            div_bbox_str = div_root.get('bbox', '[0,0,0,0]')
                            div_page_index = div_root.get('page_index', '0')
                            div_text = div_root.text or ''
                            div_bbox = extract_bbox(div_bbox_str)
                            
                            all_divs.append({
                                'idx': j,
                                'bbox': div_bbox,
                                'text': div_text,
                                'page_index': div_page_index,
                                'matched_item': None  # 记录匹配给哪个列表项
                            })
                        except:
                            pass
                    j += 1
                
                # 简化策略：明确区分首次匹配和后续匹配
                for div in all_divs:
                    div_x, div_y1, _, div_y2 = div['bbox']
                    div_y_center = (div_y1 + div_y2) / 2
                    
                    matched = False
                    
                    # 首次匹配：必须与某个列表项基本水平对齐
                    # 严格条件避免误匹配
                    for item in list_items:
                        if item['page_index'] != div['page_index']:
                            continue
                        
                        # 必须还没有值
                        if len(item['values']) > 0:
                            continue
                        
                        if not is_right_of(item['bbox'], div['bbox']):
                            continue
                        
                        _, item_y1, _, item_y2 = item['bbox']
                        item_y_center = (item_y1 + item_y2) / 2
                        y_distance = abs(div_y_center - item_y_center)
                        
                        # 首次匹配条件：y距离 < 5像素（非常严格）
                        # 只有真正在同一行的才会被首次匹配
                        if y_distance < 5:
                            item['values'].append({
                                'text': div['text'],
                                'bbox': div['bbox']
                            })
                            item['matched'] = True
                            div['matched_item'] = item
                            matched_any = True
                            values_to_remove.append(div['idx'])
                            matched = True
                            break
                    
                    if matched:
                        continue
                    
                    # 后续匹配：明确在某个已匹配项的值下方
                    candidates = []
                    
                    for item in list_items:
                        if (not item['matched'] or 
                            len(item['values']) == 0 or
                            item['page_index'] != div['page_index']):
                            continue
                        
                        last_bbox = item['values'][-1]['bbox']
                        last_x, _, _, last_y2 = last_bbox
                        
                        # div必须在最后一个值的下方
                        if div_y1 < last_y2 - 5:
                            continue
                        
                        y_distance = div_y1 - last_y2
                        x_distance = abs(div_x - last_x)
                        
                        # 后续值条件
                        if y_distance < 60 and x_distance < 60:
                            # 检查：div和最后一个值之间是否有未匹配的列表项
                            # 如果有，div可能属于那个列表项，不是后续值
                            has_unmatched_item_between = False
                            for other_item in list_items:
                                if (other_item['page_index'] != div['page_index'] or
                                    len(other_item['values']) > 0):  # 已匹配的不算
                                    continue
                                
                                _, other_y1, _, other_y2 = other_item['bbox']
                                other_y_center = (other_y1 + other_y2) / 2
                                
                                # 检查这个列表项是否在 last_y2 和 div_y1 之间
                                # 且div与它的距离<35像素（可能是首次匹配）
                                if last_y2 < other_y_center < div_y1:
                                    if abs(div_y_center - other_y_center) < 35:
                                        has_unmatched_item_between = True
                                        break
                            
                            if not has_unmatched_item_between:
                                candidates.append({
                                    'item': item,
                                    'y_distance': y_distance
                                })
                    
                    # 选择距离最近的
                    if candidates:
                        candidates.sort(key=lambda c: c['y_distance'])
                        best = candidates[0]
                        
                        best['item']['values'].append({
                            'text': div['text'],
                            'bbox': div['bbox']
                        })
                        div['matched_item'] = best['item']
                        values_to_remove.append(div['idx'])
                
                # 如果有匹配，生成新的HTML
                if matched_any:
                    new_parts_html = []
                    for item in list_items:
                        if item['matched'] and len(item['values']) > 0:
                            # 合并多个值
                            if len(item['values']) == 1:
                                # 单个值：简单合并
                                combined_text = f"{item['text']}: {item['values'][0]['text']}"
                            else:
                                # 多个值：用分号或换行符连接
                                values_text = '; '.join([v['text'] for v in item['values']])
                                combined_text = f"{item['text']}: {values_text}"
                            
                            # 使用左侧的bbox和所有值的bbox范围
                            x1, y1, _, _ = item['bbox']
                            
                            # 找到所有值的最大范围
                            max_x2 = max([v['bbox'][2] for v in item['values']])
                            max_y2 = max([v['bbox'][3] for v in item['values']])
                            
                            merged_bbox = f"[{x1}, {y1}, {max_x2}, {max_y2}]"
                            
                            new_div = f'<div className="merged_key_value" bbox="{merged_bbox}" page_index="{item["page_index"]}">{combined_text}</div>'
                            new_parts_html.append(new_div)
                        else:
                            # 保持原样
                            original_li = f'<li bbox="{list(item["bbox"])}" page_index="{item["page_index"]}" className="listitem_wrapper">{item["text"]}</li>'
                            new_parts_html.append(original_li)
                    
                    # 如果有新的组合，添加到结果
                    if new_parts_html:
                        processed_parts.extend(new_parts_html)
                    
                    # 标记已处理的value部分跳过
                    for idx in sorted(values_to_remove, reverse=True):
                        if idx < len(parts):
                            parts[idx] = ''  # 标记为已处理
                    
                    i += 1
                    continue
                    
            except Exception as e:
                # 解析失败，保持原样
                pass
        
        # 未匹配或无法处理，保持原样
        processed_parts.append(part)
        i += 1
    
    return '\n\n'.join(processed_parts)


def unescape_html_entities(html_str: str) -> str:
    """反转义HTML实体，使特殊字符正确显示
    
    转换：
    - &lt; → <
    - &gt; → >
    - &quot; → "
    - &amp; → &
    - &#...; → 对应的Unicode字符
    
    Args:
        html_str: 包含HTML实体的字符串
    
    Returns:
        反转义后的字符串
    """
    import html
    return html.unescape(html_str)


def enhance_html_for_extraction(html_str: str, unescape_for_display: bool = False) -> str:
    """增强HTML以提高参数提取准确度
    
    主要功能：
    1. 拆散<ul>，把每个<li>当作独立元素
    2. 按y坐标排序元素（确保顺序符合视觉阅读顺序）
    3. 顺序合并键值对（一对一、一对多）
    4. （可选）反转义HTML实体用于显示
    
    Args:
        html_str: 原始HTML字符串
        unescape_for_display: 是否反转义HTML实体（仅用于显示，不用于LLM处理）
    
    Returns:
        增强后的HTML字符串
    """
    # 先排序（拆散<ul>并按阅读顺序排列）
    print("  → 按y坐标排序HTML元素（拆散<ul>）...")
    sorted_html = sort_html_by_position(html_str)
    
    # 再按顺序合并键值对（新算法）
    print("  → 顺序合并键值对（一对一、一对多）...")
    enhanced_html = merge_aligned_key_values_sequential(sorted_html)
    
    # （可选）反转义HTML实体用于显示
    if unescape_for_display:
        print("  → 反转义HTML实体（用于显示）...")
        enhanced_html = unescape_html_entities(enhanced_html)
    
    return enhanced_html


