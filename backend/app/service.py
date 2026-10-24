"""兼容旧版服务导入路径。"""

from .services.eduquery_service import EduQueryService

AskDataService = EduQueryService

__all__ = ["EduQueryService", "AskDataService"]
