from django.urls import path
from .views import register_user, login_user, generate_invite_code, create_cluster, cluster_status, schedule_deployment

urlpatterns = [
    path('register/', register_user, name='register_user'),  # URL for user registration
    path('login/', login_user, name='login_user'),            # URL for user login
    path('generate_invite_code/', generate_invite_code, name='generate_invite_code'),
    path('create_cluster/', create_cluster, name='create_cluster'),
    path('clusters/<int:cluster_id>/', cluster_status, name='cluster-status'),
    path('schedule-deployment/', schedule_deployment, name='schedule_deployment'),
]
