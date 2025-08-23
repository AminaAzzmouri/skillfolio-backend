# Skillfolio Backend

This is the backend of **Skillfolio**, a web application that helps self-learners archive their certificates, track skills, and connect achievements to projects.

Built with **Django REST Framework**, the backend provides secure APIs for authentication, certificate management, and project linking.

---

## 🚀 Features (Planned)

- User authentication (register, login, logout, JWT)
- Upload and manage certificates (PDF, with metadata: title, date, specialty)
- CRUD for achievements
- Link projects to certificates (with guided description form)
- Set and track learning goals (with deadlines and progress tracking)
- REST API endpoints for the frontend

---

## 🛠️ Tech Stack

- Python / Django
- Django REST Framework (DRF)
- MySQL (production) / SQLite (development)
- JWT Authentication

---

## 📅 Project Timeline

- Week 3: Django project setup + authentication
- Week 4: Certificates & achievements models + APIs
- Week 5: Testing, polish, deployment

---

## ⚡ Getting Started

# Project Setup Instructions:

===========================================================================

# 1. Clone repo

git clone https://github.com/AminaAzzmouri/skillfolio-backend.git

===========================================================================

# 2. Create a virtual environment

python -m venv venv

===========================================================================

# 3. Activate the virtual environment:

    - Windows: venv\Scripts\activate
    - macOS/Linux: source venv/bin/activate

===========================================================================

# 4. Install dependencies

pip install django
pip install -r requirements.txt

===========================================================================

# 5. Start the Django project:

django-admin startproject skillfolio_backend

===========================================================================

# 6. Apply migrations:

python manage.py makemigrations
python manage.py migrate

===========================================================================

# 7. Run the server:

python manage.py runserver

===========================================================================

# 8. Create the users app (feature/user-model branch):

#### Inside the Django project folder (where manage.py is located), run:

python manage.py startapp users

**App Explanation:**  
 The `users` app serves as the central place for user-related models and functionality. By keeping all user, certificate, project, and goal-related models in this single app, we avoid unnecessary app fragmentation. This approach simplifies relationships between models, reduces overhead in project structure, and keeps the code easier to maintain, especially in a project where all features are tightly related to users’ achievements and certificates.

#### Make sure to add 'users' to INSTALLED_APPS in settings.py:

INSTALLED_APPS = [
...,
'rest_framework',
'users', # <-- newly created app
]

===========================================================================

# 9. Install backend auth & integration deps: (JWT, CORS, filtering)

pip install djangorestframework-simplejwt django-cors-headers django-filter
pip freeze > requirements.txt

===========================================================================

# 10. Update settings.py:

    - Add rest_framework, corsheaders, django_filters, and users to INSTALLED_APPS.
    - Add CorsMiddleware to MIDDLEWARE.
    - Enable CORS_ALLOW_ALL_ORIGINS = True (dev-only).
    - Configure REST_FRAMEWORK with JWT, permissions, filtering, pagination.
    - Add optional SIMPLE_JWT lifetimes.
    - Configure MEDIA_URL and MEDIA_ROOT for file uploads.

===========================================================================

# 11. URLs: auth endpoints + media:

In skillfolio_backend/urls.py

===========================================================================

# 12. ViewSets: user scoping + auto-owner:

In each ViewSet (Certificates/Projects/Goals), add:

            def get_queryset(self):
                return self.queryset.filter(user=self.request.user)

            def perform_create(self, serializer):
                serializer.save(user=self.request.user)

(This ensures a user only sees/modifies their objects.)

===========================================================================

# 13. Quick testing (local):

python manage.py collectstatic --noinput  # (harmless; if STATIC configured)
python manage.py migrate
python manage.py runserver

  - Use Thunder Client/Postman or curl to test:
      * Register → POST /api/auth/register/ { "email":"you@example.com", "password":"pass1234" }
      * Login → POST /api/auth/login/ → copy "access" token
      * List your certificates → GET /api/certificates/ with header Authorization: Bearer <token>
      * Create certificate → POST /api/certificates/ (JSON or multipart for file)
      * Projects filter → GET /api/projects/?certificate=<id>

===========================================================================

# 14. Security & polish (Week 4 prep):

  - Restrict CORS to your frontend origin.
  - Add validation (e.g., no past deadline, file size/type check).
  - Add search/ordering params to README.
  - Add Swagger/OpenAPI (e.g., drf-yasg) and basic tests.

===========================================================================

---

## 📌 API Quick Reference:

All endpoints are JWT-protected unless noted.
Base URL (local): http://127.0.0.1:8000

**Auth**:

| Endpoint              | Methods | Auth | Notes                                                                                       |
| --------------------- | ------- | ---- | ------------------------------------------------------------------------------------------- |
| `/api/auth/register/` | `POST`  | ❌   | Dev helper. Body: `{ "email", "password" }`. Creates a Django user using email as username. |
| `/api/auth/login/`    | `POST`  | ❌   | JWT login (email or username). Returns `{ "access", "refresh" }`.                           |
| `/api/auth/refresh/`  | `POST`  | ❌   | Exchange refresh for a new access token.                                                    |

    **Login body examples**:  { "email": "you@example.com", "password": "pass1234" }
    - Or:                     { "username": "you@example.com", "password": "pass1234" }

    Use the access token in headers: Authorization: Bearer <ACCESS_TOKEN>

**Certificates**: 
Base: /api/certificates/

| Operation     | Method      | URL                       | Body                                  | Notes                                  |
| ------------- | ----------- | ------------------------- | ------------------------------------- | -------------------------------------- |
| List          | `GET`       | `/api/certificates/       | —                                     | Returns only the authenticated user’s  |
|               |             |                           |                                       | certificates.                          |
| Retrieve      | `GET`       | `/api/certificates/{id}/` |                                       |                                        |
| Create (JSON) | `POST`      | `/api/certificates/`      | `{ "title", "issuer", "date_earned" }`| `file_upload` optional (multipart).    |
| Create (file) | `POST`      | `/api/certificates/`      | multipart fields: `title`, `issuer`,  | Requires                               |
                                                          | `date_earned`, `file_upload=@path`    |`Content-Type: multipart/form-data`.    |
| Update        | `PUT/PATCH` | `/api/certificates/{id}/` | JSON or multipart                     |                                        |
| Delete        | `DELETE`    | `/api/certificates/{id}/` | —                                     |                                        |

    **Query params**: 
        - Filtering: ?issuer=Coursera&date_earned=2024-08-01
        - Search: ?search=python (matches title, issuer)
        - Ordering: ?ordering=date_earned or ?ordering=-date_earned (also title)
        - Pagination: ?page=2

**Projects**:
Base: /api/projects/

| Operation | Method      | URL                   | Body                                     | Notes                                           |
| --------- | ----------- | --------------------- | ---------------------------------------- | ----------------------------------------------- |
| List      | `GET`       | `/api/projects/`      | —                                        | Returns only the authenticated user’s projects. |
| Retrieve  | `GET`       | `/api/projects/{id}/` | —                                        |                                                 |
| Create    | `POST`      | `/api/projects/`      | `{ "title", "description", "certificate":| `certificate` is optional.                      |
|           |             |                          <id or null> }`                         |                                                 |
| Update    | `PUT/PATCH` | `/api/projects/{id}/` | JSON                                     |                                                 |
| Delete    | `DELETE`    | `/api/projects/{id}/` | —                                        |                                                 |

    **Query params**: 
        - Filtering: ?certificate=<id>
        - Search: ?search=dashboard (matches title, description)
        - Ordering: ?ordering=date_created or ?ordering=-date_created (also title)
        - Pagination: ?page=1
        
**Goals**: 
Base: /api/goals/

| Operation | Method      | URL                | Body                                | Notes                                        |
| --------- | ----------- | ------------------ | ----------------------------------- | -------------------------------------------- |
| List      | `GET`       | `/api/goals/`      | —                                   | Returns only the authenticated user’s goals. |
| Retrieve  | `GET`       | `/api/goals/{id}/` | —                                   |                                              |
| Create    | `POST`      | `/api/goals/`      | `{ "target_projects", "deadline" }` | `deadline` is `YYYY-MM-DD`.                  |
| Update    | `PUT/PATCH` | `/api/goals/{id}/` | JSON                                |                                              |
| Delete    | `DELETE`    | `/api/goals/{id}/` | —                                   |                                              |

**Query params**: 
        - Filtering: ?deadline=2025-12-31
        - Ordering: ?ordering=created_at or ?ordering=-created_at
        - Pagination: ?page=1

**Quick cURL Examples**: 

#### Register (dev helper)
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"pass1234"}'
       
#### Login → get access/refresh
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"pass1234"}'     # Copy the "access" token.

# List certificates (requires Bearer token):
curl http://127.0.0.1:8000/api/certificates/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

#### Create certificate (JSON)
curl -X POST http://127.0.0.1:8000/api/certificates/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Django Basics","issuer":"Coursera","date_earned":"2024-08-01"}'

# Create certificate (multipart with file)
curl -X POST http://127.0.0.1:8000/api/certificates/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "title=ML Cert" \
  -F "issuer=Udacity" \
  -F "date_earned=2024-07-10" \
  -F "file_upload=@C:/path/to/file.pdf"

# Filter projects by certificate
curl "http://127.0.0.1:8000/api/projects/?certificate=3" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
  - You should only see your objects in list/detail views.

ℹ️ All list endpoints support pagination via ?page=N.
🔒 Every resource is scoped to the authenticated user: you only ever see your own objects.

---

## Branching Strategy

- **chore/django-setup:**  
  - Initial project setup, including Django project creation, virtual environment, and basic configurations.
  **Status:** Done — project bootstrapped, venv, base config.
  **Next:** Keep future tooling-only changes in new chore/* branches.
---

- **feature/user-model:**

  **Purpose:** Prepare the `users` app and the User model for future customization. This branch ensures the backend is ready for authentication and user-related features.

  **Current Status:**

  - `users` app created
  - User model placeholder in models.py
  - Added to `INSTALLED_APPS`
  - Auth (register, login, JWT) implemented
  - Integrated User model with Certificates and Projects

  **Next Steps:** Optionally customize User model later

---

- **feature/certificate-model:**

  **Purpose:** Implement the Certificate model, enabling users to upload, manage, and associate certificates with their accounts. This branch sets up the model, serializers, views, and API endpoints for certificates.

  **Current Status:**

  - Model, admin, serializer, views, URLs ready
  - Media uploads supported
  - Endpoints JWT-protected & user-scoped queries.

  **Next Steps:**: Add validations, filters, Swagger docs
  
---

- **feature/project-model:**

  **Purpose:** Implement the Project model, allowing users to document their projects and link them with certificates. This branch focuses on building a structure where achievements and certificates can be contextualized with practical applications (projects).

  **Current Status:**

  - Model, admin, serializer, views, URLs ready
  - Endpoints JWT-protected, user-scoped
  - Basic filtering enabled

  **Next Steps:**

  - Add guided questions to help users describe their projects (e.g., problem solved, tools used, impact achieved)
  - Introduce project status (planned, in progress, completed)
  - Add filed: ordering by date_created
  - Connect projects to specific skills for better tracking
  - Test API endpoints for projects and prepare for frontend integration

---

- **feature/user-goals:**

  **Purpose:** Implement the Goal model, enabling users to define learning or achievement objectives. Goals give context to certificates and projects by setting measurable targets (e.g., complete 5 projects before a deadline).

  **Current Status:**

  - Model created (target_projects, deadline, created_at)
  - Linked to User with fields: target_projects, deadline, created_at
  - Admin + serializer + views + URLs ready

  **Next Steps:**

  - Add validation to prevent past deadlines
  - Extend Goal model to track progress dynamically (e.g., % completion based on linked projects)
  - Allow users to mark goals as achieved or in progress
  - Test Goal API endpoints and integrate with frontend
  - Server-side progress (% completed projects / target), prevent past deadlines, computed fields.

---

- **fix/<fix-name>:** Bug fixes

---

- **experiment/<experiment-name>:** Experimental changes

---

## Major Backend Updates (added directly on main):

Some updates originally planned for branches were implemented directly on main:

---

**🔐 JWT Authentication**

    - **Purpose:** Real authentication for FE integration.

    - **Status:**
            - Added djangorestframework-simplejwt
            - /api/auth/login/ and /api/auth/refresh/ wired
            - Simple /api/auth/register/ endpoint
            - Default DRF permissions → IsAuthenticated

    - **Next:** Password validation, improved register, optional rate limiting

---

**🌐 CORS & Filtering**

    - **Purpose:** Enable FE–BE dev & smarter APIs.

    - **Status:**

            - Added django-cors-headers (CORS_ALLOW_ALL_ORIGINS=True, dev only)
            - Added django-filter + DRF search/order/filter
            - Pagination enabled (page size=10)

    - **Next:** Restrict CORS to FE origin, add custom filters (?certificate=ID, etc.)

---