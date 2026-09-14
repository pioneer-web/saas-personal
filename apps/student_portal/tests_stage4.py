
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.organizations.models import Organization
from apps.students.models import Student

from .models import (
    StudentAccount,
    StudentApiToken,
    StudentNotification,
)


User = get_user_model()


class StudentStage4ApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Personal Teste",
            slug="personal-teste-stage4",
        )
        self.student = Student.objects.create(
            organization=self.organization,
            name="Aluno Teste",
            email="aluno-stage4@example.com",
            phone="87999999999",
        )
        self.user = User.objects.create_user(
            email="aluno-stage4@example.com",
            password="SenhaForte123!",
            name="Aluno Teste",
        )
        self.account = StudentAccount.objects.create(
            organization=self.organization,
            student=self.student,
            user=self.user,
        )

        self.plain_token = "stage4-test-token"
        StudentApiToken.objects.create(
            account=self.account,
            token_hash=StudentApiToken.hash_token(
                self.plain_token
            ),
            expires_at=timezone.now()
            + timedelta(days=1),
        )
        self.headers = {
            "HTTP_AUTHORIZATION":
            f"Bearer {self.plain_token}",
        }

    def test_profile_is_scoped_to_student(self):
        response = self.client.get(
            "/api/student/profile/",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["student"]["name"],
            self.student.name,
        )
        self.assertEqual(
            payload["organization"]["name"],
            self.organization.name,
        )

    def test_notification_can_be_marked_read(self):
        notification = StudentNotification.objects.create(
            organization=self.organization,
            student=self.student,
            title="Teste",
            body="Mensagem de teste",
        )

        response = self.client.get(
            "/api/student/notifications/",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["unread_count"],
            1,
        )

        response = self.client.post(
            "/api/student/notifications/",
            data={
                "action": "mark_read",
                "notification_id": str(
                    notification.pk
                ),
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_notification_from_other_tenant_is_hidden(self):
        other_organization = Organization.objects.create(
            name="Outro Personal",
            slug="outro-personal-stage4",
        )
        other_student = Student.objects.create(
            organization=other_organization,
            name="Outro Aluno",
            email="outro-stage4@example.com",
        )
        notification = StudentNotification.objects.create(
            organization=other_organization,
            student=other_student,
            title="Privada",
            body="Não pode aparecer.",
        )

        response = self.client.post(
            "/api/student/notifications/",
            data={
                "action": "mark_read",
                "notification_id": str(
                    notification.pk
                ),
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertIsNone(notification.read_at)

    def test_api_rejects_missing_token(self):
        response = self.client.get(
            "/api/student/notifications/",
        )
        self.assertEqual(response.status_code, 401)
