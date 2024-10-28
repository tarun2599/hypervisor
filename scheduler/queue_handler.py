import redis
import json
from datetime import datetime
from api.models import Cluster, Deployment

class RedisQueue:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)

    def get_queue_key(self, cluster_id, priority):
        """Generate queue key for specific cluster and priority"""
        return f'cluster_{cluster_id}_{priority}_queue'

    def enqueue_deployment(self, deployment_data, cluster_id):
        """Add deployment to appropriate cluster's priority queue"""
        priority = deployment_data['priority']
        queue_key = self.get_queue_key(cluster_id, priority)
        self.redis_client.lpush(queue_key, json.dumps(deployment_data))

    def get_next_deployment(self, cluster_id):
        """Get next deployment for specific cluster prioritizing high priority queue"""
        # First try high priority queue for this cluster
        high_queue_key = self.get_queue_key(cluster_id, 'high')
        deployment_data = self.redis_client.rpop(high_queue_key)
        
        if not deployment_data:
            # If no high priority deployments, try low priority
            low_queue_key = self.get_queue_key(cluster_id, 'low')
            deployment_data = self.redis_client.rpop(low_queue_key)
        
        return json.loads(deployment_data) if deployment_data else None

    def get_queue_length(self, cluster_id):
        """Get queue lengths for a specific cluster"""
        high_queue_key = self.get_queue_key(cluster_id, 'high')
        low_queue_key = self.get_queue_key(cluster_id, 'low')
        
        return {
            'high_priority': self.redis_client.llen(high_queue_key),
            'low_priority': self.redis_client.llen(low_queue_key)
        }
