import djoser
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest.views import *
from djoser import views

router = DefaultRouter(trailing_slash=False)

router.register(r'parties', PartyViewSet)
router.register(r'billings', BillingViewSet)
router.register(r'contributions', ContributionViewSet, 'Contribution')
router.register(r'users', views.UserViewSet, 'User')
router.register(r'choices', ChoiceViewSet, 'Choice')

urlpatterns = [
    path('users_all', users),
    path('', include(router.urls)),
    path('login', views.TokenCreateView.as_view()),
    path('logout', views.TokenDestroyView.as_view()),
    path('users/me/friends', friends),
]
