import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.core.files.base import ContentFile
from .models import (
    ReportTemplate, InspectionReport,
    MaterialCertification, SpecialProcessRecord, FunctionalTestRecord,
)
from .serializers import (
    ReportTemplateSerializer, InspectionReportSerializer, InspectionReportDetailSerializer,
    MaterialCertificationSerializer, SpecialProcessRecordSerializer, FunctionalTestRecordSerializer,
)
from core.permissions import AutoPermissionMixin, user_has_permission, get_user_permissions


# 常见中文字体路径（按平台），用于将字形嵌入PDF，保证在任何阅读器中都能正确显示中文
_CJK_TTF_CANDIDATES = [
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    '/System/Library/Fonts/STHeiti Light.ttc',
]


def _register_cjk_font():
    """注册中文字体，优先嵌入真实字体文件，找不到时回退到CID字体"""
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    ttf_font_name = 'CJK-TTF'
    if ttf_font_name in pdfmetrics.getRegisteredFontNames():
        return ttf_font_name

    for path in _CJK_TTF_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(ttf_font_name, path, subfontIndex=0))
                return ttf_font_name
            except Exception:
                continue

    cid_font_name = 'STSong-Light'
    if cid_font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(cid_font_name))
    return cid_font_name


def _build_report_pdf(report):
    """使用reportlab生成检验报告PDF，返回文件字节内容"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    font_name = _register_cjk_font()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    title_style = ParagraphStyle('Title', fontName=font_name, fontSize=18, alignment=TA_CENTER, spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', fontName=font_name, fontSize=10, alignment=TA_CENTER,
                                     textColor=colors.grey, spaceAfter=16)
    heading_style = ParagraphStyle('Heading', fontName=font_name, fontSize=12, spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('Body', fontName=font_name, fontSize=9, leading=14)

    elements = [
        Paragraph(report.title or report.report_number, title_style),
        Paragraph(f"{report.report_number}　|　AS9102 首件检验报告", subtitle_style),
    ]

    elements.append(Paragraph('Form 1 - 零件号责任', heading_style))
    info_rows = [
        ['零件编号', report.plan.part.part_number, '零件名称', report.plan.part.part_name],
        ['零件版次', report.plan.part.revision or '-', '客户/供方', report.plan.part.customer or '-'],
        ['检验计划', report.plan.plan_name, '测量批次', report.batch.batch_number],
        ['检验标准', report.plan.get_standard_display(), '总体结论',
         {'PASS': '合格', 'FAIL': '不合格'}.get(report.conclusion, '-')],
    ]
    info_table = Table(info_rows, colWidths=[28 * mm, 60 * mm, 28 * mm, 60 * mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f2f5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f2f5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d9d9d9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)

    # Form 2 - 产品责任：原材料证书 / 特殊工艺 / 功能测试（无记录时不占用篇幅）
    materials = list(report.material_certifications.all())
    processes = list(report.special_processes.all())
    tests = list(report.functional_tests.all())
    if materials or processes or tests:
        elements.append(Paragraph('Form 2 - 产品责任', heading_style))

        def _compliance_table(rows, col_widths):
            t = Table(rows, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#52606d')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d9d9d9')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            return t

        if materials:
            elements.append(Paragraph('原材料证书', body_style))
            rows = [['材料规范', '证书编号', '供应商', '批次', '符合性']]
            for m in materials:
                rows.append([m.material_spec, m.cert_number or '-', m.supplier or '-',
                             m.batch_number or '-', '符合' if m.compliant else '不符合'])
            elements.append(_compliance_table(rows, [40 * mm, 30 * mm, 35 * mm, 25 * mm, 26 * mm]))
            elements.append(Spacer(1, 3 * mm))

        if processes:
            elements.append(Paragraph('特殊工艺记录', body_style))
            rows = [['工艺类型', '规范编号', '承做单位', '合格证号', '符合性']]
            for proc in processes:
                rows.append([proc.get_process_type_display(), proc.spec_number or '-',
                             proc.processor or '-', proc.cert_number or '-',
                             '符合' if proc.compliant else '不符合'])
            elements.append(_compliance_table(rows, [30 * mm, 30 * mm, 40 * mm, 30 * mm, 26 * mm]))
            elements.append(Spacer(1, 3 * mm))

        if tests:
            elements.append(Paragraph('功能测试记录', body_style))
            rows = [['测试项目', '依据规范', '结果摘要', '符合性']]
            for t_rec in tests:
                rows.append([t_rec.test_name, t_rec.spec_reference or '-',
                             (t_rec.result_summary or '-')[:40],
                             '符合' if t_rec.compliant else '不符合'])
            elements.append(_compliance_table(rows, [35 * mm, 35 * mm, 60 * mm, 26 * mm]))

    elements.append(Paragraph('Form 3 - 特性责任（尺寸实测结果）', heading_style))

    accountability = report.plan.characteristic_accountability
    if accountability:
        coverage_text = (
            f"特性完整性核对：图纸解析出 {accountability['total_dimensions']} 个尺寸，"
            f"本计划已建立 {accountability['covered_characteristics']} 个检验特性"
            f"（覆盖率 {accountability['coverage_pct']}%）。"
            + ('' if accountability['is_complete'] else '【未达到100%特性责任覆盖】')
        )
        elements.append(Paragraph(coverage_text, body_style))
        elements.append(Spacer(1, 2 * mm))

    stat_header = ['特性编号', '特性名称', '均值', '标准差', 'Cp', 'Cpk', '判定']
    stat_rows = [stat_header]
    for stat in report.batch.statistics.all():
        cpk_display = f"{stat.cpk:.2f}" if stat.cpk is not None else '-'
        cp_display = f"{stat.cp:.2f}" if stat.cp is not None else '-'
        if stat.cpk is None:
            verdict = '无法计算'
        elif stat.cpk >= 1.0:
            verdict = '合格'
        else:
            verdict = '不合格'
        stat_rows.append([
            stat.characteristic.char_number,
            stat.characteristic.char_name,
            f"{stat.mean:.4f}",
            f"{stat.std_dev:.6f}",
            cp_display,
            cpk_display,
            verdict,
        ])
    stat_table = Table(stat_rows, colWidths=[22 * mm, 38 * mm, 24 * mm, 24 * mm, 18 * mm, 18 * mm, 20 * mm])
    stat_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f54eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d9d9d9')),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
    ]))
    elements.append(stat_table)

    elements.append(Paragraph('报告摘要', heading_style))
    for line in (report.summary or '').split('\n'):
        elements.append(Paragraph(line if line.strip() else '&nbsp;', body_style))

    elements.append(Spacer(1, 12 * mm))
    footer_rows = [['生成人', report.generated_by.username if report.generated_by else '-',
                     '生成时间', report.generated_at.strftime('%Y-%m-%d %H:%M') if report.generated_at else '-']]
    footer_table = Table(footer_rows, colWidths=[28 * mm, 60 * mm, 28 * mm, 60 * mm])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d9d9d9')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f2f5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f2f5')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(footer_table)

    doc.build(elements)
    return buffer.getvalue()


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """报告模板API视图集"""
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    filterset_fields = ['standard', 'is_active']


class InspectionReportViewSet(viewsets.ModelViewSet):
    """检验报告API视图集"""
    queryset = InspectionReport.objects.all()
    serializer_class = InspectionReportSerializer
    filterset_fields = ['plan', 'batch', 'status']
    search_fields = ['report_number', 'title']
    ordering_fields = ['created_at', 'generated_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InspectionReportDetailSerializer
        return InspectionReportSerializer


class MaterialCertificationViewSet(viewsets.ModelViewSet):
    """Form2-原材料证书API视图集"""
    queryset = MaterialCertification.objects.all()
    serializer_class = MaterialCertificationSerializer
    filterset_fields = ['report', 'compliant']
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class SpecialProcessRecordViewSet(viewsets.ModelViewSet):
    """Form2-特殊工艺记录API视图集"""
    queryset = SpecialProcessRecord.objects.all()
    serializer_class = SpecialProcessRecordSerializer
    filterset_fields = ['report', 'process_type', 'compliant']
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class FunctionalTestRecordViewSet(viewsets.ModelViewSet):
    """Form2-功能测试记录API视图集"""
    queryset = FunctionalTestRecord.objects.all()
    serializer_class = FunctionalTestRecordSerializer
    filterset_fields = ['report', 'compliant']
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """生成报告"""
        report = self.get_object()
        
        if report.status not in ['DRAFT', 'GENERATING']:
            return Response(
                {'error': '报告状态不允许生成'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = 'GENERATING'
        report.save()
        
        # 模拟报告生成（实际应调用PDF生成库）
        # 这里生成简单的文本报告
        batch = report.batch
        stats = batch.statistics.all()
        
        summary_lines = [
            f"FAI报告 - {report.report_number}",
            f"零件编号: {report.plan.part.part_number}",
            f"零件名称: {report.plan.part.part_name}",
            f"检验计划: {report.plan.plan_name}",
            f"测量批次: {batch.batch_number}",
            f"\n测量统计:",
            f"总测量数: {batch.total_measurements}",
            f"通过数: {batch.pass_count}",
            f"失败数: {batch.fail_count}",
            f"\n过程能力分析:",
        ]
        
        for stat in stats:
            summary_lines.append(
                f"{stat.characteristic.char_number}: Cpk={stat.cpk} ({stat.process_capability})"
            )
        
        # 判断结论
        all_pass = batch.fail_count == 0
        cpk_acceptable = all(s.cpk and s.cpk >= 1.0 for s in stats if s.cpk)
        
        if all_pass and cpk_acceptable:
            summary_lines.append("\n结论: 合格")
            report.conclusion = 'PASS'
        else:
            summary_lines.append("\n结论: 不合格")
            report.conclusion = 'FAIL'
        
        report.summary = '\n'.join(summary_lines)
        report.status = 'COMPLETED'
        report.generated_at = timezone.now()
        report.generated_by = request.user
        report.save()
        
        return Response({
            'status': 'success',
            'message': '报告生成完成',
            'conclusion': report.conclusion
        })
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """发布报告"""
        report = self.get_object()
        
        if report.status != 'COMPLETED':
            return Response(
                {'error': '只有已完成的报告可以发布'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = 'PUBLISHED'
        report.published_at = timezone.now()
        report.published_by = request.user
        report.save()
        
        return Response({
            'status': 'success',
            'message': '报告已发布'
        })
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """下载报告"""
        report = self.get_object()
        
        if report.status not in ['COMPLETED', 'PUBLISHED']:
            return Response(
                {'error': '报告尚未生成'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 返回文本报告（实际应返回PDF）
        response = HttpResponse(report.summary, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{report.report_number}.txt"'
        return response


# 前端视图
class ReportListView(AutoPermissionMixin, LoginRequiredMixin, ListView):
    """报告列表页面"""
    model = InspectionReport
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    permission_module = 'reports'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_add'] = user_has_permission(self.request.user, 'reports', 'add')
        context['can_change'] = user_has_permission(self.request.user, 'reports', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'reports', 'delete')
        return context


class ReportDetailView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """报告详情页面"""
    model = InspectionReport
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'
    permission_module = 'reports'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_permissions'] = get_user_permissions(self.request.user)
        context['can_change'] = user_has_permission(self.request.user, 'reports', 'change')
        context['can_delete'] = user_has_permission(self.request.user, 'reports', 'delete')
        return context


class ReportCreateView(AutoPermissionMixin, LoginRequiredMixin, CreateView):
    """创建检验报告"""
    model = InspectionReport
    template_name = 'reports/report_form.html'
    fields = ['title', 'plan', 'batch', 'template']
    success_url = reverse_lazy('report_list')
    permission_module = 'reports'
    
    def get_initial(self):
        initial = super().get_initial()
        # 支持从URL参数预选零件
        part_id = self.request.GET.get('part')
        if part_id:
            try:
                from parts.models import Part
                part = Part.objects.get(pk=part_id)
                initial['title'] = f'{part.part_number} 首件检验报告'
            except Part.DoesNotExist:
                pass
        return initial
    
    def form_valid(self, form):
        # 自动生成报告编号
        import datetime
        today = datetime.date.today()
        count = InspectionReport.objects.filter(
            created_at__year=today.year,
            created_at__month=today.month,
            created_at__day=today.day
        ).count() + 1
        form.instance.report_number = f"FAI-RPT-{today.strftime('%Y%m%d')}-{count:04d}"
        
        messages.success(self.request, '检验报告创建成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from inspections.models import InspectionPlan
        from measurements.models import MeasurementBatch
        from parts.models import Part
        
        # 获取所有激活的零件
        context['parts'] = Part.objects.filter(status='ACTIVE').order_by('part_number')
        
        # 支持按零件筛选检验计划
        part_id = self.request.GET.get('part')
        if part_id:
            plans = InspectionPlan.objects.filter(part_id=part_id)
            # 只显示该零件相关的已完成测量批次
            batches = MeasurementBatch.objects.filter(plan__in=plans, status='COMPLETED')
        else:
            plans = InspectionPlan.objects.filter(status='ACTIVE').select_related('part')
            batches = MeasurementBatch.objects.filter(status='COMPLETED').select_related('plan', 'plan__part')
        
        context['plans'] = plans
        context['batches'] = batches
        context['templates'] = ReportTemplate.objects.filter(is_active=True)
        return context


class ReportUpdateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """编辑检验报告"""
    model = InspectionReport
    template_name = 'reports/report_form.html'
    fields = ['title', 'template', 'status']
    permission_module = 'reports'
    
    def get_success_url(self):
        return reverse_lazy('report_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '检验报告更新成功')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context


class ReportDeleteView(AutoPermissionMixin, LoginRequiredMixin, DeleteView):
    """删除检验报告"""
    model = InspectionReport
    success_url = reverse_lazy('report_list')
    permission_module = 'reports'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '检验报告删除成功')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class ReportGenerateView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """生成报告"""
    model = InspectionReport
    http_method_names = ['post']
    permission_module = 'reports'
    
    def post(self, request, *args, **kwargs):
        report = self.get_object()
        
        if report.status not in ['DRAFT', 'GENERATING']:
            messages.error(request, '报告状态不允许生成')
            return redirect('report_detail', pk=report.pk)
        
        report.status = 'GENERATING'
        report.save()
        
        # 获取测量数据和统计信息
        batch = report.batch
        stats = batch.statistics.all()
        
        # 生成报告摘要
        # 获取标准信息
        standard_display = report.template.get_standard_display() if report.template else report.plan.get_standard_display()
        
        summary_lines = [
            f"FAI报告 - {report.report_number}",
            f"=" * 50,
            f"",
            f"零件编号: {report.plan.part.part_number}",
            f"零件名称: {report.plan.part.part_name}",
            f"检验计划: {report.plan.plan_name}",
            f"测量批次: {batch.batch_number}",
            f"检验标准: {standard_display}",
            f"",
            f"测量统计:",
            f"-" * 50,
        ]
        
        pass_count = 0
        fail_count = 0
        
        for stat in stats:
            status_text = "合格" if stat.cpk and stat.cpk >= 1.0 else "不合格"
            if stat.cpk and stat.cpk >= 1.0:
                pass_count += 1
            else:
                fail_count += 1
            summary_lines.append(
                f"  {stat.characteristic.char_number}: {stat.characteristic.char_name}"
            )
            cpk_display = f"{stat.cpk:.2f}" if stat.cpk else '-'
            summary_lines.append(
                f"    均值: {stat.mean:.4f}, 标准差: {stat.std_dev:.6f}, Cpk: {cpk_display} [{status_text}]"
            )
        
        summary_lines.extend([
            f"",
            f"统计汇总:",
            f"  总测量项: {pass_count + fail_count}",
            f"  合格项: {pass_count}",
            f"  不合格项: {fail_count}",
            f"",
        ])
        
        # 判断结论
        if fail_count == 0:
            summary_lines.append("结论: 合格")
            report.conclusion = 'PASS'
        else:
            summary_lines.append("结论: 不合格")
            report.conclusion = 'FAIL'
        
        report.summary = '\n'.join(summary_lines)
        report.status = 'COMPLETED'
        report.generated_at = timezone.now()
        report.generated_by = request.user
        report.save()

        try:
            pdf_bytes = _build_report_pdf(report)
            report.pdf_file.save(f'{report.report_number}.pdf', ContentFile(pdf_bytes), save=True)
        except Exception:
            pass

        messages.success(request, '报告生成完成')
        return redirect('report_detail', pk=report.pk)


class ReportDownloadView(AutoPermissionMixin, LoginRequiredMixin, DetailView):
    """下载报告"""
    model = InspectionReport
    permission_module = 'reports'
    
    def get(self, request, *args, **kwargs):
        report = self.get_object()
        
        if report.status not in ['COMPLETED', 'PUBLISHED']:
            messages.error(request, '报告尚未生成')
            return redirect('report_detail', pk=report.pk)

        if report.pdf_file:
            response = HttpResponse(report.pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report.report_number}.pdf"'
            return response

        # 兼容旧数据：尚未生成PDF文件时回退为文本报告
        response = HttpResponse(report.summary, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{report.report_number}.txt"'
        return response


class ReportPublishView(AutoPermissionMixin, LoginRequiredMixin, UpdateView):
    """发布报告"""
    model = InspectionReport
    http_method_names = ['post']
    permission_module = 'reports'
    
    def post(self, request, *args, **kwargs):
        report = self.get_object()
        
        if report.status != 'COMPLETED':
            messages.error(request, '只有已完成的报告可以发布')
            return redirect('report_detail', pk=report.pk)
        
        report.status = 'PUBLISHED'
        report.published_at = timezone.now()
        report.published_by = request.user
        report.save()
        
        messages.success(request, '报告已发布')
        return redirect('report_detail', pk=report.pk)
