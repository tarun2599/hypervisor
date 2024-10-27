from django.shortcuts import render
from django.http import JsonResponse
import json
from .models import Organization, InviteCode, UserProfile
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404


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
                            user=UserProfile.objects.create(username=username, password=make_password(password)),  # Hash the password
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

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict):
                return JsonResponse({'error': 'Invalid data format'}, status=400)

            username = data.get('username')
            password = data.get('password')

            user_profile = UserProfile.objects.filter(username=username).first()
            if user_profile and check_password(password, user_profile.password):  # Check hashed password
                refresh = RefreshToken.for_user(user_profile)  # Generate JWT tokens
                return JsonResponse({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'User logged in successfully.'
                })
            else:
                return JsonResponse({'error': 'Invalid Credentials'}, status=401)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_invite_code(request):
    if request.method == 'POST':
        # The user profile can be accessed directly from the request user
        user_profile = request.user

        # Ensure the user is an admin
        if user_profile.role != 'admin':
            return JsonResponse({'error': 'You do not have permission to generate invite codes.'}, status=403)

        # Extract organization ID from the request body
        org_id = request.data.get('org_id')
        if not org_id:
            return JsonResponse({'error': 'Organization ID is required.'}, status=400)

        # Get the organization
        organization = get_object_or_404(Organization, id=org_id)

        # Create a new invite code
        invite_code = InviteCode.objects.create(organization=organization)

        return JsonResponse({'invite_code': invite_code.code, 'organization': organization.name}, status=201)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
