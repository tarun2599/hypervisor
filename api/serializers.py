from rest_framework import serializers
from .models import Cluster, Deployment, UserProfile, InviteCode, Organization

class RegisterUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True)
    org_name = serializers.CharField(max_length=255, required=False)
    invite_code = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        if not data.get('org_name') and not data.get('invite_code'):
            raise serializers.ValidationError("Either 'org_name' or 'invite_code' must be provided.")
        return data

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True)

class InviteCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InviteCode
        fields = ['code', 'organization', 'created_at', 'expires_at', 'is_active']



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
        fields = ['name', 'user', 'cpu_required', 'gpu_required', 'ram_required', 'docker_image', 'priority', 'cluster']
