"""
OCR服务模块 - 支持图纸尺寸识别
使用视觉语言模型或本地OCR引擎进行图纸识别，支持热插拔更换模型
支持URL和Base64两种图片传递方式
支持PDF文件自动转换为图片

关于CAD文件支持：
- CAD文件（.dwg, .dxf）是矢量格式，无法直接OCR识别
- DXF格式可通过cad_service.py中的DXFParser解析
- 其他CAD格式需要先转换为图片或PDF
- 推荐方案：
  1. 用户上传前将CAD导出为PDF/图片
  2. 安装ezdxf库解析DXF文件: pip install ezdxf
  3. 使用Aspose.CAD等商业库转换DWG
"""
import json
import logging
import base64
import io
import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OCRModelType(Enum):
    """OCR模型类型枚举"""
    CLOUD_AI = "cloud_ai"   # 云端视觉LLM（豆包/Kimi/GLM/DeepSeek/自定义）
    PADDLEOCR = "paddleocr" # 本地PaddleOCR（需 AVX-512，Intel CPU）
    RAPIDOCR = "rapidocr"   # 本地RapidOCR（ONNX Runtime，兼容 AMD CPU）
    BAIDUOCR = "baiduocr"   # 百度智能云OCR REST API


class LocalOCREngine:
    """OCR引擎基类（本地 + 云端REST均继承此类）

    包含通用工程尺寸解析器 _parse_dimension_text，各子类均可直接调用。
    """

    # 工程尺寸合理范围；超出此范围的数值大概率是序号/页码/比例
    _DIM_VALUE_MIN = 0.01
    _DIM_VALUE_MAX = 9999.0
    _PLAIN_INT_MIN = 2   # 只过滤"1"（几乎肯定是序号），2mm/5mm/8mm 等小尺寸正常保留

    def __init__(self):
        self.name = "LocalOCR"

    def recognize(self, image_source: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def is_available(self) -> bool:
        return False

    def _parse_dimension_text(self, text: str) -> Optional[Dict[str, Any]]:
        """从识别文本中解析工程尺寸，严格过滤无关数值（序号/日期/纯中文等）"""
        if not text:
            return None

        text = text.strip()

        if re.match(r'^[一-鿿]+$', text):
            return None
        if re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$', text):
            return None

        patterns = [
            (r'^(\d+\.?\d*)\s*\+\s*(\d+\.?\d*)\s*/?\s*-\s*(\d+\.?\d*)$', 'TOL_ASYM'),
            (r'^(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)$', 'TOL_SYM'),
            (r'^[Φ∅φ]\s*(\d+\.?\d*)(?:\s*[±]\s*(\d+\.?\d*))?$', 'DIAMETER'),
            (r'^(\d+\.?\d*)\s*°$', 'ANGULAR'),
            (r'^(\d+\.\d+)$', 'LINEAR_DECIMAL'),
            (r'^(\d+)$', 'LINEAR_INT'),
        ]

        for pattern, kind in patterns:
            m = re.match(pattern, text)
            if not m:
                continue
            g = m.groups()
            try:
                if kind == 'TOL_ASYM':
                    nominal, upper, lower = float(g[0]), float(g[1]), float(g[2])
                    if not (self._DIM_VALUE_MIN <= nominal <= self._DIM_VALUE_MAX):
                        continue
                    return {'name': text, 'nominal_value': nominal,
                            'upper_tolerance': upper, 'lower_tolerance': -lower,
                            'unit': 'mm', 'dim_type': 'LINEAR', 'is_critical': False}
                elif kind == 'TOL_SYM':
                    nominal, tol = float(g[0]), float(g[1])
                    if not (self._DIM_VALUE_MIN <= nominal <= self._DIM_VALUE_MAX):
                        continue
                    return {'name': text, 'nominal_value': nominal,
                            'upper_tolerance': tol, 'lower_tolerance': -tol,
                            'unit': 'mm', 'dim_type': 'LINEAR', 'is_critical': False}
                elif kind == 'DIAMETER':
                    nominal = float(g[0])
                    if not (self._DIM_VALUE_MIN <= nominal <= self._DIM_VALUE_MAX):
                        continue
                    upper = float(g[1]) if g[1] else None
                    lower = -float(g[1]) if g[1] else None
                    return {'name': text, 'nominal_value': nominal,
                            'upper_tolerance': upper, 'lower_tolerance': lower,
                            'unit': 'mm', 'dim_type': 'DIAMETER', 'is_critical': False}
                elif kind == 'ANGULAR':
                    nominal = float(g[0])
                    if not (0 < nominal <= 360):
                        continue
                    return {'name': text, 'nominal_value': nominal,
                            'upper_tolerance': None, 'lower_tolerance': None,
                            'unit': '°', 'dim_type': 'ANGULAR', 'is_critical': False}
                elif kind == 'LINEAR_DECIMAL':
                    nominal = float(g[0])
                    if not (self._DIM_VALUE_MIN <= nominal <= self._DIM_VALUE_MAX):
                        continue
                    return {'name': text, 'nominal_value': nominal,
                            'upper_tolerance': None, 'lower_tolerance': None,
                            'unit': 'mm', 'dim_type': 'LINEAR', 'is_critical': False}
                elif kind == 'LINEAR_INT':
                    nominal = float(g[0])
                    if nominal < self._PLAIN_INT_MIN or nominal > self._DIM_VALUE_MAX:
                        continue
                    return {'name': text, 'nominal_value': nominal,
                            'upper_tolerance': None, 'lower_tolerance': None,
                            'unit': 'mm', 'dim_type': 'LINEAR', 'is_critical': False}
            except (ValueError, TypeError):
                continue

        return None


class PaddleOCREngine(LocalOCREngine):
    """PaddleOCR本地引擎"""
    
    def __init__(self):
        super().__init__()
        self.name = "PaddleOCR"
        self._ocr = None
        self._init_error = None
    
    def is_available(self) -> bool:
        """
        检查PaddleOCR是否可用。
        
        采用两级检测策略：
        1. 先用轻量级方式检查包是否安装（importlib.util.find_spec），
           不触发实际导入，避免cv2/libGL等依赖问题导致误判
        2. 再验证核心功能是否正常
        
        这样即使cv2等依赖有问题，也能识别到PaddleOCR已安装，
        允许用户选择并尝试使用，运行时失败再给出具体错误提示。
        """
        try:
            # 第一级：轻量级检查包是否安装（不触发导入）
            import importlib.util
            if importlib.util.find_spec('paddleocr') is None:
                logger.debug("PaddleOCR可用性检查: paddleocr包未安装")
                return False
            if importlib.util.find_spec('paddle') is None:
                logger.debug("PaddleOCR可用性检查: paddle包未安装")
                return False
            
            # 第二级：验证核心功能是否正常
            # 尝试导入cv2，验证其功能完整性
            try:
                import cv2
                if not hasattr(cv2, 'INTER_LINEAR'):
                    logger.debug("PaddleOCR可用性检查: cv2功能异常(缺少INTER_LINEAR)，可能安装了冲突的opencv包")
                    # cv2有问题但PaddleOCR已安装，仍然返回True
                    # 运行时初始化会给出更具体的错误信息
                    return True
            except ImportError:
                # cv2未安装但PaddleOCR已安装，仍然返回True
                logger.debug("PaddleOCR可用性检查: cv2未安装，但paddleocr包已存在")
                return True
            except Exception:
                # cv2加载失败(libGL等)，但PaddleOCR已安装，仍然返回True
                logger.debug("PaddleOCR可用性检查: cv2加载异常，但paddleocr包已存在")
                return True
            
            return True
        except Exception as e:
            logger.debug(f"PaddleOCR可用性检查失败: {e}")
            return False
    
    def _initialize(self):
        """延迟初始化PaddleOCR"""
        if self._ocr is not None or self._init_error is not None:
            return
        try:
            os.environ.setdefault('PPOCR_LOG_LEVEL', '3')
            from paddleocr import PaddleOCR
            from django.conf import settings

            # 将模型缓存到项目目录，避免非 root 用户无法写 /root/.paddleocr
            model_home = str(settings.BASE_DIR)
            os.makedirs(os.path.join(model_home, '.paddleocr'), exist_ok=True)

            # PaddleOCR 2.x API
            self._ocr = PaddleOCR(lang='ch', use_angle_cls=True, show_log=False,
                                   home=model_home)
            logger.info("PaddleOCR 初始化成功")
        except (TypeError, ValueError) as e:
            err_str = str(e)
            if 'Unknown argument' in err_str:
                try:
                    from paddleocr import PaddleOCR
                    self._ocr = PaddleOCR(lang='ch')
                    logger.info("PaddleOCR 兼容模式初始化成功")
                except Exception as e2:
                    self._init_error = str(e2)
                    logger.error(f"PaddleOCR兼容模式初始化失败: {e2}")
            else:
                self._init_error = err_str
                logger.error(f"PaddleOCR初始化失败: {e}")
        except ImportError as e:
            self._init_error = f"缺少依赖: {e}。请执行: pip install paddlepaddle"
            logger.error(f"PaddleOCR依赖缺失: {e}")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"PaddleOCR初始化失败: {e}")
    
    def recognize(self, image_source: str) -> List[Dict[str, Any]]:
        """使用PaddleOCR识别图纸"""
        self._initialize()
        if self._init_error:
            raise RuntimeError(f"PaddleOCR初始化失败: {self._init_error}")
        if self._ocr is None:
            raise RuntimeError("PaddleOCR未正确初始化")
        
        img = self._read_image(image_source)
        result = self._ocr.ocr(img, cls=True)
        img_height, img_width = img.shape[0], img.shape[1]

        dimensions = []
        dim_counter = 0
        for line in result[0] if result and result[0] else []:
            text = line[1][0] if line and len(line) > 1 else ''
            confidence = line[1][1] if line and len(line) > 1 else 0
            bbox = line[0] if line and len(line) > 0 else None

            parsed_dim = self._parse_dimension_text(text)
            if parsed_dim:
                dim_counter += 1
                parsed_dim['id'] = f'DIM{dim_counter:03d}'
                parsed_dim['confidence'] = confidence
                if bbox and len(bbox) == 4 and img_width and img_height:
                    # PaddleOCR返回的是图片像素坐标的四个角点，转换为相对图片宽高的
                    # 中心点百分比坐标(0-100)，与云端AI识别结果使用统一的position格式
                    center_x_px = (bbox[0][0] + bbox[2][0]) / 2
                    center_y_px = (bbox[0][1] + bbox[2][1]) / 2
                    parsed_dim['bbox'] = {
                        'x': round(center_x_px / img_width * 100, 2),
                        'y': round(center_y_px / img_height * 100, 2)
                    }
                dimensions.append(parsed_dim)

        return dimensions
    
    def _read_image(self, image_source):
        """读取图片为numpy数组，并进行工程图专用预处理"""
        import numpy as np
        import cv2

        if image_source.startswith('data:'):
            img_data = base64.b64decode(image_source.split(',')[1])
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_source.startswith('/') or (isinstance(image_source, str) and ':' not in image_source):
            img = cv2.imread(image_source)
            if img is None:
                raise ValueError(f"无法读取图片文件: {image_source}")
        elif image_source.startswith('http://') or image_source.startswith('https://'):
            import requests
            response = requests.get(image_source, timeout=30)
            nparr = np.frombuffer(response.content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            raise ValueError(f"不支持的图片源类型")

        # 工程图预处理：灰度→自适应直方图均衡→降噪→转回BGR供PaddleOCR使用
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.fastNlMeansDenoising(gray, h=10)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        return img
    
    # _parse_dimension_text 及常量已移至 LocalOCREngine 基类，此处继承无需重复定义


class BaiduOCREngine(LocalOCREngine):
    """百度智能云OCR引擎（调用百度文字识别REST API，需在引擎配置中填写API Key/Secret Key）"""

    def __init__(self):
        super().__init__()
        self.name = "BaiduOCR"
        self._access_token = None

    def is_available(self) -> bool:
        try:
            from core.models import SystemConfig
            return bool(
                SystemConfig.get_value('baidu_ocr_api_key') and
                SystemConfig.get_value('baidu_ocr_secret_key')
            )
        except Exception:
            return False

    def _refresh_token(self):
        import requests
        from core.models import SystemConfig
        api_key = SystemConfig.get_value('baidu_ocr_api_key')
        secret_key = SystemConfig.get_value('baidu_ocr_secret_key')
        url = (
            "https://aip.baidubce.com/oauth/2.0/token"
            f"?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
        )
        resp = requests.post(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if 'error' in data:
            raise RuntimeError(f"百度OCR Token获取失败: {data.get('error_description', data['error'])}")
        self._access_token = data['access_token']

    def recognize(self, image_source: str) -> List[Dict[str, Any]]:
        import requests
        from urllib.parse import quote
        from PIL import Image
        import io as _io

        # 从 data URL 中提取原始 base64
        if image_source.startswith('data:'):
            img_b64 = image_source.split(',')[1]
        else:
            raise ValueError("BaiduOCR 需要 base64 格式的图片数据")

        # 获取图片尺寸（用于将像素坐标转换为百分比，供气泡图定位）
        try:
            img_bytes = base64.b64decode(img_b64)
            img_pil = Image.open(_io.BytesIO(img_bytes))
            img_width, img_height = img_pil.size
        except Exception:
            img_width = img_height = 0

        if not self._access_token:
            self._refresh_token()

        def _call_api():
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={self._access_token}"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = f"image={quote(img_b64)}&language_type=CHN_ENG"
            r = requests.post(url, headers=headers, data=payload, timeout=60)
            r.raise_for_status()
            return r.json()

        result = _call_api()
        if result.get('error_code') == 110:   # Token 过期，刷新后重试
            self._refresh_token()
            result = _call_api()
        if 'error_code' in result:
            raise RuntimeError(f"百度OCR错误 {result['error_code']}: {result.get('error_msg', '')}")

        dimensions = []
        dim_counter = 0
        for word_info in result.get('words_result', []):
            text = word_info.get('words', '').strip()
            parsed = self._parse_dimension_text(text)
            if not parsed:
                continue
            dim_counter += 1
            parsed['id'] = f'DIM{dim_counter:03d}'
            parsed['confidence'] = 0.95
            loc = word_info.get('location', {})
            if loc and img_width and img_height:
                cx = loc.get('left', 0) + loc.get('width', 0) / 2
                cy = loc.get('top', 0) + loc.get('height', 0) / 2
                parsed['bbox'] = {
                    'x': round(cx / img_width * 100, 2),
                    'y': round(cy / img_height * 100, 2),
                }
            dimensions.append(parsed)

        return dimensions


class RapidOCREngine(LocalOCREngine):
    """RapidOCR 本地引擎（基于 ONNX Runtime，无 AVX-512 依赖，兼容 AMD EPYC Zen2）"""

    def __init__(self):
        super().__init__()
        self.name = "RapidOCR"
        self._engine = None
        self._init_error = None

    def is_available(self) -> bool:
        try:
            import importlib.util
            return importlib.util.find_spec('rapidocr_onnxruntime') is not None
        except Exception:
            return False

    def _initialize(self):
        if self._engine is not None or self._init_error is not None:
            return
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            logger.info("RapidOCR 初始化成功")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"RapidOCR 初始化失败: {e}")

    def recognize(self, image_source: str) -> List[Dict[str, Any]]:
        self._initialize()
        if self._init_error:
            raise RuntimeError(f"RapidOCR初始化失败: {self._init_error}")
        if self._engine is None:
            raise RuntimeError("RapidOCR未正确初始化")

        img = self._read_image(image_source)
        result, _ = self._engine(img)
        img_height, img_width = img.shape[0], img.shape[1]

        dimensions = []
        dim_counter = 0
        for item in (result or []):
            bbox = item[0]      # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = item[1]
            confidence = item[2]

            parsed = self._parse_dimension_text(text.strip())
            if not parsed:
                continue
            dim_counter += 1
            parsed['id'] = f'DIM{dim_counter:03d}'
            parsed['confidence'] = confidence
            if bbox and len(bbox) == 4 and img_width and img_height:
                center_x = (bbox[0][0] + bbox[2][0]) / 2
                center_y = (bbox[0][1] + bbox[2][1]) / 2
                parsed['bbox'] = {
                    'x': round(center_x / img_width * 100, 2),
                    'y': round(center_y / img_height * 100, 2),
                }
            dimensions.append(parsed)
        return dimensions

    def _read_image(self, image_source):
        import numpy as np
        import cv2
        if image_source.startswith('data:'):
            img_data = base64.b64decode(image_source.split(',')[1])
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_source.startswith('http://') or image_source.startswith('https://'):
            import requests
            response = requests.get(image_source, timeout=30)
            nparr = np.frombuffer(response.content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(image_source)
            if img is None:
                raise ValueError(f"无法读取图片: {image_source}")
        return img


def get_local_ocr_engine(engine_type: str = 'paddleocr') -> Optional[LocalOCREngine]:
    """获取OCR引擎实例（本地或云端REST）"""
    engine_map = {
        'paddleocr': PaddleOCREngine,
        'rapidocr':  RapidOCREngine,
        'baiduocr':  BaiduOCREngine,
    }
    cls = engine_map.get(engine_type)
    if cls:
        engine = cls()
        if engine.is_available():
            return engine
    return None


def check_ocr_availability() -> Dict[str, Any]:
    """检查OCR服务可用性"""
    result = {
        'cloud': {'enabled': False, 'configured': False},
        'local': {'enabled': False, 'engines': []}
    }
    
    # 检查云端配置
    from core.ai_vision import is_ai_vision_configured
    if is_ai_vision_configured():
        result['cloud']['enabled'] = True
        result['cloud']['configured'] = True

    # 检查本地/云端REST引擎
    local_engines = ['paddleocr', 'rapidocr', 'baiduocr']
    for engine_type in local_engines:
        engine = get_local_ocr_engine(engine_type)
        if engine:
            result['local']['enabled'] = True
            result['local']['engines'].append({
                'type': engine_type,
                'name': engine.name,
                'available': True
            })
    
    return result


@dataclass
class DimensionResult:
    """尺寸识别结果"""
    id: str
    name: str
    nominal_value: float
    # None表示图纸上未识别到明确的公差标注，需人工核实（不能默认为0，
    # 否则会让该尺寸的公差带=0，破坏后续Cp/Cpk计算）
    upper_tolerance: Optional[float]
    lower_tolerance: Optional[float]
    unit: str
    dim_type: str
    is_critical: bool = False
    bbox: Optional[Dict] = None  # 边界框坐标


class OCRService:
    """OCR服务 - 支持热插拔模型"""
    
    # 默认引擎：云端AI（具体厂商/模型由系统配置决定）
    DEFAULT_MODEL = OCRModelType.CLOUD_AI

    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业的机械工程图纸识别专家，熟悉中国国家标准（GB/T）和ISO制图标准。
你的任务是识别图纸中的【尺寸标注】和【公差信息】，严格区分有效尺寸与无关内容（序号、技术要求文字、标题栏信息等）。

## 什么是有效尺寸标注？
- 带有尺寸线和尺寸界线的线性尺寸（如 50、25.4）
- 直径标注（前缀 φ/Φ/∅ 或 "D="，如 φ30、∅50.5）
- 半径标注（前缀 R，如 R5、R10.5）
- 角度标注（后缀 °，如 45°、120°）
- 带公差的标注（如 50±0.1、50+0.2/-0.1、50 H7/g6）
- 形位公差框格中的数值（平面度、圆度、位置度等）
- 螺纹标注（如 M12×1.5-6H）

## 什么应该被排除？
- 序号、零件号（图中的1、2、3圆圈序号）
- 粗糙度符号中的数值（Ra 1.6 单独出现时不是尺寸）
- 图框、标题栏中的版本号、日期、图号
- 技术要求文字段落
- 图纸比例（如 1:1、2:1）

## 输出格式
```json
{
    "dimensions": [
        {
            "id": "DIM001",
            "name": "尺寸名称（外径/总长/壁厚/孔径/螺距/角度等，用中文）",
            "nominal_value": 标称值数字,
            "upper_tolerance": 上公差数字（图纸上未明确标注则为null，禁止猜测或填0）,
            "lower_tolerance": 下公差数字（负值；图纸上未明确标注则为null；单侧形位公差下公差本身为null）,
            "unit": "mm",
            "dim_type": "LINEAR/DIAMETER/RADIUS/ANGULAR/GD_T/THREAD",
            "is_critical": false,
            "position": {"x": 0~100, "y": 0~100}
        }
    ],
    "notes": "标题栏未注公差标准（如 GB/T 1804-m）、配合代号说明（如 H7/g6 需查表）、基准符号、特殊技术要求等"
}
```

## 公差识别规则
- **对称公差** `50±0.1` → upper_tolerance=0.1, lower_tolerance=-0.1
- **非对称公差** `50+0.2/-0.1` → upper_tolerance=0.2, lower_tolerance=-0.1
- **只有上偏差** `50+0.2/0` → upper_tolerance=0.2, lower_tolerance=0.0
- **配合代号** `50H7` 或 `50H7/g6` → nominal_value=50，upper/lower均为null，在notes说明原始标注
- **未注公差** → upper_tolerance=null, lower_tolerance=null（不要用0填充，0是真实且含义完全不同的公差值）
- **形位公差框格** → dim_type="GD_T"，nominal_value=公差带数值，lower_tolerance=null

## position坐标
- x: 该尺寸数字在图纸图片中的水平位置（0=最左 100=最右）
- y: 垂直位置（0=最上 100=最下）
- 请根据视觉位置仔细估计，这决定气泡图标注的位置准确性，不可省略

## 重要提醒
- **只输出有效尺寸标注，不要输出序号、粗糙度值、标题栏数字**
- 公差结果将直接用于过程能力（Cp/Cpk）计算，null和0含义完全不同，未标注必须用null
- 确保输出是合法的JSON，不含注释"""

    def __init__(self, model: OCRModelType = None):
        """
        初始化OCR服务
        
        Args:
            model: 使用的模型类型，默认自动选择（优先本地引擎）
        """
        # 如果传入的是字符串，转换为枚举
        if model and isinstance(model, str):
            try:
                model = OCRModelType(model)
            except ValueError:
                logger.warning(f"未知的模型类型: {model}, 将自动选择可用引擎")
                model = None
        
        self.model = model
        self._client = None
        self._local_engine = None
        self._use_local = None
        
        # 自动检测使用哪种引擎
        self._detect_engine()
    
    def _detect_engine(self):
        """自动检测并选择可用的OCR引擎"""
        # 如果指定了模型类型
        if self.model:
            if self.model in (OCRModelType.PADDLEOCR, OCRModelType.RAPIDOCR, OCRModelType.BAIDUOCR):
                # 本地引擎
                engine_type = {
                    OCRModelType.PADDLEOCR: 'paddleocr',
                    OCRModelType.RAPIDOCR:  'rapidocr',
                    OCRModelType.BAIDUOCR:  'baiduocr',
                }.get(self.model, 'paddleocr')
                local_engine = get_local_ocr_engine(engine_type)
                if local_engine:
                    self._use_local = True
                    self._local_engine = local_engine
                else:
                    # 本地引擎不可用，尝试降级到云端
                    logger.warning(f"指定的本地引擎 {self.model.value} 不可用，尝试使用云端模型")
                    self._use_local = False
                    self._local_engine = None
                    self.model = self.DEFAULT_MODEL
            else:
                self._use_local = False
                self._local_engine = None
            return
        
        # 自动检测可用引擎
        # 1. 优先使用本地 PaddleOCR
        local_engine = get_local_ocr_engine('paddleocr')
        if local_engine:
            self._use_local = True
            self._local_engine = local_engine
            self.model = OCRModelType.PADDLEOCR
            logger.info("OCR服务: 使用本地PaddleOCR引擎")
            return

        # 1b. PaddleOCR 不可用时回退到 RapidOCR
        local_engine = get_local_ocr_engine('rapidocr')
        if local_engine:
            self._use_local = True
            self._local_engine = local_engine
            self.model = OCRModelType.RAPIDOCR
            logger.info("OCR服务: 使用本地RapidOCR引擎")
            return

        # 2. 检查云端配置
        from core.ai_vision import is_ai_vision_configured
        if is_ai_vision_configured():
            self._use_local = False
            self.model = self.DEFAULT_MODEL
            logger.info("OCR服务: 使用云端AI模型")
            return

        # 3. 都没有，抛出错误
        raise ValueError(
            "未检测到可用的OCR引擎。\n"
            "请选择以下方式之一：\n"
            "1. 安装本地OCR引擎: pip install paddleocr paddlepaddle\n"
            "2. 配置云端AI视觉模型:\n"
            "   - 方式A: 在'系统管理 > 引擎配置'页面配置（支持豆包/Kimi/GLM/自定义）\n"
            "   - 方式B: 设置环境变量 AI_VISION_PROVIDER / AI_VISION_API_KEY"
        )
    
    @property
    def client(self):
        """延迟初始化LLM客户端（仅云端模式使用）"""
        # _use_local=False 但 _local_engine 不为None → 状态不一致，清理本地引擎引用
        if not self._use_local and self._local_engine is not None:
            logger.warning("引擎状态不一致: _use_local=False 但 _local_engine 不为None，清理本地引擎引用")
            self._local_engine = None
        
        # 如果本地引擎标记为True，说明不应进入云端分支
        # 但如果走到这里说明状态不一致，自动修正
        if self._use_local and self._local_engine is not None:
            logger.warning("client属性在本地模式下被调用，这不应该发生")
            return None
        
        # _use_local=True 但 _local_engine=None → 状态不一致，自动修正为云端模式
        if self._use_local and self._local_engine is None:
            logger.warning("引擎状态不一致: _use_local=True 但 _local_engine=None，自动切换到云端模式")
            self._use_local = False
            # 同步切换model为有效的云端模型名，否则云端API会报 model not found
            if self.model in (OCRModelType.PADDLEOCR, OCRModelType.RAPIDOCR, OCRModelType.BAIDUOCR):
                self.model = self.DEFAULT_MODEL
        
        if self._client is None:
            from core.ai_vision import get_ai_vision_client, AIVisionConfigError
            try:
                self._client = get_ai_vision_client()
            except AIVisionConfigError as e:
                raise ValueError(str(e))
            except Exception as e:
                raise ValueError(f"云端AI模型客户端初始化失败: {e}")
        return self._client
    
    def is_local_mode(self) -> bool:
        """检查是否使用本地引擎"""
        return self._use_local and self._local_engine is not None
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取当前引擎信息"""
        return {
            'engine_type': 'local' if self._use_local else 'cloud',
            'model': self.model.value if self.model else None,
            'engine_name': self._local_engine.name if self._local_engine else 'Cloud AI'
        }
    
    def set_model(self, model: OCRModelType) -> None:
        """
        热插拔更换模型，同步更新引擎状态
        
        Args:
            model: 新的模型类型
        """
        self.model = model
        
        # 同步更新引擎模式
        if model in (OCRModelType.PADDLEOCR, OCRModelType.RAPIDOCR, OCRModelType.BAIDUOCR):
            # 本地引擎
            engine_type = {
                OCRModelType.PADDLEOCR: 'paddleocr',
                OCRModelType.RAPIDOCR:  'rapidocr',
                OCRModelType.BAIDUOCR:  'baiduocr',
            }.get(model, 'paddleocr')
            local_engine = get_local_ocr_engine(engine_type)
            if local_engine:
                self._use_local = True
                self._local_engine = local_engine
            else:
                # 本地引擎不可用，降级到云端
                logger.warning(f"本地引擎 {model.value} 不可用，降级到云端AI模型")
                self._use_local = False
                self._local_engine = None
                # 同步切换model为有效的云端模型名，否则云端API会报 model not found
                self.model = self.DEFAULT_MODEL
        else:
            # 云端模型
            self._use_local = False
            self._local_engine = None
            # 重置客户端，下次访问时重新初始化
            self._client = None
        
        logger.info(f"OCR模型已切换至: {model.value}, 引擎模式: {'本地' if self._use_local else '云端'}")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """获取可用模型列表"""
        from core.ai_vision import get_ai_vision_config, is_ai_vision_configured

        models = []
        engine = get_local_ocr_engine('paddleocr')
        if engine:
            models.append({"value": "paddleocr", "label": "PaddleOCR（本地）", "type": "local"})
        engine = get_local_ocr_engine('rapidocr')
        if engine:
            models.append({"value": "rapidocr", "label": "RapidOCR（本地，兼容AMD）", "type": "local"})
        engine = get_local_ocr_engine('baiduocr')
        if engine:
            models.append({"value": "baiduocr", "label": "百度OCR（云端）", "type": "cloud_ocr"})

        if is_ai_vision_configured():
            cfg = get_ai_vision_config()
            label = f"{cfg['provider_label'] or cfg['provider']} - {cfg['model']}"
            models.append({"value": "cloud_ai", "label": label, "type": "cloud"})

        return models
    
    def _encode_image_to_base64(self, image_source) -> str:
        """
        将图片编码为base64格式
        
        Args:
            image_source: 图片源，可以是文件路径、URL或Django File对象
            
        Returns:
            base64编码的图片URL（data:image/xxx;base64,...格式）
        """
        import mimetypes
        import requests
        import io
        
        # 处理URL - 尝试直接使用URL
        if isinstance(image_source, str) and (image_source.startswith('http://') or image_source.startswith('https://')):
            print(f"[OCR] 使用图片URL: {image_source[:100]}...")
            logger.info(f"使用图片URL: {image_source[:100]}...")
            
            # 首先检查URL是否可访问
            try:
                head_response = requests.head(image_source, timeout=10, allow_redirects=True)
                if head_response.status_code == 404:
                    raise ValueError(f"文件不存在（404错误），请确认文件已正确上传")
                elif head_response.status_code != 200:
                    raise ValueError(f"文件访问失败（状态码: {head_response.status_code}）")
                
                # 检查是否是支持的图片格式
                content_type = head_response.headers.get('Content-Type', '')
                print(f"[OCR] Content-Type: {content_type}")
                
                # 支持的图片格式
                supported_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']
                
                if content_type and content_type in supported_types:
                    # 是图片格式，直接返回URL
                    return image_source
                elif content_type and content_type == 'application/pdf':
                    # PDF文件 - 转换为图片
                    print(f"[OCR] 检测到PDF文件，正在转换为图片...")
                    return self._convert_pdf_to_base64(image_source)
                elif content_type and ('dwg' in content_type.lower() or 'dxf' in content_type.lower()):
                    raise ValueError(f"DWG/DXF文件暂不支持直接OCR识别，请导出为图片格式后上传")
                else:
                    # 尝试下载并处理
                    print(f"[OCR] 未知文件类型: {content_type}，尝试下载处理")
                    response = requests.get(image_source, timeout=30)
                    response.raise_for_status()
                    content = response.content
                    
                    # 检测文件类型
                    if content[:4] == b'%PDF':
                        # PDF文件 - 转换为图片
                        print(f"[OCR] 检测到PDF文件内容，正在转换为图片...")
                        return self._convert_pdf_bytes_to_base64(content)
                    elif content[:4] == b'PNG\x89' or content[:8] == b'\x89PNG\r\n\x1a\n':
                        # PNG图片，编码为base64
                        base64_data = base64.b64encode(content).decode('utf-8')
                        return f"data:image/png;base64,{base64_data}"
                    elif content[:2] == b'\xff\xd8':
                        # JPEG图片
                        base64_data = base64.b64encode(content).decode('utf-8')
                        return f"data:image/jpeg;base64,{base64_data}"
                    else:
                        # 尝试作为图片处理
                        mime_type = content_type if content_type.startswith('image/') else 'image/png'
                        base64_data = base64.b64encode(content).decode('utf-8')
                        return f"data:{mime_type};base64,{base64_data}"
                        
            except requests.exceptions.RequestException as e:
                raise ValueError(f"无法访问文件URL: {e}")
        
        # 处理相对URL（本地部署场景）- 以 /media/ 开头的路径
        if isinstance(image_source, str) and image_source.startswith('/media/'):
            print(f"[OCR] 检测到相对URL路径: {image_source}")
            logger.info(f"检测到相对URL路径: {image_source}")
            
            # 尝试从文件系统读取
            from django.conf import settings
            from urllib.parse import unquote
            import os
            
            # 构建本地文件路径（URL解码）
            relative_path = image_source.replace('/media/', '', 1)
            # URL解码（处理中文文件名）
            relative_path = unquote(relative_path)
            local_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            
            print(f"[OCR] 尝试读取本地文件: {local_path}")
            logger.info(f"尝试读取本地文件: {local_path}")
            
            if os.path.exists(local_path):
                print(f"[OCR] 本地文件存在，正在读取...")
                logger.info(f"本地文件存在，正在读取...")
                
                # 获取文件扩展名判断类型
                _, ext = os.path.splitext(local_path)
                ext = ext.lower()
                
                with open(local_path, 'rb') as f:
                    content = f.read()
                
                # 判断文件类型
                if ext == '.pdf' or content[:4] == b'%PDF':
                    print(f"[OCR] 检测到PDF文件，正在转换为图片...")
                    return self._convert_pdf_bytes_to_base64(content)
                elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    mime_type = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }.get(ext, 'image/png')
                    base64_data = base64.b64encode(content).decode('utf-8')
                    print(f"[OCR] 图片编码成功，大小: {len(base64_data)} 字符")
                    return f"data:{mime_type};base64,{base64_data}"
                else:
                    # 尝试作为图片处理
                    base64_data = base64.b64encode(content).decode('utf-8')
                    return f"data:image/png;base64,{base64_data}"
            else:
                raise ValueError(f"本地文件不存在: {local_path}")
        
        # 处理其他类型的图片源
        content = None
        filename = 'image.png'
        
        # 处理Django File对象
        if hasattr(image_source, 'read'):
            # Django File对象或文件句柄
            content = image_source.read()
            if hasattr(image_source, 'name'):
                filename = image_source.name
        elif isinstance(image_source, str):
            # 文件路径
            with open(image_source, 'rb') as f:
                content = f.read()
            filename = image_source
        elif isinstance(image_source, bytes):
            # 直接是字节数据
            content = image_source
        else:
            raise ValueError(f"不支持的图片源类型: {type(image_source)}")
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type or not mime_type.startswith('image/'):
            # 默认使用PNG
            mime_type = 'image/png'
        
        # 编码为base64
        base64_data = base64.b64encode(content).decode('utf-8')
        logger.info(f"图片已编码为base64, 大小: {len(base64_data)} 字符")
        return f"data:{mime_type};base64,{base64_data}"
    
    def _convert_pdf_to_base64(self, pdf_url: str) -> str:
        """
        将PDF文件URL转换为图片base64
        
        Args:
            pdf_url: PDF文件的URL
            
        Returns:
            第一页的base64编码图片
        """
        import requests
        
        try:
            # 下载PDF
            response = requests.get(pdf_url, timeout=60)
            response.raise_for_status()
            pdf_bytes = response.content
            
            return self._convert_pdf_bytes_to_base64(pdf_bytes)
        except Exception as e:
            raise ValueError(f"PDF转换失败: {e}")
    
    def _convert_pdf_bytes_to_base64(self, pdf_bytes: bytes) -> str:
        """
        将PDF字节数据转换为图片base64
        
        Args:
            pdf_bytes: PDF文件的字节数据
            
        Returns:
            第一页的base64编码图片
        """
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            
            # 打开PDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if len(pdf_document) == 0:
                raise ValueError("PDF文件没有页面")
            
            # 获取第一页
            page = pdf_document[0]
            
            # 4x缩放 ≈ 288 DPI，工程图细节标注需要高分辨率
            zoom = 4.0
            mat = fitz.Matrix(zoom, zoom)

            # 渲染页面为图片（白色背景）
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

            # 转换为PIL Image并做对比度增强（提升工程图细线/小字识别率）
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            from PIL import ImageEnhance, ImageFilter
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Sharpness(img).enhance(1.5)

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            base64_data = base64.b64encode(buffer.read()).decode('utf-8')
            pdf_document.close()
            
            print(f"[OCR] PDF转换成功，图片大小: {len(base64_data)} 字符")
            return f"data:image/png;base64,{base64_data}"
            
        except ImportError:
            raise ValueError("PDF转换功能需要安装PyMuPDF库: pip install PyMuPDF")
        except Exception as e:
            raise ValueError(f"PDF转换失败: {e}")
    
    def recognize_drawing(
        self, 
        image_source, 
        prompt: str = None
    ) -> List[DimensionResult]:
        """
        识别图纸中的尺寸标注
        
        Args:
            image_source: 图片源，可以是：
                - URL字符串（http://或https://）
                - 文件路径
                - Django File对象
                - 字节数据
            prompt: 自定义提示词（可选）
            
        Returns:
            识别结果列表
        """
        print(f"[OCR] 开始OCR识别, 图片源类型: {type(image_source).__name__}")
        print(f"[OCR] 当前引擎模式: {'本地' if self._use_local else '云端'}, 本地引擎: {self._local_engine.name if self._local_engine else 'None'}")
        logger.info(f"开始OCR识别, 图片源类型: {type(image_source).__name__}")
        logger.info(f"当前引擎模式: {'本地' if self._use_local else '云端'}, 本地引擎: {self._local_engine.name if self._local_engine else 'None'}")
        
        # 如果使用本地引擎
        if self._use_local and self._local_engine:
            return self._recognize_local(image_source)
        
        # 状态不一致自动修正
        if not self._use_local and self._local_engine is not None:
            logger.warning("引擎状态不一致: _use_local=False 但 _local_engine 不为None，清理本地引擎引用")
            self._local_engine = None
        
        if self._use_local and self._local_engine is None:
            logger.warning("引擎状态不一致: _use_local=True 但 _local_engine=None，自动切换到云端模式")
            self._use_local = False
            if self.model in (OCRModelType.PADDLEOCR, OCRModelType.RAPIDOCR, OCRModelType.BAIDUOCR):
                self.model = self.DEFAULT_MODEL
        
        # 云端识别（带模型降级机制）
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # 兜底检查：确保model是有效的云端模型名
        if self.model in (OCRModelType.PADDLEOCR, OCRModelType.RAPIDOCR, OCRModelType.BAIDUOCR):
            logger.warning(f"云端识别时model仍为本地引擎({self.model.value})，自动切换到默认云端模型")
            self.model = self.DEFAULT_MODEL
        
        # 编码图片
        try:
            image_url = self._encode_image_to_base64(image_source)
            print(f"[OCR] 图片编码成功, URL长度: {len(image_url)}")
            logger.info(f"图片编码成功, URL长度: {len(image_url)}")
        except Exception as e:
            print(f"[OCR] 图片编码失败: {e}")
            logger.error(f"图片编码失败: {e}")
            raise
        
        # 构建消息
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": prompt or "请识别这张工程图纸中的所有尺寸标注和公差信息。"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
            ])
        ]
        
        try:
            # 调用LLM进行识别（带模型降级机制）
            return self._invoke_cloud_with_fallback(messages)
            
        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            raise
    
    def _invoke_cloud_with_fallback(self, messages) -> List[DimensionResult]:
        """
        调用「系统管理 > 引擎配置」页面中配置的云端AI视觉模型进行识别。

        厂商/模型由后台配置决定（豆包/Kimi/GLM/自定义），不同厂商的模型名称
        互不兼容，因此不再做跨厂商的模型降级尝试，调用失败时直接报错并说明原因。
        """
        logger.info("调用云端AI视觉模型进行识别")
        response = self.client.invoke(messages=messages, temperature=0.1)

        content = response.content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            content = " ".join(text_parts)

        return self._parse_response(content)
    
    def _recognize_local(self, image_source) -> List[DimensionResult]:
        """使用本地OCR引擎识别，失败时报错（不自动降级到云端，避免引擎混淆）"""
        try:
            engine_name = self._local_engine.name if self._local_engine else 'Unknown'
            print(f"[OCR] 使用本地引擎识别: {engine_name}")
            logger.info(f"使用本地{engine_name}引擎识别")
            
            # 编码图片（为本地引擎准备）
            image_url = self._encode_image_to_base64(image_source)
            
            # 调用本地引擎识别
            results = self._local_engine.recognize(image_url)
            
            print(f"[OCR] 本地引擎识别完成，返回 {len(results)} 个结果")
            logger.info(f"本地引擎识别完成，返回 {len(results)} 个结果")
            
            # 转换为DimensionResult
            dimension_results = []
            for i, dim in enumerate(results):
                upper_tol = dim.get('upper_tolerance')
                lower_tol = dim.get('lower_tolerance')
                dimension_results.append(DimensionResult(
                    id=dim.get('id', f'DIM{i+1:03d}'),
                    name=dim.get('name', f'尺寸{i+1}'),
                    nominal_value=float(dim.get('nominal_value', 0)),
                    # 未识别到的公差保留None，不要伪造为0
                    upper_tolerance=float(upper_tol) if upper_tol is not None else None,
                    lower_tolerance=float(lower_tol) if lower_tol is not None else None,
                    unit=dim.get('unit', 'mm'),
                    dim_type=dim.get('dim_type', 'LINEAR'),
                    is_critical=bool(dim.get('is_critical', False)),
                    bbox=dim.get('bbox')
                ))
            
            # 如果本地引擎没有识别到结果，返回一个示例结果说明
            if not dimension_results:
                print(f"[OCR] 本地引擎未识别到尺寸信息")
                logger.warning("本地引擎未识别到尺寸信息")
                # 返回一个提示性结果
                dimension_results.append(DimensionResult(
                    id='DIM001',
                    name='未识别到尺寸',
                    nominal_value=0.0,
                    upper_tolerance=0.0,
                    lower_tolerance=0.0,
                    unit='mm',
                    dim_type='LINEAR',
                    is_critical=False
                ))
            
            return dimension_results
            
        except Exception as e:
            engine_name = self._local_engine.name if self._local_engine else 'Unknown'
            print(f"[OCR] 本地引擎{engine_name}识别失败: {e}")
            logger.error(f"本地引擎{engine_name}识别失败: {e}")
            raise ValueError(f"本地{engine_name}识别失败: {str(e)}。如需改用云端AI，请在下拉框切换引擎后重新识别。")
    
    def _can_use_cloud(self) -> bool:
        """检查是否可以使用云端识别"""
        from core.ai_vision import is_ai_vision_configured
        return is_ai_vision_configured()
    
    def _recognize_cloud(self, image_source) -> List[DimensionResult]:
        """使用云端AI模型识别（带降级机制）"""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # 兜底检查：确保model是有效的云端模型名
        if self.model in (OCRModelType.PADDLEOCR, OCRModelType.RAPIDOCR, OCRModelType.BAIDUOCR):
            logger.warning(f"云端识别时model仍为本地引擎({self.model.value})，自动切换到默认云端模型")
            self.model = self.DEFAULT_MODEL
        
        image_url = self._encode_image_to_base64(image_source)
        
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": "请识别这张工程图纸中的所有尺寸标注和公差信息。"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
            ])
        ]
        
        return self._invoke_cloud_with_fallback(messages)
    
    def _parse_response(self, content: str) -> List[DimensionResult]:
        """解析LLM响应"""
        results = []
        
        # 调试：打印原始响应内容
        logger.info(f"LLM原始响应长度: {len(content)}")
        logger.info(f"LLM原始响应前500字符: {content[:500]}")
        
        try:
            # 尝试提取JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                for dim in data.get("dimensions", []):
                    try:
                        nominal = dim.get("nominal_value")
                        upper = dim.get("upper_tolerance")
                        lower = dim.get("lower_tolerance")

                        # 气泡位置坐标（百分比0-100），用于在图纸上准确显示气泡标记；
                        # 缺失/格式不对时设为None，前端会回退为提示"位置未知"而非伪造位置
                        position = dim.get("position")
                        bbox = None
                        if isinstance(position, dict) and 'x' in position and 'y' in position:
                            try:
                                bbox = {'x': float(position['x']), 'y': float(position['y'])}
                            except (ValueError, TypeError):
                                bbox = None

                        results.append(DimensionResult(
                            id=dim.get("id", f"DIM{len(results)+1:03d}"),
                            name=dim.get("name", ""),
                            nominal_value=float(nominal) if nominal is not None else 0.0,
                            # 未识别到公差时保留None，不要伪造为0（0是一个真实的、含义完全不同的公差值）
                            upper_tolerance=float(upper) if upper is not None else None,
                            lower_tolerance=float(lower) if lower is not None else None,
                            unit=dim.get("unit", "mm"),
                            dim_type=dim.get("dim_type", "LINEAR"),
                            is_critical=bool(dim.get("is_critical", False)),
                            bbox=bbox
                        ))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析尺寸数据失败: {dim}, 错误: {e}")
                        continue
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}, 尝试正则提取")
            # 如果JSON解析失败，尝试简单的正则提取
            import re
            # 匹配类似 50±0.1, 100+0.2/-0.1, 25H7 等格式
            patterns = [
                r'(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)',  # 50±0.1
                r'(\d+\.?\d*)\s*\+\s*(\d+\.?\d*)\s*/[-]\s*(\d+\.?\d*)',  # 100+0.2/-0.1
                r'(\d+\.?\d*)',  # 简单数字
            ]
            
            for match in re.finditer(patterns[0], content):
                nominal = float(match.group(1))
                tolerance = float(match.group(2))
                results.append(DimensionResult(
                    id=f"DIM{len(results)+1:03d}",
                    name=f"尺寸{len(results)+1}",
                    nominal_value=nominal,
                    upper_tolerance=tolerance,
                    lower_tolerance=-tolerance,
                    unit="mm",
                    dim_type="LINEAR"
                ))
        
        return results
    
    def recognize_with_bbox(
        self, 
        image_url: str
    ) -> List[Dict[str, Any]]:
        """
        识别图纸并返回边界框坐标
        
        Args:
            image_url: 图纸图片URL
            
        Returns:
            包含边界框的识别结果
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        bbox_prompt = """请识别图纸中的所有尺寸标注区域，并输出它们的边界框坐标。

输出格式：
{
    "regions": [
        {
            "id": "DIM001",
            "text": "识别到的尺寸文本",
            "bbox": {
                "topLeftX": x_min,
                "topLeftY": y_min,
                "bottomRightX": x_max,
                "bottomRightY": y_max
            }
        }
    ]
}

注意：坐标为相对值(0-1000)，(0,0)为左上角。"""
        
        messages = [
            SystemMessage(content="你是一个专业的工程图纸识别助手。"),
            HumanMessage(content=[
                {"type": "text", "text": bbox_prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ]
        
        response = self.client.invoke(messages=messages, temperature=0.1)

        content = response.content
        if isinstance(content, list):
            content = " ".join(
                item.get("text", "") 
                for item in content 
                if isinstance(item, dict) and item.get("type") == "text"
            )
        
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except:
            pass
        
        return {"regions": []}


# 全局OCR服务实例
_ocr_service: Optional[OCRService] = None


def get_ocr_service(model: OCRModelType = None) -> OCRService:
    """
    获取OCR服务实例（单例模式）
    
    Args:
        model: 可选，指定使用的模型，可以是OCRModelType枚举或字符串
        
    Returns:
        OCR服务实例
    """
    global _ocr_service
    # 如果传入的是字符串，转换为枚举
    if model and isinstance(model, str):
        try:
            model = OCRModelType(model)
        except ValueError:
            logger.warning(f"未知的模型类型: {model}, 使用默认模型")
            model = None
    if _ocr_service is None:
        _ocr_service = OCRService(model)
    elif model and _ocr_service.model != model:
        _ocr_service.set_model(model)
    return _ocr_service
