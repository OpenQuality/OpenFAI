"""
图纸评审服务模块 - 实现图纸评审的完整功能
包含：翻译完整性检查、内控正确性检查、识图完整性检查、技术标准识别、
      外观面生成、技术标准解读、检验SOP生成
"""
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """评审状态"""
    PASS = "PASS"           # 通过
    WARNING = "WARNING"     # 警告
    FAIL = "FAIL"          # 不通过
    NOT_APPLICABLE = "N/A"  # 不适用


@dataclass
class ReviewCheckItem:
    """评审检查项"""
    category: str                    # 检查类别
    item_name: str                   # 检查项名称
    status: str                      # 状态：PASS/WARNING/FAIL/N/A
    description: str                 # 描述
    details: List[str] = field(default_factory=list)  # 详细信息
    issues: List[str] = field(default_factory=list)   # 问题列表
    recommendations: List[str] = field(default_factory=list)  # 建议


@dataclass
class TechnicalStandard:
    """技术标准"""
    process_name: str               # 工序名称
    standard_code: str             # 标准编号
    standard_name: str             # 标准名称
    key_parameters: List[Dict]     # 关键参数
    control_points: List[str]      # 控制要点
    inspection_method: str         # 检验方法


@dataclass
class SurfaceZone:
    """外观面区域"""
    zone_id: str                    # 区域编号
    zone_type: str                  # A/B/C级面
    description: str                # 描述
    location: str                   # 位置
    quality_requirements: List[str] # 质量要求
    color_code: str                 # 颜色代码


@dataclass
class InspectionSOPItem:
    """检验SOP项目"""
    item_no: str                    # 项目编号
    category: str                   # 类别：尺寸/外观/性能/标识
    inspection_object: str          # 检验对象
    attribute: str                  # 属性
    inspection_tool: str            # 检验工具
    inspection_method: str          # 检验方法
    sampling_ratio: str             # 抽样比例
    acceptance_criteria: str        # 验收标准
    is_key_characteristic: bool = False  # 是否关键特性


class DrawingReviewService:
    """图纸评审服务"""
    
    # 图纸评审系统提示词
    DRAWING_REVIEW_PROMPT = """你是一个专业的图纸评审工程师。请对这张工程图纸进行全面的评审分析。

请按以下方面进行评审，并以JSON格式输出：

1. 翻译完整性检查（检查图纸中是否有需要翻译的外文内容）
{
    "translation_check": {
        "status": "PASS/WARNING/FAIL/N/A",
        "has_foreign_text": true/false,
        "translated_items": [
            {"original": "原文", "translation": "译文", "location": "位置"}
        ],
        "untranslated_items": ["未翻译内容1", "未翻译内容2"],
        "translation_accuracy": "准确/基本准确/存在错误",
        "issues": ["问题1", "问题2"],
        "recommendations": ["建议1", "建议2"]
    }
}

2. 内控标准检查（检查图纸中的内控标注是否正确、合理）
{
    "internal_control_check": {
        "status": "PASS/WARNING/FAIL/N/A",
        "has_internal_control": true/false,
        "internal_control_items": [
            {
                "dimension": "尺寸描述",
                "requirement": "内控要求",
                "is_reasonable": true/false,
                "reason": "原因说明"
            }
        ],
        "issues": ["问题1"],
        "recommendations": ["建议1"]
    }
}

3. 识图完整性检查（检查尺寸标注是否完整、正确）
{
    "drawing_completeness_check": {
        "status": "PASS/WARNING/FAIL/N/A",
        "dimensions_count": 数字,
        "tolerance_completeness": "完整/部分完整/不完整",
        "missing_dimensions": ["缺失尺寸1"],
        "missing_tolerances": ["缺失公差1"],
        "gd_t_items": ["形位公差1"],
        "surface_finish_requirements": ["表面处理要求1"],
        "issues": ["问题1"],
        "recommendations": ["建议1"]
    }
}

4. 技术标准识别（识别各工序需要遵循的技术标准）
{
    "technical_standards": [
        {
            "process_name": "工序名称（原材料/机加工/打磨/表面处理/检验/包装/出货）",
            "standard_code": "标准编号",
            "standard_name": "标准名称",
            "key_parameters": [
                {"parameter": "参数名", "value": "要求值", "unit": "单位"}
            ],
            "control_points": ["控制要点1"],
            "inspection_method": "检验方法"
        }
    ]
}

5. 零件基本信息
{
    "part_info": {
        "part_number": "零件编号",
        "part_name": "零件名称",
        "revision": "版本",
        "material": "材料",
        "customer": "客户",
        "surface_finish": "表面处理"
    }
}

请确保输出完整的JSON格式。"""

    # 外观面生成系统提示词
    SURFACE_ZONE_PROMPT = """你是一个专业的质量工程师。请根据零件图纸分析并划分外观面区域。

外观面定义：
- A级面（Zone A）：零件组装之后能直接看到的表面（最高质量要求）
- B级面（Zone B）：零件组装之后能间接看到的表面（中等质量要求）
- C级面（Zone C）：零件组装之后不能看到的表面（一般质量要求）

请分析图纸，识别零件的各个表面，并根据组装后的可见性进行分级。

输出JSON格式：
{
    "surface_zones": [
        {
            "zone_id": "区域编号（如A1, A2, B1, C1等）",
            "zone_type": "A/B/C",
            "description": "表面描述",
            "location": "在零件上的位置",
            "quality_requirements": ["质量要求1", "质量要求2"],
            "color_code": "颜色代码（A级绿色GREEN，B级黄色YELLOW，C级灰色GREY）",
            "estimated_area": "估计面积或占比"
        }
    ],
    "surface_finish": "表面处理要求",
    "assembly_context": "组装场景说明（帮助判断哪些面可见）"
}"""

    # 技术标准解读系统提示词
    STANDARD_INTERPRETATION_PROMPT = """你是一个专业的工艺工程师和质量工程师。请对以下技术标准进行详细解读，提取关键参数和控制重点。

对于每个技术标准，请输出：

1. 标准概述和适用范围
2. 关键技术参数
3. 工艺控制要点
4. 检验方法
5. 常见问题及预防措施
6. 内部检验控制重点

输出JSON格式：
{
    "standard_interpretations": [
        {
            "standard_code": "标准编号",
            "standard_name": "标准名称",
            "overview": "标准概述",
            "applicable_processes": ["适用工序"],
            "key_parameters": [
                {
                    "parameter": "参数名称",
                    "requirement": "要求值",
                    "unit": "单位",
                    "tolerance": "公差",
                    "inspection_method": "检验方法",
                    "importance": "重要性（高/中/低）"
                }
            ],
            "process_control_points": [
                {
                    "point": "控制点",
                    "requirement": "要求",
                    "method": "控制方法"
                }
            ],
            "common_issues": [
                {
                    "issue": "问题",
                    "cause": "原因",
                    "prevention": "预防措施"
                }
            ],
            "internal_control_focus": ["内部控制重点1", "内部控制重点2"]
        }
    ]
}"""

    # 检验SOP生成系统提示词
    INSPECTION_SOP_PROMPT = """你是一个专业的质量工程师。请根据零件图纸和技术标准，生成完整的检验SOP。

检验SOP应包含以下检验项目：
1. 尺寸检验（关键尺寸、配合尺寸、特殊公差尺寸等）
2. 外观检验（表面质量、划伤、碰伤、毛刺等）
3. 性能检验（表面处理质量、组装性能、特殊测试等）
4. 标识检验（零件标识、包装标识等）

输出JSON格式：
{
    "sop_document": {
        "document_title": "文档标题",
        "document_number": "文档编号",
        "part_number": "零件编号",
        "part_name": "零件名称",
        "revision": "版本",
        "customer": "客户",
        "material": "材料",
        "surface_finish": "表面处理",
        "inspection_environment": {
            "temperature": "温度要求",
            "humidity": "湿度要求"
        },
        "inspection_items": {
            "dimension_items": [
                {
                    "item_no": "项目编号",
                    "inspection_object": "检验对象",
                    "attribute": "属性（尺寸/装配尺寸/特殊公差等）",
                    "nominal_value": "标称值",
                    "upper_limit": "上限",
                    "lower_limit": "下限",
                    "unit": "单位",
                    "inspection_tool": "检验工具（CMM/PP/DC等）",
                    "inspection_method": "检验方法",
                    "sampling_ratio": "抽样比例",
                    "is_key_characteristic": true/false
                }
            ],
            "appearance_items": [
                {
                    "item_no": "项目编号",
                    "inspection_object": "检验对象（如毛刺、划伤、氧化等）",
                    "zone": "外观面区域（A/B/C）",
                    "inspection_tool": "检验工具（目视/放大镜等）",
                    "inspection_method": "检验方法",
                    "sampling_ratio": "抽样比例",
                    "acceptance_criteria": "验收标准"
                }
            ],
            "performance_items": [
                {
                    "item_no": "项目编号",
                    "inspection_object": "检验对象",
                    "inspection_tool": "检验工具",
                    "inspection_method": "检验方法",
                    "sampling_ratio": "抽样比例",
                    "acceptance_criteria": "验收标准"
                }
            ],
            "identification_items": [
                {
                    "item_no": "项目编号",
                    "inspection_object": "检验对象（零件标识/包装标识）",
                    "content": "标识内容",
                    "location": "标识位置",
                    "inspection_method": "检验方法（目视/对字）",
                    "sampling_ratio": "抽样比例",
                    "acceptance_criteria": "验收标准"
                }
            ]
        },
        "notes": ["注意事项1", "注意事项2"],
        "reference_standards": ["参考标准1", "参考标准2"]
    }
}"""

    def __init__(self):
        """初始化评审服务"""
        self._client = None
    
    @property
    def client(self):
        """延迟初始化LLM客户端"""
        if self._client is None:
            from core.ai_vision import get_ai_vision_client
            self._client = get_ai_vision_client()
        return self._client
    
    def _get_image_url(self, image_source) -> str:
        """获取图片URL或Base64"""
        import base64
        
        if isinstance(image_source, str):
            if image_source.startswith('http'):
                return image_source
            elif image_source.startswith('data:'):
                return image_source
            else:
                # 本地文件路径
                with open(image_source, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                # 检测文件类型
                ext = image_source.lower().split('.')[-1]
                mime_type = {
                    'png': 'image/png',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'gif': 'image/gif',
                    'bmp': 'image/bmp'
                }.get(ext, 'image/png')
                return f"data:{mime_type};base64,{image_base64}"
        else:
            raise ValueError(f"不支持的图片源类型: {type(image_source)}")
    
    def review_drawing(
        self, 
        image_source,
        review_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        图纸评审
        
        Args:
            image_source: 图纸图片源
            review_types: 评审类型列表，可选：['translation', 'internal_control', 'completeness', 'standards']
                         默认进行全部评审
        
        Returns:
            评审结果字典
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info("开始图纸评审...")
        
        if review_types is None:
            review_types = ['translation', 'internal_control', 'completeness', 'standards']
        
        # 获取图片URL
        image_url = self._get_image_url(image_source)
        
        # 构建提示词
        messages = [
            SystemMessage(content=self.DRAWING_REVIEW_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": "请对这张工程图纸进行全面评审，包括翻译检查、内控检查、识图完整性检查和技术标准识别。"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ]
        
        try:
            response = self.client.invoke(
                messages=messages,
                temperature=0.1
            )
            
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 解析结果
            result = self._parse_review_result(content)
            
            logger.info("图纸评审完成")
            return result
            
        except Exception as e:
            logger.error(f"图纸评审失败: {str(e)}")
            raise
    
    def generate_surface_zones(self, image_source, part_info: Dict = None) -> List[SurfaceZone]:
        """
        生成外观面区域
        
        Args:
            image_source: 图纸图片源
            part_info: 零件基本信息
            
        Returns:
            外观面区域列表
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info("开始生成外观面区域...")
        
        # 获取图片URL
        image_url = self._get_image_url(image_source)
        
        # 构建提示词
        prompt = "请分析这张工程图纸，根据外观面定义划分A/B/C级面区域。"
        if part_info:
            prompt += f"\n\n零件信息：{json.dumps(part_info, ensure_ascii=False)}"
        
        messages = [
            SystemMessage(content=self.SURFACE_ZONE_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ]
        
        try:
            response = self.client.invoke(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 解析结果
            zones = self._parse_surface_zones(content)
            
            logger.info(f"外观面区域生成完成，共{len(zones)}个区域")
            return zones
            
        except Exception as e:
            logger.error(f"外观面区域生成失败: {str(e)}")
            raise
    
    def interpret_standards(
        self, 
        technical_standards: List[Dict],
        image_source = None
    ) -> List[Dict]:
        """
        解读技术标准
        
        Args:
            technical_standards: 技术标准列表
            image_source: 图纸图片源（可选，用于结合图纸分析）
            
        Returns:
            标准解读结果列表
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info(f"开始解读{len(technical_standards)}个技术标准...")
        
        # 构建提示词
        standards_text = json.dumps(technical_standards, ensure_ascii=False, indent=2)
        
        messages = [
            SystemMessage(content=self.STANDARD_INTERPRETATION_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": f"请对以下技术标准进行详细解读：\n\n{standards_text}"}
            ])
        ]
        
        # 如果提供了图纸，添加图片
        if image_source:
            image_url = self._get_image_url(image_source)
            messages[1].content.append(
                {"type": "image_url", "image_url": {"url": image_url}}
            )
        
        try:
            response = self.client.invoke(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 解析结果
            interpretations = self._parse_standard_interpretations(content)
            
            logger.info("技术标准解读完成")
            return interpretations
            
        except Exception as e:
            logger.error(f"技术标准解读失败: {str(e)}")
            raise
    
    def generate_inspection_sop(
        self, 
        image_source,
        part_info: Dict,
        dimensions: List[Dict] = None,
        technical_standards: List[Dict] = None,
        surface_zones: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        生成检验SOP
        
        Args:
            image_source: 图纸图片源
            part_info: 零件基本信息
            dimensions: 尺寸数据
            technical_standards: 技术标准解读
            surface_zones: 外观面区域
            
        Returns:
            检验SOP文档
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info("开始生成检验SOP...")
        
        # 获取图片URL
        image_url = self._get_image_url(image_source)
        
        # 构建提示词
        prompt = f"""请根据以下信息生成完整的检验SOP：

零件信息：
{json.dumps(part_info, ensure_ascii=False, indent=2)}
"""
        
        if dimensions:
            prompt += f"\n尺寸数据：\n{json.dumps(dimensions[:20], ensure_ascii=False, indent=2)}"  # 限制数量
        
        if technical_standards:
            prompt += f"\n技术标准：\n{json.dumps(technical_standards[:5], ensure_ascii=False, indent=2)}"
        
        if surface_zones:
            prompt += f"\n外观面区域：\n{json.dumps(surface_zones, ensure_ascii=False, indent=2)}"
        
        messages = [
            SystemMessage(content=self.INSPECTION_SOP_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ]
        
        try:
            response = self.client.invoke(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 解析结果
            sop = self._parse_inspection_sop(content)
            
            logger.info("检验SOP生成完成")
            return sop
            
        except Exception as e:
            logger.error(f"检验SOP生成失败: {str(e)}")
            raise
    
    def full_review_process(
        self, 
        image_source,
        part_info: Dict = None
    ) -> Dict[str, Any]:
        """
        完整评审流程：图纸评审 + 外观面生成 + 标准解读 + SOP生成
        
        Args:
            image_source: 图纸图片源
            part_info: 零件基本信息
            
        Returns:
            完整评审结果
        """
        logger.info("开始完整评审流程...")
        
        result = {}
        
        # 1. 图纸评审
        review_result = self.review_drawing(image_source)
        result['drawing_review'] = review_result
        
        # 提取零件信息和标准
        if not part_info:
            part_info = review_result.get('part_info', {})
        
        technical_standards = review_result.get('technical_standards', [])
        dimensions = review_result.get('dimensions', [])
        
        # 2. 外观面生成
        try:
            surface_zones = self.generate_surface_zones(image_source, part_info)
            result['surface_zones'] = [self._surface_zone_to_dict(z) for z in surface_zones]
        except Exception as e:
            logger.warning(f"外观面生成失败: {str(e)}")
            result['surface_zones'] = []
        
        # 3. 技术标准解读
        if technical_standards:
            try:
                interpretations = self.interpret_standards(technical_standards, image_source)
                result['standard_interpretations'] = interpretations
            except Exception as e:
                logger.warning(f"标准解读失败: {str(e)}")
                result['standard_interpretations'] = technical_standards
        
        # 4. 检验SOP生成
        try:
            sop = self.generate_inspection_sop(
                image_source,
                part_info,
                dimensions,
                technical_standards,
                result.get('surface_zones')
            )
            result['inspection_sop'] = sop
        except Exception as e:
            logger.warning(f"SOP生成失败: {str(e)}")
            result['inspection_sop'] = None
        
        logger.info("完整评审流程完成")
        return result
    
    def _parse_review_result(self, content: str) -> Dict:
        """解析评审结果"""
        result = {
            'translation_check': {'status': 'N/A'},
            'internal_control_check': {'status': 'N/A'},
            'drawing_completeness_check': {'status': 'N/A'},
            'technical_standards': [],
            'part_info': {},
            'dimensions': []
        }
        
        try:
            # 提取JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # 解析各个部分
                if 'translation_check' in data:
                    result['translation_check'] = data['translation_check']
                
                if 'internal_control_check' in data:
                    result['internal_control_check'] = data['internal_control_check']
                
                if 'drawing_completeness_check' in data:
                    result['drawing_completeness_check'] = data['drawing_completeness_check']
                
                if 'technical_standards' in data:
                    result['technical_standards'] = data['technical_standards']
                
                if 'part_info' in data:
                    result['part_info'] = data['part_info']
                    
        except json.JSONDecodeError as e:
            logger.warning(f"评审结果JSON解析失败: {str(e)}")
        
        return result
    
    def _parse_surface_zones(self, content: str) -> List[SurfaceZone]:
        """解析外观面区域"""
        zones = []
        
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                for zone_data in data.get('surface_zones', []):
                    zones.append(SurfaceZone(
                        zone_id=zone_data.get('zone_id', ''),
                        zone_type=zone_data.get('zone_type', 'C'),
                        description=zone_data.get('description', ''),
                        location=zone_data.get('location', ''),
                        quality_requirements=zone_data.get('quality_requirements', []),
                        color_code=zone_data.get('color_code', 'GREY')
                    ))
                    
        except json.JSONDecodeError as e:
            logger.warning(f"外观面区域JSON解析失败: {str(e)}")
        
        return zones
    
    def _parse_standard_interpretations(self, content: str) -> List[Dict]:
        """解析标准解读"""
        interpretations = []
        
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                interpretations = data.get('standard_interpretations', [])
                    
        except json.JSONDecodeError as e:
            logger.warning(f"标准解读JSON解析失败: {str(e)}")
        
        return interpretations
    
    def _parse_inspection_sop(self, content: str) -> Dict:
        """解析检验SOP"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                return data.get('sop_document', {})
                    
        except json.JSONDecodeError as e:
            logger.warning(f"检验SOP JSON解析失败: {str(e)}")
        
        return {}
    
    def _surface_zone_to_dict(self, zone: SurfaceZone) -> Dict:
        """外观面区域转字典"""
        return {
            'zone_id': zone.zone_id,
            'zone_type': zone.zone_type,
            'description': zone.description,
            'location': zone.location,
            'quality_requirements': zone.quality_requirements,
            'color_code': zone.color_code
        }


# 全局评审服务实例
_review_service: Optional[DrawingReviewService] = None


def get_review_service() -> DrawingReviewService:
    """
    获取图纸评审服务实例（单例模式）
    
    Returns:
        图纸评审服务实例
    """
    global _review_service
    if _review_service is None:
        _review_service = DrawingReviewService()
    return _review_service
