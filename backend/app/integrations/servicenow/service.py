from app.core.config import get_settings
from app.integrations.servicenow.adapter import MockServiceNowAdapter, RealServiceNowAdapter

def get_adapter():
    settings=get_settings()
    if settings.servicenow_mode.lower()=="real":
        return RealServiceNowAdapter(settings.servicenow_instance_url,settings.servicenow_username,settings.servicenow_password)
    return MockServiceNowAdapter()
