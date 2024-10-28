from django.test import TestCase
from .models import UserProfile, Organization, Cluster

class UserProfileTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="TestOrg")
        self.user = UserProfile.objects.create(username="testuser", password="testpass", organization=self.organization)

    def test_user_profile_creation(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.organization.name, "TestOrg")

class ClusterTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="TestOrg")
        self.user = UserProfile.objects.create(username="testuser", password="testpass", organization=self.organization)
        self.cluster = Cluster.objects.create(name="TestCluster", user=self.user, total_cpu=16, total_gpu=2, total_ram=64)

    def test_cluster_creation(self):
        self.assertEqual(self.cluster.name, "TestCluster")
        self.assertEqual(self.cluster.total_cpu, 16)
        self.assertEqual(self.cluster.user.username, "testuser")
