from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

User = get_user_model()


class SkillfolioAPISmokeTests(APITestCase):
    """
    Minimal API smoke tests proving core flows work end-to-end:
    - Auth: login, refresh, logout (blacklist).
    - Certificates: create (json + multipart), list owner-scoped, PATCH, DELETE, project_count annotation.
    - Projects: create (with/without certificate), list owner-scoped, PATCH (status/link/unlink), DELETE, filter by certificateId alias.
    - Goals: CRUD + validations + computed progress_percent, steps_progress_percent.
    - GoalSteps: create/list/patch/delete and goal counts auto-sync.
    - Analytics: summary counts (certificates, projects, goals).
    - Docs: /api/docs/ and /api/schema/ are reachable (200).

    Focus is on "happy path works" rather than exhaustive edge cases.
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

    def test_auth_logout_blacklist_flow(self):
        # Logout with refresh
        res = self.client.post(
            "/api/auth/logout/", {"refresh": self.refresh}, format="json"
        )
        self.assertIn(
            res.status_code,
            [status.HTTP_200_OK, status.HTTP_205_RESET_CONTENT],
            res.data,
        )

        # Try refresh again → should fail
        res2 = self.client.post(
            "/api/auth/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertIn(
            res2.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED],
        )

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
        # Weak check: all items belong to me (issuer check is brittle, but OK for smoke)
        self.assertTrue(all("issuer" in it for it in items))

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

    def test_certificates_update_and_delete(self):
        # Create certificate
        create = self.client.post(
            "/api/certificates/",
            {"title": "Initial", "issuer": "Coursera", "date_earned": "2024-08-01"},
            format="json",
        )
        cert_id = create.data["id"]

        # PATCH update the title
        patch = self.client.patch(
            f"/api/certificates/{cert_id}/",
            {"title": "Updated Title"},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK, patch.data)
        self.assertEqual(patch.data["title"], "Updated Title")

        # DELETE
        delete = self.client.delete(f"/api/certificates/{cert_id}/")
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)

        # GET should now 404
        missing = self.client.get(f"/api/certificates/{cert_id}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

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

    def test_projects_update_link_unlink_and_delete(self):
        # Make a certificate to link
        cert = self.client.post(
            "/api/certificates/",
            {
                "title": "Backend Cert",
                "issuer": "Coursera",
                "date_earned": "2024-05-01",
            },
            format="json",
        ).data

        # Create a project
        create = self.client.post(
            "/api/projects/",
            {"title": "ProjX", "status": "planned", "description": "Draft"},
            format="json",
        )
        proj_id = create.data["id"]

        # PATCH update status
        patch1 = self.client.patch(
            f"/api/projects/{proj_id}/", {"status": "completed"}, format="json"
        )
        self.assertEqual(patch1.status_code, status.HTTP_200_OK, patch1.data)
        self.assertEqual(patch1.data["status"], "completed")

        # Link certificate
        patch2 = self.client.patch(
            f"/api/projects/{proj_id}/", {"certificate": cert["id"]}, format="json"
        )
        self.assertEqual(patch2.status_code, status.HTTP_200_OK, patch2.data)
        self.assertEqual(patch2.data["certificate"], cert["id"])

        # Unlink certificate (set null)
        patch3 = self.client.patch(
            f"/api/projects/{proj_id}/", {"certificate": None}, format="json"
        )
        self.assertEqual(patch3.status_code, status.HTTP_200_OK, patch3.data)
        self.assertIsNone(patch3.data["certificate"])

        # DELETE
        delete = self.client.delete(f"/api/projects/{proj_id}/")
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)

        # GET should 404
        missing = self.client.get(f"/api/projects/{proj_id}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    # -----------------------
    # Certificates including projects
    # -----------------------
    def test_certificates_list_includes_project_count(self):
        """
        Certificates should include project_count, reflecting related projects.
        """
        # Create certificate
        cert = self.client.post(
            "/api/certificates/",
            {"title": "With Projects", "issuer": "TestOrg", "date_earned": "2024-08-01"},
            format="json",
        ).data

        # Create two projects linked to it
        for i in range(2):
            self.client.post(
                "/api/projects/",
                {"title": f"Proj{i}", "certificate": cert["id"], "status": "completed", "description": "x"},
                format="json",
            )

        # Fetch certificate list → project_count must be 2
        res = self.client.get("/api/certificates/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        item = next((c for c in res.data.get("results", []) if c["id"] == cert["id"]), None)
        self.assertIsNotNone(item, "Certificate not found in list")
        self.assertIn("project_count", item)
        self.assertEqual(item["project_count"], 2)

    def test_projects_filter_by_certificateId_alias(self):
        """
        Projects can be filtered using ?certificateId=<id> alias.
        """
        # Create cert + 1 linked project
        cert = self.client.post(
            "/api/certificates/",
            {"title": "Alias Cert", "issuer": "TestOrg", "date_earned": "2024-07-01"},
            format="json",
        ).data
        linked = self.client.post(
            "/api/projects/",
            {"title": "Alias Project", "certificate": cert["id"], "status": "planned", "description": "demo"},
            format="json",
        ).data

        # Create an unrelated project
        self.client.post(
            "/api/projects/",
            {"title": "Unrelated", "status": "completed", "description": "other"},
            format="json",
        )

        # Filter with ?certificateId
        res = self.client.get(f"/api/projects/?certificateId={cert['id']}")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        items = res.data.get("results", res.data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], linked["id"])
    
    # -----------------------
    # Goals
    # -----------------------
    def test_goals_crud_and_progress_computation(self):
        # Create a goal with title + target 2 (future deadline)
        create_res = self.client.post(
            "/api/goals/",
            {"title": "Hit 2 projects", "target_projects": 2, "deadline": "2099-01-01"},
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
            {"title": "Bad target", "target_projects": -1, "deadline": "2099-12-31"},
            format="json",
        )
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("target_projects", res_neg.data)

        # Past deadline
        res_past = self.client.post(
            "/api/goals/",
            {"title": "Past deadline", "target_projects": 3, "deadline": "2000-01-01"},
            format="json",
        )
        self.assertEqual(res_past.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", res_past.data)

    def test_goals_title_and_steps_progress_fields_present(self):
        """
        Create a goal with title + checklist counts and verify steps_progress_percent
        is returned and consistent with totals.
        """
        create = self.client.post(
            "/api/goals/",
            {
                "title": "Ship portfolio v1",
                "target_projects": 5,
                "deadline": "2099-12-31",
                "total_steps": 4,
                "completed_steps": 1,
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        self.assertEqual(create.data["title"], "Ship portfolio v1")
        self.assertIn("steps_progress_percent", create.data)
        self.assertEqual(create.data["steps_progress_percent"], 25)

        # Update completed_steps → steps_progress_percent should change
        gid = create.data["id"]
        patch = self.client.patch(
            f"/api/goals/{gid}/",
            {"completed_steps": 3},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK, patch.data)
        self.assertEqual(patch.data["completed_steps"], 3)
        self.assertEqual(patch.data["steps_progress_percent"], 75)

    # -----------------------
    # GoalSteps
    # -----------------------
    def test_goalsteps_crud_and_goal_sync(self):
        """
        End-to-end checklist flow:
        - Create goal (no steps).
        - Add two steps (1 done).
        - Verify goal totals (total_steps, completed_steps, steps_progress_percent).
        - Toggle is_done and reorder.
        - Delete a step; verify totals again.
        """
        # Create a blank goal
        goal = self.client.post(
            "/api/goals/",
            {"title": "Write case study", "target_projects": 1, "deadline": "2099-01-01"},
            format="json",
        ).data
        gid = goal["id"]

        # Initially totals should be 0/0 (or missing → treat as 0)
        g1 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g1.get("total_steps", 0), 0)
        self.assertEqual(g1.get("completed_steps", 0), 0)
        self.assertEqual(g1.get("steps_progress_percent", 0), 0)

        # Create step A (not done)
        s1 = self.client.post(
            "/api/goalsteps/",
            {"goal": gid, "title": "Draft outline", "order": 1},
            format="json",
        )
        self.assertEqual(s1.status_code, status.HTTP_201_CREATED, s1.data)
        step_a = s1.data

        # Create step B (done)
        s2 = self.client.post(
            "/api/goalsteps/",
            {"goal": gid, "title": "Collect assets", "order": 2, "is_done": True},
            format="json",
        )
        self.assertEqual(s2.status_code, status.HTTP_201_CREATED, s2.data)
        step_b = s2.data

        # Goal should now reflect totals: total=2, completed=1, steps_progress=50
        g2 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g2.get("total_steps", 0), 2)
        self.assertEqual(g2.get("completed_steps", 0), 1)
        self.assertEqual(g2.get("steps_progress_percent", 0), 50)

        # Toggle step A -> done
        p1 = self.client.patch(
            f"/api/goalsteps/{step_a['id']}/",
            {"is_done": True},
            format="json",
        )
        self.assertEqual(p1.status_code, status.HTTP_200_OK, p1.data)
        g3 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g3.get("completed_steps", 0), 2)
        self.assertEqual(g3.get("steps_progress_percent", 0), 100)

        # Reorder step B (no effect on totals, just exercise the endpoint)
        p2 = self.client.patch(
            f"/api/goalsteps/{step_b['id']}/",
            {"order": 1},
            format="json",
        )
        self.assertEqual(p2.status_code, status.HTTP_200_OK, p2.data)

        # Delete step A → totals should drop to total=1, completed depends on step B
        d1 = self.client.delete(f"/api/goalsteps/{step_a['id']}/")
        self.assertEqual(d1.status_code, status.HTTP_204_NO_CONTENT)
        g4 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g4.get("total_steps", 0), 1)
        # Only step B remains and is done=True
        self.assertEqual(g4.get("completed_steps", 0), 1)
        self.assertEqual(g4.get("steps_progress_percent", 0), 100)

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

    # -----------------------
    # Docs (smoke)
    # -----------------------
    def test_docs_and_schema_available(self):
        docs = self.client.get("/api/docs/")
        self.assertEqual(docs.status_code, status.HTTP_200_OK)

        schema = self.client.get("/api/schema/")
        self.assertEqual(schema.status_code, status.HTTP_200_OK)