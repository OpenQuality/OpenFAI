from django.apps import AppConfig


class PartsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parts'
    verbose_name = '零件管理'
    
    # 标记是否需要更新NULL值（在WSGI启动阶段处理）
    _need_null_update = False
    
    def ready(self):
        """应用启动时执行"""
        import os
        if os.environ.get('OPENFAI_ENV') == 'DEV':
            return
        
        # 仅设置标志位，不在 ready() 中访问数据库
        # 数据库操作移到 WSGI 启动阶段执行
        self._need_null_update = True
