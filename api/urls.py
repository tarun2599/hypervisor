from django.urls import path
from .views import register_user, login_user, generate_invite_code

urlpatterns = [
    path('register/', register_user, name='register_user'),  # URL for user registration
    path('login/', login_user, name='login_user'),            # URL for user login
    path('generate_invite_code/', generate_invite_code, name='generate_invite_code')
]
