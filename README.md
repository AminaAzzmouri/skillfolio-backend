# Skillfolio Backend

This is the backend of **Skillfolio**, a web application that helps self-learners archive their certificates, track skills, and connect achievements to projects.

Built with **Django REST Framework**, the backend provides secure APIs for authentication, certificate management, and project linking.

---

## 🚀 Features (Planned)

- User authentication (register, login, logout, JWT)
- Upload and manage certificates (PDF, with metadata: title, date, specialty)
- CRUD for achievements
- Link projects to certificates (with guided description form)
- Set and track learning goals (with deadlines, validations, and progress tracking ✅)
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
- Week 4: Certificates & achievements models + APIs + Goals model + validations + computed progress
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
      * Register 
      → POST /api/auth/register/ { "email":"you@example.com", "password":"pass1234" }

      * Login 
      → POST /api/auth/login/ → copy "access" token
      
      * List your certificates 
      → GET /api/certificates/ with header Authorization: Bearer <token>
      
      * Create certificate 
      → POST /api/certificates/ (JSON or multipart for file)
      
      * Projects filter 
      → GET /api/projects/?certificate=<id>

      * How to see progress_percent for goal settings + test validations

        1. Login to obtain your token:
          curl -X POST http://127.0.0.1:8000/api/auth/login/ \
          -H "Content-Type: application/json" \
          -d '{"username":"you@example.com","password":"pass1234"}'

              → **Response:**
                {
                  "refresh": "...",
                  "access": "..."
                }

           access → short-lived token for Authorization headers.
           refresh → longer-lived token you can use at /api/auth/refresh/.

        2. Use the token in requests

          curl http://127.0.0.1:8000/api/goals/ \
          -H "Authorization: Bearer ACCESS_TOKEN_HERE"

         → You should see:
                            {
                              "id": 3,
                              "target_projects": 5,
                              "deadline": "2025-12-31",
                              "created_at": "2025-08-23T10:55:41Z",
                              "progress_percent": 20.0,   // computed from completed projects
                              "user": 1
                            }

        → Renew when expired

        curl -X POST http://127.0.0.1:8000/api/auth/refresh/ \
        -H "Content-Type: application/json" \
        -d '{"refresh":"YOUR_REFRESH_TOKEN"}'

        3. Test validations:

            - Negative target:

              curl -X POST http://127.0.0.1:8000/api/goals/ \
              -H "Authorization: Bearer ACCESS_TOKEN" \
              -H "Content-Type: application/json" \
              -d '{"target_projects": -1, "deadline": "2030-01-01"}'

            → Expected: {"target_projects": ["target_projects must be > 0."]}

            - Past deadline:

              curl -X POST http://127.0.0.1:8000/api/goals/ \
              -H "Authorization: Bearer ACCESS_TOKEN" \
              -H "Content-Type: application/json" \
              -d '{"target_projects": 3, "deadline": "2000-01-01"}'

            → Expected: {"deadline": ["deadline cannot be in the past."]}

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
                                                                                       Includes progress_percent.
| Retrieve  | `GET`       | `/api/goals/{id}/` | —                                   |                                              |
| Create    | `POST`      | `/api/goals/`      | `{ "target_projects", "deadline" }` | `deadline` is `YYYY-MM-DD`.                  |
                                                                                       Validates positive target and future date.
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
  
  -----------------------------------------------------------------------------------------------------------------------------------------------
  This returns the new user’s id, username and email. It stores the email both as username and email in the default Django User model. Without running this, there is no user to log in.
  -----------------------------------------------------------------------------------------------------------------------------------------------
       
#### Login → get access/refresh
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"you@example.com","password":"pass1234"}'     # Use the returned access token for subsequent requests.

  -----------------------------------------------------------------------------------------------------------------------------------------------
  If the registration succeeded, you should receive a JSON response with access and refresh tokens. These tokens must be included in the Authorization: Bearer <access_token> header when calling protected endpoints.
  -----------------------------------------------------------------------------------------------------------------------------------------------

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

-----------------------------------------------------------------------------------------------------------------------------------------------
  With the access token, you can call GET /api/certificates/, POST /api/certificates/ (for creation), and similar endpoints for projects and goals. Because the viewsets use OwnerScopedModelViewSet, each user sees only their own certificates/projects/goals.
  -----------------------------------------------------------------------------------------------------------------------------------------------

# Filter projects by certificate
curl "http://127.0.0.1:8000/api/projects/?certificate=3" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
  - You should only see your objects in list/detail views.

-----------------------------------------------------------------------------------------------------------------------------------------------
ℹ️ All list endpoints support pagination via ?page=N.
🔒 Every resource is scoped to the authenticated user: you only ever see your own objects.
-----------------------------------------------------------------------------------------------------------------------------------------------

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

  - Guided Questions → Auto-generated description:

      * Form UX (short answers + dropdowns):
        - Work type (dropdown): Individual, Team
        - Duration (short input): number + unit (e.g., 3 weeks)
        - Primary goal (dropdown): Practice a new skill, Deliver a feature, Build a demo, Solve a real problem
        - Challenges faced (multi-select or short free text, concise)
        - Skills/tools used (short comma-separated list or chips)
        - Outcome/impact (dropdown): Improved performance, Learned fundamentals, Shipped MVP, Refactored legacy, Other (short)
        - Skills to practice more (short chips)

      * BE model fields (minimal, additive; description remains stored):
        - work_type (CharField, choices: individual, team)
        - duration_text (CharField, e.g., “3 weeks”)
        - primary_goal (CharField, limited choices)
        - challenges_short (TextField, short)
        - skills_used (TextField, short “chips” CSV for now)
        - outcome_short (CharField/TextField, short)
        - skills_to_improve (TextField, short)
        - Keep description as the auto-generated field (still editable by user before submit)

      * Auto-generation template (FE):
        - work_type (CharField, choices: individual, team)
        - duration_text (CharField, e.g., “3 weeks”)
        - primary_goal (CharField, limited choices)
        - challenges_short (TextField, short)
        - skills_used (TextField, short “chips” CSV for now)
        - outcome_short (CharField/TextField, short)
        - skills_to_improve (TextField, short)
        - Keep description as the auto-generated field (still editable by user before submit)

        ${title} — ${work_type === 'team' ? 'Team project' : 'Individual project'} (~${duration_text}).
        Goal: ${primary_goal}.
        What I built: ${short_summary_optional}.
        Challenges: ${challenges_short || 'N/A'}.
        Skills/Tools: ${skills_used || 'N/A'}.
        Outcome: ${outcome_short || 'N/A'}.
        Next focus: ${skills_to_improve || 'N/A'}.

        - The FE composes description from the answers; user can tweak the text before submitting.
        - Store both the answers (new fields) and the final description.
  
  - Add edit/delete for projects in UI
  - Filtering & search (e.g., ?certificate=<id>, ?status=completed, ?search=…)
  - Pagination (ensure FE reads results when pagination is enabled)
  
---

- **feature/user-goals:**

  **Purpose:** Implement the Goal model, enabling users to define learning or achievement objectives. Goals give context to certificates and projects by setting measurable targets (e.g., complete 5 projects before a deadline).

  **Current Status:**

  - Model created (target_projects, deadline, created_at)
  - Linked to User with fields: target_projects, deadline, created_at
  - Admin + serializer + views + URLs ready
  - Note: Core validations and computed fields were completed in feature/models-enhancements (see below).

  **Next Steps:**

  - Extend Goal model to allow marking as achieved/in-progress.
  - Add optional status field.
  - Surface goals in Dashboard FE.

---

- **feature/models-enhancements:**

  **Purpose:** Harden and enrich existing models/serializers without breaking FE contracts. Add validation, computed fields, ordering, and admin quality-of-life improvements.

  **Current Status:**

  - Goals: serializer-level validations added
      * target_projects must be > 0
      * deadline must be in the future

  - Goals: added computed progress_percent (0–100) to list/detail responses
 (computed from user’s completed projects vs target_projects; placeholder logic is in place and can be refined)

  - Meta ordering kept/confirmed (Certificates: -date_earned, Projects: -date_created, Goals: deadline)

  - Admin polish: confirmed list display for Projects, default admin for Certificates/Goals

  **Next Steps:**

  - Add certificate file constraints (type/size; e.g., PDF/images; ≤ 5MB) with clear 400 messages
  - Add project status field (planned / in_progress / completed) and server-side checks if needed
  - Add lightweight analytics endpoints (counts/progress) for dashboard
  - Optional: object-level permissions hook points for future roles
  - Optional: DRF schema/docs (drf-yasg) updates for new fields/validations

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