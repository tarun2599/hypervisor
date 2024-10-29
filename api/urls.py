from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .views import register_user, login_user, generate_invite_code, create_cluster, cluster_status, schedule_deployment, stop_deployment, user_clusters, organization_clusters, get_deployment, cluster_deployments

# Create Info object with tags
info = openapi.Info(
    title="MLOps Platform API",
    default_version='v1',
    description="""
MLOps Platform API documentation.

The API is organized into the following sections:
1. Authentication - User registration and login
2. Organization Management - Invite code generation
3. Cluster Management - Create and manage clusters
4. Deployment Management - Schedule and manage deployments
    """,
    terms_of_service="https://www.google.com/policies/terms/",
    contact=openapi.Contact(email="contact@mlopsplatform.local"),
    license=openapi.License(name="BSD License"),
)

schema_view = get_schema_view(
    info=info,
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        path('api/', include('api.urls')),  # Only include API urls, not scheduler
    ],
)

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

