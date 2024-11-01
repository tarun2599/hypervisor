from django.db import transaction
from .models import Deployment
from django.http import JsonResponse
import json
from .models import Organization, InviteCode, UserProfile, Cluster
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .serializers import RegisterUserSerializer, LoginSerializer, InviteCodeSerializer, ClusterSerializer, ClusterStatusSerializer, DeploymentSerializer
import requests
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework.decorators import authentication_classes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# 1. Authentication Endpoints
@swagger_auto_schema(
    method='post',
    request_body=RegisterUserSerializer,
    responses={
        201: openapi.Response(
            description="User registered successfully",
            examples={
                "application/json": {
                    "username": "user123",
                    "organization": "org_name",
                    "role": "developer",
                    "joined_at": "2024-01-01T00:00:00Z"
                }
            }
        ),
        400: "Invalid data",
        404: "Invite code not found",
        500: "Server error"
    },
    operation_description="Register a new user with organization name or invite code",
    tags=['1. Authentication'],
    operation_id='1_1_register'
)


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
            
            # also create a django user just to authenticate
            django_user = User.objects.create(id=user_profile.id, username=username)

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

# Login User
@swagger_auto_schema(
    method='post',
    request_body=LoginSerializer,
    responses={
        200: openapi.Response(
            description="Login successful",
            examples={
                "application/json": {
                    "refresh": "refresh_token",
                    "access": "access_token",
                    "message": "User logged in successfully."
                }
            }
        ),
        401: "Invalid credentials",
        400: "Invalid data"
    },
    operation_description="Login and get access tokens",
    tags=['1. Authentication'],
    operation_id='1_2_login'
)

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
            django_user = User.objects.get(username=username)
            refresh = RefreshToken.for_user(django_user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'User logged in successfully.'
            })
        else:
            return Response({'error': 'Invalid Credentials'}, status=401)
    return Response(serializer.errors, status=400)

# Generate Invite Code
@swagger_auto_schema(
    method='post',
    responses={
        201: InviteCodeSerializer,
        403: "Permission denied",
        404: "User profile not found",
        400: "Organization ID required"
    },
    operation_description="Generate invite code for organization (Admin only)",
    tags=['2. Organization Management'],
    operation_id='2_1_invite'
)

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


# Create Cluster
@swagger_auto_schema(
    method='post',
    request_body=ClusterSerializer,
    responses={
        201: ClusterSerializer,
        400: "Invalid data",
        404: "User not found"
    },
    operation_description="Create a new cluster",
    tags=['3. Cluster Management'],
    operation_id='3_1_create_cluster'
)

@api_view(['POST'])

def create_cluster(request):
    serializer = ClusterSerializer(data=request.data)

    if serializer.is_valid():
        # Check if the user and organization exist
        user_id = request.user.id
        
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

# Cluster Status
@swagger_auto_schema(
    method='get',
    responses={
        200: ClusterStatusSerializer,
        404: "Cluster not found",
        403: "Permission denied"
    },
    operation_description="Get status of a specific cluster",
    tags=['3. Cluster Management'],
    operation_id='3_2_cluster_status'
)

@api_view(['GET'])

def cluster_status(request, cluster_id):
    try:
        # Retrieve the cluster by ID
        cluster = Cluster.objects.get(id=cluster_id)
        user_id = request.user.id
        # Check if user has access to this cluster
        user_profile = UserProfile.objects.get(id=user_id)
        if cluster.user != user_profile and cluster.user.organization != user_profile.organization:
            return Response({"error": "You don't have permission to view this cluster"}, status=403)
        
        serializer = ClusterStatusSerializer(cluster)  # Remove cluster= from here
        return Response(serializer.data, status=200)  # Use Response instead of JsonResponse
        
    except Cluster.DoesNotExist:
        return Response({"error": "Cluster not found"}, status=404)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# Schedule Deployment
@swagger_auto_schema(
    method='post',
    request_body=DeploymentSerializer,
    responses={
        200: openapi.Response(
            description="Deployment scheduled successfully",
            examples={
                "application/json": {
                    "message": "Deployment queued successfully",
                    "deployment_id": "id",
                    "cluster_id": "cluster_id"
                }
            }
        ),
        400: "Invalid data",
        403: "Permission denied",
        404: "Cluster/Deployment not found"
    },
    operation_description="Schedule a new deployment",
    tags=['4. Deployment Management'],
    operation_id='4_1_deployment'
)

@api_view(['POST'])

def schedule_deployment(request):
    serializer = DeploymentSerializer(data=request.data)

    if serializer.is_valid():
        # Extract user_id and cluster_id from the request data
        user_id = request.user.id
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
            if cluster.user.id != user_id:
                return JsonResponse({
                    "error": "You don't have permission to schedule deployments on this cluster"
                }, status=403)

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
        headers = {
            "Content-Type": "application/json"
        }
        scheduling_server_url = "http://localhost:8000/scheduler/schedule/"
        try:
            response = requests.post(scheduling_server_url, json=scheduling_data, headers=headers)
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



# Stop Deployment
@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response(
            description="Deployment stopped successfully",
            examples={
                "application/json": {
                    "message": "Deployment stopped successfully",
                    "deployment_id": "id"
                }
            }
        ),
        400: "Deployment not in running state",
        403: "Permission denied",
        404: "Deployment not found"
    },
    operation_description="Stop a running deployment",
    tags=['4. Deployment Management'],
    operation_id='4_2_stop_deployment'
)

@api_view(['POST'])

def stop_deployment(request, deployment_id):
    """Stop a deployment and restore cluster resources"""
    try:
        # Get deployment
        deployment = get_object_or_404(Deployment, id=deployment_id)
        
        user_id = request.user.id
        if deployment.cluster.user.id != user_id:
            return JsonResponse({
                "error": "You don't have permission to stop deployments on this cluster"
            }, status=403)
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
            "Content-Type": "application/json"
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

# User Clusters
@swagger_auto_schema(
    method='get',
    responses={
        200: ClusterSerializer(many=True),
        500: "Server error"
    },
    operation_description="Get all clusters belonging to the authenticated user",
    tags=['3. Cluster Management'],
    operation_id='3_3_user_clusters'
)

@api_view(['GET'])

def user_clusters(request):
    """Fetch all clusters belonging to the authenticated user"""
    try:
        user_id = request.user.id
        user = UserProfile.objects.get(id=user_id)
        clusters = Cluster.objects.filter(user=user)
        serializer = ClusterStatusSerializer(clusters, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)




# Organization Clusters
@swagger_auto_schema(
    method='get',
    responses={
        200: ClusterSerializer(many=True),
        400: "User not in organization",
        404: "User profile not found"
    },
    operation_description="Get all clusters in the user's organization",
    tags=['3. Cluster Management'],
    operation_id='3_5__org_clusters'
)

@api_view(['GET'])

def organization_clusters(request):
    """Fetch all clusters in the user's organization"""
    try:
        user_id = request.user.id
        user_profile = UserProfile.objects.get(id=user_id)
        organization = user_profile.organization
        if not organization:
            return Response({"error": "User is not associated with any organization"}, status=400)
            
        # Get all users in the organization
        org_users = UserProfile.objects.filter(organization=organization)
        # Get all clusters belonging to these users
        clusters = Cluster.objects.filter(user__in=org_users)
        
        serializer = ClusterSerializer(clusters, many=True)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# Get Deployment
@swagger_auto_schema(
    method='get',
    responses={
        200: DeploymentSerializer,
        403: "Permission denied",
        404: "Deployment not found"
    },
    operation_description="Get details of a specific deployment",
    tags=['4. Deployment Management'],
    operation_id='4_3_fetch_deployments'
)

@api_view(['GET'])

def get_deployment(request, deployment_id):
    """Fetch a specific deployment by ID"""
    try:
        
        deployment = get_object_or_404(Deployment, id=deployment_id)
        # Check if user has access to this deployment
        user_id = request.user.id
        user_profile = UserProfile.objects.get(id=user_id)
        if deployment.user != user_profile and deployment.cluster.user.organization != user_profile.organization:
            return Response({"error": "You don't have permission to view this deployment"}, status=403)
            
        serializer = DeploymentSerializer(deployment)
        return Response(serializer.data)
    except Deployment.DoesNotExist:
        return Response({"error": "Deployment not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@swagger_auto_schema(
    method='get',
    responses={
        200: DeploymentSerializer(many=True),
        403: "Permission denied",
        404: "Cluster not found"
    },
    operation_description="Get all deployments in a specific cluster",
    tags=['4. Deployment Management'],
    operation_id='4_4_fetch_cluster_deployments'
)

@api_view(['GET'])

def cluster_deployments(request, cluster_id):
    """Fetch all deployments in a specific cluster"""
    try:
        cluster = get_object_or_404(Cluster, id=cluster_id)
        # Check if user has access to this cluster
        user_id = request.user.id
        user_profile = UserProfile.objects.get(id=user_id)
        if cluster.user != user_profile and cluster.user.organization != user_profile.organization:
            return Response({"error": "You don't have permission to view deployments in this cluster"}, status=403)
            
        deployments = Deployment.objects.filter(cluster=cluster)
        serializer = DeploymentSerializer(deployments, many=True)
        return Response(serializer.data)
    except Cluster.DoesNotExist:
        return Response({"error": "Cluster not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)