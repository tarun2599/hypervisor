from api.models import Cluster, Deployment
from .queue_handler import RedisQueue
from django.db import transaction

class DeploymentScheduler:
    def __init__(self):
        self.queue = RedisQueue()

    def can_deploy(self, cluster, deployment):
        """Check if deployment can fit in cluster"""
        return (
            cluster.total_cpu - cluster.utilized_cpu >= deployment.cpu_required and
            cluster.total_gpu - cluster.utilized_gpu >= deployment.gpu_required and
            cluster.total_ram - cluster.utilized_ram >= deployment.ram_required
        )

    def process_cluster_queue(self, cluster_id):
        """Process deployments for a specific cluster - only process low priority when high is empty"""
        def process_priority_queue(priority):
            queue_key = self.queue.get_queue_key(cluster_id, priority)
            deployment_data = self.queue.get_next_deployment(cluster_id)
            
            if deployment_data:
                try:
                    cluster = Cluster.objects.get(id=cluster_id)
                    deployment = Deployment.objects.get(id=deployment_data['deployment_id'])
                    
                    if self.can_deploy(cluster, deployment):
                        # Update deployment status and cluster resources
                        deployment.status = 'running'
                        deployment.save()
                        
                        cluster.utilized_cpu += deployment.cpu_required
                        cluster.utilized_gpu += deployment.gpu_required
                        cluster.utilized_ram += deployment.ram_required
                        cluster.save()
                        
                except (Cluster.DoesNotExist, Deployment.DoesNotExist):
                    pass

        # First check if high priority queue has any deployments
        high_queue_key = self.queue.get_queue_key(cluster_id, 'high')
        high_queue_length = self.redis_client.llen(high_queue_key)

        # Process high priority queue
        process_priority_queue('high')

        # Only process low priority if high priority queue is empty
        if high_queue_length == 0:
            process_priority_queue('low')
