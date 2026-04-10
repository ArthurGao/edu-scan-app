from fastapi import APIRouter

from app.api.v1 import admin, auth, exam_sessions, exams, formulas, history, mistakes, practice, question_gen, scan, stats, subscription, webhooks

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(scan.router, prefix="/scan", tags=["Scan & Solve"])
api_router.include_router(history.router, prefix="/history", tags=["History"])
api_router.include_router(mistakes.router, prefix="/mistakes", tags=["Mistake Book"])
api_router.include_router(formulas.router, prefix="/formulas", tags=["Formulas"])
api_router.include_router(stats.router, prefix="/stats", tags=["Learning Stats"])
api_router.include_router(exams.router, prefix="/exams", tags=["Exam Papers"])
api_router.include_router(question_gen.router, prefix="/question-gen", tags=["Question Generation"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["Subscription"])
api_router.include_router(exam_sessions.router, prefix="/sessions", tags=["Exam Practice"])
api_router.include_router(practice.router, prefix="/practice", tags=["Practice Generation"])
