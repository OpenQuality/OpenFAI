"""
图纸分析服务模块 - 支持控制要求分析、关键风险点识别和SOP生成
使用视觉语言模型进行深度图纸分析
"""
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型枚举"""
    CONTROL_REQUIREMENTS = "control_requirements"
    RISK_POINTS = "risk_points"
    SOP_GENERATION = "sop_generation"
    FULL_ANALYSIS = "full_analysis"


@dataclass
class ControlRequirementResult:
    """控制要求分析结果"""
    requirement_id: str
    requirement_name: str
    control_type: str
    description: str
    nominal_value: Optional[float] = None
    upper_limit: Optional[float] = None
    lower_limit: Optional[float] = None
    unit: str = "mm"
    risk_level: str = "MEDIUM"
    risk_factors: List[str] = field(default_factory=list)
    impact_analysis: str = ""
    inspection_method: str = ""
    inspection_tool: str = ""
    inspection_frequency: str = ""
    is_key_characteristic: bool = False
    is_safety_critical: bool = False


@dataclass
class RiskPointResult:
    """关键风险点识别结果"""
    risk_id: str
    risk_name: str
    description: str
    risk_category: str = ""
    severity: str = "MAJOR"
    probability: float = 0.5
    affected_dimensions: List[str] = field(default_factory=list)
    affected_processes: List[str] = field(default_factory=list)
    prevention_measures: str = ""
    correction_measures: str = ""
    contingency_plan: str = ""


@dataclass
class SOPSection:
    """SOP章节"""
    title: str
    content: str
    subsections: List['SOPSection'] = field(default_factory=list)


@dataclass
class SOPDocumentResult:
    """SOP文档生成结果"""
    document_title: str
    document_type: str
    version: str = "1.0"
    sections: List[SOPSection] = field(default_factory=list)
    control_requirements: List[str] = field(default_factory=list)
    risk_points: List[str] = field(default_factory=list)


class DrawingAnalysisService:
    """图纸分析服务 - 支持深度分析"""
    
    # 控制要求分析系统提示词
    CONTROL_REQUIREMENTS_PROMPT = """你是一个专业的质量控制工程师。你的任务是分析工程图纸，识别关键控制要求。

请仔细分析图纸，识别以下内容：
1. 尺寸控制要求（关键尺寸、配合尺寸等）
2. 表面质量要求（粗糙度、表面处理等）
3. 材料要求（材质、硬度等）
4. 形位公差要求（位置度、同轴度、平面度等）
5. 工艺要求（热处理、加工方法等）
6. 装配要求（配合关系、安装要求等）
7. 安全要求（关键安全特性等）

对每个控制要求，评估其风险等级：
- HIGH: 直接影响产品功能、安全，或客户特别关注
- MEDIUM: 影响产品质量，需要重点关注
- LOW: 一般性要求，常规控制即可

输出JSON格式：
{
    "control_requirements": [
        {
            "requirement_id": "CR001",
            "requirement_name": "要求名称",
            "control_type": "DIMENSION/SURFACE/MATERIAL/GEOMETRY/PROCESS/ASSEMBLY/SAFETY/OTHER",
            "description": "详细描述",
            "nominal_value": 标称值,
            "upper_limit": 上限,
            "lower_limit": 下限,
            "unit": "单位",
            "risk_level": "HIGH/MEDIUM/LOW",
            "risk_factors": ["风险因素1", "风险因素2"],
            "impact_analysis": "影响分析",
            "inspection_method": "检测方法",
            "inspection_tool": "检测工具",
            "inspection_frequency": "检测频次",
            "is_key_characteristic": true/false,
            "is_safety_critical": true/false
        }
    ]
}"""

    # 关键风险点识别系统提示词
    RISK_POINTS_PROMPT = """你是一个专业的风险管理工程师。你的任务是分析工程图纸，识别关键风险点。

请分析图纸中可能存在的风险：
1. 制造风险（加工难度、设备能力、工艺限制等）
2. 测量风险（检测难度、测量不确定度等）
3. 质量风险（潜在缺陷、失效模式等）
4. 装配风险（配合问题、安装难度等）
5. 安全风险（安全特性失效风险等）
6. 成本风险（材料成本、加工成本等）

对每个风险点，评估：
- 严重程度：CRITICAL（严重）、MAJOR（重要）、MINOR（次要）
- 发生概率：0.0-1.0
- 预防措施、纠正措施、应急预案

输出JSON格式：
{
    "risk_points": [
        {
            "risk_id": "RP001",
            "risk_name": "风险名称",
            "description": "风险描述",
            "risk_category": "风险类别",
            "severity": "CRITICAL/MAJOR/MINOR",
            "probability": 0.0-1.0,
            "affected_dimensions": ["影响的尺寸ID"],
            "affected_processes": ["影响的工序"],
            "prevention_measures": "预防措施",
            "correction_measures": "纠正措施",
            "contingency_plan": "应急预案"
        }
    ]
}"""

    # SOP生成系统提示词
    SOP_GENERATION_PROMPT = """你是一个专业的技术文档编写专家。你的任务是根据工程图纸生成标准操作程序(SOP)和内部指导书。

请生成以下内容：
1. 文档标题和基本信息
2. 目的和适用范围
3. 参考文件
4. 操作步骤（详细的操作流程）
5. 质量控制要点
6. 注意事项和安全警告
7. 检验要求和方法
8. 记录要求

输出JSON格式：
{
    "document_title": "文档标题",
    "document_type": "SOP/WORK_INSTRUCTION/INSPECTION_GUIDE/CONTROL_PLAN/INTERNAL_GUIDE",
    "version": "1.0",
    "sections": [
        {
            "title": "章节标题",
            "content": "章节内容",
            "subsections": [
                {
                    "title": "子章节标题",
                    "content": "子章节内容"
                }
            ]
        }
    ],
    "control_requirements": ["关联的控制要求ID"],
    "risk_points": ["关联的风险点ID"]
}"""

    def __init__(self):
        """初始化分析服务"""
        self._client = None
    
    @property
    def client(self):
        """延迟初始化LLM客户端"""
        if self._client is None:
            from core.ai_vision import get_ai_vision_client
            self._client = get_ai_vision_client()
        return self._client
    
    def _get_image_url(self, image_source) -> str:
        """获取图片URL"""
        from .ocr_service import get_ocr_service
        ocr_service = get_ocr_service()
        return ocr_service._encode_image_to_base64(image_source)
    
    def analyze_control_requirements(
        self, 
        image_source,
        dimensions: List[Dict] = None
    ) -> List[ControlRequirementResult]:
        """
        分析控制要求
        
        Args:
            image_source: 图纸图片源
            dimensions: 已识别的尺寸列表（可选）
            
        Returns:
            控制要求分析结果列表
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info("开始分析控制要求...")
        
        # 获取图片URL
        image_url = self._get_image_url(image_source)
        
        # 构建提示词
        prompt = "请分析这张工程图纸，识别所有关键控制要求。"
        if dimensions:
            prompt += f"\n\n已知尺寸信息：\n{json.dumps(dimensions, ensure_ascii=False, indent=2)}"
        
        messages = [
            SystemMessage(content=self.CONTROL_REQUIREMENTS_PROMPT),
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
            
            return self._parse_control_requirements(content)
            
        except Exception as e:
            logger.error(f"控制要求分析失败: {str(e)}")
            raise
    
    def analyze_risk_points(
        self, 
        image_source,
        dimensions: List[Dict] = None,
        control_requirements: List[Dict] = None
    ) -> List[RiskPointResult]:
        """
        识别关键风险点
        
        Args:
            image_source: 图纸图片源
            dimensions: 已识别的尺寸列表（可选）
            control_requirements: 已识别的控制要求列表（可选）
            
        Returns:
            关键风险点识别结果列表
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info("开始识别关键风险点...")
        
        # 获取图片URL
        image_url = self._get_image_url(image_source)
        
        # 构建提示词
        prompt = "请分析这张工程图纸，识别所有关键风险点。"
        if dimensions:
            prompt += f"\n\n已知尺寸信息：\n{json.dumps(dimensions, ensure_ascii=False, indent=2)}"
        if control_requirements:
            prompt += f"\n\n已知控制要求：\n{json.dumps(control_requirements, ensure_ascii=False, indent=2)}"
        
        messages = [
            SystemMessage(content=self.RISK_POINTS_PROMPT),
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
            
            return self._parse_risk_points(content)
            
        except Exception as e:
            logger.error(f"关键风险点识别失败: {str(e)}")
            raise
    
    def generate_sop(
        self, 
        image_source,
        part_info: Dict,
        dimensions: List[Dict] = None,
        control_requirements: List[Dict] = None,
        risk_points: List[Dict] = None,
        document_type: str = "SOP"
    ) -> SOPDocumentResult:
        """
        生成SOP文档
        
        Args:
            image_source: 图纸图片源
            part_info: 零件基本信息
            dimensions: 已识别的尺寸列表（可选）
            control_requirements: 已识别的控制要求列表（可选）
            risk_points: 已识别的风险点列表（可选）
            document_type: 文档类型
            
        Returns:
            SOP文档生成结果
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        logger.info(f"开始生成{document_type}文档...")
        
        # 获取图片URL
        image_url = self._get_image_url(image_source)
        
        # 构建提示词
        prompt = f"""请根据这张工程图纸生成{document_type}文档。

零件信息：
{json.dumps(part_info, ensure_ascii=False, indent=2)}"""
        
        if dimensions:
            prompt += f"\n\n尺寸信息：\n{json.dumps(dimensions, ensure_ascii=False, indent=2)}"
        if control_requirements:
            prompt += f"\n\n控制要求：\n{json.dumps(control_requirements, ensure_ascii=False, indent=2)}"
        if risk_points:
            prompt += f"\n\n风险点：\n{json.dumps(risk_points, ensure_ascii=False, indent=2)}"
        
        messages = [
            SystemMessage(content=self.SOP_GENERATION_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ]
        
        try:
            response = self.client.invoke(
                messages=messages,
                temperature=0.3
            )
            
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            return self._parse_sop_document(content, document_type)
            
        except Exception as e:
            logger.error(f"SOP文档生成失败: {str(e)}")
            raise
    
    def full_analysis(
        self, 
        image_source,
        part_info: Dict,
        generate_sop: bool = True
    ) -> Dict[str, Any]:
        """
        完整分析：控制要求 + 风险点 + SOP
        
        Args:
            image_source: 图纸图片源
            part_info: 零件基本信息
            generate_sop: 是否生成SOP文档
            
        Returns:
            完整分析结果
        """
        logger.info("开始完整图纸分析...")
        
        # 1. 先识别尺寸
        from .ocr_service import get_ocr_service
        ocr_service = get_ocr_service()
        dimensions = ocr_service.recognize_drawing(image_source)
        dimensions_data = [
            {
                "id": d.id,
                "name": d.name,
                "nominal_value": float(d.nominal_value),
                # 未识别到的公差保持None，不要伪造为0（详见ocr_service.DimensionResult注释）
                "upper_tolerance": float(d.upper_tolerance) if d.upper_tolerance is not None else None,
                "lower_tolerance": float(d.lower_tolerance) if d.lower_tolerance is not None else None,
                "unit": d.unit,
                "dim_type": d.dim_type,
                "is_critical": d.is_critical,
                "position": d.bbox
            }
            for d in dimensions
        ]
        
        # 2. 分析控制要求
        control_requirements = self.analyze_control_requirements(image_source, dimensions_data)
        control_requirements_data = [
            {
                "requirement_id": cr.requirement_id,
                "requirement_name": cr.requirement_name,
                "control_type": cr.control_type,
                "description": cr.description,
                "risk_level": cr.risk_level,
                "is_key_characteristic": cr.is_key_characteristic
            }
            for cr in control_requirements
        ]
        
        # 3. 识别关键风险点
        risk_points = self.analyze_risk_points(image_source, dimensions_data, control_requirements_data)
        risk_points_data = [
            {
                "risk_id": rp.risk_id,
                "risk_name": rp.risk_name,
                "severity": rp.severity,
                "probability": rp.probability
            }
            for rp in risk_points
        ]
        
        result = {
            "dimensions": dimensions_data,
            "control_requirements": [self._control_requirement_to_dict(cr) for cr in control_requirements],
            "risk_points": [self._risk_point_to_dict(rp) for rp in risk_points]
        }
        
        # 4. 生成SOP文档（可选）
        if generate_sop:
            sop_document = self.generate_sop(
                image_source, 
                part_info, 
                dimensions_data, 
                control_requirements_data, 
                risk_points_data
            )
            result["sop_document"] = self._sop_document_to_dict(sop_document)
        
        logger.info(f"完整图纸分析完成，识别{len(dimensions)}个尺寸，{len(control_requirements)}个控制要求，{len(risk_points)}个风险点")
        
        return result
    
    def _parse_control_requirements(self, content: str) -> List[ControlRequirementResult]:
        """解析控制要求响应"""
        results = []
        
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                for cr in data.get("control_requirements", []):
                    results.append(ControlRequirementResult(
                        requirement_id=cr.get("requirement_id", f"CR{len(results)+1:03d}"),
                        requirement_name=cr.get("requirement_name", ""),
                        control_type=cr.get("control_type", "OTHER"),
                        description=cr.get("description", ""),
                        nominal_value=cr.get("nominal_value"),
                        upper_limit=cr.get("upper_limit"),
                        lower_limit=cr.get("lower_limit"),
                        unit=cr.get("unit", "mm"),
                        risk_level=cr.get("risk_level", "MEDIUM"),
                        risk_factors=cr.get("risk_factors", []),
                        impact_analysis=cr.get("impact_analysis", ""),
                        inspection_method=cr.get("inspection_method", ""),
                        inspection_tool=cr.get("inspection_tool", ""),
                        inspection_frequency=cr.get("inspection_frequency", ""),
                        is_key_characteristic=bool(cr.get("is_key_characteristic", False)),
                        is_safety_critical=bool(cr.get("is_safety_critical", False))
                    ))
        except json.JSONDecodeError as e:
            logger.warning(f"控制要求JSON解析失败: {str(e)}")
        
        return results
    
    def _parse_risk_points(self, content: str) -> List[RiskPointResult]:
        """解析关键风险点响应"""
        results = []
        
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                for rp in data.get("risk_points", []):
                    results.append(RiskPointResult(
                        risk_id=rp.get("risk_id", f"RP{len(results)+1:03d}"),
                        risk_name=rp.get("risk_name", ""),
                        description=rp.get("description", ""),
                        risk_category=rp.get("risk_category", ""),
                        severity=rp.get("severity", "MAJOR"),
                        probability=float(rp.get("probability", 0.5)),
                        affected_dimensions=rp.get("affected_dimensions", []),
                        affected_processes=rp.get("affected_processes", []),
                        prevention_measures=rp.get("prevention_measures", ""),
                        correction_measures=rp.get("correction_measures", ""),
                        contingency_plan=rp.get("contingency_plan", "")
                    ))
        except json.JSONDecodeError as e:
            logger.warning(f"风险点JSON解析失败: {str(e)}")
        
        return results
    
    def _parse_sop_document(self, content: str, document_type: str) -> SOPDocumentResult:
        """解析SOP文档响应"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                sections = []
                for section_data in data.get("sections", []):
                    section = self._parse_section(section_data)
                    sections.append(section)
                
                return SOPDocumentResult(
                    document_title=data.get("document_title", ""),
                    document_type=data.get("document_type", document_type),
                    version=data.get("version", "1.0"),
                    sections=sections,
                    control_requirements=data.get("control_requirements", []),
                    risk_points=data.get("risk_points", [])
                )
        except json.JSONDecodeError as e:
            logger.warning(f"SOP文档JSON解析失败: {str(e)}")
        
        return SOPDocumentResult(
            document_title="分析文档",
            document_type=document_type
        )
    
    def _parse_section(self, section_data: Dict) -> SOPSection:
        """解析章节"""
        subsections = []
        for sub_data in section_data.get("subsections", []):
            subsections.append(self._parse_section(sub_data))
        
        return SOPSection(
            title=section_data.get("title", ""),
            content=section_data.get("content", ""),
            subsections=subsections
        )
    
    def _control_requirement_to_dict(self, cr: ControlRequirementResult) -> Dict:
        """控制要求转字典"""
        return {
            "requirement_id": cr.requirement_id,
            "requirement_name": cr.requirement_name,
            "control_type": cr.control_type,
            "description": cr.description,
            "nominal_value": cr.nominal_value,
            "upper_limit": cr.upper_limit,
            "lower_limit": cr.lower_limit,
            "unit": cr.unit,
            "risk_level": cr.risk_level,
            "risk_factors": cr.risk_factors,
            "impact_analysis": cr.impact_analysis,
            "inspection_method": cr.inspection_method,
            "inspection_tool": cr.inspection_tool,
            "inspection_frequency": cr.inspection_frequency,
            "is_key_characteristic": cr.is_key_characteristic,
            "is_safety_critical": cr.is_safety_critical
        }
    
    def _risk_point_to_dict(self, rp: RiskPointResult) -> Dict:
        """风险点转字典"""
        return {
            "risk_id": rp.risk_id,
            "risk_name": rp.risk_name,
            "description": rp.description,
            "risk_category": rp.risk_category,
            "severity": rp.severity,
            "probability": rp.probability,
            "affected_dimensions": rp.affected_dimensions,
            "affected_processes": rp.affected_processes,
            "prevention_measures": rp.prevention_measures,
            "correction_measures": rp.correction_measures,
            "contingency_plan": rp.contingency_plan
        }
    
    def _sop_document_to_dict(self, sop: SOPDocumentResult) -> Dict:
        """SOP文档转字典"""
        def section_to_dict(section: SOPSection) -> Dict:
            return {
                "title": section.title,
                "content": section.content,
                "subsections": [section_to_dict(s) for s in section.subsections]
            }
        
        return {
            "document_title": sop.document_title,
            "document_type": sop.document_type,
            "version": sop.version,
            "sections": [section_to_dict(s) for s in sop.sections],
            "control_requirements": sop.control_requirements,
            "risk_points": sop.risk_points
        }


# 全局分析服务实例
_analysis_service: Optional[DrawingAnalysisService] = None


def get_analysis_service() -> DrawingAnalysisService:
    """
    获取分析服务实例（单例模式）
    
    Returns:
        分析服务实例
    """
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = DrawingAnalysisService()
    return _analysis_service
