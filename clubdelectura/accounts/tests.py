from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class CustomUserManagerTests(TestCase):
    def test_create_user_normalizes_email_and_sets_password(self):
        user = CustomUser.objects.create_user(
            email="Jane.Doe@Example.com",
            password="s3cret-pass",
            first_name="Jane",
            last_name="Doe",
        )

        self.assertEqual(user.email, "Jane.Doe@example.com")
        self.assertTrue(user.check_password("s3cret-pass"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email=None, password="x", first_name="A", last_name="B"
            )

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="s3cret-pass",
            first_name="Admin",
            last_name="User",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class CustomUserModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="reader@example.com",
            password="password123",
            first_name="Book",
            last_name="Worm",
        )

    def test_str_returns_full_name(self):
        self.assertEqual(str(self.user), "Book Worm")

    def test_get_full_name(self):
        self.assertEqual(self.user.get_full_name(), "Book Worm")

    def test_get_short_name(self):
        self.assertEqual(self.user.get_short_name(), "Book")

    def test_email_is_the_username_field(self):
        self.assertEqual(CustomUser.USERNAME_FIELD, "email")
        self.assertEqual(CustomUser.objects.get(email="reader@example.com"), self.user)


class SignUpViewTests(TestCase):
    def test_get_renders_signup_form(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)

    def test_post_creates_user_and_redirects(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "newreader@example.com",
                "first_name": "New",
                "last_name": "Reader",
                "password1": "a-strong-password-1",
                "password2": "a-strong-password-1",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CustomUser.objects.filter(email="newreader@example.com").exists()
        )

    def test_authenticated_user_is_redirected_away_from_signup(self):
        user = CustomUser.objects.create_user(
            email="already@example.com",
            password="password123",
            first_name="Already",
            last_name="In",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:signup"))
        self.assertRedirects(response, reverse("index"))


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="login@example.com",
            password="password123",
            first_name="Log",
            last_name="In",
        )

    def test_get_renders_login_form_for_anonymous_user(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_post_with_valid_credentials_logs_in(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "login@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.user.pk
        )

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("index"))
