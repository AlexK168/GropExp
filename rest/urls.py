import djoser
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest.views import *

router = DefaultRouter()
router.register(r'parties', PartyViewSet)
# router.register(r'account', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken'))
]
