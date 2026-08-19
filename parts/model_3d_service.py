"""
3D模型解析服务模块 - 支持STEP、IGES、STL等格式的解析
"""
import json
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import struct

logger = logging.getLogger(__name__)


class Model3DFormat(Enum):
    """3D模型格式枚举"""
    STEP = "step"
    IGES = "iges"
    STL = "stl"
    OBJ = "obj"
    PLY = "ply"


@dataclass
class BoundingBox:
    """边界框"""
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0
    
    @property
    def dimensions(self) -> tuple:
        """返回三个方向的尺寸"""
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z
        )
    
    def to_dict(self) -> Dict:
        """转字典"""
        return {
            "min": [self.min_x, self.min_y, self.min_z],
            "max": [self.max_x, self.max_y, self.max_z],
            "dimensions": list(self.dimensions)
        }


@dataclass
class MeshData:
    """网格数据"""
    vertices: List[List[float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    normals: List[List[float]] = field(default_factory=list)


@dataclass
class Model3DResult:
    """3D模型解析结果"""
    file_format: str
    vertex_count: int = 0
    face_count: int = 0
    edge_count: int = 0
    bounding_box: Optional[BoundingBox] = None
    volume: Optional[float] = None
    surface_area: Optional[float] = None
    mesh_data: Optional[MeshData] = None
    metadata: Dict = field(default_factory=dict)
    features: List[Dict] = field(default_factory=list)


class Model3DParser:
    """3D模型解析器"""
    
    SUPPORTED_FORMATS = {
        '.step': Model3DFormat.STEP,
        '.stp': Model3DFormat.STEP,
        '.iges': Model3DFormat.IGES,
        '.igs': Model3DFormat.IGES,
        '.stl': Model3DFormat.STL,
        '.obj': Model3DFormat.OBJ,
        '.ply': Model3DFormat.PLY,
    }
    
    def __init__(self):
        """初始化解析器"""
        pass
    
    def get_format(self, filename: str) -> Optional[Model3DFormat]:
        """
        获取文件格式
        
        Args:
            filename: 文件名
            
        Returns:
            模型格式枚举，不支持则返回None
        """
        ext = os.path.splitext(filename)[1].lower()
        return self.SUPPORTED_FORMATS.get(ext)
    
    def is_supported(self, filename: str) -> bool:
        """
        检查文件是否支持
        
        Args:
            filename: 文件名
            
        Returns:
            是否支持该格式
        """
        return self.get_format(filename) is not None
    
    def parse(self, file_source) -> Model3DResult:
        """
        解析3D模型文件
        
        Args:
            file_source: 文件源，可以是文件路径、URL或Django File对象
            
        Returns:
            解析结果
        """
        # 获取文件路径
        filepath = self._get_filepath(file_source)
        filename = os.path.basename(filepath)
        
        # 确定格式
        format_type = self.get_format(filename)
        if not format_type:
            raise ValueError(f"不支持的文件格式: {filename}")
        
        logger.info(f"开始解析3D模型: {filename}, 格式: {format_type.value}")
        
        # 根据格式选择解析方法
        if format_type == Model3DFormat.STEP:
            result = self._parse_step(filepath)
        elif format_type == Model3DFormat.IGES:
            result = self._parse_iges(filepath)
        elif format_type == Model3DFormat.STL:
            result = self._parse_stl(filepath)
        elif format_type == Model3DFormat.OBJ:
            result = self._parse_obj(filepath)
        elif format_type == Model3DFormat.PLY:
            result = self._parse_ply(filepath)
        else:
            raise ValueError(f"未实现该格式的解析: {format_type.value}")
        
        result.file_format = format_type.value
        
        # 分析特征
        result.features = self._extract_features(result)
        
        logger.info(f"3D模型解析完成: {result.vertex_count}顶点, {result.face_count}面")
        
        return result
    
    def _get_filepath(self, file_source) -> str:
        """获取文件路径"""
        if isinstance(file_source, str):
            # 检查是否是URL
            if file_source.startswith('http://') or file_source.startswith('https://'):
                # 下载文件到临时目录
                import requests
                response = requests.get(file_source, timeout=60)
                response.raise_for_status()
                
                # 从URL提取文件名
                filename = os.path.basename(file_source.split('?')[0])
                temp_dir = tempfile.gettempdir()
                filepath = os.path.join(temp_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                return filepath
            else:
                # 本地文件路径
                return file_source
        
        elif hasattr(file_source, 'read'):
            # Django File对象或文件句柄
            temp_dir = tempfile.gettempdir()
            filename = getattr(file_source, 'name', 'model.tmp')
            if '/' in filename:
                filename = os.path.basename(filename)
            
            filepath = os.path.join(temp_dir, filename)
            
            # 写入临时文件
            with open(filepath, 'wb') as f:
                if hasattr(file_source, 'seek'):
                    file_source.seek(0)
                content = file_source.read()
                f.write(content)
            
            return filepath
        
        else:
            raise ValueError(f"不支持的文件源类型: {type(file_source)}")
    
    def _parse_step(self, filepath: str) -> Model3DResult:
        """
        解析STEP文件
        
        STEP是ISO标准格式，包含完整的B-Rep信息
        """
        result = Model3DResult(file_format="step")
        
        try:
            # 尝试使用PythonOCC
            from OCC.Core.STEPControl import STEPControl_Reader
            from OCC.Core.IFSelect import IFSelect_RetDone
            from OCC.Core.BRepTools import breptools
            from OCC.Core.BRepBndLib import brepbndlib
            from OCC.Core.Bnd import Bnd_Box
            from OCC.Core.GProp import GProp_GProps
            from OCC.Core.BRepGProp import brepgprop
            from OCC.Core.TopExp import TopExp_Explorer
            from OCC.Core.TopAbs import TopAbs_VERTEX, TopAbs_FACE, TopAbs_EDGE
            from OCC.Core.BRep import BRep_Tool
            from OCC.Core.TopoDS import topods
            
            # 读取STEP文件
            reader = STEPControl_Reader()
            status = reader.ReadFile(filepath)
            
            if status != IFSelect_RetDone:
                raise ValueError("STEP文件读取失败")
            
            reader.TransferRoots()
            shape = reader.OneShape()
            
            # 计算边界框
            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            
            result.bounding_box = BoundingBox(
                min_x=xmin, min_y=ymin, min_z=zmin,
                max_x=xmax, max_y=ymax, max_z=zmax
            )
            
            # 计算体积和表面积
            props = GProp_GProps()
            brepgprop.VolumeProperties(shape, props)
            result.volume = props.Mass()
            
            brepgprop.SurfaceProperties(shape, props)
            result.surface_area = props.Mass()
            
            # 统计顶点、面、边数量
            vertex_exp = TopExp_Explorer(shape, TopAbs_VERTEX)
            while vertex_exp.More():
                result.vertex_count += 1
                vertex_exp.Next()
            
            face_exp = TopExp_Explorer(shape, TopAbs_FACE)
            while face_exp.More():
                result.face_count += 1
                face_exp.Next()
            
            edge_exp = TopExp_Explorer(shape, TopAbs_EDGE)
            while edge_exp.More():
                result.edge_count += 1
                edge_exp.Next()
            
            logger.info(f"STEP文件解析成功(OCC): {result.vertex_count}顶点, {result.face_count}面, 体积{result.volume:.2f}mm³")
            
        except ImportError:
            # 如果没有PythonOCC，使用简化解析
            logger.warning("PythonOCC未安装，使用简化STEP解析")
            result = self._parse_step_simple(filepath)
        
        return result
    
    def _parse_step_simple(self, filepath: str) -> Model3DResult:
        """
        简化的STEP解析（不依赖OCC）
        
        仅提取基本几何信息
        """
        result = Model3DResult(file_format="step")
        
        vertices = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # STEP文件的基本结构解析
            # 提取CARTESIAN_POINT
            import re
            point_pattern = r'#\d+\s*=\s*CARTESIAN_POINT\s*\(\s*\'[^\']*\'\s*,\s*\(\s*([\d\.\-+Ee]+)\s*,\s*([\d\.\-+Ee]+)\s*,\s*([\d\.\-+Ee]+)\s*\)\s*\)'
            
            for match in re.finditer(point_pattern, content):
                x, y, z = float(match.group(1)), float(match.group(2)), float(match.group(3))
                vertices.append([x, y, z])
            
            if vertices:
                # 计算边界框
                xs = [v[0] for v in vertices]
                ys = [v[1] for v in vertices]
                zs = [v[2] for v in vertices]
                
                result.bounding_box = BoundingBox(
                    min_x=min(xs), min_y=min(ys), min_z=min(zs),
                    max_x=max(xs), max_y=max(ys), max_z=max(zs)
                )
                result.vertex_count = len(vertices)
            
            # 统计面和边（简化）
            face_count = content.count('ADVANCED_FACE')
            if face_count == 0:
                face_count = content.count('FACE_OUTER_BOUND')
            result.face_count = face_count
            
            # 提取元数据
            result.metadata = {
                "schema": re.search(r'FILE_SCHEMA\s*\(\s*\(\s*\'([^\']+)\'\s*\)\s*\)', content),
                "description": re.search(r'FILE_DESCRIPTION\s*\(\s*\'([^\']+)\'', content),
            }
            result.metadata = {k: v.group(1) if v else None for k, v in result.metadata.items()}
            
            logger.info(f"STEP文件简化解析完成: {result.vertex_count}顶点, {result.face_count}面")
            
        except Exception as e:
            logger.error(f"STEP简化解析失败: {str(e)}")
            raise ValueError(f"STEP文件解析失败: {str(e)}")
        
        return result
    
    def _parse_iges(self, filepath: str) -> Model3DResult:
        """
        解析IGES文件
        
        IGES是较旧的交换格式
        """
        result = Model3DResult(file_format="iges")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # IGES文件有固定的列格式
            vertices = []
            
            for line in lines:
                if len(line) >= 80:
                    # 检查记录类型（第73列）
                    record_type = line[72:74].strip()
                    
                    # 解析不同的实体类型
                    if record_type in ['116', '118', '124']:  # 点、线、矩阵等
                        # 简化处理，仅提取坐标信息
                        pass
            
            result.metadata = {
                "note": "IGES格式支持有限，建议转换为STEP格式以获得更好的解析结果"
            }
            
            logger.info(f"IGES文件解析完成（简化模式）")
            
        except Exception as e:
            logger.error(f"IGES解析失败: {str(e)}")
        
        return result
    
    def _parse_stl(self, filepath: str) -> Model3DResult:
        """
        解析STL文件
        
        STL是最简单的3D格式，仅包含三角面片
        """
        result = Model3DResult(file_format="stl")
        mesh = MeshData()
        
        # 检查是ASCII还是二进制格式
        with open(filepath, 'rb') as f:
            header = f.read(80)
            is_ascii = header.lower().startswith(b'solid')
        
        if is_ascii:
            # ASCII STL
            result = self._parse_stl_ascii(filepath)
        else:
            # 二进制STL
            result = self._parse_stl_binary(filepath)
        
        return result
    
    def _parse_stl_ascii(self, filepath: str) -> Model3DResult:
        """解析ASCII格式STL"""
        result = Model3DResult(file_format="stl")
        mesh = MeshData()
        
        vertices = []
        faces = []
        normals = []
        vertex_map = {}
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        import re
        
        # 提取所有facet
        facet_pattern = r'facet\s+normal\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+outer\s+loop\s+vertex\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+vertex\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+vertex\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+([\d\.\-+Ee]+)\s+endloop\s+endfacet'
        
        for match in re.finditer(facet_pattern, content, re.IGNORECASE):
            # 法向量
            nx, ny, nz = float(match.group(1)), float(match.group(2)), float(match.group(3))
            normals.append([nx, ny, nz])
            
            # 三个顶点
            face_indices = []
            for i in range(3):
                vx = float(match.group(4 + i*3))
                vy = float(match.group(5 + i*3))
                vz = float(match.group(6 + i*3))
                
                vertex = (vx, vy, vz)
                if vertex not in vertex_map:
                    vertex_map[vertex] = len(vertices)
                    vertices.append([vx, vy, vz])
                
                face_indices.append(vertex_map[vertex])
            
            faces.append(face_indices)
        
        mesh.vertices = vertices
        mesh.faces = faces
        mesh.normals = normals
        
        result.vertex_count = len(vertices)
        result.face_count = len(faces)
        result.mesh_data = mesh
        
        # 计算边界框
        if vertices:
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            zs = [v[2] for v in vertices]
            
            result.bounding_box = BoundingBox(
                min_x=min(xs), min_y=min(ys), min_z=min(zs),
                max_x=max(xs), max_y=max(ys), max_z=max(zs)
            )
            
            # 计算体积（近似）
            result.volume = self._calculate_mesh_volume(mesh)
            result.surface_area = self._calculate_mesh_surface_area(mesh)
        
        return result
    
    def _parse_stl_binary(self, filepath: str) -> Model3DResult:
        """解析二进制格式STL"""
        result = Model3DResult(file_format="stl")
        mesh = MeshData()
        
        vertices = []
        faces = []
        normals = []
        vertex_map = {}
        
        with open(filepath, 'rb') as f:
            # 跳过80字节头
            f.read(80)
            
            # 读取面片数量（4字节小端）
            num_triangles = struct.unpack('<I', f.read(4))[0]
            
            for _ in range(num_triangles):
                # 法向量（3个float）
                nx, ny, nz = struct.unpack('<3f', f.read(12))
                normals.append([nx, ny, nz])
                
                # 三个顶点
                face_indices = []
                for _ in range(3):
                    vx, vy, vz = struct.unpack('<3f', f.read(12))
                    
                    vertex = (vx, vy, vz)
                    if vertex not in vertex_map:
                        vertex_map[vertex] = len(vertices)
                        vertices.append([vx, vy, vz])
                    
                    face_indices.append(vertex_map[vertex])
                
                faces.append(face_indices)
                
                # 属性字节（跳过）
                f.read(2)
        
        mesh.vertices = vertices
        mesh.faces = faces
        mesh.normals = normals
        
        result.vertex_count = len(vertices)
        result.face_count = len(faces)
        result.mesh_data = mesh
        
        # 计算边界框
        if vertices:
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            zs = [v[2] for v in vertices]
            
            result.bounding_box = BoundingBox(
                min_x=min(xs), min_y=min(ys), min_z=min(zs),
                max_x=max(xs), max_y=max(ys), max_z=max(zs)
            )
            
            # 计算体积和表面积
            result.volume = self._calculate_mesh_volume(mesh)
            result.surface_area = self._calculate_mesh_surface_area(mesh)
        
        return result
    
    def _parse_obj(self, filepath: str) -> Model3DResult:
        """解析OBJ文件"""
        result = Model3DResult(file_format="obj")
        mesh = MeshData()
        
        vertices = []
        faces = []
        normals = []
        
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                
                if parts[0] == 'v':
                    # 顶点
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'vn':
                    # 法向量
                    normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'f':
                    # 面
                    face_indices = []
                    for p in parts[1:]:
                        # OBJ面的格式可能是: v, v/vt, v/vt/vn, v//vn
                        idx = int(p.split('/')[0]) - 1  # OBJ索引从1开始
                        face_indices.append(idx)
                    faces.append(face_indices)
        
        mesh.vertices = vertices
        mesh.faces = faces
        mesh.normals = normals
        
        result.vertex_count = len(vertices)
        result.face_count = len(faces)
        result.mesh_data = mesh
        
        # 计算边界框
        if vertices:
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            zs = [v[2] for v in vertices]
            
            result.bounding_box = BoundingBox(
                min_x=min(xs), min_y=min(ys), min_z=min(zs),
                max_x=max(xs), max_y=max(ys), max_z=max(zs)
            )
            
            result.volume = self._calculate_mesh_volume(mesh)
            result.surface_area = self._calculate_mesh_surface_area(mesh)
        
        return result
    
    def _parse_ply(self, filepath: str) -> Model3DResult:
        """解析PLY文件"""
        result = Model3DResult(file_format="ply")
        mesh = MeshData()
        
        vertices = []
        faces = []
        
        # PLY文件有头部声明格式
        with open(filepath, 'rb') as f:
            # 读取头部
            line = f.readline().decode('ascii').strip()
            if line != 'ply':
                raise ValueError("无效的PLY文件")
            
            format_line = None
            num_vertices = 0
            num_faces = 0
            
            while True:
                line = f.readline().decode('ascii').strip()
                if line == 'end_header':
                    break
                
                parts = line.split()
                if parts[0] == 'format':
                    format_line = line
                elif parts[0] == 'element' and parts[1] == 'vertex':
                    num_vertices = int(parts[2])
                elif parts[0] == 'element' and parts[1] == 'face':
                    num_faces = int(parts[2])
            
            # 读取顶点（假设是binary_little_endian）
            for _ in range(num_vertices):
                v = struct.unpack('<3f', f.read(12))
                vertices.append(list(v))
            
            # 读取面
            for _ in range(num_faces):
                n = struct.unpack('<B', f.read(1))[0]  # 面的顶点数
                face_indices = list(struct.unpack(f'<{n}I', f.read(4*n)))
                faces.append(face_indices)
        
        mesh.vertices = vertices
        mesh.faces = faces
        
        result.vertex_count = len(vertices)
        result.face_count = len(faces)
        result.mesh_data = mesh
        
        # 计算边界框
        if vertices:
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            zs = [v[2] for v in vertices]
            
            result.bounding_box = BoundingBox(
                min_x=min(xs), min_y=min(ys), min_z=min(zs),
                max_x=max(xs), max_y=max(ys), max_z=max(zs)
            )
            
            result.volume = self._calculate_mesh_volume(mesh)
            result.surface_area = self._calculate_mesh_surface_area(mesh)
        
        return result
    
    def _calculate_mesh_volume(self, mesh: MeshData) -> float:
        """
        计算网格体积（使用有符号四面体体积法）
        """
        if not mesh.vertices or not mesh.faces:
            return 0.0
        
        def signed_volume_of_triangle(p1, p2, p3):
            return (p1[0] * (p2[1] * p3[2] - p3[1] * p2[2]) -
                    p2[0] * (p1[1] * p3[2] - p3[1] * p1[2]) +
                    p3[0] * (p1[1] * p2[2] - p2[1] * p1[2])) / 6.0
        
        total_volume = 0.0
        for face in mesh.faces:
            if len(face) >= 3:
                p1 = mesh.vertices[face[0]]
                p2 = mesh.vertices[face[1]]
                p3 = mesh.vertices[face[2]]
                total_volume += signed_volume_of_triangle(p1, p2, p3)
        
        return abs(total_volume)
    
    def _calculate_mesh_surface_area(self, mesh: MeshData) -> float:
        """
        计算网格表面积
        """
        if not mesh.vertices or not mesh.faces:
            return 0.0
        
        import math
        
        def triangle_area(p1, p2, p3):
            # 使用叉积计算三角形面积
            v1 = [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]]
            v2 = [p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]]
            
            # 叉积
            cross = [
                v1[1] * v2[2] - v1[2] * v2[1],
                v1[2] * v2[0] - v1[0] * v2[2],
                v1[0] * v2[1] - v1[1] * v2[0]
            ]
            
            # 模长的一半
            return math.sqrt(cross[0]**2 + cross[1]**2 + cross[2]**2) / 2.0
        
        total_area = 0.0
        for face in mesh.faces:
            if len(face) >= 3:
                p1 = mesh.vertices[face[0]]
                p2 = mesh.vertices[face[1]]
                p3 = mesh.vertices[face[2]]
                total_area += triangle_area(p1, p2, p3)
        
        return total_area
    
    def _extract_features(self, result: Model3DResult) -> List[Dict]:
        """
        从解析结果中提取特征
        
        提取孔、槽、凸台等常见特征
        """
        features = []
        
        # 基于边界框尺寸推断零件类型
        if result.bounding_box:
            dims = result.bounding_box.dimensions
            max_dim = max(dims)
            min_dim = min(dims)
            
            # 长宽比判断
            aspect_ratio = max_dim / min_dim if min_dim > 0 else 1.0
            
            if aspect_ratio > 5:
                features.append({
                    "type": "elongated_part",
                    "description": "细长零件",
                    "max_dimension": max_dim,
                    "aspect_ratio": aspect_ratio
                })
            elif aspect_ratio < 1.5:
                features.append({
                    "type": "compact_part",
                    "description": "紧凑零件",
                    "dimensions": list(dims)
                })
        
        # 如果有网格数据，分析孔特征
        if result.mesh_data and result.mesh_data.vertices:
            # 简化：基于顶点分布检测可能的孔特征
            # 实际应用中需要更复杂的算法
            pass
        
        return features


# 全局解析器实例
_parser: Optional[Model3DParser] = None


def get_model_3d_parser() -> Model3DParser:
    """
    获取3D模型解析器实例（单例模式）
    
    Returns:
        解析器实例
    """
    global _parser
    if _parser is None:
        _parser = Model3DParser()
    return _parser
