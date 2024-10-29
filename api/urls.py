from django.urls import path
from .views import register_user, login_user, generate_invite_code, create_cluster, cluster_status, schedule_deployment, stop_deployment, user_clusters, organization_clusters, get_deployment, cluster_deployments

urlpatterns = [
    path('register/', register_user, name='register_user'),  # URL for user registration
    path('login/', login_user, name='login_user'),            # URL for user login
    path('generate_invite_code/', generate_invite_code, name='generate_invite_code'),
    path('create_cluster/', create_cluster, name='create_cluster'),
    path('clusters/<int:cluster_id>/', cluster_status, name='cluster-status'),
    path('schedule_deployment/', schedule_deployment, name='schedule_deployment'),
    path('deployments/<int:deployment_id>/stop/', stop_deployment, name='stop-deployment'),
    path('user/clusters/', user_clusters, name='user-clusters'),
    path('organization/clusters/', organization_clusters, name='organization-clusters'),
    path('deployments/<int:deployment_id>/', get_deployment, name='get-deployment'),
    path('clusters/<int:cluster_id>/deployments/', cluster_deployments, name='cluster-deployments'),
]
