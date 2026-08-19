"""
CAD文件解析服务 - 预留接口

CAD文件（.dwg, .dxf等）是矢量格式，不是图像，无法直接使用OCR识别。
本服务提供CAD解析的统一接口，支持多种解析方案的热插拔。

支持的CAD格式：
- DWG: AutoCAD原生格式
- DXF: AutoCAD交换格式（文本格式，较易解析）
- DWF/DWFX: AutoCAD压缩格式

解析方案：
1. CAD转图片方案（推荐入门）
   - 使用ODA File Converter或Teigha将CAD转为PDF/图片
   - 再使用现有OCR服务识别尺寸
   - 优点：实现简单，复用现有OCR
   - 缺点：需要额外安装转换工具

2. 直接解析方案（推荐专业场景）
   - 使用专业CAD解析库（ODA SDK, Open Design Alliance）
   - 直接提取CAD中的尺寸标注、公差信息
   - 优点：精确度高，保留原始数据
   - 缺点：需要商业授权或复杂配置

3. 第三方API方案（推荐云环境）
   - 调用专业CAD解析服务API
   - 如Aspose.CAD, AutoCAD Web API等
   - 优点：无需本地安装，跨平台
   - 缺点：需要付费，依赖网络

关于OCR方案：
- PaddleOCR: 优秀的开源OCR，适合识别中文，但仅支持图片
- DeepSeek OCR: 基于大模型的视觉识别，同样仅支持图片
- 以上OCR方案都无法直接处理CAD文件，需要先转换为图片

当前实现状态：
- 已实现：CAD文件上传存储
- 已实现：CAD转图片接口预留
- 待实现：具体转换逻辑（需根据部署环境选择方案）
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile
import os

logger = logging.getLogger(__name__)


class CADFormat(Enum):
    """CAD文件格式"""
    DWG = "dwg"
    DXF = "dxf"
    DWF = "dwf"
    DWFX = "dwfx"


@dataclass
class CADDimension:
    """CAD尺寸标注数据"""
    id: str
    dimension_type: str  # LINEAR, DIAMETER, RADIUS, ANGULAR, ORDINATE
    start_point: Tuple[float, float, float]  # 起点 (x, y, z)
    end_point: Tuple[float, float, float]    # 终点
    measured_value: float  # 测量值
    nominal_value: float   # 标称值
    upper_tolerance: float # 上公差
    lower_tolerance: float # 下公差
    unit: str
    layer: str             # 所在图层
    text: str              # 标注文本
    block_name: Optional[str] = None  # 所属块名


@dataclass
class CADParseResult:
    """CAD解析结果"""
    success: bool
    dimensions: List[CADDimension]
    layers: List[str]
    blocks: List[str]
    metadata: Dict[str, Any]
    error_message: Optional[str] = None


class CADParserBase(ABC):
    """CAD解析器基类 - 预留接口"""
    
    @abstractmethod
    def parse(self, file_path: str, options: Dict = None) -> CADParseResult:
        """
        解析CAD文件
        
        Args:
            file_path: CAD文件路径
            options: 解析选项
                - layers: 指定解析的图层（None表示全部）
                - extract_blocks: 是否提取块中的尺寸
                - include_hidden: 是否包含隐藏图层
        
        Returns:
            CADParseResult: 解析结果
        """
        pass
    
    @abstractmethod
    def convert_to_image(
        self, 
        file_path: str, 
        output_dir: str = None,
        dpi: int = 300,
        page_size: Tuple[float, float] = None
    ) -> List[str]:
        """
        将CAD文件转换为图片
        
        Args:
            file_path: CAD文件路径
            output_dir: 输出目录（None则使用临时目录）
            dpi: 图片分辨率
            page_size: 页面大小 (width, height) in mm
        
        Returns:
            生成的图片路径列表
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[CADFormat]:
        """获取支持的CAD格式"""
        pass
    
    def get_format(self, file_path: str) -> CADFormat:
        """获取文件格式"""
        ext = Path(file_path).suffix.lower().replace('.', '')
        try:
            return CADFormat(ext)
        except ValueError:
            raise ValueError(f"不支持的CAD格式: {ext}")


class DXFParser(CADParserBase):
    """
    DXF文件解析器
    
    DXF是AutoCAD的文本交换格式，可以直接解析提取尺寸信息。
    使用ezdxf库（开源）进行解析。
    
    安装：pip install ezdxf
    """
    
    def __init__(self):
        self._ezdxf = None
    
    @property
    def ezdxf(self):
        """延迟加载ezdxf库"""
        if self._ezdxf is None:
            try:
                import ezdxf
                self._ezdxf = ezdxf
            except ImportError:
                raise ImportError(
                    "DXF解析需要安装ezdxf库: pip install ezdxf"
                )
        return self._ezdxf
    
    def get_supported_formats(self) -> List[CADFormat]:
        return [CADFormat.DXF]
    
    def parse(self, file_path: str, options: Dict = None) -> CADParseResult:
        """
        解析DXF文件
        
        Args:
            file_path: DXF文件路径
            options: 解析选项
        
        Returns:
            CADParseResult: 解析结果
        """
        options = options or {}
        dimensions = []
        layers = []
        blocks = []
        
        try:
            doc = self.ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # 获取所有图层
            layers = [layer.dxf.name for layer in doc.layers]
            
            # 获取所有块
            blocks = [block.name for block in doc.blocks]
            
            # 查询所有尺寸标注实体
            for entity in msp.query('DIMENSION'):
                try:
                    dim = self._parse_dimension(entity)
                    if dim:
                        dimensions.append(dim)
                except Exception as e:
                    logger.warning(f"解析尺寸失败: {e}")
            
            return CADParseResult(
                success=True,
                dimensions=dimensions,
                layers=layers,
                blocks=blocks,
                metadata={
                    'file_format': 'DXF',
                    'total_entities': len(list(msp)),
                    'dimension_count': len(dimensions)
                }
            )
            
        except Exception as e:
            logger.error(f"DXF解析失败: {e}")
            return CADParseResult(
                success=False,
                dimensions=[],
                layers=[],
                blocks=[],
                metadata={},
                error_message=str(e)
            )
    
    def _parse_dimension(self, entity) -> Optional[CADDimension]:
        """解析单个尺寸标注"""
        # DXF尺寸标注类型映射
        dim_type_map = {
            0: 'ROTATED',    # 旋转尺寸
            1: 'ALIGNED',    # 对齐尺寸
            2: 'ANGULAR',    # 角度尺寸
            3: 'DIAMETER',   # 直径尺寸
            4: 'RADIUS',     # 半径尺寸
            5: 'ANGULAR_3P', # 三点角度尺寸
            6: 'ORDINATE',   # 坐标尺寸
        }
        
        dim_type = dim_type_map.get(entity.dxf.dimtype, 'UNKNOWN')
        
        # 获取测量点
        try:
            start_point = (
                entity.dxf.defpoint.x,
                entity.dxf.defpoint.y,
                entity.dxf.defpoint.z if hasattr(entity.dxf.defpoint, 'z') else 0
            )
            end_point = start_point  # 简化处理
            
            # 尝试获取实际测量值
            measured_value = entity.get_measurement()
            
            return CADDimension(
                id=f"DIM_{entity.dxf.handle}",
                dimension_type=dim_type,
                start_point=start_point,
                end_point=end_point,
                measured_value=measured_value,
                nominal_value=measured_value,
                upper_tolerance=0,
                lower_tolerance=0,
                unit='mm',
                layer=entity.dxf.layer,
                text=entity.dxf.text if hasattr(entity.dxf, 'text') else ''
            )
        except Exception as e:
            logger.debug(f"解析尺寸细节失败: {e}")
            return None
    
    def convert_to_image(
        self, 
        file_path: str, 
        output_dir: str = None,
        dpi: int = 300,
        page_size: Tuple[float, float] = None
    ) -> List[str]:
        """
        将DXF转换为图片
        
        使用matplotlib进行渲染
        """
        output_dir = output_dir or tempfile.gettempdir()
        output_paths = []
        
        try:
            import matplotlib.pyplot as plt
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            
            doc = self.ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # 创建渲染
            fig = plt.figure(figsize=(20, 15), dpi=dpi)
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            frontend = Frontend(ctx, out)
            frontend.draw_layout(msp)
            
            # 保存图片
            output_path = os.path.join(
                output_dir, 
                f"{Path(file_path).stem}.png"
            )
            fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            output_paths.append(output_path)
            
        except Exception as e:
            logger.error(f"DXF转图片失败: {e}")
            raise
        
        return output_paths


class DWGConverterPlaceholder(CADParserBase):
    """
    DWG文件转换器占位实现
    
    DWG是AutoCAD的二进制格式，需要专业工具解析。
    
    可选方案：
    
    1. ODA File Converter (免费工具)
       - 安装: https://www.opendesign.com/guestfiles/oda_file_converter
       - 使用命令行转换: ODAFileConverter input output ACAD2010 DXF
       - 然后用DXF解析器处理
    
    2. Teigha Converter (开源)
       - 安装: apt-get install teigha-converter
       - 使用: teigha_convert input.dwg output.dxf
    
    3. LibreDWG (开源库)
       - 安装: pip install pplibredwg
       - 支持DWG到DXF的转换
    
    4. Aspose.CAD (商业库)
       - 功能全面，支持各种CAD格式
       - 提供Python API
       - 官网: https://products.aspose.com/cad/python
    
    5. AutoCAD Web API (云服务)
       - 需要Autodesk账号
       - API文档: https://aps.autodesk.com/
    """
    
    def get_supported_formats(self) -> List[CADFormat]:
        return [CADFormat.DWG, CADFormat.DWF, CADFormat.DWFX]
    
    def parse(self, file_path: str, options: Dict = None) -> CADParseResult:
        """
        DWG解析 - 当前为占位实现
        
        实际部署时，选择以下方案之一：
        
        方案A: DWG -> DXF -> 解析
        ```python
        # 使用LibreDWG转换
        from libredwg import dwg2dxf
        dxf_path = file_path.replace('.dwg', '.dxf')
        dwg2dxf(file_path, dxf_path)
        # 使用DXF解析器
        return DXFParser().parse(dxf_path, options)
        ```
        
        方案B: 使用Aspose.CAD
        ```python
        import aspose.cad as cad
        image = cad.Image.load(file_path)
        # 提取尺寸信息...
        ```
        
        方案C: 使用ODA SDK
        ```python
        # 需要安装ODA SDK
        from OdaQt import OdaFile
        # ...
        ```
        """
        return CADParseResult(
            success=False,
            dimensions=[],
            layers=[],
            blocks=[],
            metadata={
                'file_format': 'DWG',
                'note': 'DWG解析需要安装专业CAD库或转换工具'
            },
            error_message=(
                "DWG文件解析需要安装专业CAD解析库。\n"
                "推荐方案:\n"
                "1. 安装 LibreDWG: pip install pplibredwg\n"
                "2. 使用 ODA File Converter 转换为 DXF\n"
                "3. 使用 Aspose.CAD 商业库\n"
                "请根据部署环境选择合适的方案。"
            )
        )
    
    def convert_to_image(
        self, 
        file_path: str, 
        output_dir: str = None,
        dpi: int = 300,
        page_size: Tuple[float, float] = None
    ) -> List[str]:
        """
        DWG转图片 - 占位实现
        
        实际部署时，可以使用：
        1. Aspose.CAD: cad.Image.load(file_path).save(output_path)
        2. ODA File Converter: 先转PDF再转图片
        """
        raise NotImplementedError(
            "DWG转图片需要安装专业CAD库。\n"
            "推荐使用 Aspose.CAD 或 ODA File Converter。"
        )


class CADService:
    """
    CAD服务 - 统一入口
    
    根据文件格式自动选择解析器，支持热插拔扩展。
    """
    
    def __init__(self):
        self._parsers: Dict[CADFormat, CADParserBase] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """注册默认解析器"""
        self.register_parser(DXFParser())
        # DWG解析器需要根据部署环境配置
        # self.register_parser(DWGConverterPlaceholder())
    
    def register_parser(self, parser: CADParserBase):
        """注册解析器"""
        for fmt in parser.get_supported_formats():
            self._parsers[fmt] = parser
            logger.info(f"注册CAD解析器: {fmt.value} -> {parser.__class__.__name__}")
    
    def get_parser(self, file_path: str) -> CADParserBase:
        """获取文件对应的解析器"""
        ext = Path(file_path).suffix.lower().replace('.', '')
        try:
            fmt = CADFormat(ext)
            if fmt not in self._parsers:
                raise ValueError(
                    f"未注册 {fmt.value} 格式的解析器。"
                    f"支持的格式: {[f.value for f in self._parsers.keys()]}"
                )
            return self._parsers[fmt]
        except ValueError:
            raise ValueError(f"不支持的CAD格式: {ext}")
    
    def parse(
        self, 
        file_path: str, 
        options: Dict = None
    ) -> CADParseResult:
        """
        解析CAD文件
        
        Args:
            file_path: CAD文件路径或URL
            options: 解析选项
        
        Returns:
            CADParseResult: 解析结果
        """
        import os
        
        # 处理URL
        if file_path.startswith('http'):
            # 下载文件到临时目录
            import requests
            response = requests.get(file_path, timeout=60)
            response.raise_for_status()
            
            # 保存临时文件
            temp_dir = tempfile.mkdtemp()
            filename = file_path.split('/')[-1] or 'cad_file'
            temp_path = os.path.join(temp_dir, filename)
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            file_path = temp_path
        
        parser = self.get_parser(file_path)
        return parser.parse(file_path, options)
    
    def convert_to_image(
        self, 
        file_path: str,
        output_dir: str = None,
        dpi: int = 300
    ) -> List[str]:
        """
        将CAD文件转换为图片
        
        Args:
            file_path: CAD文件路径或URL
            output_dir: 输出目录
            dpi: 图片分辨率
        
        Returns:
            生成的图片路径列表
        """
        parser = self.get_parser(file_path)
        return parser.convert_to_image(file_path, output_dir, dpi)
    
    def get_supported_formats(self) -> List[str]:
        """获取所有支持的格式"""
        return [fmt.value for fmt in self._parsers.keys()]
    
    def is_supported(self, file_path: str) -> bool:
        """检查文件是否支持"""
        ext = Path(file_path).suffix.lower().replace('.', '')
        return ext in [fmt.value for fmt in CADFormat]


# 全局CAD服务实例
_cad_service: Optional[CADService] = None


def get_cad_service() -> CADService:
    """获取CAD服务实例"""
    global _cad_service
    if _cad_service is None:
        _cad_service = CADService()
    return _cad_service


def parse_cad_file(file_path: str, options: Dict = None) -> CADParseResult:
    """
    解析CAD文件的便捷函数
    
    Args:
        file_path: CAD文件路径
        options: 解析选项
    
    Returns:
        CADParseResult: 解析结果
    """
    return get_cad_service().parse(file_path, options)


def cad_to_image(
    file_path: str, 
    output_dir: str = None,
    dpi: int = 300
) -> List[str]:
    """
    CAD转图片的便捷函数
    
    Args:
        file_path: CAD文件路径
        output_dir: 输出目录
        dpi: 图片分辨率
    
    Returns:
        生成的图片路径列表
    """
    return get_cad_service().convert_to_image(file_path, output_dir, dpi)
