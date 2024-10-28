from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .scheduler import DeploymentScheduler
from .queue_handler import queue_instance
from api.models import Cluster, Deployment

scheduler = DeploymentScheduler()
queue = queue_instance


@api_view(['POST'])
def schedule(request):
    """Endpoint to receive deployment requests"""
    try:
        deployment_data = request.data
        cluster_id = request.data.get('cluster_id')
        
        if not cluster_id:
            return Response({
                "error": "cluster_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            if(deployment_data['is_scheduled']):
                
                # Add to specified cluster's queue and process it
                queue.enqueue_deployment(deployment_data, cluster_id)
            
            scheduler.process_cluster_queue(cluster_id)
            
            return Response({
                "message": "Deployment queued successfully",
                "deployment_id": deployment_data['deployment_id'],
                "cluster_id": cluster_id
            }, status=status.HTTP_200_OK)
            
        except Cluster.DoesNotExist:
            return Response({
                "error": "Specified cluster not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Deployment.DoesNotExist:
            return Response({
                "error": "Deployment not found"
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        print(str(e))
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
def queue_status(request):
    """Get current queue status for all clusters"""
    try:
        clusters = Cluster.objects.all()
        status_data = {}
        
        for cluster in clusters:
            status_data[f"cluster_{cluster.id}"] = {
                "name": cluster.name,
                "queues": queue.get_queue_length(cluster.id)
            }
        
        return Response(status_data)
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def cluster_queue_status(request, cluster_id):
    """Get queue status for specific cluster"""
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        queue_lengths = queue.get_queue_length(cluster_id)
        
        return Response({
            "cluster_name": cluster.name,
            "queues": queue_lengths
        })
    except Cluster.DoesNotExist:
        return Response(
            {"error": "Cluster not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
