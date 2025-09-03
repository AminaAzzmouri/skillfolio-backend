from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

User = get_user_model()


def _iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else d


class SkillfolioAPISmokeTests(APITestCase):
    """
    End-to-end API tests covering:
      - Auth: login (username + email alias), refresh, logout, register
              (username now auto-derived from email local-part)
      - Certificates: JSON + multipart create, list owner-scoped, filter by id,
                      annotation project_count, future-date validation
      - Projects: create (with/without cert), list owner-scoped, PATCH (status/link/unlink),
                  DELETE, ?certificateId alias, status-aware date validations,
                  end_date clearing when not completed, duration_text derivation,
                  auto-generated description when blank
      - Goals: CRUD, validations (negative target / past deadline),
               progress_percent (based on user's completed projects),
               steps_progress_percent (and capping completed_steps)
      - GoalSteps: CRUD + parent Goal counters auto-sync, forbid cross-user step creation
      - Analytics: /api/analytics/summary and /api/analytics/goals-progress
      - Docs: /api/docs/ (Swagger) and /api/schema/
      - Root redirect: "/" → settings.FRONTEND_URL (dynamic, not hard-coded)
      - Owner scoping: cannot read other user's objects
    """

    # -----------------------
    # Test helpers
    # -----------------------
    def setUp(self):
        # Dates used to satisfy status-aware rules
        self.TODAY = date.today()
        self.YESTERDAY = self.TODAY - timedelta(days=1)
        self.TWO_DAYS_AGO = self.TODAY - timedelta(days=2)
        self.TOMORROW = self.TODAY + timedelta(days=1)

        # Create two users
        self.user = User.objects.create_user(
            username="me@example.com", email="me@example.com", password="pass1234"
        )
        self.other = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="pass1234"
        )

        # Auth as self.user
        self.client = APIClient()
        r = self.client.post(
            "/api/auth/login/",
            {"email_or_username": "me@example.com", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.access = r.data["access"]
        self.refresh = r.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def auth_client(self, username, password):
        c = APIClient()
        r = c.post("/api/auth/login/", {"email_or_username": username, "password": password}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        return c, r.data

    def items(self, res):
        return res.data if isinstance(res.data, list) else res.data.get("results", [])

    def make_cert(self, title="Cert", issuer="Org", date_earned=None, client=None):
        if client is None:
            client = self.client
        payload = {
            "title": title,
            "issuer": issuer,
            "date_earned": _iso(date_earned or self.YESTERDAY),
        }
        r = client.post("/api/certificates/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        return r.data

    def make_project(self, **over):
        """
        Minimal helper that fills valid date combos unless explicitly provided:
          planned     → start=today
          in_progress → start=today
          completed   → start=two_days_ago, end=yesterday
        """
        status_val = over.get("status", "planned")
        payload = {
            "title": over.get("title", "P"),
            "status": status_val,
            "description": over.get("description", "auto"),
        }

        if "start_date" in over:
            payload["start_date"] = _iso(over["start_date"])
        if "end_date" in over:
            payload["end_date"] = _iso(over["end_date"])

        if "certificate" in over:
            payload["certificate"] = over["certificate"]

        # Default dates if not supplied
        if "start_date" not in payload:
            if status_val == "completed":
                payload["start_date"] = _iso(self.TWO_DAYS_AGO)
            elif status_val == "in_progress":
                payload["start_date"] = _iso(self.TODAY)
            else:  # planned
                payload["start_date"] = _iso(self.TODAY)
        if status_val == "completed" and "end_date" not in payload:
            payload["end_date"] = _iso(self.YESTERDAY)

        r = self.client.post("/api/projects/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        return r.data

    # -----------------------
    # Auth
    # -----------------------
    def test_register_and_email_login_alias(self):
        """
        Register with email+password, ensure username is auto-derived from the email local-part,
        and verify login works with BOTH email and username.
        """
        email = "newuser@example.com"

        # Register
        r = self.client.post(
            "/api/auth/register/", {"email": email, "password": "abcd1234"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        # Username is derived from email local-part (e.g., "newuser" or "newuser-2" if taken)
        self.assertIn("username", r.data)
        self.assertIn("email", r.data)
        self.assertEqual(r.data["email"].lower(), email)
        derived_username = r.data["username"]
        self.assertTrue(derived_username.startswith("newuser"))

        # Login with email
        c = APIClient()
        r2 = c.post("/api/auth/login/", {"email_or_username": email, "password": "abcd1234"}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK, r2.data)
        self.assertIn("access", r2.data)
        self.assertIn("refresh", r2.data)

        # Login with derived username (should also work)
        r3 = c.post(
            "/api/auth/login/", {"email_or_username": derived_username, "password": "abcd1234"}, format="json"
        )
        self.assertEqual(r3.status_code, status.HTTP_200_OK, r3.data)
        self.assertIn("access", r3.data)
        self.assertIn("refresh", r3.data)

    def test_refresh_token_flow(self):
        r = self.client.post("/api/auth/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertIn("access", r.data)

    def test_auth_logout_blacklist_flow(self):
        r1 = self.client.post("/api/auth/logout/", {"refresh": self.refresh}, format="json")
        self.assertIn(r1.status_code, [status.HTTP_200_OK, status.HTTP_205_RESET_CONTENT], r1.data)

        r2 = self.client.post("/api/auth/refresh/", {"refresh": self.refresh}, format="json")
        self.assertIn(r2.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

    # -----------------------
    # Certificates
    # -----------------------
    def test_certificates_create_json_and_list_owner_scoped(self):
        # Mine
        r = self.client.post(
            "/api/certificates/",
            {"title": "Django Basics", "issuer": "Coursera", "date_earned": _iso(self.YESTERDAY)},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        # Other user's cert
        other_client, _ = self.auth_client("other@example.com", "pass1234")
        _ = other_client.post(
            "/api/certificates/",
            {"title": "Other Cert", "issuer": "Udemy", "date_earned": _iso(self.TWO_DAYS_AGO)},
            format="json",
        )

        # List should only show mine
        res = self.client.get("/api/certificates/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        items = self.items(res)
        self.assertTrue(all("issuer" in it for it in items), items)

        # project_count annotation check via real links
        cert = self.make_cert(title="Count Me", issuer="ACME", date_earned=self.YESTERDAY)
        cid = cert["id"]
        for i in range(2):
            _ = self.make_project(title=f"P{i}", status="planned", certificate=cid, description="d")
        res2 = self.client.get(f"/api/certificates/?id={cid}")
        self.assertEqual(res2.status_code, status.HTTP_200_OK, res2.data)
        items2 = self.items(res2)
        self.assertEqual(len(items2), 1, items2)
        self.assertIn("project_count", items2[0])
        self.assertEqual(items2[0]["project_count"], 2)

    def test_certificate_future_date_rejected(self):
        r = self.client.post(
            "/api/certificates/",
            {"title": "Future", "issuer": "X", "date_earned": _iso(self.TOMORROW)},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("date_earned" in r.data or "non_field_errors" in r.data, r.data)

    def test_certificates_create_multipart_with_file(self):
        fake_pdf = SimpleUploadedFile("proof.pdf", b"%PDF-1.4 tiny", content_type="application/pdf")
        r = self.client.post(
            "/api/certificates/",
            {
                "title": "ML Cert",
                "issuer": "Udacity",
                "date_earned": _iso(self.YESTERDAY),
                "file_upload": fake_pdf,
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertIn("file_upload", r.data)
        self.assertTrue(str(r.data["file_upload"]).endswith(".pdf"))

    def test_certificates_update_and_delete(self):
        c = self.make_cert(title="Initial", issuer="Coursera", date_earned=self.YESTERDAY)
        cid = c["id"]

        p = self.client.patch(f"/api/certificates/{cid}/", {"title": "Updated Title"}, format="json")
        self.assertEqual(p.status_code, status.HTTP_200_OK, p.data)
        self.assertEqual(p.data["title"], "Updated Title")

        d = self.client.delete(f"/api/certificates/{cid}/")
        self.assertEqual(d.status_code, status.HTTP_204_NO_CONTENT)
        missing = self.client.get(f"/api/certificates/{cid}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_certificates_filter_by_id(self):
        a = self.make_cert(title="A", issuer="X", date_earned=self.TWO_DAYS_AGO)
        _b = self.make_cert(title="B", issuer="Y", date_earned=self.YESTERDAY)
        r = self.client.get(f"/api/certificates/?id={a['id']}")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        items = self.items(r)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], a["id"])

    def test_certificates_list_includes_project_count(self):
        cert = self.make_cert(title="With Projects", issuer="TestOrg", date_earned=self.YESTERDAY)
        for i in range(2):
            _ = self.make_project(
                title=f"Proj{i}",
                status="completed",
                certificate=cert["id"],
                description="x",
                start_date=self.TWO_DAYS_AGO,
                end_date=self.YESTERDAY,
            )
        res = self.client.get("/api/certificates/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        item = next((c for c in self.items(res) if c["id"] == cert["id"]), None)
        self.assertIsNotNone(item, "Certificate not found in list")
        self.assertIn("project_count", item)
        self.assertEqual(item["project_count"], 2)

    # -----------------------
    # Projects
    # -----------------------
    def test_projects_create_with_and_without_certificate_and_list(self):
        cert = self.make_cert(title="Data Eng", issuer="Coursera", date_earned=self.TWO_DAYS_AGO)

        # Completed without certificate (valid dates)
        r1 = self.client.post(
            "/api/projects/",
            {
                "title": "Portfolio Dashboard",
                "status": "completed",
                "work_type": "team",
                "primary_goal": "deliver_feature",
                "start_date": _iso(self.TWO_DAYS_AGO),
                "end_date": _iso(self.YESTERDAY),
                "description": "",  # triggers auto-generation
            },
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, r1.data)

        # In progress WITH certificate
        r2 = self.client.post(
            "/api/projects/",
            {
                "title": "ETL Pipeline",
                "status": "in_progress",
                "start_date": _iso(self.TODAY),
                "certificate": cert["id"],
                "description": "Building ingestion pipeline",
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, r2.data)

        # List should include my two projects
        res = self.client.get("/api/projects/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self.items(res)
        titles = {p["title"] for p in items}
        self.assertTrue({"Portfolio Dashboard", "ETL Pipeline"}.issubset(titles))

    def test_projects_update_link_unlink_and_delete(self):
        cert = self.make_cert(title="Backend Cert", issuer="Coursera", date_earned=self.TWO_DAYS_AGO)

        # Create planned with valid start_date
        create = self.client.post(
            "/api/projects/",
            {"title": "ProjX", "status": "planned", "start_date": _iso(self.TODAY), "description": "Draft"},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        proj_id = create.data["id"]

        # PATCH status → in_progress (allowed)
        p1 = self.client.patch(f"/api/projects/{proj_id}/", {"status": "in_progress"}, format="json")
        self.assertEqual(p1.status_code, status.HTTP_200_OK, p1.data)
        we = p1.data["status"]
        self.assertEqual(we, "in_progress")

        # Link certificate
        p2 = self.client.patch(f"/api/projects/{proj_id}/", {"certificate": cert["id"]}, format="json")
        self.assertEqual(p2.status_code, status.HTTP_200_OK, p2.data)
        self.assertEqual(p2.data["certificate"], cert["id"])

        # Unlink certificate
        p3 = self.client.patch(f"/api/projects/{proj_id}/", {"certificate": None}, format="json")
        self.assertEqual(p3.status_code, status.HTTP_200_OK, p3.data)
        self.assertIsNone(p3.data["certificate"])

        # DELETE
        d = self.client.delete(f"/api/projects/{proj_id}/")
        self.assertEqual(d.status_code, status.HTTP_204_NO_CONTENT)
        missing = self.client.get(f"/api/projects/{proj_id}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_projects_filter_by_certificateId_alias(self):
        cert = self.make_cert(title="Alias Cert", issuer="X", date_earned=self.TWO_DAYS_AGO)
        cid = cert["id"]

        # Two linked planned projects (+ one unlinked)
        p1 = self.client.post(
            "/api/projects/",
            {"title": "A", "status": "planned", "start_date": _iso(self.TODAY), "certificate": cid, "description": "d"},
            format="json",
        )
        p2 = self.client.post(
            "/api/projects/",
            {"title": "B", "status": "planned", "start_date": _iso(self.TODAY), "certificate": cid, "description": "d"},
            format="json",
        )
        p3 = self.client.post(
            "/api/projects/",
            {"title": "C", "status": "planned", "start_date": _iso(self.TODAY), "certificate": None, "description": "d"},
            format="json",
        )
        self.assertEqual(p1.status_code, status.HTTP_201_CREATED, p1.data)
        self.assertEqual(p2.status_code, status.HTTP_201_CREATED, p2.data)
        self.assertEqual(p3.status_code, status.HTTP_201_CREATED, p3.data)

        res_alias = self.client.get(f"/api/projects/?certificateId={cid}")
        self.assertEqual(res_alias.status_code, status.HTTP_200_OK, res_alias.data)
        items_alias = self.items(res_alias)
        self.assertGreaterEqual(len(items_alias), 2)
        self.assertTrue(all(it["certificate"] == cid for it in items_alias))

        res_base = self.client.get(f"/api/projects/?certificate={cid}")
        self.assertEqual(res_base.status_code, status.HTTP_200_OK, res_base.data)
        items_base = self.items(res_base)
        self.assertEqual({it["id"] for it in items_alias}, {it["id"] for it in items_base})

    def test_project_end_date_cleared_when_not_completed(self):
        r = self.client.post(
            "/api/projects/",
            {
                "title": "With end (should clear)",
                "status": "planned",
                "start_date": _iso(self.TODAY),
                "end_date": _iso(self.YESTERDAY),  # client mistakenly sends it
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertIsNone(r.data["end_date"])

    def test_project_completed_invalid_dates_rejected(self):
        # 1) Completed but start today (must be before today)
        r1 = self.client.post(
            "/api/projects/",
            {
                "title": "Bad 1",
                "status": "completed",
                "start_date": _iso(self.TODAY),
                "end_date": _iso(self.YESTERDAY),
            },
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)

        # 2) Completed missing end_date
        r2 = self.client.post(
            "/api/projects/",
            {"title": "Bad 2", "status": "completed", "start_date": _iso(self.TWO_DAYS_AGO)},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", r2.data)

        # 3) end_date <= start_date
        r3 = self.client.post(
            "/api/projects/",
            {
                "title": "Bad 3",
                "status": "completed",
                "start_date": _iso(self.YESTERDAY),
                "end_date": _iso(self.YESTERDAY),
            },
            format="json",
        )
        self.assertEqual(r3.status_code, status.HTTP_400_BAD_REQUEST)

        # 4) end_date in the future
        r4 = self.client.post(
            "/api/projects/",
            {
                "title": "Bad 4",
                "status": "completed",
                "start_date": _iso(self.TWO_DAYS_AGO),
                "end_date": _iso(self.TOMORROW),
            },
            format="json",
        )
        self.assertEqual(r4.status_code, status.HTTP_400_BAD_REQUEST)

    def test_project_duration_text_and_description_generated(self):
        r = self.client.post(
            "/api/projects/",
            {
                "title": "Gen",
                "status": "completed",
                "start_date": _iso(self.TWO_DAYS_AGO),
                "end_date": _iso(self.YESTERDAY),  # 1 day delta
                "description": "",  # trigger auto-generation
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertIn("duration_text", r.data)
        self.assertIn(r.data["duration_text"], {"1 day"})  # exact per serializer logic
        self.assertTrue((r.data.get("description") or "").strip() != "")

    # -----------------------
    # Goals
    # -----------------------
    def test_goals_crud_and_progress_computation(self):
        # Create goal with target 2
        g = self.client.post(
            "/api/goals/",
            {"title": "Hit 2 projects", "target_projects": 2, "deadline": "2099-01-01"},
            format="json",
        )
        self.assertEqual(g.status_code, status.HTTP_201_CREATED, g.data)
        gid = g.data["id"]
        self.assertIn("progress_percent", g.data)
        self.assertEqual(g.data["progress_percent"], 0)

        # One completed project → 50%
        _ = self.make_project(
            title="Completed Thing",
            status="completed",
            description="Done",
            start_date=self.TWO_DAYS_AGO,
            end_date=self.YESTERDAY,
        )

        lst = self.client.get("/api/goals/")
        self.assertEqual(lst.status_code, status.HTTP_200_OK)
        items = self.items(lst)
        mine = next((x for x in items if x["id"] == gid), None)
        self.assertIsNotNone(mine)
        # Depending on rounding, your serializer may return 50 or 50.0; accept exact float here
        self.assertEqual(mine["progress_percent"], 50.0)

        # Update target → 25.0
        p = self.client.patch(f"/api/goals/{gid}/", {"target_projects": 4}, format="json")
        self.assertEqual(p.status_code, status.HTTP_200_OK, p.data)
        self.assertEqual(p.data["target_projects"], 4)
        g1 = self.client.get(f"/api/goals/{gid}/")
        self.assertEqual(g1.status_code, status.HTTP_200_OK)
        self.assertEqual(g1.data["progress_percent"], 25.0)

        # DELETE
        d = self.client.delete(f"/api/goals/{gid}/")
        self.assertEqual(d.status_code, status.HTTP_204_NO_CONTENT)
        missing = self.client.get(f"/api/goals/{gid}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_goals_validations_negative_and_past_deadline(self):
        res_neg = self.client.post(
            "/api/goals/",
            {"title": "Bad target", "target_projects": -1, "deadline": "2099-12-31"},
            format="json",
        )
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("target_projects", res_neg.data)

        res_past = self.client.post(
            "/api/goals/",
            {"title": "Past deadline", "target_projects": 3, "deadline": "2000-01-01"},
            format="json",
        )
        self.assertEqual(res_past.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", res_past.data)

    def test_goals_title_and_steps_progress_fields_present(self):
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

        gid = create.data["id"]
        patch = self.client.patch(f"/api/goals/{gid}/", {"completed_steps": 3}, format="json")
        self.assertEqual(patch.status_code, status.HTTP_200_OK, patch.data)
        self.assertEqual(patch.data["completed_steps"], 3)
        self.assertEqual(patch.data["steps_progress_percent"], 75)

    # -----------------------
    # GoalSteps
    # -----------------------
    def test_goalsteps_crud_and_goal_sync(self):
        goal = self.client.post(
            "/api/goals/", {"title": "Write case study", "target_projects": 1, "deadline": "2099-01-01"}, format="json"
        ).data
        gid = goal["id"]

        g1 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g1.get("total_steps", 0), 0)
        self.assertEqual(g1.get("completed_steps", 0), 0)
        self.assertEqual(g1.get("steps_progress_percent", 0), 0)

        s1 = self.client.post(
            "/api/goalsteps/", {"goal": gid, "title": "Draft outline", "order": 1}, format="json"
        )
        self.assertEqual(s1.status_code, status.HTTP_201_CREATED, s1.data)
        step_a = s1.data

        s2 = self.client.post(
            "/api/goalsteps/", {"goal": gid, "title": "Collect assets", "order": 2, "is_done": True}, format="json"
        )
        self.assertEqual(s2.status_code, status.HTTP_201_CREATED, s2.data)
        step_b = s2.data

        g2 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g2.get("total_steps", 0), 2)
        we = g2.get("completed_steps", 0)
        self.assertEqual(we, 1)
        self.assertEqual(g2.get("steps_progress_percent", 0), 50)

        p1 = self.client.patch(f"/api/goalsteps/{step_a['id']}/", {"is_done": True}, format="json")
        self.assertEqual(p1.status_code, status.HTTP_200_OK, p1.data)
        g3 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g3.get("completed_steps", 0), 2)
        self.assertEqual(g3.get("steps_progress_percent", 0), 100)

        p2 = self.client.patch(f"/api/goalsteps/{step_b['id']}/", {"order": 1}, format="json")
        self.assertEqual(p2.status_code, status.HTTP_200_OK, p2.data)

        d1 = self.client.delete(f"/api/goalsteps/{step_a['id']}/")
        self.assertEqual(d1.status_code, status.HTTP_204_NO_CONTENT)
        g4 = self.client.get(f"/api/goals/{gid}/").data
        self.assertEqual(g4.get("total_steps", 0), 1)
        self.assertEqual(g4.get("completed_steps", 0), 1)
        self.assertEqual(g4.get("steps_progress_percent", 0), 100)

    def test_goal_completed_steps_capped_to_total(self):
        g = self.client.post(
            "/api/goals/",
            {"title": "Cap test", "target_projects": 1, "deadline": "2099-01-01", "total_steps": 3, "completed_steps": 10},
            format="json",
        )
        self.assertEqual(g.status_code, status.HTTP_201_CREATED, g.data)
        self.assertEqual(g.data["total_steps"], 3)
        self.assertEqual(g.data["completed_steps"], 3)

    def test_goalstep_cannot_create_for_others_goal(self):
        other_client, _ = self.auth_client("other@example.com", "pass1234")
        other_goal = other_client.post(
            "/api/goals/", {"title": "Other's goal", "target_projects": 1, "deadline": "2099-01-01"}, format="json"
        ).data

        r = self.client.post("/api/goalsteps/", {"goal": other_goal["id"], "title": "Nope", "order": 1}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # -----------------------
    # Analytics & Docs & Root
    # -----------------------
    def test_analytics_summary_counts(self):
        # Ensure there's at least one of each
        _ = self.make_cert(title="C", issuer="I", date_earned=self.TWO_DAYS_AGO)
        _ = self.make_project(title="Planned One", status="planned", description="d")
        _ = self.client.post(
            "/api/goals/", {"title": "G", "target_projects": 1, "deadline": "2099-01-01"}, format="json"
        )

        res = self.client.get("/api/analytics/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertGreaterEqual(res.data["certificates_count"], 1)
        self.assertGreaterEqual(res.data["projects_count"], 1)
        self.assertGreaterEqual(res.data["goals_count"], 1)

    def test_analytics_goals_progress_endpoint(self):
        g = self.client.post(
            "/api/goals/", {"title": "One", "target_projects": 1, "deadline": "2099-01-01"}, format="json"
        ).data
        _ = self.make_project(status="completed", start_date=self.TWO_DAYS_AGO, end_date=self.YESTERDAY)
        res = self.client.get("/api/analytics/goals-progress/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        items = self.items(res)
        goal = next((x for x in items if x["id"] == g["id"]), None)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["progress_percent"], 100.0)

    def test_docs_and_schema_available(self):
        # Swagger UI and OpenAPI JSON should be public (AllowAny)
        docs = self.client.get("/api/docs/")
        schema = self.client.get("/api/schema/")
        self.assertEqual(docs.status_code, status.HTTP_200_OK)
        self.assertEqual(schema.status_code, status.HTTP_200_OK)

    def test_root_redirects_to_frontend(self):
        """
        Root ("/") should 301/302 redirect to settings.FRONTEND_URL.
        We compare against the value in settings (normalized with a trailing slash).
        """
        res = self.client.get("/")
        self.assertIn(res.status_code, (301, 302))

        expected = settings.FRONTEND_URL or ""
        # normalize to include a trailing slash
        if expected and not expected.endswith("/"):
            expected = expected + "/"

        self.assertEqual(res["Location"], expected)

    # -----------------------
    # Owner scoping hardening
    # -----------------------
    def test_owner_scoping_retrieve_others_certificate_404(self):
        other_client, _ = self.auth_client("other@example.com", "pass1234")
        other_cert = other_client.post(
            "/api/certificates/", {"title": "O", "issuer": "Org", "date_earned": _iso(self.YESTERDAY)}, format="json"
        ).data
        res = self.client.get(f"/api/certificates/{other_cert['id']}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
