from rest_framework import serializers
from .models import Cluster, Deployment

class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = ['name', 'total_cpu', 'total_gpu', 'total_ram', 'user']

class ClusterStatusSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username')  # Get the username of the creator

    class Meta:
        model = Cluster
        fields = [
            'name',
            'user',
            'created_at',  # Make sure you have a created_at field in your Cluster model
            'total_cpu',
            'total_gpu',
            'total_ram',
            'utilized_cpu',
            'utilized_gpu',
            'utilized_ram'
        ]
        
class DeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deployment
        fields = ['name', 'user', 'cpu_required', 'gpu_required', 'ram_required', 'docker_image', 'priority', 'cluster_id']