from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
import os
import json
import logging
from .models import Part, CADExtraction, Dimension, DimensionTemplate, PartAttachment, SOPDocument, ControlRequirement, RiskPoint
from .serializers import (
    PartSerializer, PartListSerializer, CADExtractionSerializer, 
    DimensionSerializer, DimensionTemplateSerializer, PartAttachmentSerializer
)
from .ocr_service import get_ocr_service, OCRModelType
from core.permissions import AutoPermissionMixin, user_has_permission, get_user_permissions

logger = logging.getLogger(__name__)


class DimensionTemplateViewSet(viewsets.ModelViewSet):
    """尺寸模板API视图集"""
    queryset = DimensionTemplate.objects.all()
    serializer_class = DimensionTemplateSerializer
    filterset_fields = ['template_type', 'is_public', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    
    def get_queryset(self):
        """只返回公开的模板或用户自己的模板"""
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            return queryset.filter(models.Q(is_public=True) | models.Q(created_by=user))
        return queryset.filter(is_public=True)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PartViewSet(viewsets.ModelViewSet):
    """零件API视图集"""
    queryset = Part.objects.all()
    serializer_class = PartSerializer
    filterset_fields = ['part_number', 'customer', 'status']
    search_fields = ['part_number', 'part_name', 'customer']
    ordering_fields = ['created_at', 'part_number']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PartListSerializer
        return PartSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_cad(self, request, pk=None):
        """上传CAD文件"""
        part = self.get_object()
        cad_file = request.FILES.get('cad_file')
        
        if not cad_file:
            return Response(
                {'error': '请选择CAD文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 删除旧文件
        if part.cad_file:
            part.cad_file.delete()
        
        part.cad_file = cad_file
        part.cad_file_type = os.path.splitext(cad_file.name)[1].upper()
        part.save()
        
        return Response({
            'status': 'success',
            'message': 'CAD文件上传成功',
            'file': cad_file.name
        })
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_files(self, request, pk=None):
        """上传多种类型文件"""
        part = self.get_object()
        uploaded_files = []
        
        # 处理CAD文件
        if 'cad_file' in request.FILES:
            cad_file = request.FILES['cad_file']
            if part.cad_file:
                part.cad_file.delete()
            part.cad_file = cad_file
            part.cad_file_type = os.path.splitext(cad_file.name)[1].upper()
            uploaded_files.append(f"CAD文件: {cad_file.name}")
        
        # 处理图片文件
        if 'drawing_file' in request.FILES:
            drawing_file = request.FILES['drawing_file']
            if part.drawing_file:
                part.drawing_file.delete()
            part.drawing_file = drawing_file
            uploaded_files.append(f"图片文件: {drawing_file.name}")
        
        # 处理PDF文件
        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            if part.pdf_file:
                part.pdf_file.delete()
            part.pdf_file = pdf_file
            uploaded_files.append(f"PDF文件: {pdf_file.name}")
        
        if not uploaded_files:
            return Response(
                {'error': '请选择至少一个文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        part.save()
        
        return Response({
            'status': 'success',
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'files': uploaded_files
        })
    
    @action(detail=True, methods=['post'])
    def parse_cad(self, request, pk=None):
        """解析CAD文件"""
        part = self.get_object()
        
        if not part.cad_file:
            return Response(
                {'error': '请先上传CAD文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建解析记录
        extraction = CADExtraction.objects.create(
            part=part,
            status='PROCESSING'
        )
        
        # 模拟CAD解析（实际应调用专业CAD解析库）
        # 这里生成示例数据
        sample_data = [
            {
                'dim_id': 'DIM001',
                'dim_type': 'DIAMETER',
                'name': '外径',
                'nominal_value': 50.0,
                'upper_tolerance': 0.1,
                'lower_tolerance': -0.1,
                'unit': 'mm'
            },
            {
                'dim_id': 'DIM002',
                'dim_type': 'LINEAR',
                'name': '总长',
                'nominal_value': 100.0,
                'upper_tolerance': 0.2,
                'lower_tolerance': -0.2,
                'unit': 'mm'
            },
            {
                'dim_id': 'DIM003',
                'dim_type': 'LINEAR',
                'name': '壁厚',
                'nominal_value': 5.0,
                'upper_tolerance': 0.05,
                'lower_tolerance': -0.05,
                'unit': 'mm',
                'is_critical': True
            },
        ]
        
        # 保存解析结果
        for data in sample_data:
            Dimension.objects.create(
                extraction=extraction,
                **data
            )
        
        extraction.extraction_data = sample_data
        extraction.status = 'COMPLETED'
        extraction.extracted_at = timezone.now()
        extraction.save()
        
        return Response({
            'status': 'success',
            'extraction_id': str(extraction.id),
            'dimensions_count': len(sample_data),
            'message': 'CAD解析完成'
        })
    
    @action(detail=True, methods=['post'])
    def ocr_drawing(self, request, pk=None):
        """
        OCR识别图纸
        
        请求参数:
        - model: OCR模型名称（可选）
        - file_type: 要识别的文件类型，可选值: 'drawing'(图片文件), 'cad'(CAD文件), 'pdf'(PDF文档)
        - 如果未指定file_type，按以下顺序选择: drawing_file -> pdf_file -> cad_file
        """
        part = self.get_object()
        
        # 获取模型参数
        model_name = request.data.get('model', OCRModelType.CLOUD_AI.value)
        file_type = request.data.get('file_type', 'drawing')
        
        # 根据文件类型选择要识别的文件
        file_to_recognize = None
        file_label = ''
        
        if file_type == 'drawing' and part.drawing_file:
            file_to_recognize = part.drawing_file
            file_label = part.drawing_filename  # 使用原始文件名
        elif file_type == 'pdf' and part.pdf_file:
            file_to_recognize = part.pdf_file
            file_label = part.pdf_filename  # 使用原始文件名
        elif file_type == 'cad' and part.cad_file:
            file_to_recognize = part.cad_file
            file_label = part.cad_filename  # 使用原始文件名
        # 如果指定的文件类型不存在，尝试其他类型
        elif part.drawing_file:
            file_to_recognize = part.drawing_file
            file_label = part.drawing_filename
        elif part.pdf_file:
            file_to_recognize = part.pdf_file
            file_label = part.pdf_filename
        elif part.cad_file:
            file_to_recognize = part.cad_file
            file_label = part.cad_filename
        
        if not file_to_recognize:
            return Response(
                {'error': '请先上传文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 获取OCR服务
            ocr_service = get_ocr_service()
            
            # 设置模型（如果指定了不同的模型）
            for model_type in OCRModelType:
                if model_type.value == model_name:
                    ocr_service.set_model(model_type)
                    break
            
            # 获取文件的签名URL
            # 使用S3签名URL，让OCR服务可以访问文件
            try:
                file_url = file_to_recognize.url
                logger.info(f"OCR识别 - 文件类型: {file_label}, URL前80字符: {file_url[:80] if file_url else 'None'}")
            except Exception as url_error:
                logger.error(f"获取文件URL失败: {url_error}")
                return Response(
                    {'error': f'无法获取文件URL: {str(url_error)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 执行OCR识别 - 使用URL
            results = ocr_service.recognize_drawing(file_url)
            
            logger.info(f"OCR识别返回 {len(results)} 个尺寸")
            for i, dim in enumerate(results[:3]):  # 只打印前3条
                logger.info(f"  尺寸[{i}]: id={dim.id}, nominal={dim.nominal_value}, upper={dim.upper_tolerance}, lower={dim.lower_tolerance}")
            
            # 转换为字典列表
            dimensions_data = [
                {
                    'id': dim.id,
                    'name': dim.name,
                    'nominal_value': dim.nominal_value,
                    'upper_tolerance': dim.upper_tolerance,
                    'lower_tolerance': dim.lower_tolerance,
                    'unit': dim.unit,
                    'dim_type': dim.dim_type,
                    'is_critical': dim.is_critical,
                    'position': dim.bbox
                }
                for dim in results
            ]
            
            # 保存识别结果
            extraction = CADExtraction.objects.create(
                part=part,
                extraction_data={'dimensions': dimensions_data, 'source_file': file_label},
                status='COMPLETED',
                extracted_at=timezone.now()
            )
            
            # 保存尺寸记录
            for dim in results:
                Dimension.objects.create(
                    extraction=extraction,
                    dim_id=dim.id,
                    dim_type=dim.dim_type,
                    name=dim.name,
                    nominal_value=dim.nominal_value,
                    upper_tolerance=dim.upper_tolerance,
                    lower_tolerance=dim.lower_tolerance,
                    unit=dim.unit,
                    is_critical=dim.is_critical,
                    position=dim.bbox
                )

            return Response({
                'status': 'success',
                'extraction_id': str(extraction.id),
                'dimensions': dimensions_data,
                'dimensions_count': len(dimensions_data),
                'model_used': ocr_service.model.value,
                'source_file': file_label,
                'message': f'OCR识别完成，识别到{len(dimensions_data)}个尺寸（来源: {file_label}）'
            })
            
        except Exception as e:
            import traceback
            logger.error(f"OCR识别失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'OCR识别失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def ocr_models(self, request):
        """获取可用的OCR模型列表"""
        ocr_service = get_ocr_service()
        return Response({
            'models': ocr_service.get_available_models(),
            'current_model': ocr_service.model.value if ocr_service.model else None
        })
    
    @action(detail=True, methods=['get'])
    def pdf_preview(self, request, pk=None):
        """将PDF文件转为图片用于预览（解决media文件访问问题）"""
        part = self.get_object()
        
        # 确定要预览的文件
        file_to_preview = None
        file_type = request.query_params.get('file_type', 'pdf')
        
        if file_type == 'pdf' and part.pdf_file:
            file_to_preview = part.pdf_file
        elif file_type == 'drawing' and part.drawing_file:
            file_to_preview = part.drawing_file
        elif file_type == 'cad' and part.cad_file:
            file_to_preview = part.cad_file
        
        # 如果没指定类型，按优先级选择
        if not file_to_preview:
            if part.pdf_file:
                file_to_preview = part.pdf_file
            elif part.drawing_file:
                file_to_preview = part.drawing_file
            elif part.cad_file:
                file_to_preview = part.cad_file
        
        if not file_to_preview:
            return Response(
                {'error': '没有可预览的文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.http import HttpResponse
            import fitz  # PyMuPDF
            from PIL import Image
            import io as _io
            
            # 读取文件内容
            file_content = file_to_preview.read()
            file_to_preview.seek(0)  # 重置文件指针
            
            # 检查是否是PDF
            if file_content[:4] == b'%PDF':
                pdf_document = fitz.open(stream=file_content, filetype="pdf")
                if len(pdf_document) == 0:
                    return Response({'error': 'PDF文件没有页面'}, status=status.HTTP_400_BAD_REQUEST)
                
                page = pdf_document[0]
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pdf_document.close()
                
                buffer = _io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                return HttpResponse(buffer.read(), content_type='image/png')
            else:
                # 非PDF文件（图片等），直接返回
                import mimetypes
                _, ext = os.path.splitext(file_to_preview.name)
                mime_type = mimetypes.guess_type(f"file{ext}")[0] or 'image/png'
                return HttpResponse(file_content, content_type=mime_type)
                
        except ImportError:
            return Response(
                {'error': 'PDF预览需要安装PyMuPDF库: pip install PyMuPDF'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"PDF预览转换失败: {e}")
            return Response(
                {'error': f'文件预览失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_model_3d(self, request, pk=None):
        """上传3D模型文件"""
        part = self.get_object()
        model_file = request.FILES.get('model_3d_file')
        
        if not model_file:
            return Response(
                {'error': '请选择3D模型文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查文件格式
        from .model_3d_service import get_model_3d_parser
        parser = get_model_3d_parser()
        if not parser.is_supported(model_file.name):
            return Response(
                {'error': f'不支持的文件格式，支持格式: STEP(.stp/.step), IGES(.igs/.iges), STL, OBJ, PLY'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 删除旧文件
        if part.model_3d_file:
            part.model_3d_file.delete()
        
        part.model_3d_file = model_file
        part.save()
        
        return Response({
            'status': 'success',
            'message': '3D模型文件上传成功',
            'file': model_file.name
        })
    
    @action(detail=True, methods=['post'])
    def analyze_model_3d(self, request, pk=None):
        """解析3D模型文件"""
        part = self.get_object()
        
        if not part.model_3d_file:
            return Response(
                {'error': '请先上传3D模型文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .model_3d_service import get_model_3d_parser
            from .models import Model3DAnalysis
            
            # 创建解析记录
            file_ext = os.path.splitext(part.model_3d_file.name)[1].upper()
            analysis = Model3DAnalysis.objects.create(
                part=part,
                status='PROCESSING',
                file_format=file_ext.lower().replace('.', '')
            )
            
            # 解析3D模型
            parser = get_model_3d_parser()
            result = parser.parse(part.model_3d_file)
            
            # 更新解析记录
            analysis.status = 'COMPLETED'
            analysis.file_size = part.model_3d_file.size
            analysis.vertex_count = result.vertex_count
            analysis.face_count = result.face_count
            analysis.edge_count = result.edge_count
            
            if result.bounding_box:
                analysis.bounding_box = result.bounding_box.to_dict()
            
            analysis.volume = result.volume
            analysis.surface_area = result.surface_area
            analysis.metadata = result.metadata
            analysis.features = result.features
            
            if result.mesh_data:
                # 简化网格数据，只保留前1000个顶点用于预览
                preview_vertices = result.mesh_data.vertices[:1000]
                preview_faces = result.mesh_data.faces[:1000]
                analysis.mesh_data = {
                    'vertices': preview_vertices,
                    'faces': preview_faces,
                    'vertex_count': result.vertex_count,
                    'face_count': result.face_count,
                    'is_preview': result.vertex_count > 1000
                }
            
            analysis.geometry_data = {
                'file_format': result.file_format,
                'has_mesh': result.mesh_data is not None
            }
            
            analysis.analyzed_at = timezone.now()
            analysis.save()
            
            return Response({
                'status': 'success',
                'analysis_id': str(analysis.id),
                'vertex_count': result.vertex_count,
                'face_count': result.face_count,
                'edge_count': result.edge_count,
                'bounding_box': analysis.bounding_box,
                'volume': float(result.volume) if result.volume else None,
                'surface_area': float(result.surface_area) if result.surface_area else None,
                'features': result.features,
                'message': f'3D模型解析完成'
            })
            
        except Exception as e:
            import traceback
            logger.error(f"3D模型解析失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 更新失败状态
            if 'analysis' in locals():
                analysis.status = 'FAILED'
                analysis.error_message = str(e)
                analysis.save()
            
            return Response(
                {'error': f'3D模型解析失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def analyze_control_requirements(self, request, pk=None):
        """分析控制要求"""
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        file_label = ''
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
            file_label = '图片文件'
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
            file_label = 'PDF文档'
        elif part.cad_file:
            file_to_analyze = part.cad_file
            file_label = 'CAD文件'
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .analysis_service import get_analysis_service
            from .models import ControlRequirement
            
            # 获取分析服务
            analysis_service = get_analysis_service()
            
            # 获取已有的尺寸数据
            dimensions = part.dimensions.all()
            dimensions_data = [
                {
                    "id": d.dim_id,
                    "name": d.name,
                    "nominal_value": float(d.nominal_value),
                    "upper_tolerance": float(d.upper_tolerance) if d.upper_tolerance is not None else None,
                    "lower_tolerance": float(d.lower_tolerance) if d.lower_tolerance is not None else None,
                    "unit": d.unit,
                    "dim_type": d.dim_type,
                    "is_critical": d.is_critical
                }
                for d in dimensions
            ] if dimensions.exists() else None
            
            # 分析控制要求
            results = analysis_service.analyze_control_requirements(
                file_to_analyze.url,
                dimensions_data
            )
            
            # 保存到数据库
            created_requirements = []
            for cr in results:
                requirement = ControlRequirement.objects.create(
                    part=part,
                    requirement_id=cr.requirement_id,
                    requirement_name=cr.requirement_name,
                    control_type=cr.control_type,
                    description=cr.description,
                    nominal_value=cr.nominal_value,
                    upper_limit=cr.upper_limit,
                    lower_limit=cr.lower_limit,
                    unit=cr.unit,
                    risk_level=cr.risk_level,
                    risk_factors=cr.risk_factors,
                    impact_analysis=cr.impact_analysis,
                    inspection_method=cr.inspection_method,
                    inspection_tool=cr.inspection_tool,
                    inspection_frequency=cr.inspection_frequency,
                    is_key_characteristic=cr.is_key_characteristic,
                    is_safety_critical=cr.is_safety_critical
                )
                created_requirements.append(requirement)
            
            return Response({
                'status': 'success',
                'message': f'控制要求分析完成，识别到{len(created_requirements)}个控制要求',
                'control_requirements': [
                    {
                        'id': str(r.id),
                        'requirement_id': r.requirement_id,
                        'requirement_name': r.requirement_name,
                        'control_type': r.control_type,
                        'description': r.description,
                        'risk_level': r.risk_level,
                        'is_key_characteristic': r.is_key_characteristic
                    }
                    for r in created_requirements
                ],
                'total_count': len(created_requirements)
            })
            
        except Exception as e:
            import traceback
            logger.error(f"控制要求分析失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'控制要求分析失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def analyze_risk_points(self, request, pk=None):
        """识别关键风险点"""
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        elif part.cad_file:
            file_to_analyze = part.cad_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .analysis_service import get_analysis_service
            from .models import RiskPoint, ControlRequirement
            
            # 获取分析服务
            analysis_service = get_analysis_service()
            
            # 获取已有的数据
            dimensions = part.dimensions.all()
            dimensions_data = [
                {
                    "id": d.dim_id,
                    "name": d.name,
                    "nominal_value": float(d.nominal_value)
                }
                for d in dimensions
            ] if dimensions.exists() else None
            
            control_requirements = part.control_requirements.all()
            cr_data = [
                {
                    "requirement_id": cr.requirement_id,
                    "requirement_name": cr.requirement_name,
                    "control_type": cr.control_type,
                    "risk_level": cr.risk_level
                }
                for cr in control_requirements
            ] if control_requirements.exists() else None
            
            # 识别风险点
            results = analysis_service.analyze_risk_points(
                file_to_analyze.url,
                dimensions_data,
                cr_data
            )
            
            # 保存到数据库
            created_risks = []
            for rp in results:
                risk = RiskPoint.objects.create(
                    part=part,
                    risk_id=rp.risk_id,
                    risk_name=rp.risk_name,
                    description=rp.description,
                    risk_category=rp.risk_category,
                    severity=rp.severity,
                    probability=rp.probability,
                    affected_dimensions=rp.affected_dimensions,
                    affected_processes=rp.affected_processes,
                    prevention_measures=rp.prevention_measures,
                    correction_measures=rp.correction_measures,
                    contingency_plan=rp.contingency_plan
                )
                created_risks.append(risk)
            
            return Response({
                'status': 'success',
                'message': f'关键风险点识别完成，识别到{len(created_risks)}个风险点',
                'risk_points': [
                    {
                        'id': str(r.id),
                        'risk_id': r.risk_id,
                        'risk_name': r.risk_name,
                        'severity': r.severity,
                        'probability': float(r.probability)
                    }
                    for r in created_risks
                ],
                'total_count': len(created_risks)
            })
            
        except Exception as e:
            import traceback
            logger.error(f"关键风险点识别失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'关键风险点识别失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_sop(self, request, pk=None):
        """生成SOP文档"""
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        elif part.cad_file:
            file_to_analyze = part.cad_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取文档类型
        document_type = request.data.get('document_type', 'SOP')
        
        try:
            from .analysis_service import get_analysis_service
            from .models import SOPDocument, ControlRequirement, RiskPoint
            
            # 获取分析服务
            analysis_service = get_analysis_service()
            
            # 零件信息
            part_info = {
                "part_number": part.part_number,
                "part_name": part.part_name,
                "revision": part.revision,
                "material": part.material,
                "customer": part.customer,
                "description": part.description
            }
            
            # 获取已有数据
            dimensions = part.dimensions.all()
            dimensions_data = [
                {
                    "id": d.dim_id,
                    "name": d.name,
                    "nominal_value": float(d.nominal_value)
                }
                for d in dimensions
            ] if dimensions.exists() else None
            
            control_requirements = part.control_requirements.all()
            cr_data = [
                {
                    "requirement_id": cr.requirement_id,
                    "requirement_name": cr.requirement_name
                }
                for cr in control_requirements
            ] if control_requirements.exists() else None
            
            risk_points = part.risk_points.all()
            rp_data = [
                {
                    "risk_id": rp.risk_id,
                    "risk_name": rp.risk_name
                }
                for rp in risk_points
            ] if risk_points.exists() else None
            
            # 生成SOP
            result = analysis_service.generate_sop(
                file_to_analyze.url,
                part_info,
                dimensions_data,
                cr_data,
                rp_data,
                document_type
            )
            
            # 生成文档编号
            date_str = timezone.now().strftime('%Y%m%d')
            count = SOPDocument.objects.filter(
                document_number__startswith=f'SOP-{part.part_number}-{date_str}'
            ).count()
            document_number = f'SOP-{part.part_number}-{date_str}-{count+1:03d}'
            
            # 保存到数据库
            sop = SOPDocument.objects.create(
                part=part,
                document_number=document_number,
                document_title=result.document_title,
                document_type=result.document_type,
                version=result.version,
                content=json.dumps([s.__dict__ for s in result.sections], ensure_ascii=False),
                sections=[{
                    'title': s.title,
                    'content': s.content
                } for s in result.sections],
                status='DRAFT',
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # 关联控制要求和风险点
            if result.control_requirements:
                cr_ids = result.control_requirements
                cr_objs = ControlRequirement.objects.filter(requirement_id__in=cr_ids)
                sop.control_requirements.set(cr_objs)
            
            if result.risk_points:
                rp_ids = result.risk_points
                rp_objs = RiskPoint.objects.filter(risk_id__in=rp_ids)
                sop.risk_points.set(rp_objs)
            
            return Response({
                'status': 'success',
                'message': f'{document_type}文档生成成功',
                'sop_document': {
                    'id': str(sop.id),
                    'document_number': sop.document_number,
                    'document_title': sop.document_title,
                    'document_type': sop.document_type,
                    'version': sop.version,
                    'sections': sop.sections,
                    'created_at': sop.created_at.isoformat()
                }
            })
            
        except Exception as e:
            import traceback
            logger.error(f"SOP文档生成失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'SOP文档生成失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def full_analysis(self, request, pk=None):
        """完整图纸分析：尺寸识别 + 控制要求分析 + 风险点识别 + SOP生成"""
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        elif part.cad_file:
            file_to_analyze = part.cad_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .analysis_service import get_analysis_service
            from .models import ControlRequirement, RiskPoint, SOPDocument, Dimension, CADExtraction
            
            # 获取分析服务
            analysis_service = get_analysis_service()
            
            # 零件信息
            part_info = {
                "part_number": part.part_number,
                "part_name": part.part_name,
                "revision": part.revision,
                "material": part.material,
                "customer": part.customer,
                "description": part.description
            }
            
            # 执行完整分析
            result = analysis_service.full_analysis(
                file_to_analyze.url,
                part_info,
                generate_sop=True
            )
            
            # 保存尺寸
            if result.get('dimensions'):
                extraction = CADExtraction.objects.create(
                    part=part,
                    extraction_data={'dimensions': result['dimensions']},
                    status='COMPLETED',
                    extracted_at=timezone.now()
                )
                
                for dim_data in result['dimensions']:
                    Dimension.objects.create(
                        extraction=extraction,
                        dim_id=dim_data.get('id'),
                        dim_type=dim_data.get('dim_type', 'LINEAR'),
                        name=dim_data.get('name'),
                        nominal_value=dim_data.get('nominal_value', 0),
                        upper_tolerance=dim_data.get('upper_tolerance', 0),
                        lower_tolerance=dim_data.get('lower_tolerance', 0),
                        unit=dim_data.get('unit', 'mm'),
                        is_critical=dim_data.get('is_critical', False),
                        position=dim_data.get('position')
                    )
            
            # 保存控制要求
            cr_ids = []
            if result.get('control_requirements'):
                for cr_data in result['control_requirements']:
                    cr = ControlRequirement.objects.create(
                        part=part,
                        requirement_id=cr_data.get('requirement_id'),
                        requirement_name=cr_data.get('requirement_name'),
                        control_type=cr_data.get('control_type', 'OTHER'),
                        description=cr_data.get('description'),
                        nominal_value=cr_data.get('nominal_value'),
                        upper_limit=cr_data.get('upper_limit'),
                        lower_limit=cr_data.get('lower_limit'),
                        unit=cr_data.get('unit', 'mm'),
                        risk_level=cr_data.get('risk_level', 'MEDIUM'),
                        risk_factors=cr_data.get('risk_factors', []),
                        impact_analysis=cr_data.get('impact_analysis', ''),
                        inspection_method=cr_data.get('inspection_method', ''),
                        inspection_tool=cr_data.get('inspection_tool', ''),
                        inspection_frequency=cr_data.get('inspection_frequency', ''),
                        is_key_characteristic=cr_data.get('is_key_characteristic', False),
                        is_safety_critical=cr_data.get('is_safety_critical', False)
                    )
                    cr_ids.append(cr.requirement_id)
            
            # 保存风险点
            rp_ids = []
            if result.get('risk_points'):
                for rp_data in result['risk_points']:
                    rp = RiskPoint.objects.create(
                        part=part,
                        risk_id=rp_data.get('risk_id'),
                        risk_name=rp_data.get('risk_name'),
                        description=rp_data.get('description'),
                        risk_category=rp_data.get('risk_category', ''),
                        severity=rp_data.get('severity', 'MAJOR'),
                        probability=rp_data.get('probability', 0.5),
                        affected_dimensions=rp_data.get('affected_dimensions', []),
                        affected_processes=rp_data.get('affected_processes', []),
                        prevention_measures=rp_data.get('prevention_measures', ''),
                        correction_measures=rp_data.get('correction_measures', ''),
                        contingency_plan=rp_data.get('contingency_plan', '')
                    )
                    rp_ids.append(rp.risk_id)
            
            # 保存SOP
            if result.get('sop_document'):
                sop_data = result['sop_document']
                
                # 生成文档编号
                date_str = timezone.now().strftime('%Y%m%d')
                count = SOPDocument.objects.filter(
                    document_number__startswith=f'SOP-{part.part_number}-{date_str}'
                ).count()
                document_number = f'SOP-{part.part_number}-{date_str}-{count+1:03d}'
                
                sop = SOPDocument.objects.create(
                    part=part,
                    document_number=document_number,
                    document_title=sop_data.get('document_title', f'{part.part_name} 标准操作程序'),
                    document_type=sop_data.get('document_type', 'SOP'),
                    version=sop_data.get('version', '1.0'),
                    content=json.dumps(sop_data.get('sections', []), ensure_ascii=False),
                    sections=sop_data.get('sections', []),
                    status='DRAFT',
                    created_by=request.user if request.user.is_authenticated else None
                )
                
                # 关联控制要求和风险点
                if cr_ids:
                    cr_objs = ControlRequirement.objects.filter(requirement_id__in=cr_ids)
                    sop.control_requirements.set(cr_objs)
                if rp_ids:
                    rp_objs = RiskPoint.objects.filter(risk_id__in=rp_ids)
                    sop.risk_points.set(rp_objs)
            
            return Response({
                'status': 'success',
                'message': '完整图纸分析完成',
                'summary': {
                    'dimensions_count': len(result.get('dimensions', [])),
                    'control_requirements_count': len(result.get('control_requirements', [])),
                    'risk_points_count': len(result.get('risk_points', [])),
                    'sop_generated': 'sop_document' in result
                },
                'data': result
            })
            
        except Exception as e:
            import traceback
            logger.error(f"完整图纸分析失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'完整图纸分析失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def drawing_review(self, request, pk=None):
        """
        图纸评审
        
        包括：
        1. 翻译完整性检查
        2. 内控正确性检查
        3. 识图完整性检查
        4. 技术标准识别
        """
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        elif part.cad_file:
            file_to_analyze = part.cad_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .drawing_review_service import get_review_service
            from .models import DrawingReview, StandardInterpretation
            
            # 获取评审服务
            review_service = get_review_service()
            
            # 执行图纸评审
            review_result = review_service.review_drawing(file_to_analyze.url)
            
            # 计算总体状态
            statuses = [
                review_result.get('translation_check', {}).get('status', 'N/A'),
                review_result.get('internal_control_check', {}).get('status', 'N/A'),
                review_result.get('drawing_completeness_check', {}).get('status', 'N/A')
            ]
            
            if 'FAIL' in statuses:
                overall_status = 'FAIL'
            elif 'WARNING' in statuses:
                overall_status = 'WARNING'
            elif all(s == 'PASS' for s in statuses if s != 'N/A'):
                overall_status = 'PASS'
            else:
                overall_status = 'N/A'
            
            # 保存评审记录
            drawing_review = DrawingReview.objects.create(
                part=part,
                translation_status=review_result.get('translation_check', {}).get('status', 'N/A'),
                translation_result=review_result.get('translation_check', {}),
                internal_control_status=review_result.get('internal_control_check', {}).get('status', 'N/A'),
                internal_control_result=review_result.get('internal_control_check', {}),
                completeness_status=review_result.get('drawing_completeness_check', {}).get('status', 'N/A'),
                completeness_result=review_result.get('drawing_completeness_check', {}),
                technical_standards=review_result.get('technical_standards', []),
                extracted_part_info=review_result.get('part_info', {}),
                overall_status=overall_status,
                reviewed_by=request.user if request.user.is_authenticated else None,
                reviewed_at=timezone.now()
            )
            
            # 保存技术标准解读
            standards = review_result.get('technical_standards', [])
            for std in standards:
                StandardInterpretation.objects.create(
                    part=part,
                    drawing_review=drawing_review,
                    standard_code=std.get('standard_code', ''),
                    standard_name=std.get('standard_name', ''),
                    process_name=std.get('process_name', ''),
                    overview=std.get('overview', ''),
                    key_parameters=std.get('key_parameters', []),
                    process_control_points=std.get('control_points', []),
                    internal_control_focus=std.get('control_points', [])
                )
            
            return Response({
                'status': 'success',
                'message': '图纸评审完成',
                'review_id': str(drawing_review.id),
                'overall_status': overall_status,
                'translation_check': review_result.get('translation_check', {}),
                'internal_control_check': review_result.get('internal_control_check', {}),
                'completeness_check': review_result.get('drawing_completeness_check', {}),
                'technical_standards': review_result.get('technical_standards', []),
                'part_info': review_result.get('part_info', {})
            })
            
        except Exception as e:
            import traceback
            logger.error(f"图纸评审失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'图纸评审失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_surface_zones(self, request, pk=None):
        """
        生成外观面区域
        
        根据零件图纸和外观面定义自动划分A/B/C级面
        """
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .drawing_review_service import get_review_service
            from .models import SurfaceZone
            
            # 获取评审服务
            review_service = get_review_service()
            
            # 零件信息
            part_info = {
                "part_number": part.part_number,
                "part_name": part.part_name,
                "revision": part.revision,
                "material": part.material,
                "customer": part.customer
            }
            
            # 生成外观面区域
            zones = review_service.generate_surface_zones(file_to_analyze.url, part_info)
            
            # 保存到数据库
            created_zones = []
            for zone in zones:
                sz = SurfaceZone.objects.create(
                    part=part,
                    zone_id=zone.zone_id,
                    zone_type=zone.zone_type,
                    description=zone.description,
                    location=zone.location,
                    quality_requirements=zone.quality_requirements,
                    color_code=zone.color_code
                )
                created_zones.append(sz)
            
            return Response({
                'status': 'success',
                'message': f'外观面区域生成完成，共{len(created_zones)}个区域',
                'zones': [
                    {
                        'id': str(z.id),
                        'zone_id': z.zone_id,
                        'zone_type': z.zone_type,
                        'description': z.description,
                        'location': z.location,
                        'quality_requirements': z.quality_requirements,
                        'color_code': z.color_code
                    }
                    for z in created_zones
                ],
                'summary': {
                    'zone_a_count': len([z for z in created_zones if z.zone_type == 'A']),
                    'zone_b_count': len([z for z in created_zones if z.zone_type == 'B']),
                    'zone_c_count': len([z for z in created_zones if z.zone_type == 'C'])
                }
            })
            
        except Exception as e:
            import traceback
            logger.error(f"外观面区域生成失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'外观面区域生成失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def interpret_standards(self, request, pk=None):
        """
        解读技术标准
        
        对图纸中识别的技术标准进行详细解读，提取关键参数和控制重点
        """
        part = self.get_object()
        
        # 获取技术标准（从图纸评审结果或请求参数）
        technical_standards = request.data.get('technical_standards', None)
        
        if not technical_standards:
            # 尝试从最近的图纸评审获取
            from .models import DrawingReview
            latest_review = DrawingReview.objects.filter(part=part).order_by('-created_at').first()
            if latest_review and latest_review.technical_standards:
                technical_standards = latest_review.technical_standards
        
        if not technical_standards:
            return Response(
                {'error': '未找到技术标准，请先进行图纸评审或提供标准列表'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .drawing_review_service import get_review_service
            from .models import StandardInterpretation
            
            # 获取评审服务
            review_service = get_review_service()
            
            # 获取图纸文件（可选）
            file_to_analyze = None
            if part.drawing_file:
                file_to_analyze = part.drawing_file.url
            elif part.pdf_file:
                file_to_analyze = part.pdf_file.url
            
            # 解读技术标准
            interpretations = review_service.interpret_standards(technical_standards, file_to_analyze)
            
            # 保存解读结果
            saved_interpretations = []
            for interp in interpretations:
                si = StandardInterpretation.objects.create(
                    part=part,
                    standard_code=interp.get('standard_code', ''),
                    standard_name=interp.get('standard_name', ''),
                    process_name=interp.get('applicable_processes', [''])[0] if isinstance(interp.get('applicable_processes'), list) else '',
                    overview=interp.get('overview', ''),
                    key_parameters=interp.get('key_parameters', []),
                    process_control_points=interp.get('process_control_points', []),
                    common_issues=interp.get('common_issues', []),
                    internal_control_focus=interp.get('internal_control_focus', [])
                )
                saved_interpretations.append(si)
            
            return Response({
                'status': 'success',
                'message': f'技术标准解读完成，共{len(saved_interpretations)}个标准',
                'interpretations': [
                    {
                        'id': str(si.id),
                        'standard_code': si.standard_code,
                        'standard_name': si.standard_name,
                        'overview': si.overview,
                        'key_parameters': si.key_parameters,
                        'process_control_points': si.process_control_points,
                        'internal_control_focus': si.internal_control_focus
                    }
                    for si in saved_interpretations
                ]
            })
            
        except Exception as e:
            import traceback
            logger.error(f"技术标准解读失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'技术标准解读失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_inspection_sop(self, request, pk=None):
        """
        生成检验SOP
        
        结合零件图纸、技术标准解读、外观面区域生成完整的检验SOP
        包含尺寸、外观、性能、标识检验项目
        """
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .drawing_review_service import get_review_service
            from .models import SOPDocument, InspectionSOPItem, SurfaceZone, StandardInterpretation, Dimension, CADExtraction
            
            # 获取评审服务
            review_service = get_review_service()
            
            # 收集已有数据
            part_info = {
                "part_number": part.part_number,
                "part_name": part.part_name,
                "revision": part.revision,
                "material": part.material,
                "customer": part.customer,
                "surface_finish": part.surface_treatment
            }
            
            # 获取尺寸数据
            dimensions = []
            latest_extraction = CADExtraction.objects.filter(part=part, status='COMPLETED').order_by('-created_at').first()
            if latest_extraction:
                dimensions = list(latest_extraction.dimensions.all().values(
                    'dim_id', 'name', 'nominal_value', 'upper_tolerance', 'lower_tolerance', 'unit', 'is_critical'
                ))
            
            # 获取技术标准解读
            standards = list(StandardInterpretation.objects.filter(part=part).values(
                'standard_code', 'standard_name', 'key_parameters', 'process_control_points'
            ))
            
            # 获取外观面区域
            zones = list(SurfaceZone.objects.filter(part=part).values(
                'zone_id', 'zone_type', 'description', 'quality_requirements'
            ))
            
            # 生成检验SOP
            sop_result = review_service.generate_inspection_sop(
                file_to_analyze.url,
                part_info,
                dimensions,
                standards,
                zones
            )
            
            # 生成文档编号
            date_str = timezone.now().strftime('%Y%m%d')
            count = SOPDocument.objects.filter(
                document_number__startswith=f'INS-{part.part_number}-{date_str}'
            ).count()
            document_number = f'INS-{part.part_number}-{date_str}-{count+1:03d}'
            
            # 保存SOP文档
            sop_document = SOPDocument.objects.create(
                part=part,
                document_number=document_number,
                document_title=sop_result.get('document_title', f'{part.part_name} 检验SOP'),
                document_type='INSPECTION_GUIDE',
                version='1.0',
                content=json.dumps(sop_result, ensure_ascii=False),
                sections=sop_result.get('notes', []),
                status='DRAFT',
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # 保存检验项目
            inspection_items = sop_result.get('inspection_items', {})
            sequence = 0
            
            # 尺寸检验项目
            for item in inspection_items.get('dimension_items', []):
                sequence += 1
                InspectionSOPItem.objects.create(
                    sop_document=sop_document,
                    item_no=item.get('item_no', f'DIM-{sequence}'),
                    category='DIMENSION',
                    inspection_object=item.get('inspection_object', ''),
                    attribute=item.get('attribute', ''),
                    nominal_value=item.get('nominal_value'),
                    upper_limit=item.get('upper_limit'),
                    lower_limit=item.get('lower_limit'),
                    unit=item.get('unit', 'mm'),
                    inspection_tool=item.get('inspection_tool', ''),
                    inspection_method=item.get('inspection_method', ''),
                    sampling_ratio=item.get('sampling_ratio', '100%'),
                    is_key_characteristic=item.get('is_key_characteristic', False),
                    sequence=sequence
                )
            
            # 外观检验项目
            for item in inspection_items.get('appearance_items', []):
                sequence += 1
                # 查找关联的外观面区域
                surface_zone = None
                if item.get('zone'):
                    surface_zone = SurfaceZone.objects.filter(
                        part=part, zone_type=item.get('zone')
                    ).first()
                
                InspectionSOPItem.objects.create(
                    sop_document=sop_document,
                    item_no=item.get('item_no', f'APP-{sequence}'),
                    category='APPEARANCE',
                    inspection_object=item.get('inspection_object', ''),
                    inspection_tool=item.get('inspection_tool', '目视'),
                    inspection_method=item.get('inspection_method', ''),
                    sampling_ratio=item.get('sampling_ratio', '100%'),
                    acceptance_criteria=item.get('acceptance_criteria', ''),
                    surface_zone=surface_zone,
                    sequence=sequence
                )
            
            # 性能检验项目
            for item in inspection_items.get('performance_items', []):
                sequence += 1
                InspectionSOPItem.objects.create(
                    sop_document=sop_document,
                    item_no=item.get('item_no', f'PRF-{sequence}'),
                    category='PERFORMANCE',
                    inspection_object=item.get('inspection_object', ''),
                    inspection_tool=item.get('inspection_tool', ''),
                    inspection_method=item.get('inspection_method', ''),
                    sampling_ratio=item.get('sampling_ratio', '100%'),
                    acceptance_criteria=item.get('acceptance_criteria', ''),
                    sequence=sequence
                )
            
            # 标识检验项目
            for item in inspection_items.get('identification_items', []):
                sequence += 1
                InspectionSOPItem.objects.create(
                    sop_document=sop_document,
                    item_no=item.get('item_no', f'IDN-{sequence}'),
                    category='IDENTIFICATION',
                    inspection_object=item.get('inspection_object', ''),
                    inspection_method=item.get('inspection_method', '目视'),
                    sampling_ratio=item.get('sampling_ratio', '100%'),
                    acceptance_criteria=item.get('acceptance_criteria', ''),
                    sequence=sequence
                )
            
            return Response({
                'status': 'success',
                'message': '检验SOP生成完成',
                'sop_document': {
                    'id': str(sop_document.id),
                    'document_number': sop_document.document_number,
                    'document_title': sop_document.document_title,
                    'inspection_items_count': sequence
                },
                'inspection_items': {
                    'dimension_count': len(inspection_items.get('dimension_items', [])),
                    'appearance_count': len(inspection_items.get('appearance_items', [])),
                    'performance_count': len(inspection_items.get('performance_items', [])),
                    'identification_count': len(inspection_items.get('identification_items', []))
                }
            })
            
        except Exception as e:
            import traceback
            logger.error(f"检验SOP生成失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'检验SOP生成失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def full_review_process(self, request, pk=None):
        """
        完整评审流程
        
        一键执行：图纸评审 → 外观面生成 → 标准解读 → 检验SOP生成
        """
        part = self.get_object()
        
        # 获取要分析的文件
        file_to_analyze = None
        
        if part.drawing_file:
            file_to_analyze = part.drawing_file
        elif part.pdf_file:
            file_to_analyze = part.pdf_file
        
        if not file_to_analyze:
            return Response(
                {'error': '请先上传图纸文件'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .drawing_review_service import get_review_service
            from .models import DrawingReview, SurfaceZone, StandardInterpretation, SOPDocument, InspectionSOPItem
            
            # 获取评审服务
            review_service = get_review_service()
            
            # 零件信息
            part_info = {
                "part_number": part.part_number,
                "part_name": part.part_name,
                "revision": part.revision,
                "material": part.material,
                "customer": part.customer,
                "surface_finish": part.surface_treatment
            }
            
            # 执行完整评审流程
            result = review_service.full_review_process(file_to_analyze.url, part_info)
            
            # 保存图纸评审结果
            drawing_review = None
            if 'drawing_review' in result:
                review_data = result['drawing_review']
                statuses = [
                    review_data.get('translation_check', {}).get('status', 'N/A'),
                    review_data.get('internal_control_check', {}).get('status', 'N/A'),
                    review_data.get('drawing_completeness_check', {}).get('status', 'N/A')
                ]
                
                if 'FAIL' in statuses:
                    overall_status = 'FAIL'
                elif 'WARNING' in statuses:
                    overall_status = 'WARNING'
                elif all(s == 'PASS' for s in statuses if s != 'N/A'):
                    overall_status = 'PASS'
                else:
                    overall_status = 'N/A'
                
                drawing_review = DrawingReview.objects.create(
                    part=part,
                    translation_status=review_data.get('translation_check', {}).get('status', 'N/A'),
                    translation_result=review_data.get('translation_check', {}),
                    internal_control_status=review_data.get('internal_control_check', {}).get('status', 'N/A'),
                    internal_control_result=review_data.get('internal_control_check', {}),
                    completeness_status=review_data.get('drawing_completeness_check', {}).get('status', 'N/A'),
                    completeness_result=review_data.get('drawing_completeness_check', {}),
                    technical_standards=review_data.get('technical_standards', []),
                    extracted_part_info=review_data.get('part_info', {}),
                    overall_status=overall_status,
                    reviewed_by=request.user if request.user.is_authenticated else None,
                    reviewed_at=timezone.now()
                )
            
            # 保存外观面区域
            zones_count = 0
            if 'surface_zones' in result:
                for zone_data in result['surface_zones']:
                    SurfaceZone.objects.create(
                        part=part,
                        zone_id=zone_data.get('zone_id', ''),
                        zone_type=zone_data.get('zone_type', 'C'),
                        description=zone_data.get('description', ''),
                        location=zone_data.get('location', ''),
                        quality_requirements=zone_data.get('quality_requirements', []),
                        color_code=zone_data.get('color_code', 'GREY')
                    )
                    zones_count += 1
            
            # 保存标准解读
            interpretations_count = 0
            if 'standard_interpretations' in result:
                for interp in result['standard_interpretations']:
                    StandardInterpretation.objects.create(
                        part=part,
                        drawing_review=drawing_review,
                        standard_code=interp.get('standard_code', ''),
                        standard_name=interp.get('standard_name', ''),
                        process_name=interp.get('applicable_processes', [''])[0] if isinstance(interp.get('applicable_processes'), list) else '',
                        overview=interp.get('overview', ''),
                        key_parameters=interp.get('key_parameters', []),
                        process_control_points=interp.get('process_control_points', []),
                        common_issues=interp.get('common_issues', []),
                        internal_control_focus=interp.get('internal_control_focus', [])
                    )
                    interpretations_count += 1
            
            # 保存检验SOP
            sop_created = False
            if 'inspection_sop' in result and result['inspection_sop']:
                sop_data = result['inspection_sop']
                
                date_str = timezone.now().strftime('%Y%m%d')
                count = SOPDocument.objects.filter(
                    document_number__startswith=f'INS-{part.part_number}-{date_str}'
                ).count()
                document_number = f'INS-{part.part_number}-{date_str}-{count+1:03d}'
                
                sop_document = SOPDocument.objects.create(
                    part=part,
                    document_number=document_number,
                    document_title=sop_data.get('document_title', f'{part.part_name} 检验SOP'),
                    document_type='INSPECTION_GUIDE',
                    version='1.0',
                    content=json.dumps(sop_data, ensure_ascii=False),
                    status='DRAFT',
                    created_by=request.user if request.user.is_authenticated else None
                )
                
                # 保存检验项目
                inspection_items = sop_data.get('inspection_items', {})
                sequence = 0
                
                for item in inspection_items.get('dimension_items', []):
                    sequence += 1
                    InspectionSOPItem.objects.create(
                        sop_document=sop_document,
                        item_no=item.get('item_no', f'DIM-{sequence}'),
                        category='DIMENSION',
                        inspection_object=item.get('inspection_object', ''),
                        attribute=item.get('attribute', ''),
                        nominal_value=item.get('nominal_value'),
                        upper_limit=item.get('upper_limit'),
                        lower_limit=item.get('lower_limit'),
                        unit=item.get('unit', 'mm'),
                        inspection_tool=item.get('inspection_tool', ''),
                        inspection_method=item.get('inspection_method', ''),
                        sampling_ratio=item.get('sampling_ratio', '100%'),
                        is_key_characteristic=item.get('is_key_characteristic', False),
                        sequence=sequence
                    )
                
                for item in inspection_items.get('appearance_items', []):
                    sequence += 1
                    InspectionSOPItem.objects.create(
                        sop_document=sop_document,
                        item_no=item.get('item_no', f'APP-{sequence}'),
                        category='APPEARANCE',
                        inspection_object=item.get('inspection_object', ''),
                        inspection_tool=item.get('inspection_tool', '目视'),
                        inspection_method=item.get('inspection_method', ''),
                        sampling_ratio=item.get('sampling_ratio', '100%'),
                        acceptance_criteria=item.get('acceptance_criteria', ''),
                        sequence=sequence
                    )
                
                for item in inspection_items.get('performance_items', []):
                    sequence += 1
                    InspectionSOPItem.objects.create(
                        sop_document=sop_document,
                        item_no=item.get('item_no', f'PRF-{sequence}'),
                        category='PERFORMANCE',
                        inspection_object=item.get('inspection_object', ''),
                        inspection_tool=item.get('inspection_tool', ''),
                        inspection_method=item.get('inspection_method', ''),
                        sampling_ratio=item.get('sampling_ratio', '100%'),
                        acceptance_criteria=item.get('acceptance_criteria', ''),
                        sequence=sequence
                    )
                
                for item in inspection_items.get('identification_items', []):
                    sequence += 1
                    InspectionSOPItem.objects.create(
                        sop_document=sop_document,
                        item_no=item.get('item_no', f'IDN-{sequence}'),
                        category='IDENTIFICATION',
                        inspection_object=item.get('inspection_object', ''),
                        inspection_method=item.get('inspection_method', '目视'),
                        sampling_ratio=item.get('sampling_ratio', '100%'),
                        acceptance_criteria=item.get('acceptance_criteria', ''),
                        sequence=sequence
                    )
                
                sop_created = True
            
            return Response({
                'status': 'success',
                'message': '完整评审流程完成',
                'summary': {
                    'drawing_review': drawing_review is not None,
                    'drawing_review_status': drawing_review.overall_status if drawing_review else None,
                    'surface_zones_count': zones_count,
                    'standard_interpretations_count': interpretations_count,
                    'inspection_sop_created': sop_created
                }
            })
            
        except Exception as e:
            import traceback
            logger.error(f"完整评审流程失败: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'完整评审流程失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def ocr(self, request):
        """通过文件URL进行OCR识别（用于旧字段文件的OCR识别）"""
        from rest_framework.parsers import JSONParser
        
        file_url = request.data.get('file_url')
        file_type = request.data.get('file_type', 'IMAGE').upper()
        model = request.data.get('model', 'doubao-seed-1-8-251228')
        file_name = request.data.get('file_name', '')  # 原始文件名
        part_id = request.data.get('part_id')
        
        if not file_url:
            return Response(
                {'status': 'error', 'error': '缺少文件URL'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # CAD文件需要特殊处理
        if file_type == 'CAD':
            return Response(
                {'status': 'error', 'error': 'CAD文件是矢量格式，无法直接进行OCR识别。请先将其转换为PDF或图片格式后上传，或在"系统管理 > 引擎配置"中安装本地CAD解析引擎。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 如果没有传递文件名，尝试从URL中提取（去掉签名参数）
        if not file_name:
            file_name = file_url.split('/')[-1].split('?')[0] if file_url else '未知'
        
        # 创建识别中状态的记录
        extraction = CADExtraction.objects.create(
            part_id=part_id,
            extraction_data={
                'source_file': file_name,
                'source_type': file_type,
                'dimensions': []
            },
            status='PROCESSING'
        )
        
        try:
            ocr_service = get_ocr_service(model)
            # 调用OCR服务，传递文件URL
            results = ocr_service.recognize_drawing(file_url)
            
            # 转换为字典格式
            dimensions = []
            for r in results:
                dimensions.append({
                    'id': r.id,
                    'name': r.name,
                    'nominal_value': r.nominal_value,
                    'upper_tolerance': r.upper_tolerance,
                    'lower_tolerance': r.lower_tolerance,
                    'unit': r.unit,
                    'dim_type': r.dim_type,
                    'is_critical': r.is_critical,
                    'position': r.bbox
                })
            
            # 更新识别结果记录为成功状态
            extraction.extraction_data = {
                'source_file': file_name,
                'source_type': file_type,
                'dimensions': dimensions
            }
            extraction.status = 'COMPLETED'
            extraction.extracted_at = timezone.now()
            extraction.save()
            
            # 创建尺寸记录
            for dim in results:
                Dimension.objects.create(
                    extraction=extraction,
                    dim_id=dim.id,
                    name=dim.name,
                    nominal_value=dim.nominal_value,
                    upper_tolerance=dim.upper_tolerance,
                    lower_tolerance=dim.lower_tolerance,
                    unit=dim.unit,
                    dim_type=dim.dim_type,
                    is_critical=dim.is_critical,
                    position=dim.bbox
                )

            return Response({
                'status': 'success',
                'message': f'识别完成',
                'model_used': model,
                'source_file': file_name,
                'dimensions': dimensions,
                'extraction_id': str(extraction.id)
            })
        except Exception as e:
            import traceback
            logger.error(f"OCR识别失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 更新识别结果记录为失败状态
            extraction.status = 'FAILED'
            extraction.error_message = str(e)
            extraction.save()
            
            return Response(
                {'status': 'error', 'error': f'OCR识别失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def create_inspection_plan(self, request, pk=None):
        """从OCR识别结果创建检验计划"""
        part = self.get_object()
        
        # 获取最新的OCR识别结果
        extraction = CADExtraction.objects.filter(
            part=part, status='COMPLETED'
        ).order_by('-created_at').first()
        
        if not extraction:
            return Response(
                {'error': '未找到OCR识别结果，请先进行图纸识别'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not extraction.reviewed:
            return Response(
                {'error': 'AI/OCR识别结果尚未经人工复核确认，请先在图纸识别页面核对每个尺寸的数值、'
                           '公差和气泡位置，确认无误后点击"确认复核"，才能生成正式检验计划。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 导入检验计划模型
        from inspections.models import InspectionPlan, InspectionCharacteristic
        
        # 创建检验计划
        plan_name = request.data.get('plan_name', f'{part.part_number} 检验计划')
        standard = request.data.get('standard', 'AS9102')
        
        # 生成计划编号
        date_str = timezone.now().strftime('%Y%m%d')
        count = InspectionPlan.objects.filter(
            plan_number__startswith=f'FAI-{date_str}'
        ).count()
        plan_number = f'FAI-{date_str}-{count+1:04d}'
        
        plan = InspectionPlan.objects.create(
            plan_number=plan_number,
            plan_name=plan_name,
            part=part,
            standard=standard,
            status='DRAFT',
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # 从识别结果创建检验特性 - 优先从extraction_data获取，其次从Dimension表获取
        dimensions_data = extraction.extraction_data.get('dimensions', [])
        created_count = 0
        
        logger.info(f"创建检验计划 - extraction_id={extraction.id}, extraction_data keys={list(extraction.extraction_data.keys()) if isinstance(extraction.extraction_data, dict) else 'not_dict'}, dimensions_count={len(dimensions_data)}")
        
        # 如果extraction_data中没有数据，尝试从Dimension表获取
        if not dimensions_data:
            dimensions_data = [
                {
                    'id': dim.dim_id,
                    'name': dim.name,
                    'dim_type': dim.dim_type,
                    'nominal_value': float(dim.nominal_value) if dim.nominal_value is not None else 0,
                    # 未识别到的公差保持None，不要伪造为0（会破坏后续Cp/Cpk计算）
                    'upper_tolerance': float(dim.upper_tolerance) if dim.upper_tolerance is not None else None,
                    'lower_tolerance': float(dim.lower_tolerance) if dim.lower_tolerance is not None else None,
                    'unit': dim.unit,
                    'is_critical': dim.is_critical
                }
                for dim in extraction.dimensions.all()
            ]
            logger.info(f"从Dimension表获取数据, count={len(dimensions_data)}")
        
        for idx, dim in enumerate(dimensions_data, 1):
            # 处理dim_type字段名不一致的情况
            dim_type = dim.get('dim_type') or dim.get('type', 'LINEAR')
            
            # 兼容多种字段名格式（用is not None判断，避免把合法的0公差/0标称值误判为"未提供"）
            def _first_present(d, *keys):
                for key in keys:
                    if d.get(key) is not None:
                        return d.get(key)
                return None

            nominal_value = _first_present(dim, 'nominal_value', 'value', 'nominal')
            upper_tolerance = _first_present(dim, 'upper_tolerance', 'upper', 'usl')
            lower_tolerance = _first_present(dim, 'lower_tolerance', 'lower', 'lsl')

            # 确保是数字类型。理论值缺失时默认0，但公差缺失（None）必须保留None，
            # 不能伪造为0——0是一个真实的、含义完全不同的公差值，会让该尺寸被
            # 当成"零公差"参与后续Cp/Cpk计算，产生虚假的不合格判定。
            try:
                nominal_value = float(nominal_value) if nominal_value is not None else 0
            except (ValueError, TypeError):
                nominal_value = 0
            try:
                upper_tolerance = float(upper_tolerance) if upper_tolerance is not None else None
            except (ValueError, TypeError):
                upper_tolerance = None
            try:
                lower_tolerance = float(lower_tolerance) if lower_tolerance is not None else None
            except (ValueError, TypeError):
                lower_tolerance = None
            
            if idx <= 3:  # 只打印前3条日志
                logger.info(f"处理尺寸[{idx}]: id={dim.get('id')}, nominal={nominal_value}, upper={upper_tolerance}, lower={lower_tolerance}")
            
            InspectionCharacteristic.objects.create(
                plan=plan,
                char_number=dim.get('id', f'DIM{idx:03d}'),
                char_name=dim.get('name', f'尺寸{idx}'),
                char_type='DIMENSION' if dim_type in ['LINEAR', 'DIAMETER', 'RADIUS'] else 'GD_T',
                nominal_value=nominal_value,
                upper_tolerance=upper_tolerance,
                lower_tolerance=lower_tolerance,
                unit=dim.get('unit', 'mm'),
                is_critical=dim.get('is_critical', False),
                sequence=idx,
                measurement_method='MANUAL'  # 默认手动测量
            )
            created_count += 1
        
        return Response({
            'status': 'success',
            'message': f'检验计划创建成功，包含 {created_count} 个检验特性',
            'plan_id': str(plan.id),
            'plan_number': plan.plan_number,
            'plan_name': plan.plan_name,
            'characteristics_count': created_count,
            'redirect_url': f'/inspections/{plan.id}/'
        })


class CADExtractionViewSet(viewsets.ModelViewSet):
    """CAD解析API视图集"""
    queryset = CADExtraction.objects.all()
    serializer_class = CADExtractionSerializer
    filterset_fields = ['part', 'status']

    def destroy(self, request, *args, **kwargs):
        """删除解析结果"""
        extraction = self.get_object()
        extraction.delete()
        return Response({'status': 'success', 'message': '解析结果已删除'})

    @action(detail=True, methods=['post'])
    def confirm_review(self, request, pk=None):
        """
        人工确认核实CAD/OCR识别结果。
        必须先调用此接口，才能基于该解析记录生成正式检验特性，
        防止未经核实的AI识别错误（尤其是公差、气泡位置）直接进入正式FAI流程。
        """
        from django.utils import timezone
        extraction = self.get_object()

        if extraction.status != 'COMPLETED':
            return Response(
                {'error': '只有识别已完成的记录才能确认复核'},
                status=status.HTTP_400_BAD_REQUEST
            )

        unverified_count = extraction.dimensions.filter(tolerance_verified=False).count()

        extraction.reviewed = True
        extraction.reviewed_by = request.user
        extraction.reviewed_at = timezone.now()
        extraction.save(update_fields=['reviewed', 'reviewed_by', 'reviewed_at'])

        # 复核确认后，将该批次尺寸统一标记为已核实（用户已在复核界面查看/修正过）
        extraction.dimensions.update(tolerance_verified=True)

        return Response({
            'status': 'success',
            'message': f'识别结果已确认复核，共{extraction.dimensions.count()}个尺寸'
                       + (f'（其中{unverified_count}个此前未单独核实，已随本次复核一并确认）' if unverified_count else ''),
            'reviewed_at': extraction.reviewed_at,
        })


class DimensionViewSet(viewsets.ModelViewSet):
    """尺寸API视图集"""
    queryset = Dimension.objects.all()
    serializer_class = DimensionSerializer
    filterset_fields = ['extraction', 'dim_type', 'is_critical']


# 前端视图
class PartListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """零件列表页面"""
    model = Part
    template_name = 'parts/part_list.html'
    context_object_name = 'parts'
    paginate_by = 20
    permission_module = 'parts'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 筛选功能
        search = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')
        customer = self.request.GET.get('customer', '')
        
        if search:
            queryset = queryset.filter(
                models.Q(part_number__icontains=search) |
                models.Q(part_name__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if customer:
            queryset = queryset.filter(customer__icontains=customer)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['customer_filter'] = self.request.GET.get('customer', '')
        context['status_choices'] = Part.STATUS_CHOICES
        # 添加权限信息
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'parts', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'parts', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'parts', 'delete')
        return context


class PartDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """零件详情页面"""
    model = Part
    template_name = 'parts/part_detail.html'
    context_object_name = 'part'
    permission_module = 'parts'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['extractions'] = self.object.extractions.all()
        # 添加权限信息
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'parts', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'parts', 'delete')
        return context


class PartCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建零件页面"""
    model = Part
    template_name = 'parts/part_form.html'
    fields = ['part_number', 'part_name', 'revision', 'description', 
              'material', 'customer', 'customer_part_number',
              'batch_serial_number', 'order_number', 'production_quantity', 
              'fai_quantity', 'department', 'operator',
              'cad_file', 'drawing_file', 'pdf_file']
    success_url = reverse_lazy('part_list')
    permission_module = 'parts'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        # 保存文件元信息（原始文件名和大小）
        self._save_file_metadata()
        messages.success(self.request, '零件创建成功')
        return response
    
    def _save_file_metadata(self):
        """保存文件元信息到file_metadata字段"""
        metadata = {}
        if 'cad_file' in self.request.FILES:
            f = self.request.FILES['cad_file']
            metadata['cad'] = {
                'original_name': f.name,
                'size': f.size
            }
        if 'drawing_file' in self.request.FILES:
            f = self.request.FILES['drawing_file']
            metadata['drawing'] = {
                'original_name': f.name,
                'size': f.size
            }
        if 'pdf_file' in self.request.FILES:
            f = self.request.FILES['pdf_file']
            metadata['pdf'] = {
                'original_name': f.name,
                'size': f.size
            }
        if metadata:
            current = self.object.file_metadata or {}
            current.update(metadata)
            self.object.file_metadata = current
            self.object.save(update_fields=['file_metadata'])


class PartUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑零件页面"""
    model = Part
    template_name = 'parts/part_form.html'
    fields = ['part_number', 'part_name', 'revision', 'description', 
              'material', 'customer', 'customer_part_number',
              'batch_serial_number', 'order_number', 'production_quantity', 
              'fai_quantity', 'department', 'operator',
              'cad_file', 'drawing_file', 'pdf_file', 'status']
    permission_module = 'parts'
    
    def get_success_url(self):
        return reverse_lazy('part_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        # 保存文件元信息（原始文件名和大小）
        self._save_file_metadata()
        messages.success(self.request, '零件更新成功')
        return response
    
    def _save_file_metadata(self):
        """保存文件元信息到file_metadata字段"""
        metadata = {}
        if 'cad_file' in self.request.FILES:
            f = self.request.FILES['cad_file']
            metadata['cad'] = {
                'original_name': f.name,
                'size': f.size
            }
        if 'drawing_file' in self.request.FILES:
            f = self.request.FILES['drawing_file']
            metadata['drawing'] = {
                'original_name': f.name,
                'size': f.size
            }
        if 'pdf_file' in self.request.FILES:
            f = self.request.FILES['pdf_file']
            metadata['pdf'] = {
                'original_name': f.name,
                'size': f.size
            }
        if metadata:
            current = self.object.file_metadata or {}
            current.update(metadata)
            self.object.file_metadata = current
            self.object.save(update_fields=['file_metadata'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context


class PartDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除零件页面"""
    model = Part
    success_url = reverse_lazy('part_list')
    permission_module = 'parts'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '零件删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class DrawingOCRView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """图纸识别页面"""
    model = Part
    template_name = 'parts/drawing_ocr.html'
    context_object_name = 'part'
    permission_module = 'parts'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['extractions'] = self.object.extractions.all()
        
        # 获取所有附件（包括PDF、图片、CAD）
        all_attachments = list(self.object.attachments.all().order_by('-uploaded_at'))
        
        # 添加旧字段中的文件（pdf_file, drawing_file, cad_file）
        if self.object.cad_file:
            all_attachments.append({
                'id': 'legacy_cad',
                'file': self.object.cad_file,
                'file_name': self.object.cad_filename,
                'file_type': 'CAD',
                'is_legacy': True
            })
        if self.object.pdf_file:
            all_attachments.append({
                'id': 'legacy_pdf',
                'file': self.object.pdf_file,
                'file_name': self.object.pdf_filename,
                'file_type': 'PDF',
                'is_legacy': True
            })
        if self.object.drawing_file:
            all_attachments.append({
                'id': 'legacy_drawing',
                'file': self.object.drawing_file,
                'file_name': self.object.drawing_filename,
                'file_type': 'IMAGE',
                'is_legacy': True
            })
        
        context['ocr_attachments'] = all_attachments
        
        # 获取可用的OCR引擎 - 使用importlib检测已安装的包，避免shell调用pip的开销和超时风险
        import importlib.util

        ocr_engines = []
        from core.ai_vision import get_ai_vision_config, is_ai_vision_configured
        if is_ai_vision_configured():
            cfg = get_ai_vision_config()
            provider = cfg.get('provider', '')
            ocr_engines.append({
                'id': 'cloud_ai',
                'name': f"{cfg['provider_label'] or provider} - {cfg['model']}",
                'type': 'cloud',
            })

        def is_package_installed(import_name):
            try:
                return importlib.util.find_spec(import_name) is not None
            except (ImportError, ValueError):
                return False

        if is_package_installed('paddleocr'):
            ocr_engines.append({'id': 'paddleocr', 'name': 'PaddleOCR (本地)', 'type': 'local'})

        if is_package_installed('easyocr'):
            ocr_engines.append({'id': 'easyocr', 'name': 'EasyOCR (本地)', 'type': 'local'})

        if is_package_installed('pytesseract'):
            ocr_engines.append({'id': 'tesseract', 'name': 'Tesseract (本地)', 'type': 'local'})

        if is_package_installed('rapidocr_onnxruntime'):
            ocr_engines.append({'id': 'rapidocr', 'name': 'RapidOCR (本地)', 'type': 'local'})

        # 百度OCR（需配置 API Key + Secret Key）
        from parts.ocr_service import get_local_ocr_engine as _get_ocr_engine
        if _get_ocr_engine('baiduocr'):
            ocr_engines.append({'id': 'baiduocr', 'name': '百度OCR (云端)', 'type': 'cloud_ocr'})
        
        context['ocr_engines'] = ocr_engines
        
        # 添加检验计划列表
        context['inspection_plans'] = self.object.inspection_plans.all()
        return context


class ControlRequirementViewSet(viewsets.ModelViewSet):
    """控制要求API视图集"""
    from .models import ControlRequirement
    from .serializers import ControlRequirementSerializer
    
    queryset = ControlRequirement.objects.all()
    serializer_class = ControlRequirementSerializer
    filterset_fields = ['part', 'control_type', 'risk_level', 'is_key_characteristic']
    search_fields = ['requirement_id', 'requirement_name', 'description']
    ordering_fields = ['created_at', 'requirement_id', 'risk_level']


class RiskPointViewSet(viewsets.ModelViewSet):
    """关键风险点API视图集"""
    from .models import RiskPoint
    from .serializers import RiskPointSerializer
    
    queryset = RiskPoint.objects.all()
    serializer_class = RiskPointSerializer
    filterset_fields = ['part', 'severity', 'risk_category']
    search_fields = ['risk_id', 'risk_name', 'description']
    ordering_fields = ['created_at', 'severity', 'risk_id']


class SOPDocumentViewSet(viewsets.ModelViewSet):
    """SOP文档API视图集"""
    from .models import SOPDocument
    from .serializers import SOPDocumentSerializer
    
    queryset = SOPDocument.objects.all()
    serializer_class = SOPDocumentSerializer
    filterset_fields = ['part', 'document_type', 'status']
    search_fields = ['document_number', 'document_title']
    ordering_fields = ['created_at', 'document_number']


class Model3DAnalysisViewSet(viewsets.ModelViewSet):
    """3D模型解析API视图集"""
    from .models import Model3DAnalysis
    from .serializers import Model3DAnalysisSerializer
    
    queryset = Model3DAnalysis.objects.all()
    serializer_class = Model3DAnalysisSerializer
    filterset_fields = ['part', 'status', 'file_format']
    ordering_fields = ['created_at']


class DrawingReviewViewSet(viewsets.ModelViewSet):
    """图纸评审API视图集"""
    from .models import DrawingReview
    from .serializers import DrawingReviewSerializer
    
    queryset = DrawingReview.objects.all()
    serializer_class = DrawingReviewSerializer
    filterset_fields = ['part', 'overall_status']
    ordering_fields = ['-created_at']


class SurfaceZoneViewSet(viewsets.ModelViewSet):
    """外观面区域API视图集"""
    from .models import SurfaceZone
    from .serializers import SurfaceZoneSerializer
    
    queryset = SurfaceZone.objects.all()
    serializer_class = SurfaceZoneSerializer
    filterset_fields = ['part', 'zone_type']
    ordering_fields = ['zone_type', 'zone_id']


class StandardInterpretationViewSet(viewsets.ModelViewSet):
    """技术标准解读API视图集"""
    from .models import StandardInterpretation
    from .serializers import StandardInterpretationSerializer
    
    queryset = StandardInterpretation.objects.all()
    serializer_class = StandardInterpretationSerializer
    filterset_fields = ['part', 'drawing_review']
    search_fields = ['standard_code', 'standard_name']
    ordering_fields = ['-created_at']


class InspectionSOPItemViewSet(viewsets.ModelViewSet):
    """检验SOP项目API视图集"""
    from .models import InspectionSOPItem
    from .serializers import InspectionSOPItemSerializer
    
    queryset = InspectionSOPItem.objects.all()
    serializer_class = InspectionSOPItemSerializer
    filterset_fields = ['sop_document', 'category', 'is_key_characteristic']
    ordering_fields = ['category', 'sequence']


class PartAttachmentViewSet(viewsets.ModelViewSet):
    """零件附件API视图集"""
    from core.permissions import user_has_permission
    from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
    
    queryset = PartAttachment.objects.all()
    serializer_class = PartAttachmentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ['part', 'file_type', 'ocr_status']
    ordering_fields = ['-uploaded_at']
    
    def get_queryset(self):
        """根据用户权限过滤"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # 按零件过滤
        part_id = self.request.query_params.get('part')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """批量上传附件"""
        files = request.FILES.getlist('files')
        file_types = request.data.getlist('file_types')
        
        if not files:
            return Response(
                {'status': 'error', 'error': '请选择至少一个文件'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取零件ID
        part_id = request.data.get('part')
        if not part_id:
            return Response(
                {'status': 'error', 'error': '缺少零件ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证零件是否存在
        try:
            from django.db.models import UUIDField
            # 尝试使用UUID查询
            part = Part.objects.get(pk=part_id)
        except Part.DoesNotExist:
            return Response(
                {'status': 'error', 'error': '零件不存在', 'part_id': part_id},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'status': 'error', 'error': f'查询错误: {str(e)}', 'part_id': part_id},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_count = 0
        errors = []
        
        for i, file in enumerate(files):
            file_type = file_types[i] if i < len(file_types) else 'OTHER'
            
            try:
                attachment = PartAttachment.objects.create(
                    part=part,
                    file=file,
                    file_name=file.name,
                    file_type=file_type,
                    file_size=file.size,
                    uploaded_by=request.user if request.user.is_authenticated else None
                )
                uploaded_count += 1
            except Exception as e:
                errors.append(f'{file.name}: {str(e)}')
        
        if uploaded_count > 0:
            return Response({
                'status': 'success',
                'message': f'成功上传 {uploaded_count} 个文件',
                'uploaded_count': uploaded_count,
                'errors': errors
            })
        else:
            return Response(
                {'status': 'error', 'error': '上传失败', 'details': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """将附件文件转为图片用于预览（解决media文件访问问题）"""
        attachment = self.get_object()
        
        try:
            from django.http import HttpResponse
            import fitz  # PyMuPDF
            from PIL import Image
            import io as _io
            
            # 读取文件内容
            file_content = attachment.file.read()
            attachment.file.seek(0)
            
            # 检查是否是PDF
            if file_content[:4] == b'%PDF':
                pdf_document = fitz.open(stream=file_content, filetype="pdf")
                if len(pdf_document) == 0:
                    return Response({'error': 'PDF文件没有页面'}, status=400)
                
                page = pdf_document[0]
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pdf_document.close()
                
                buffer = _io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                return HttpResponse(buffer.read(), content_type='image/png')
            else:
                # 非PDF文件，直接返回原文件
                import mimetypes
                _, ext = os.path.splitext(attachment.file.name)
                mime_type = mimetypes.guess_type(f"file{ext}")[0] or 'image/png'
                return HttpResponse(file_content, content_type=mime_type)
                
        except ImportError:
            return Response(
                {'error': 'PDF预览需要安装PyMuPDF库'}, 
                status=500
            )
        except Exception as e:
            logger.error(f"附件预览转换失败: {e}")
            return Response(
                {'error': f'文件预览失败: {str(e)}'}, 
                status=500
            )

    @action(detail=True, methods=['post'])
    def ocr(self, request, pk=None):
        """对附件进行OCR识别"""
        attachment = self.get_object()
        
        # 检查文件类型是否支持OCR
        if attachment.file_type not in ['PDF', 'IMAGE', 'CAD']:
            return Response(
                {'status': 'error', 'error': f'{attachment.get_file_type_display()} 文件不支持OCR识别'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # CAD文件需要特殊处理
        if attachment.file_type == 'CAD':
            return Response(
                {'status': 'error', 'error': 'CAD文件是矢量格式，无法直接进行OCR识别。请先将其转换为PDF或图片格式后上传，或在"系统管理 > 引擎配置"中安装本地CAD解析引擎。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 更新状态为识别中
        attachment.ocr_status = 'PROCESSING'
        attachment.save()
        
        try:
            # 获取OCR服务（使用前端传入的引擎类型）
            model_name = request.data.get('model')
            ocr_service = get_ocr_service(model_name)

            # 获取文件URL（S3存储使用URL访问）
            file_url = attachment.file.url

            # 调用OCR服务（使用URL而不是本地路径）
            results = ocr_service.recognize_drawing(file_url)
            
            # 调试日志
            logger.info(f"OCR识别返回结果数量: {len(results) if results else 0}")
            if results:
                logger.info(f"OCR识别结果[0]: id={results[0].id}, name={results[0].name}, nominal={results[0].nominal_value}")
            else:
                logger.warning("OCR识别未返回任何尺寸结果")
            
            # 转换为字典列表
            dimensions_data = []
            for dim in results:
                try:
                    dimensions_data.append({
                        'id': dim.id,
                        'name': dim.name,
                        'nominal_value': float(dim.nominal_value) if dim.nominal_value is not None else 0.0,
                        # 未识别到的公差保持None，不要伪造为0（会破坏后续Cp/Cpk计算）
                        'upper_tolerance': float(dim.upper_tolerance) if dim.upper_tolerance is not None else None,
                        'lower_tolerance': float(dim.lower_tolerance) if dim.lower_tolerance is not None else None,
                        'unit': dim.unit,
                        'dim_type': dim.dim_type,
                        'is_critical': dim.is_critical,
                        'position': dim.bbox
                    })
                except Exception as e:
                    logger.warning(f"转换尺寸数据失败: {dim}, 错误: {e}")
            
            logger.info(f"转换后的dimensions_data: {dimensions_data}")
            
            # 保存识别结果
            attachment.ocr_status = 'COMPLETED'
            attachment.ocr_data = {'dimensions': dimensions_data}
            attachment.save()
            
            # 始终创建CADExtraction记录（即使没有识别到尺寸）
            extraction = CADExtraction.objects.create(
                part=attachment.part,
                extraction_data={
                    'source_file': attachment.file_name,
                    'source_type': attachment.file_type,
                    'dimensions': dimensions_data
                },
                status='COMPLETED'
            )
            
            # 如果识别到尺寸数据，创建尺寸记录
            if dimensions_data:
                for dim in results:
                    Dimension.objects.create(
                        extraction=extraction,
                        dim_id=dim.id,
                        dim_type=dim.dim_type,
                        name=dim.name,
                        nominal_value=dim.nominal_value if dim.nominal_value is not None else 0.0,
                        # 未识别到的公差保持None，不要伪造为0（会破坏后续Cp/Cpk计算）
                        upper_tolerance=dim.upper_tolerance,
                        lower_tolerance=dim.lower_tolerance,
                        unit=dim.unit,
                        is_critical=dim.is_critical,
                        position=dim.bbox
                    )
            
            return Response({
                'status': 'success',
                'message': f'OCR识别完成，识别到{len(dimensions_data)}个尺寸',
                'dimensions': dimensions_data,
                'dimensions_count': len(dimensions_data),
                'model_used': ocr_service.model.value if ocr_service.model else None
            })
            
        except Exception as e:
            attachment.ocr_status = 'FAILED'
            attachment.ocr_error = str(e)
            attachment.save()
            
            return Response(
                {'status': 'error', 'error': f'识别失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==================== SOP文档前端页面视图 ====================

class SOPListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """SOP文档列表页面"""
    model = SOPDocument
    template_name = 'parts/sop_list.html'
    context_object_name = 'sop_documents'
    paginate_by = 20
    permission_module = 'parts'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 按零件筛选
        part_id = self.request.GET.get('part')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        # 按状态筛选
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        # 按类型筛选
        doc_type = self.request.GET.get('document_type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'parts', 'add')
        return context


class SOPDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """SOP文档详情页面"""
    model = SOPDocument
    template_name = 'parts/sop_detail.html'
    context_object_name = 'sop'
    permission_module = 'parts'


class SOPCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建SOP文档"""
    model = SOPDocument
    template_name = 'parts/sop_form.html'
    fields = ['part', 'document_number', 'document_title', 'document_type', 'version', 
              'content', 'status', 'effective_date', 'notes']
    permission_module = 'parts'

    def get_success_url(self):
        return reverse_lazy('sop_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parts'] = Part.objects.all().order_by('part_number')
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'SOP文档创建成功')
        return super().form_valid(form)


class SOPUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑SOP文档"""
    model = SOPDocument
    template_name = 'parts/sop_form.html'
    fields = ['document_title', 'document_type', 'version', 'content', 
              'status', 'effective_date', 'notes']
    permission_module = 'parts'
    
    def get_success_url(self):
        return reverse_lazy('sop_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'SOP文档更新成功')
        return super().form_valid(form)


# ==================== 控制要求前端页面视图 ====================

class ControlRequirementListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """控制要求列表页面"""
    model = ControlRequirement
    template_name = 'parts/control_requirement_list.html'
    context_object_name = 'requirements'
    paginate_by = 20
    permission_module = 'parts'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        part_id = self.request.GET.get('part')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        risk_level = self.request.GET.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        control_type = self.request.GET.get('control_type')
        if control_type:
            queryset = queryset.filter(control_type=control_type)
        key_char = self.request.GET.get('key_char')
        if key_char == '1':
            queryset = queryset.filter(is_key_characteristic=True)
        elif key_char == '0':
            queryset = queryset.filter(is_key_characteristic=False)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'parts', 'add')
        # 传递可用零件列表用于筛选
        context['available_parts'] = Part.objects.all().order_by('part_number')
        return context


class ControlRequirementDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """控制要求详情页面"""
    model = ControlRequirement
    template_name = 'parts/control_requirement_detail.html'
    context_object_name = 'requirement'
    permission_module = 'parts'


class ControlRequirementCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建控制要求"""
    model = ControlRequirement
    template_name = 'parts/control_requirement_form.html'
    fields = ['part', 'requirement_id', 'requirement_name', 'control_type',
              'description', 'nominal_value', 'upper_limit', 'lower_limit', 'unit',
              'risk_level', 'inspection_method', 'inspection_tool', 'is_key_characteristic']
    permission_module = 'parts'

    def get_success_url(self):
        return reverse_lazy('control_requirement_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parts'] = Part.objects.all().order_by('part_number')
        return context

    def form_valid(self, form):
        messages.success(self.request, '控制要求创建成功')
        return super().form_valid(form)


class ControlRequirementUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑控制要求"""
    model = ControlRequirement
    template_name = 'parts/control_requirement_form.html'
    fields = ['requirement_name', 'control_type', 'description',
              'nominal_value', 'upper_limit', 'lower_limit', 'unit',
              'risk_level', 'inspection_method', 'inspection_tool', 'is_key_characteristic']
    permission_module = 'parts'
    
    def get_success_url(self):
        return reverse_lazy('control_requirement_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '控制要求更新成功')
        return super().form_valid(form)


# ==================== 风险点前端页面视图 ====================

class RiskPointListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """风险点列表页面"""
    model = RiskPoint
    template_name = 'parts/risk_point_list.html'
    context_object_name = 'risk_points'
    paginate_by = 20
    permission_module = 'parts'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        part_id = self.request.GET.get('part')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(risk_category=category)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'parts', 'add')
        # 传递可用零件列表用于筛选
        context['available_parts'] = Part.objects.all().order_by('part_number')
        return context


class RiskPointDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """风险点详情页面"""
    model = RiskPoint
    template_name = 'parts/risk_point_detail.html'
    context_object_name = 'risk_point'
    permission_module = 'parts'


class RiskPointCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建风险点"""
    model = RiskPoint
    template_name = 'parts/risk_point_form.html'
    fields = ['part', 'risk_id', 'risk_name', 'description', 'risk_category',
              'severity', 'probability', 'prevention_measures', 'correction_measures']
    permission_module = 'parts'

    def get_success_url(self):
        return reverse_lazy('risk_point_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parts'] = Part.objects.all().order_by('part_number')
        return context

    def form_valid(self, form):
        messages.success(self.request, '风险点创建成功')
        return super().form_valid(form)


class RiskPointUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑风险点"""
    model = RiskPoint
    template_name = 'parts/risk_point_form.html'
    fields = ['risk_name', 'description', 'risk_category',
              'severity', 'probability', 'prevention_measures', 'correction_measures']
    permission_module = 'parts'
    
    def get_success_url(self):
        return reverse_lazy('risk_point_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '风险点更新成功')
        return super().form_valid(form)
