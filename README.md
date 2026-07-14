# Job Application Submission and Review Microservice Architecture

## A decoupled microservice architecture built with Django, utilizing Redis Pub/Sub channels asynchronous event streaming.

This project implements a decoupled, distributed microservices architecture modeled after a real-world enterprise Applicant Tracking System (ATS). It isolates candidate operations (**User Service**) from recruiter operations (**Admin Service**) using a strict **Database-per-Service** design pattern. By leveraging a centralized Redis message broker, the platform facilitates fast synchronous REST API communication alongside highly scalable, bi-directional asynchronous event workflows. This setup ensures that high-volume operations—such as heavy job application spikes and real-time recruitment status adjustments—are handled instantly without thread-blocking dependencies, memory leaks, or database cross-contamination.

---

## Project Architecture Layout

The system is split into two completely isolated Django applications and an independent Redis container, communicating via networks mapped out in a `docker-compose.yml` grid:

*   **User Microservice (Port 8000):** Candidate-facing portal tracking profiles and submission states via an isolated local database (`user_db.sqlite3`).
*   **Admin Microservice (Port 8001):** Recruiter-facing dashboard handling vacancies and candidate evaluation boards via an isolated local database (`admin_db.sqlite3`).
*   **Redis Message Broker (Port 6379):** The async engine running Pub/Sub pipelines to bridge data states seamlessly.

```mermaid
graph TD
    %% --- Theme & Style Settings ---
    classDef userStack fill:#e6f2ff,stroke:#0066cc,stroke-width:2px,color:#000;
    classDef adminStack fill:#ebfaeb,stroke:#2d862d,stroke-width:2px,color:#000;
    classDef brokerStack fill:#ffe6e6,stroke:#cc0000,stroke-width:2px,color:#000;
    classDef clientStack fill:#f9f9f9,stroke:#333,stroke-width:1px,color:#000;

    %% --- External Actors / Clients ---
    subgraph Clients [Client Layer]
        Candidate[Candidate / Browser <br> Port 8000]:::clientStack
        Recruiter[HR Admin Portal <br> Port 8001]:::clientStack
    end

    %% --- User Microservice Stack ---
    subgraph UserMS [User Microservice Stack - Port 8000]
        UserApp[User App <br> Django + DRF]:::userStack
        UserDB[(user_db.sqlite3)]:::userStack
        UserWorker[Listener To Incoming Events <br> listen_status_update]:::userStack
    end

    %% --- Redis Message Broker ---
    subgraph MessageBroker [Central Infrastructure Network]
        Redis[Redis Docker Container <br> Port 6379 Broker]:::brokerStack
    end

    %% --- Admin Microservice Stack ---
    subgraph AdminMS [Admin Microservice Stack - Port 8001]
        AdminApp[Admin App <br> Django + DRF]:::adminStack
        AdminDB[(admin_db.sqlite3)]:::adminStack
        AdminWorker[Listener To Incoming Events <br> listen_applications]:::adminStack
    end

    %% --- Communication & Flow Logic Network ---
    
    %% User Interactions
    Candidate -->|1. Applies / Browses| UserApp
    Recruiter -->|Manage Jobs / Reviews| AdminApp

    %% Storage Mapping
    UserApp -->|Read / Write| UserDB
    UserWorker -->|Update Status| UserDB
    AdminApp -->|Read / Write| AdminDB
    AdminWorker -->|Persist New App| AdminDB

    %% 1. Synchronous Endpoint Fetch
    UserApp ==>|2. SYNC HTTP REST CALL <br> Fetch Open Job Postings| AdminApp

    %% 2. Async Submission Flow
    UserApp ---->|3. ASYNC EVENT <br> Publish to 'admin_events'| Redis
    Redis ---->|4. SUBSCRIBE <br> Fetch New Application| AdminWorker

    %% 3. Async Bi-Directional Signal Loop
    AdminApp ---->|5. POST-SAVE SIGNAL <br> Publish to 'user_events'| Redis
    Redis ---->|6. SUBSCRIBE <br> Process HIRED/REJECTED Status| UserWorker

```
---

## How to Install and Run the project

Follow these step-by-step instructions to orchestrate, build, and interact with the complete distributed microservice platform on your machine.

### 1. Prerequisites
Ensure you have **Docker** and **Docker Compose** installed on your Computer. 

### 2. Project Directory Setup
Verify that your directory matches the structural topology below:
```text
microservices_django/
│
├── admin_service/           # Admin Django Application Folder
│   ├── Dockerfile
│   └── ...
├── user_service/            # User Django Application Folder
│   ├── Dockerfile
│   └── ...
└── docker-compose.yml       # Centralized orchestration blueprint
```

### 3. Build and Spin Up the Containers
Open your terminal in the root folder (where `docker-compose.yml` resides) and execute:
```bash
docker-compose up --build
```

### 4. Create Superuser Profiles (For Admin Dashboard Access)
Because the databases are isolated, you must create an admin login credential inside each container separately to test the graphical panels. 

Open a new terminal window and run:
*   **For User Dashboard (Port 8000):**
    ```bash
    docker exec -it user-service python manage.py createsuperuser
    ```
*   **For Admin Dashboard (Port 8001):**
    ```bash
    docker exec -it admin-service python manage.py createsuperuser
    ```

---
