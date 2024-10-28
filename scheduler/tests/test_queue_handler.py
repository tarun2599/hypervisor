from django.test import TestCase
from .queue_handler import RedisQueue

class RedisQueueTestCase(TestCase):
    def setUp(self):
        self.queue = RedisQueue()

    def test_enqueue_deployment(self):
        deployment_data = {"deployment_id": 1, "priority": "high", "cluster_id": 1}
        result = self.queue.enqueue_deployment(deployment_data, 1)
        self.assertTrue(result > 0)

    def test_get_next_deployment(self):
        deployment_data = {"deployment_id": 1, "priority": "high", "cluster_id": 1}
        self.queue.enqueue_deployment(deployment_data, 1)
        next_deployment = self.queue.get_next_deployment(1)
        self.assertEqual(next_deployment['deployment_id'], 1)

    def test_get_queue_length(self):
        deployment_data = {"deployment_id": 1, "priority": "high", "cluster_id": 1}
        self.queue.enqueue_deployment(deployment_data, 1)
        queue_lengths = self.queue.get_queue_length(1)
        self.assertEqual(queue_lengths['high_priority'], 1)
