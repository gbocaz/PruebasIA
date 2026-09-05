from fastapi import APIRouter

from app.api.agent_protocol import router as agent_protocol_router
from app.api.agent_deployment import bootstrap_router, router as agent_deployment_router
from app.api.agents_admin import router as agents_admin_router
from app.api.alerts import router as alerts_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.collector_protocol import router as collector_protocol_router
from app.api.dashboard import router as dashboard_router
from app.api.devices import router as devices_router
from app.api.groups import router as groups_router
from app.api.installations import router as installations_router
from app.api.network import router as network_router
from app.api.packages import router as packages_router
from app.api.reports import router as reports_router
from app.api.search import router as search_router
from app.api.software import router as software_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(devices_router)
api_router.include_router(groups_router)
api_router.include_router(software_router)
api_router.include_router(packages_router)
api_router.include_router(installations_router)
api_router.include_router(network_router)
api_router.include_router(alerts_router)
api_router.include_router(audit_router)
api_router.include_router(dashboard_router)
api_router.include_router(search_router)
api_router.include_router(agents_admin_router)
api_router.include_router(reports_router)
api_router.include_router(agent_protocol_router)
api_router.include_router(agent_deployment_router)
api_router.include_router(bootstrap_router)
api_router.include_router(collector_protocol_router)
