# MLOps Platform

## Overview

This project is an MLOps platform designed to manage and deploy machine learning models. It includes user registration, authentication, cluster management, and deployment scheduling using Django and Redis.

## Features

- User registration and authentication
- Invite code generation for organization management
- Cluster creation and status monitoring
- Deployment scheduling with priority queues
- Redis integration for queue management

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- Redis server
- Django and related packages (see `requirements.txt`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mlops_platform
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

2. **Install Dependencies**\
  Install all project dependencies from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set Up the Database**\
  To set up the database, make and apply migrations:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

4. **Run the Redis Server**\
  Ensure that Redis is running on your machine. You can start it with:
    ```bash
    redis-server
    ```

5. **Running the Service**\
  To start the Django development server, use the following command:
    ```bash
    python manage.py runserver
    ```
  &emsp; &emsp; &ensp; You can access the application by opening your browser and going to [http://localhost:8000](http://localhost:8000).

6.  **User Authentication**\
    After registering, you must log in to obtain an access token. This token is returned in the response upon a successful login. For any subsequent requests that require authorization, include this token in the request header as:
    ```bash
    Authorization: Bearer <access-token>
    ```


7.  **View API Documentation**\

    You can explore and test the API endpoints through the **Swagger documentation** available at [`/swagger/`](http://localhost:8000/swagger/) (or the equivalent path configured in the project).

    This provides an interactive interface where you can review the available API endpoints, their request and response formats, and try out requests directly.


8. **Algorithm**\
  The core algorithm of your MLOps platform revolves around the deployment scheduling process, which utilizes priority queues managed by Redis. Here's a more detailed explanation:\
  *Deployment Scheduling Algorithm*
    1. Priority Queues:
        - Deployments are categorized into two priority levels: high and low.
        - Each cluster has its own set of queues in Redis, allowing for independent processing.
    2. Queue Management:
        - Enqueue:  When a deployment request is received, it is added to the appropriate queue based on its priority (high or low). This ensures that deployments with higher urgency are processed before those with lower urgency.
        - Dequeue: The `DeploymentScheduler` processes deployments by dequeuing them from the highest priority queue first.
    3. Processing Events:\
        The queue is processed on two key events:
        - New Deployment Scheduled: Whenever a new deployment is added to the queue.
        - Existing Deployment Stopped: When a deployment is stopped, freeing up resources.
    4. Deployment Process:
        - High Priority Processing:
            - Each deployment in the high priority queue is traversed.
            - Deployments are attempted based on resource feasibility.
            - If resources are insufficient, the deployment remains in the queue.
        - Low Priority Processing:
            - Only processed if the high priority queue is empty.
            - Ensures that all high urgency tasks are handled first.
    5. Resource Management:
        - The scheduler updates the cluster's resource usage when a deployment is started or completed.
        - This ensures that resource allocation is dynamically managed and prevents over-commitment.
    6. Fallback to Low Priority:
        - If the high priority queue is empty, the scheduler will process the low priority queue, ensuring that all queued deployments are eventually addressed.

9. **Architecture**\
  The architecture of your MLOps platform is designed to support scalable and efficient management of machine learning deployments. Here's a detailed breakdown:
  *Components*
    1. API Service:
        - Purpose: Manages user interactions, including registration, authentication, and cluster management.
        - Technology: Built with Django and Django REST Framework.
        - Endpoints: Provides RESTful endpoints for user and cluster operations, as well as deployment scheduling.
    2. Scheduler Service:
        - Purpose: Handles the queuing and processing of deployment requests.
        - Technology: Utilizes a custom scheduling algorithm implemented in Python.
        - Integration: Interacts with Redis for queue management and the API service for deployment data.
    3. Redis:
        - Purpose: Serves as the in-memory data store for managing deployment queues.
        - Technology: Redis is chosen for its speed and efficiency in handling queue operations.
        - Functionality: Stores deployment data in priority queues, allowing the scheduler to efficiently process requests.
        <!-- end of the list -->
    This architecture supports scalability by allowing multiple clusters to be managed independently, with Redis providing fast access to deployment queues. The separation of API and Scheduler services ensures that user interactions and deployment processing can be scaled independently, providing flexibility and efficiency.
10. **Database Schema**\
  The database schema consists of the following models:
    - **UserProfile**: Stores user information and roles.
    - **Organization**: Represents organizations in the system.
    - **Cluster**: Contains cluster details and resource information.
    - **Deployment**: Tracks deployment details and status.

11. **Additional Notes**
    - Ensure Redis is installed and running before starting the Scheduler Service.
