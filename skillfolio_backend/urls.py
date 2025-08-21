from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from users import views

router = routers.DefaultRouter()
router.register(r'certificates', views.CertificateViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'goals', views.GoalViewSet)



urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include(router.urls)),
]
