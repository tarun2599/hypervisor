from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import UserProfile, Organization, Cluster

class UserTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="TestOrg")

    def test_register_user(self):
        url = reverse('register_user')
        data = {"username": "newuser", "password": "newpass", "organization": self.organization.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login_user(self):
        UserProfile.objects.create(username="testuser", password="testpass", organization=self.organization)
        url = reverse('login_user')
        data = {"username": "testuser", "password": "testpass"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class ClusterTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="TestOrg")
        self.user = UserProfile.objects.create(username="testuser", password="testpass", organization=self.organization)

    def test_create_cluster(self):
        url = reverse('create_cluster')
        data = {"name": "NewCluster", "total_cpu": 16, "total_gpu": 2, "total_ram": 32, "user": self.user.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
