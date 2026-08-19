# CAD文件识别支持方案

## 当前系统支持情况

| 文件格式 | 存储支持 | OCR识别 | 解析尺寸 | 说明 |
|---------|---------|---------|---------|------|
| PNG/JPG | ✅ | ✅ | ✅ | 直接使用视觉模型识别 |
| PDF | ✅ | ✅ | ✅ | 自动转换为图片后识别 |
| DXF | ✅ | ⚠️ | ✅ | 需安装ezdxf库解析 |
| DWG | ✅ | ❌ | ❌ | 需专业工具转换 |
| DWF | ✅ | ❌ | ❌ | 需专业工具转换 |

## 关于OCR方案

### PaddleOCR
- **类型**: 开源OCR引擎
- **能力**: 识别图片中的文字
- **CAD支持**: ❌ 不支持，只能识别图片
- **适用场景**: 预算有限、离线部署、中文识别
- **安装状态**: ✅ **已默认安装**，开箱即用

### DeepSeek OCR (视觉模型)
- **类型**: 基于大模型的视觉识别
- **能力**: 理解图片内容，提取结构化信息
- **CAD支持**: ❌ 不支持，只能识别图片
- **适用场景**: 复杂图纸理解、需要上下文推理

### 当前系统使用的方案
- 使用 **视觉语言模型** (豆包视觉模型/Kimi)
- 支持图片和PDF（自动转图片）
- 能够识别尺寸标注、公差、技术要求
- 提供结构化的JSON输出

## CAD文件解决方案

### 方案1: 用户端转换（推荐入门）

**流程**: 用户在上传前将CAD导出为PDF或图片

**优点**:
- 无需额外部署
- 实现简单
- 兼容所有CAD软件

**缺点**:
- 增加用户操作步骤
- 可能丢失矢量精度

**实现**: 当前系统已支持，无需开发

---

### 方案2: DXF直接解析（推荐开发环境）

**适用**: DXF格式文件

**依赖**: `pip install ezdxf`

**能力**:
- 直接读取尺寸标注数据
- 无需转换为图片
- 精确度高

**代码示例**:
```python
from parts.cad_service import DXFParser, parse_cad_file

# 解析DXF文件
result = parse_cad_file('/path/to/file.dxf')

for dim in result.dimensions:
    print(f"尺寸: {dim.nominal_value} {dim.unit}")
    print(f"公差: {dim.upper_tolerance}/{dim.lower_tolerance}")
```

---

### 方案3: CAD转图片服务（推荐生产环境）

**适用**: DWG/DXF/DWF等所有CAD格式

**依赖**: ODA File Converter 或 Aspose.CAD

**流程**:
```
DWG文件 → CAD转换器 → PDF/图片 → OCR识别 → 尺寸数据
```

**选项A: ODA File Converter（免费）**
```bash
# 安装
# Ubuntu
sudo apt-get install oda-file-converter

# 转换命令
ODAFileConverter input.dwg output_dir ACAD2010 PDF
```

**选项B: Aspose.CAD（商业）**
```python
import aspose.cad as cad

# 加载CAD文件
image = cad.Image.load("input.dwg")

# 导出为PDF
pdf_options = cad.imageoptions.PdfOptions()
image.save("output.pdf", pdf_options)

# 导出为PNG
png_options = cad.imageoptions.PngOptions()
image.save("output.png", png_options)
```

**选项C: LibreDWG（开源）**
```bash
# 安装
pip install pplibredwg

# DWG转DXF
dwg2dxf input.dwg output.dxf
```

---

### 方案4: 云端API服务（推荐云部署）

**适用**: 所有CAD格式

**优点**:
- 无需本地安装
- 跨平台兼容
- 专业支持

**选项A: Autodesk Platform Services (APS)**
- 官方API
- 支持所有AutoCAD格式
- 需要Autodesk开发者账号

**选项B: Aspose.CAD Cloud**
- 商业云服务
- REST API调用
- 按需付费

**代码示例**:
```python
import requests

# 调用云端API转换CAD
response = requests.post(
    'https://api.aspose.cloud/v3.0/cad/convert',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    files={'file': open('input.dwg', 'rb')},
    data={'format': 'PNG'}
)

# 保存转换结果
with open('output.png', 'wb') as f:
    f.write(response.content)
```

---

## 系统预留接口

系统已在 `parts/cad_service.py` 中预留以下接口：

```python
from parts.cad_service import CADService, CADParseResult

# 获取CAD服务
service = CADService()

# 检查文件是否支持
is_supported = service.is_supported('file.dwg')

# 解析CAD文件（提取尺寸）
result = service.parse('file.dxf')

# 转换为图片（用于OCR）
images = service.convert_to_image('file.dxf', dpi=300)
```

## 推荐部署方案

### 开发/测试环境
1. 支持PNG/JPG/PDF直接上传
2. DXF文件安装ezdxf解析
3. 其他格式提示用户转换为PDF

### 生产环境（私有部署）
1. 安装ODA File Converter或LibreDWG
2. 实现CAD到图片的自动转换
3. 使用现有OCR服务识别

### 云端部署
1. 集成Aspose.CAD Cloud或APS API
2. 所有CAD格式云端转换
3. 无需本地安装

## 扩展开发指南

### 添加新的CAD解析器

1. 继承 `CADParserBase` 类
2. 实现必需方法：
   - `parse()`: 解析文件
   - `convert_to_image()`: 转换为图片
   - `get_supported_formats()`: 返回支持的格式

3. 注册解析器：
```python
from parts.cad_service import get_cad_service

service = get_cad_service()
service.register_parser(MyCustomParser())
```

### 与OCR服务集成

```python
from parts.cad_service import cad_to_image
from parts.ocr_service import get_ocr_service

# CAD转图片
images = cad_to_image('input.dwg')

# OCR识别
ocr = get_ocr_service()
for img in images:
    dimensions = ocr.recognize_drawing(img)
    # 处理尺寸数据...
```

## 常见问题

**Q: 为什么不能直接OCR识别CAD文件？**
A: CAD文件是矢量数据格式，包含几何定义而非像素图像。OCR只能识别图像中的文字。

**Q: PaddleOCR能识别CAD吗？**
A: 不能。PaddleOCR是图像文字识别引擎，只能处理图片格式。

**Q: 推荐哪种方案？**
A: 
- 快速实现：让用户导出为PDF
- 精确解析：DXF格式 + ezdxf库
- 全格式支持：Aspose.CAD商业库

**Q: 如何获取尺寸的精确值？**
A: 使用DXF解析器可直接获取精确的尺寸数值，无需OCR识别，精度更高。
