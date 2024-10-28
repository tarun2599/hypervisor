from django.db import transaction
from .models import Deployment
from django.http import JsonResponse
import json
from .models import Organization, InviteCode, UserProfile, Cluster
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .serializers import ClusterSerializer, ClusterStatusSerializer, DeploymentSerializer
import requests
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User


from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .models import UserProfile, Organization, InviteCode
from .serializers import RegisterUserSerializer, LoginSerializer, InviteCodeSerializer
from rest_framework.decorators import authentication_classes


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # No authentication required
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterUserSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        org_name = serializer.validated_data.get('org_name')
        invite_code = serializer.validated_data.get('invite_code')

        try:
            # Handle organization creation or retrieval
            if org_name:
                organization = Organization.objects.create(name=org_name)
            else:
                # Validate invite code
                invite = InviteCode.objects.get(code=invite_code, is_active=True)
                if not invite.is_valid():
                    return JsonResponse({'error': 'Invite code is invalid or expired.'}, status=400)
                organization = invite.organization

            # Save user with hashed password
            user_profile = UserProfile.objects.create(
                username=username,
                password=make_password(password),
                organization=organization
            )

            # If using invite code, deactivate it
            if invite_code:
                invite.is_active = False
                invite.save()
            
            response_data = {
                'username': user_profile.username,
                'organization': user_profile.organization.name if user_profile.organization else None,
                'role': user_profile.role,
                'joined_at': user_profile.joined_at
            }
            
            return JsonResponse(response_data , status=201)
        except InviteCode.DoesNotExist:
            return JsonResponse({'error': 'Invite code not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@authentication_classes([])  # No authentication required
@permission_classes([AllowAny])
def login_user(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user_profile = UserProfile.objects.filter(username=username).first()
        if user_profile and check_password(password, user_profile.password):
            django_user = User.objects.get_or_create(username=username)[0]
            refresh = RefreshToken.for_user(django_user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'User logged in successfully.'
            })
        else:
            return Response({'error': 'Invalid Credentials'}, status=401)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
def generate_invite_code(request):
    try:
        user_profile = UserProfile.objects.get(username=request.user)

        if user_profile.role != 'admin':
            return Response({'error': 'You do not have permission to generate invite codes.'}, status=403)

        org_id = user_profile.organization.id
        if not org_id:
            return Response({'error': 'Organization ID is required.'}, status=400)

        organization = get_object_or_404(Organization, id=org_id)
        invite_code = InviteCode.objects.create(organization=organization)

        serializer = InviteCodeSerializer(invite_code)
        return Response(serializer.data, status=201)
    except UserProfile.DoesNotExist:
        return Response({'error': 'User profile not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def create_cluster(request):
    serializer = ClusterSerializer(data=request.data)

    if serializer.is_valid():
        # Check if the user and organization exist
        user_id = request.data.get('user')
        
        try:
            user = UserProfile.objects.get(id=user_id)
            
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)

        # Set the organization and user fields
        cluster = serializer.save(user=user)
        return JsonResponse(ClusterSerializer(cluster).data, status=201)

    return JsonResponse(serializer.errors, status=400)

@api_view(['GET'])
def cluster_status(request, cluster_id):
    try:
        # Retrieve the cluster by ID
        cluster = Cluster.objects.get(id=cluster_id)
        serializer = ClusterStatusSerializer(cluster)
        return JsonResponse(serializer.data, status=200)
    except Cluster.DoesNotExist:
        return JsonResponse({"error": "Cluster not found"}, status=404)

@api_view(['POST'])
def schedule_deployment(request):
    serializer = DeploymentSerializer(data=request.data)

    if serializer.is_valid():
        # Extract user_id and cluster_id from the request data
        user_id = request.data.get('user')
        cluster_id = request.data.get('cluster')
        cpu_required = request.data.get('cpu_required')
        gpu_required = request.data.get('gpu_required')
        ram_required = request.data.get('ram_required')

        if not cluster_id:
            return JsonResponse({"error": "cluster_id is required"}, status=400)

        # Check if the user and cluster exist
        try:
            user = UserProfile.objects.get(id=user_id)
            cluster = Cluster.objects.get(id=cluster_id)
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        except Cluster.DoesNotExist:
            return JsonResponse({"error": "Cluster not found"}, status=404)

        # Save the deployment to the database
        
        cluster = Cluster.objects.get(id=cluster_id)
        
        if(cluster.total_cpu < cpu_required or cluster.total_gpu < gpu_required or cluster.total_ram < ram_required):
            return JsonResponse({"error": "cannot make this deployment on given cluster. deployment requiements exceeds cluster specifications"}, status=404)
        
        deployment = serializer.save(user=user, cluster=cluster)
        
        # Prepare data to send to the scheduling server
        scheduling_data = {
            "user_id": user_id,
            "cpu": deployment.cpu_required,
            "gpu": deployment.gpu_required,
            "ram": deployment.ram_required,
            "service_name": request.data.get('service_name'),
            "docker_image": deployment.docker_image,
            "priority": deployment.priority,
            "deployment_id": deployment.id,
            "cluster_id": cluster_id,
            "is_scheduled": True
        }

        # Send data to the scheduling server
        scheduling_server_url = "http://localhost:8000/scheduler/schedule/"
        try:
            response = requests.post(scheduling_server_url, json=scheduling_data, headers=request.headers)
            if response.status_code == 200:
                return JsonResponse({
                    "message": "Deployment scheduled successfully",
                    "deployment_id": deployment.id,
                    "cluster_id": cluster_id
                }, status=201)
            else:
                return JsonResponse({"error": "Failed to communicate with scheduling server"}, status=502)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(serializer.errors, status=400)



@api_view(['POST'])
def stop_deployment(request, deployment_id):
    """Stop a deployment and restore cluster resources"""
    try:
        # Get deployment
        deployment = get_object_or_404(Deployment, id=deployment_id)
        
        # Check if deployment is actually running
        if deployment.status != 'running':
            return JsonResponse({
                "error": "Deployment is not running"
            }, status=400)

        # Get associated cluster
        cluster = deployment.cluster
        if not cluster:
            return JsonResponse({
                "error": "Deployment is not associated with any cluster"
            }, status=400)

        cluster_id = cluster.id  # Store cluster_id before nullifying the relationship

        # Use transaction to ensure atomicity
        # with transaction.atomic():
            # Restore cluster resources
        cluster.utilized_cpu -= deployment.cpu_required
        cluster.utilized_gpu -= deployment.gpu_required
        cluster.utilized_ram -= deployment.ram_required
        
        # Ensure we don't go below 0 for any resource
        cluster.utilized_cpu = max(0, cluster.utilized_cpu)
        cluster.utilized_gpu = max(0, cluster.utilized_gpu)
        cluster.utilized_ram = max(0, cluster.utilized_ram)
        
        cluster.save()

        # Update deployment status
        deployment.status = 'stopped'
        deployment.save()
        headers = {
            "Content-Type": "application/json",
            "Authorization": request.headers.get("Authorization")
        }
        # Process queue for this cluster since resources were freed
        scheduling_server_url = "http://localhost:8000/scheduler/schedule/"
        requests.post(scheduling_server_url, json={"cluster_id": cluster_id, "is_scheduled": False}, headers=headers)

        return JsonResponse({
            "message": "Deployment stopped successfully",
            "deployment_id": deployment_id,
            "cluster_status": {
                "name": cluster.name,
                "utilized_cpu": cluster.utilized_cpu,
                "utilized_gpu": cluster.utilized_gpu,
                "utilized_ram": cluster.utilized_ram
            }
        }, status=200)

    except Deployment.DoesNotExist:
        return JsonResponse({
            "error": "Deployment not found"
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)

