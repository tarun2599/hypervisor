from django.urls import path
from . import views

urlpatterns = [
    path('schedule/', views.schedule, name='schedule'),
    path('queue-status/<int:cluster_id>/', views.cluster_queue_status, name='cluster-queue-status'),
]
