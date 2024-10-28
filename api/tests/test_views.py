from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api.models import UserProfile, Organization, Cluster
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

class UserTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="TestOrg")
        # Create a Django user for authentication
        self.django_user = User.objects.create_user(username="testuser", password="testpass")
        self.token = RefreshToken.for_user(self.django_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')

    def test_register_user(self):
        url = reverse('register_user')
        data = {
            "username": "newuser",
            "password": "newpass",
            "org_name": self.organization.id,
            "role": "developer"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login_user(self):
        # Create user with hashed password
        UserProfile.objects.create(
            username="testuser",
            password=make_password("testpass"),  # Hash the password
            organization=self.organization
        )
        
        url = reverse('login_user')
        data = {"username": "testuser", "password": "testpass"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class ClusterTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="TestOrg")
        # Create Django user and UserProfile
        self.django_user = User.objects.create_user(username="testuser", password="testpass")
        self.user = UserProfile.objects.create(
            username="testuser", 
            password="testpass", 
            organization=self.organization
        )
        # Generate token and set authorization header
        self.token = RefreshToken.for_user(self.django_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')

    def test_create_cluster(self):
        url = reverse('create_cluster')
        data = {
            "name": "NewCluster", 
            "total_cpu": 16, 
            "total_gpu": 2, 
            "total_ram": 32, 
            "user": self.user.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
