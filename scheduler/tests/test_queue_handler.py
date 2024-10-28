from django.test import TestCase
from scheduler.queue_handler import RedisQueue
import redis

class RedisQueueTestCase(TestCase):
    def setUp(self):
        self.queue = RedisQueue()
        # Clear the test queues before each test
        self.clean_test_queues()

    def tearDown(self):
        # Clean up after each test
        self.clean_test_queues()

    def clean_test_queues(self):
        # Clean both high and low priority queues for the test cluster
        test_cluster_id = 1
        high_queue_key = self.queue.get_queue_key(test_cluster_id, 'high')
        low_queue_key = self.queue.get_queue_key(test_cluster_id, 'low')
        self.queue.redis_client.delete(high_queue_key)
        self.queue.redis_client.delete(low_queue_key)

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
        # Ensure queue is empty at start
        queue_lengths = self.queue.get_queue_length(1)
        self.assertEqual(queue_lengths['high_priority'], 0)

        # Add one deployment
        deployment_data = {"deployment_id": 1, "priority": "high", "cluster_id": 1}
        self.queue.enqueue_deployment(deployment_data, 1)
        
        # Check length is now 1
        queue_lengths = self.queue.get_queue_length(1)
        self.assertEqual(queue_lengths['high_priority'], 1)
