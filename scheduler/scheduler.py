from api.models import Cluster, Deployment
from .queue_handler import queue_instance
from django.db import transaction
import json

class DeploymentScheduler:
    def __init__(self):
        self.queue = queue_instance

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
            """Process all deployments in a specific priority queue"""
            processed_deployments = set()  # Track processed deployments to avoid infinite loop
            while True:
                # Get next deployment from the priority queue 
                queue_key = self.queue.get_queue_key(cluster_id, priority)
                deployment_data_bytes = self.queue.redis_client.lindex(queue_key, -1)  # Peek at last deployment 
                
                if not deployment_data_bytes:
                    break  # Queue is empty
                   
                deployment_data = json.loads(deployment_data_bytes)
                deployment_id = deployment_data['deployment_id']
               
                if deployment_id in processed_deployments:
                    # We've seen this deployment before, stop processing
                    break
                
                self.queue.redis_client.rpop(queue_key)  
                processed_deployments.add(deployment_id)
               
                try:
                    deployment = Deployment.objects.get(id=deployment_id)
                    cluster = Cluster.objects.get(id=cluster_id)

                    if self.can_deploy(cluster, deployment):
                        # Only now remove it from queue since we can deploy it
                        # self.queue.redis_client.rpop(queue_key)
                       
                        
                            # Update cluster resource utilization
                        cluster.utilized_cpu += deployment.cpu_required
                        cluster.utilized_gpu += deployment.gpu_required
                        cluster.utilized_ram += deployment.ram_required
                        cluster.save()

                        # Update deployment status
                        deployment.status = 'running'
                        deployment.cluster = cluster
                        deployment.save()
                    else:
                        # Can't deploy now, leave it in queue and try next
                        self.queue.enqueue_deployment(deployment_data, cluster_id)
                       
                        continue

                except (Deployment.DoesNotExist, Cluster.DoesNotExist):
                    # Remove invalid deployments from queue
                    self.queue.redis_client.rpop(queue_key)
                    continue
                except Exception as e:
                    print(f"Error processing deployment {deployment_id}: {str(e)}")
                    continue

        # First check if high priority queue has any deployments
        queue_length = self.queue.get_queue_length(cluster_id)
        print(queue_length)
        # Process high priority queue
        process_priority_queue('high')

        # Only process low priority if high priority queue is empty
        if queue_length['high_priority'] == 0:
            process_priority_queue('low')
