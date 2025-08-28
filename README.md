# Skillfolio Backend

This is the backend of **Skillfolio**, a web application that helps self-learners archive their certificates, track skills, and connect achievements to projects.

Built with **Django REST Framework**, the backend provides secure APIs for authentication, certificate management, and project linking.

---

## 🚀 Features (Planned)

- User authentication (register, login, logout, JWT)
- Upload and manage certificates (PDF, with metadata: title, date, specialty)
- CRUD for achievements
- Link projects to certificates (with guided description form + auto-generated description from guided answers ✅)
- Set and track learning goals (with deadlines, validations, and progress tracking ✅)
- Filtering / search / ordering across list endpoints ✅ (see Quick Reference)
- Analytics endpoints for dashboard summary & goal progress (frontend) ✅
- Interactive API docs with Swagger/OpenAPI (drf-yasg) ✅
- Polished Django Admin (list_display, filters, search, ordering) ✅

---

## 🛠️ Tech Stack

- Python / Django
- Django REST Framework (DRF)
- SQLite (development) / MySQL (production)
- JWT Authentication
- django-filter (filtering)
- django-cors-headers (CORS)

---

## 📅 Project Timeline

- Week 3: Django project setup + authentication
- Week 4: 
      * Certificates, Projects, Goals models 
      * APIs validations
      * Computed progress
      * Project guided-questions → auto-description
      * Analytics endpoints
- Week 5: Testing, polish, deployment

---

## ⚡ Getting Started

# Project Setup Instructions:
===========================================================================

# 1. Clone repo
     git clone https://github.com/AminaAzzmouri/skillfolio-backend.git

# 2. Create a virtual environment
     python -m venv venv

# 3. Activate the virtual environment:
    - Windows: venv\Scripts\activate
    - macOS/Linux: source venv/bin/activate

# 4. Install Django:
     pip install django

# 5. Install dependencies
- We keep all backend dependencies pinned in requirements.txt (includes DRF, CORS, filters, SimpleJWT and the token blacklist extra for logout).
     pip install -r requirements.txt

- If you add/change packages, re-freeze:
     pip freeze > requirements.txt

# 5. Start the Django project:
     django-admin startproject skillfolio_backend

# 6. Apply migrations:
     python manage.py makemigrations
     python manage.py migrate

The blacklist tables for logout are created here because 
     rest_framework_simplejwt.token_blacklist is installed

# 7. Run the server:
     python manage.py runserver

# 8. Create the users app  (if it doesn’t exist yet):

#### Inside the Django project folder (where manage.py is located), run:
     python manage.py startapp users

#### **App Explanation:**  
     The users app is the central place for user-related domain models and logic (users, certificates, projects, goals) to avoid fragmentation and simplify relationships.
      
     This approach simplifies relationships between models, reduces overhead in project structure, and keeps the code easier to maintain, especially in a project where all features are tightly related to users’ achievements and certificates.

#### Add 'users' to INSTALLED_APPS in settings.py:

     INSTALLED_APPS = [
     ...,
     'rest_framework',
     'users', # <-- newly created app
     ]

# 9. Install backend auth & integration deps: (JWT, CORS, filtering)
(Already covered by requirements.txt; shown here for clarity)     

       pip install djangorestframework-simplejwt django-cors-headers django-filter
     
## For logout blacklist support:
       pip install "djangorestframework-simplejwt[token_blacklist]"
       pip freeze > requirements.txt

# 10. Security & polish:
  - Restrict CORS to your frontend origin.
  - Add validation (e.g., no past deadline, file size/type check).
  - Add search/ordering params to README.
  - Add Swagger/OpenAPI (e.g., drf-yasg) and basic tests.

---

## 🧪 Running Tests

- Run the built-in API smoke tests:

            python manage.py test

- What’s covered:
* Auth: login (access/refresh) and refresh flow
* Certificates: create (json + multipart) and list (owner scoped)
* Projects: create (with/without certificate) and list (owner scoped)
* Analytics: /api/analytics/summary/ returns counts for the logged-in user

---

## ✅ What’s Done So Far

# Authentication
* JWT login with email/username
* Register endpoint (dev helper)
* Refresh endpoint
* Logout endpoint (blacklist refresh tokens) → /api/auth/logout/ ✅

# Certificates
* Model, serializer, viewset, endpoints
* File upload support with size/type validation (≤ 5MB, PDF/Images)
* Date validation: no future date_earned

# Projects
* Model, serializer, viewset, endpoints
* Linked to certificates (nullable)
* Guided fields (work_type, duration_text, primary_goal, etc.)
* Auto-generated description if blank
* status field: planned, in_progress, completed

# Goals
* Model, serializer, viewset, endpoints
* Validations: deadline in the future, target_projects > 0
* Computed progress_percent included in responses

# Filters / Search / Ordering
* Certificates: filter by issuer/date, search title/issuer, order by date/title
* Projects: filter by certificate/status, search title/description, order by date/title
* Goals: filter by deadline, order by created_at

# Analytics
* /api/analytics/summary/ → counts of certificates, projects, goals
* /api/analytics/goals-progress/ → list of goals with progress

# Docs
* Swagger docs now working (/api/docs/).

# Admin
* Certificates: issuer/date filters, searchable title/issuer, ordered by newest
* Projects: status/work_type filters, searchable fields, newest-first ordering
* Goals: deadline filters, searchable targets, ordered by deadline
→ Admin now useful for quick QA/debugging

---

## 🔮 What’s Next

# Permissions (nice to have): 
Optional object-level permission class (extra belt-and-suspenders; current owner scoping via queryset is already enforced).

# Frontend polish support:
- Project edit/delete flows
- Certificate preview (image/PDF in dashboard cards)
- Dashboard graphs for counts/progress

# Deployment hardening:
 - Restrict CORS to FE origin
 - Production DB migration to MySQL/PostgreSQL
 - Add caching & performance tuning
 - Unit & integration tests

# Admin polish (future):
- Group fields in detail forms (Basic Info, Guided Fields, Links)
- Add inline previews for related certificates/projects

# Goals: Introduce a computed or persisted **status field** (e.g., on_track, achieved, expired).  
   * Computed option: calculate status dynamically from `progress_percent` and `deadline` in the serializer (no schema change).  
   * Persisted option: add a `status` field in the model (with choices) and update automatically when goals are met or deadlines pass.  
   This would make goals more informative by clearly showing whether they are still in progress, completed, or expired.

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


- Login body examples**:  
          { "email": "you@example.com", "password": "pass1234" }
- Or:     
          { "username": "you@example.com", "password": "pass1234" }

- Use the access token in headers: Authorization: Bearer <ACCESS_TOKEN>


**Certificates**:  Base: /api/certificates/

* Filter: ?issuer=<str>&date_earned=<YYYY-MM-DD>
* Search: ?search=<substring> ( matches title, issuer)
* Ordering: ?ordering=date_earned or ?ordering=-date_earned (also title)

* Default ordering: newest first (-date_earned)

| Operation     | Method      | URL                       | Body                                  | Notes                                  |
| ------------- | ----------- | ------------------------- | ------------------------------------- | -------------------------------------- |
| List          | `GET`       | `/api/certificates/       | —                                     | Returns only the authenticated user’s certificates.                          |
| Retrieve      | `GET`       | `/api/certificates/{id}/` |                                       |                                        |
| Create (JSON) | `POST`      | `/api/certificates/`      | `{ "title", "issuer", "date_earned" }`| `file_upload` optional (multipart).    |
| Create (file) | `POST`      | `/api/certificates/`      | multipart fields: `title`, `issuer`,  `date_earned`, `file_upload=@path`   | Requires `Content-Type: multipart/form-data`.    |
| Update        | `PUT/PATCH` | `/api/certificates/{id}/` | JSON or multipart                     |                                        |
| Delete        | `DELETE`    | `/api/certificates/{id}/` | —                                     |                                        |


**Projects**: Base: /api/projects/

* Filter: ?certificate=<id>&status=<planned|in_progress|completed>
* Search: ?search=<substring> (matches title, description)
* Ordering: ordering=date_created or ?ordering=-date_created (also title)
* Pagination: ?page=1

* Default newest first (-date_created)
* Auto-description: If description is blank on create, BE generates one from guided fields (work_type, duration_text, primary_goal, challenges_short, skills_used, outcome_short, skills_to_improve).

| Operation | Method      | URL                   | Body                                     | Notes                                           |
| --------- | ----------- | --------------------- | ---------------------------------------- | ----------------------------------------------- |
| List      | `GET`       | `/api/projects/`      | —                                        | Returns only the authenticated user’s projects. |
| Retrieve  | `GET`       | `/api/projects/{id}/` | —                                        |                                                 |
| Create    | `POST`      | `/api/projects/`      | `{ "title", "description", "certificate": <id or null> }`| `certificate` is optional, ⚡Auto-description: If `description` is blank, the backend composes one from guided-question  fields (work_type, duration_text, primary_goal,  challenges_short, skills_used, outcome_short, skills_to_improve).   |                                                                                                
| Update    | `PUT/PATCH` | `/api/projects/{id}/` | JSON                                     |                                                 |
| Delete    | `DELETE`    | `/api/projects/{id}/` | —                                        |                                                 |


        
**Goals**: Base: /api/goals/

* Filter: ?deadline=<YYYY-MM-DD>
* Ordering: ?ordering=created_at or ?ordering=-created_at
* Pagination: ?page=1

* Default ordering: newest first (-created_at)
* Field: progress_percent Computed (read-only)

| Operation | Method      | URL                | Body                                | Notes                                        |
| --------- | ----------- | ------------------ | ----------------------------------- | -------------------------------------------- |
| List      | `GET`       | `/api/goals/`      | —                                   | Returns only the authenticated user’s goals. Includes progress_percent. |
| Retrieve  | `GET`       | `/api/goals/{id}/` | —                                   |                                              |
| Create    | `POST`      | `/api/goals/`      | `{ "target_projects", "deadline" }` | `deadline` is `YYYY-MM-DD`. Validates positive target and future date. |
| Update    | `PUT/PATCH` | `/api/goals/{id}/` | JSON                                |                                              |
| Delete    | `DELETE`    | `/api/goals/{id}/` | —                                   |                                              |

---

## 📖 API Documentation (Swagger / drf-yasg)

1. What we already have:
     * /api/docs/ → interactive API docs. 
       Lists all endpoints (certificates, projects, goals, auth, analytics, logout).

     * You can try requests directly from the browser by pasting Bearer <ACCESS_TOKEN> into the “Authorize” button.

     * /api/schema/ → machine-readable OpenAPI JSON spec (useful for frontend integration and API clients).

2. What extra annotations could add:
Currently, Swagger auto-generates docs from ViewSets and serializers. If we add @swagger_auto_schema decorators, we can:

     * Group endpoints with tags → e.g., put login/logout/register under Auth.

     * Add descriptions → clear human-friendly explanations for each operation.

     * Customize schemas → define exact input/output when auto-detection is imperfect.

Example:
     @swagger_auto_schema(
    tags=["Auth"],
    operation_description="Login with email + password. Returns access and refresh JWT tokens."
     )
     def post(self, request, *args, **kwargs):
     ...

3. Why this matters

     * Frontend devs & testers → instantly know what each endpoint expects.
     * Contributors → clearer reference if the API is ever made public.
     * Future me → easy reminder of inputs/outputs after a break.

✅ In short:
 /api/docs/ already works well.
 Adding annotations is optional, but makes the docs prettier, grouped, and self-explanatory.

---

## 🔍 Quick cURL Examples: 

python manage.py collectstatic --noinput  # (harmless; if STATIC configured)
python manage.py migrate
python manage.py runserver

# 1) Register:

            curl -X POST http://127.0.0.1:8000/api/auth/register/ \
            -H "Content-Type: application/json" \
            -d '{"email":"you@example.com","password":"pass1234"}'
  
          Returns the new user’s id/username/email (email is used as the username).
  
       
# 2) Login → get access/refresh

            curl -X POST http://127.0.0.1:8000/api/auth/login/ \
            -H "Content-Type: application/json" \
            -d '{"username":"you@example.com","password":"pass1234"}'

- You’ll receive { "access": "...", "refresh": "..." }. 
* access → short-lived token for Authorization headers.
* refresh → longer-lived token you can use at /api/auth/refresh/.
  
- Use Authorization: Bearer <ACCESS_TOKEN> for protected endpoints.

- With the access token, you can call GET /api/certificates/, POST /api/certificates/ (for creation), and similar endpoints for projects and goals. 
  Because the viewsets use OwnerScopedModelViewSet, each user sees only their own certificates/projects/goals.

- Renew when expired

            curl -X POST http://127.0.0.1:8000/api/auth/refresh/ \
            -H "Content-Type: application/json" \
            -d '{"refresh":"YOUR_REFRESH_TOKEN"}'

# 3) Certificates

# Create (json)

            curl -X POST http://127.0.0.1:8000/api/certificates/ \
            -H "Authorization: Bearer <ACCESS_TOKEN>" \
            -H "Content-Type: application/json" \
            -d '{"title":"Django Basics","issuer":"Coursera","date_earned":"2024-08-01"}'

# Create with file

            curl -X POST http://127.0.0.1:8000/api/certificates/ \
            -H "Authorization: Bearer <ACCESS_TOKEN>" \
            -F "title=ML Cert" \
            -F "issuer=Udacity" \
            -F "date_earned=2024-07-10" \
            -F "file_upload=@C:/path/to/file.pdf"

# List (default = newest first)

            curl http://127.0.0.1:8000/api/certificates/ \
            -H "Authorization: Bearer <ACCESS_TOKEN>"

# Filter by issuer + date

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/certificates/?issuer=Coursera&date_earned=2025-08-01"

# Search by title/issuer

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/certificates/?search=python"

# Order oldest → newest

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/certificates/?ordering=date_earned"

# Partial update (PATCH)

            curl -X PATCH http://127.0.0.1:8000/api/certificates/5/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{"title":"Updated Title"}'

# Full update (PUT)

            curl -X PUT http://127.0.0.1:8000/api/certificates/5/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{"title":"New Title","issuer":"Udemy","date_earned":"2024-08-01"}'

# PATCH file with multipart (optional)

            curl -X PATCH http://127.0.0.1:8000/api/certificates/5/ \
            -H "Authorization: Bearer <ACCESS>" \
            -F "file_upload=@C:/path/to/new.pdf"

# DELETE

            curl -X DELETE http://127.0.0.1:8000/api/certificates/5/ \
            -H "Authorization: Bearer <ACCESS>"

# 4) Projects

# Create (leave description blank; include guided answers):

            curl -X POST http://127.0.0.1:8000/api/projects/ \
            -H "Authorization: Bearer token" \
            -H "Content-Type: application/json" \
            -d '{
              "title": "Portfolio Dashboard",
              "status": "completed",
              "work_type": "team",
              "duration_text": "2 weeks",
              "primary_goal": "deliver_feature",
              "tools_used": "React, Django, DRF",
              "skills_used": "React, Zustand, Tailwind",
              "problem_solved": "Visualize certificate progress in one place.",
              "outcome_short": "Shipped a responsive dashboard showing live stats.",
              "skills_to_improve": "Test coverage and CI"
            }'

- GET the created project and you should see a description like:

            “Portfolio Dashboard was a team project completed in 2 weeks. The main goal was 
            to deliver a functional feature. It addressed: Visualize certificate progress in 
            one place. Key tools/skills: React, Django, DRF, React, Zustand, Tailwind. Outcome: 
            Shipped a responsive dashboard showing live stats. Next, I plan to improve: Test 
            coverage and CI.”

- (If you provide `description` in POST/PUT, we keep the provided text.)

# List

            curl -H http://127.0.0.1:8000/api/projects/
            "Authorization: Bearer <ACCESS>"


- You should only see your objects in list/detail views.

# Filter by certificate id

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?certificate=12"

# Filter by status

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?status=completed"

# Search title/description

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?search=dashboard"

# Order oldest → newest

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?ordering=date_created"

# Paginate

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?page=2"

# Partial update: PATCH (status / guided fields / link a certificate):

            curl -X PATCH http://127.0.0.1:8000/api/projects/12/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{
               "status": "in_progress",
               "certificate": 5,
               "duration_text": "3 weeks",
               "primary_goal": "deliver_feature"
               }'

# FULL update

            curl -X PATCH http://127.0.0.1:8000/api/projects/12/ \curl -X PUT http://127.0.0.1:8000/api/projects/12/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{
                   "title": "Rewritten Project",
                   "description": "Full replace",
                   "certificate": null,
                   "status": "completed",
                   "work_type": "team",
                   "duration_text": "10 days",
                   "primary_goal": "build_demo",
                   "challenges_short": "X",
                   "skills_used": "React, DRF",
                   "outcome_short": "Shipped!",
                   "skills_to_improve": "Testing"
               }'

# Delete

            curl -X DELETE http://127.0.0.1:8000/api/projects/12/ \
            -H "Authorization: Bearer <ACCESS>"

# 5) Goals
    
# Create

            url -X POST http://127.0.0.1:8000/api/goals/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{"target_projects": 5, "deadline": "2025-12-31"}'


# List Progress_percent for goal settings

            curl http://127.0.0.1:8000/api/goals/ \
            -H "Authorization: Bearer ACCESS_TOKEN_HERE"

- You should see:
            {
               "id": 3,
               "target_projects": 5,
               "deadline": "2025-12-31",
               "created_at": "2025-08-23T10:55:41Z",
               "progress_percent": 20.0,   // computed from completed projects
               "user": 1
            }

# Filter by deadline

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/goals/?deadline=2025-12-31"

# Order oldest → newest

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/goals/?ordering=created_at"

# Order oldest → newest

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?ordering=date_created"

# Paginate

            curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
            "http://127.0.0.1:8000/api/projects/?page=2"

# Goal Settings validations

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

# Partial Update

            curl -X PATCH http://127.0.0.1:8000/api/goals/7/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{"target_projects": 10}'

# Full Update

            curl -X PUT http://127.0.0.1:8000/api/goals/7/ \
            -H "Authorization: Bearer <ACCESS>" \
            -H "Content-Type: application/json" \
            -d '{"target_projects": 12, "deadline": "2025-12-31"}'

# DELETE:

            curl -X DELETE http://127.0.0.1:8000/api/goals/7/ \
            -H "Authorization: Bearer <ACCESS>"

# 6) Analytics

# Summary counts

            curl -H "Authorization: Bearer <ACCESS>" 
            http://127.0.0.1:8000/api/analytics/summary/
 
            → Expected: {"certificates_count": 2, "projects_count": 5, "goals_count": 1}

# Goals with progress

            curl -H "Authorization: Bearer <ACCESS>" 
            http://127.0.0.1:8000/api/analytics/goals-progress/
            
            → Expected:  [{"id": 3, "target_projects": 5, à"progress_percent": 40.0, ...}]

# 7) Logout (refresh-token blacklist)

            curl -X POST http://127.0.0.1:8000/api/auth/logout/ \
            -H "Authorization: Bearer <ACCESS_TOKEN>" \
            -H "Content-Type: application/json" \
            -d '{"refresh": "<REFRESH_TOKEN>"}'
            
- Expected:  {"detail":"Successfully logged out."}

            - Try to refresh again with the same refresh -> should now fail
            curl -X POST http://127.0.0.1:8000/api/auth/refresh/ \
            -H "Content-Type: application/json" \
            -d '{"refresh":"<REFRESH_TOKEN>"}'

- Expected: 401/400 error (blacklisted): { "detail": "Invalid or expired refresh token." }

---

## ⚡ Development Notes

- All resources are scoped per user (you only ever see your own objects).
- Pagination enabled → use ?page=N.
- Default ordering:
    * Certificates: newest first (-date_earned)
    * Projects: newest first (-date_created)
    * Goals: newest first (-created_at)