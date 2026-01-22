from open_webui.session.session_service_dict import DictSessionService
from open_webui.session.session_service import SessionService
from open_webui.env import REDIS_URL

__service: SessionService
if REDIS_URL:
    pass
else:
    __service = DictSessionService()

SESSION_SERVICE = __service
