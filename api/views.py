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

@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        try:
            # Load JSON data from request body
            data = json.loads(request.body)

            # Ensure data is a dictionary
            if not isinstance(data, dict):
                return JsonResponse({'error': 'Invalid data format'}, status=400)

            # Extract parameters from the data
            username = data.get('username')
            password = data.get('password')
            invite_code = data.get('invite_code')
            org_name = data.get('org_name') 

            # Check if the username already exists
            if UserProfile.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)

            # Check if invite code is provided
            if invite_code:
                try:
                    invite = InviteCode.objects.get(code=invite_code)
                    if invite.is_valid():
                        organization = invite.organization

                        # Create user with developer/viewer role based on invite code
                        role = 'developer' if invite.organization else 'viewer'
                        user_profile = UserProfile.objects.create(
                            username=username, 
                            password=make_password(password),  # Hash the password
                            organization=organization,
                            role=role
                        )
                        return JsonResponse({'message': 'User registered successfully with invite code'}, status=201)
                    else:
                        return JsonResponse({'error': 'Invite code has expired'}, status=400)
                except InviteCode.DoesNotExist:
                    return JsonResponse({'error': 'Invalid invite code'}, status=400)

            # If no invite code, create new organization
            elif org_name:
                organization = Organization.objects.create(name=org_name)
                user_profile = UserProfile.objects.create(
                    username=username,
                    password=make_password(password),  # Hash the password
                    organization=organization,
                    role='admin'  # Admin role for the user
                )
                return JsonResponse({'message': 'User registered successfully as admin of new organization'}, status=201)

            return JsonResponse({'error': 'No valid input provided'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=400)

        user_profile = UserProfile.objects.filter(username=username).first()
        if user_profile and check_password(password, user_profile.password):
            # Create a Django User instance for JWT
            django_user = User.objects.get_or_create(username=username)[0]
            refresh = RefreshToken.for_user(django_user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'User logged in successfully.'
            })
        else:
            return Response({'error': 'Invalid Credentials'}, status=401)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_invite_code(request):
    try:
        # Get UserProfile from Django User
        user_profile = UserProfile.objects.get(username=request.user)

        # Ensure the user is an admin
        if user_profile.role != 'admin':
            return Response({'error': 'You do not have permission to generate invite codes.'}, status=403)

        # Extract organization ID from the request data
        org_id = user_profile.organization.id
        if not org_id:
            return Response({'error': 'Organization ID is required.'}, status=400)

        # Get the organization
        organization = get_object_or_404(Organization, id=org_id)

        # Create a new invite code
        invite_code = InviteCode.objects.create(organization=organization)

        return Response({
            'invite_code': invite_code.code, 
            'organization': organization.name
        }, status=201) 
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
        cluster_id = request.data.get('cluster_id')

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
        deployment = serializer.save(user=user)
        
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
            "cluster_id": cluster_id
        }

        # Send data to the scheduling server
        scheduling_server_url = "http://localhost:8000/scheduler/schedule"
        try:
            response = requests.post(scheduling_server_url, json=scheduling_data)
            if response.status_code == 200:
                return JsonResponse({
                    "message": "Deployment scheduled successfully",
                    "deployment_id": deployment.id,
                    "cluster_id": cluster_id
                }, status=status.HTTP_201_CREATED)
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
        with transaction.atomic():
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
            deployment.cluster = None  # Remove cluster association
            deployment.save()

            # Process queue for this cluster since resources were freed
            scheduling_server_url = "http://localhost:8000/scheduler/schedule"
            requests.post(scheduling_server_url, json={"cluster_id": cluster_id})

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

