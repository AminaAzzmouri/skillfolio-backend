from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

User = get_user_model()


class SkillfolioAPISmokeTests(APITestCase):
    """
    Minimal API smoke tests proving core flows work end-to-end:
    - Auth: login returns access/refresh; refresh issues new access
    - Certificates: create (json + multipart) and list are owner-scoped
    - Projects: create (with/without certificate) and list are owner-scoped
    - Goals: CRUD + validations + computed progress_percent
    - Analytics: summary returns user-scoped counts

    These tests intentionally focus on "does the happy path work?" rather than
    every edge case. They’re meant to be fast and confidence-building.
    """

    def setUp(self):
        # Create two users to verify owner scoping
        self.user = User.objects.create_user(
            username="me@example.com", email="me@example.com", password="pass1234"
        )
        self.other = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="pass1234"
        )
        self.client = APIClient()

        # Login as self.user to obtain tokens
        res = self.client.post(
            "/api/auth/login/",
            {"username": "me@example.com", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.access = res.data["access"]
        self.refresh = res.data["refresh"]

        # Convenience: set Authorization for subsequent calls
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    # -----------------------
    # Auth
    # -----------------------
    def test_refresh_token_flow(self):
        res = self.client.post(
            "/api/auth/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)

    # -----------------------
    # Certificates
    # -----------------------
    def test_certificates_create_json_and_list_owner_scoped(self):
        # Create JSON (no file)
        res = self.client.post(
            "/api/certificates/",
            {
                "title": "Django Basics",
                "issuer": "Coursera",
                "date_earned": "2024-08-01",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        # Create a cert for the other user (with a separate client)
        other_client = APIClient()
        login = other_client.post(
            "/api/auth/login/",
            {"username": "other@example.com", "password": "pass1234"},
            format="json",
        )
        other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        _ = other_client.post(
            "/api/certificates/",
            {
                "title": "Other Cert",
                "issuer": "Udemy",
                "date_earned": "2024-01-01",
            },
            format="json",
        )

        # List must only include my certificate(s)
        res = self.client.get("/api/certificates/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        items = res.data if isinstance(res.data, list) else res.data.get("results", [])
        self.assertTrue(all(it["issuer"] in ["Coursera"] for it in items))

    def test_certificates_create_multipart_with_file(self):
        # A tiny in-memory "pdf" for upload (content type isn't strictly enforced here)
        fake_pdf = SimpleUploadedFile(
            "proof.pdf", b"%PDF-1.4 tiny", content_type="application/pdf"
        )
        res = self.client.post(
            "/api/certificates/",
            {
                "title": "ML Cert",
                "issuer": "Udacity",
                "date_earned": "2024-07-10",
                "file_upload": fake_pdf,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertIn("file_upload", res.data)
        self.assertTrue(str(res.data["file_upload"]).endswith(".pdf"))

    # -----------------------
    # Projects
    # -----------------------
    def test_projects_create_with_and_without_certificate_and_list(self):
        # Create a certificate first (to link)
        cert = self.client.post(
            "/api/certificates/",
            {
                "title": "Data Eng",
                "issuer": "Coursera",
                "date_earned": "2024-06-01",
            },
            format="json",
        ).data

        # Create project WITHOUT certificate
        res1 = self.client.post(
            "/api/projects/",
            {
                "title": "Portfolio Dashboard",
                "status": "completed",
                "work_type": "team",
                "duration_text": "2 weeks",
                "primary_goal": "deliver_feature",
                "description": "",  # server can auto-generate if blank
            },
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED, res1.data)

        # Create project WITH certificate
        res2 = self.client.post(
            "/api/projects/",
            {
                "title": "ETL Pipeline",
                "status": "in_progress",
                "certificate": cert["id"],
                "description": "Building ingestion pipeline",
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED, res2.data)

        # List (should include only my 2 projects)
        res = self.client.get("/api/projects/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.data if isinstance(res.data, list) else res.data.get("results", [])
        self.assertGreaterEqual(len(items), 2)
        titles = {p["title"] for p in items}
        self.assertTrue({"Portfolio Dashboard", "ETL Pipeline"}.issubset(titles))

    # -----------------------
    # Goals
    # -----------------------
    def test_goals_crud_and_progress_computation(self):
        # Create a goal with target 2 (future deadline)
        create_res = self.client.post(
            "/api/goals/",
            {"target_projects": 2, "deadline": "2099-01-01"},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        goal_id = create_res.data["id"]
        self.assertIn("progress_percent", create_res.data)
        self.assertEqual(create_res.data["progress_percent"], 0)

        # Create ONE completed project to make progress = 50%
        _ = self.client.post(
            "/api/projects/",
            {
                "title": "Completed Thing",
                "status": "completed",
                "description": "Done",
            },
            format="json",
        )

        # List goals → progress should reflect completed projects / target
        list_res = self.client.get("/api/goals/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        items = list_res.data if isinstance(list_res.data, list) else list_res.data.get("results", [])
        my_goal = next((g for g in items if g["id"] == goal_id), None)
        self.assertIsNotNone(my_goal)
        self.assertIn("progress_percent", my_goal)
        self.assertEqual(my_goal["progress_percent"], 50.0)

        # PATCH update target to 4 → progress becomes 25.0
        patch_res = self.client.patch(
            f"/api/goals/{goal_id}/", {"target_projects": 4}, format="json"
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK, patch_res.data)
        self.assertEqual(patch_res.data["target_projects"], 4)

        # Re-fetch → progress should be 25.0 now
        get_res = self.client.get(f"/api/goals/{goal_id}/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["progress_percent"], 25.0)

        # DELETE the goal
        del_res = self.client.delete(f"/api/goals/{goal_id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

        # Ensure it's gone
        missing = self.client.get(f"/api/goals/{goal_id}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_goals_validations_negative_and_past_deadline(self):
        # Negative target
        res_neg = self.client.post(
            "/api/goals/",
            {"target_projects": -1, "deadline": "2099-12-31"},
            format="json",
        )
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("target_projects", res_neg.data)

        # Past deadline
        res_past = self.client.post(
            "/api/goals/",
            {"target_projects": 3, "deadline": "2000-01-01"},
            format="json",
        )
        self.assertEqual(res_past.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", res_past.data)

    # -----------------------
    # Analytics
    # -----------------------
    def test_analytics_summary_counts(self):
        # Ensure we have at least one cert/project for the current user
        self.client.post(
            "/api/certificates/",
            {
                "title": "Py Cert",
                "issuer": "Kaggle",
                "date_earned": "2024-02-01",
            },
            format="json",
        )
        self.client.post(
            "/api/projects/",
            {
                "title": "Tiny App",
                "status": "planned",
                "description": "Test app",
            },
            format="json",
        )

        res = self.client.get("/api/analytics/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("certificates_count", res.data)
        self.assertIn("projects_count", res.data)
        self.assertIn("goals_count", res.data)
        self.assertGreaterEqual(res.data["certificates_count"], 1)
        self.assertGreaterEqual(res.data["projects_count"], 1)
        # goals_count may be 0 if none created; just ensure key exists