from fastapi import APIRouter

from app.api.v1 import formulas, history, mistakes, scan, stats

api_router = APIRouter()

api_router.include_router(scan.router, prefix="/scan", tags=["Scan & Solve"])
api_router.include_router(history.router, prefix="/history", tags=["History"])
api_router.include_router(mistakes.router, prefix="/mistakes", tags=["Mistake Book"])
api_router.include_router(formulas.router, prefix="/formulas", tags=["Formulas"])
api_router.include_router(stats.router, prefix="/stats", tags=["Learning Stats"])
