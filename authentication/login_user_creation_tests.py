import pytest
from rest_framework.test import APIRequestFactory

from applications.models import Application
from authentication.models import OTP
from authentication.models import User
from authentication.services import UserCreationService
from authentication.views import ForgotPasswordView
from authentication.views import LoginView


@pytest.mark.django_db
def test_login_accepts_case_insensitive_email_with_whitespace(monkeypatch):
    password = "MemberLogin#123"
    user = User.objects.create_user(email="Member.User@example.com", password=password)

    # Avoid SMTP dependency during test.
    monkeypatch.setattr(
        "authentication.views.EmailService.send_otp_email",
        lambda *args, **kwargs: True,
    )

    request = APIRequestFactory().post(
        "/api/v1/auth/login/",
        {
            "email": "  member.user@EXAMPLE.com  ",
            "password": password,
        },
        format="json",
    )

    response = LoginView.as_view()(request)

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["email"] == user.email
    assert "session_id" in response.data


@pytest.mark.django_db
def test_login_recovers_user_from_approved_application(monkeypatch):
    email = "fresh.approved.member@example.com"
    app_password = "FreshMember#123"

    application = Application.objects.create(
        username="fresh_member",
        email=email,
        password_hash=app_password,
        first_name="Fresh",
        last_name="Member",
        age_range=Application.AGE_RANGE_CHOICES[0][0],
        phone_number="256774000001",
        address="Kampala",
        payment_method="mtn",
        status="approved",
    )

    monkeypatch.setattr(
        "authentication.views.EmailService.send_otp_email",
        lambda *args, **kwargs: True,
    )

    request = APIRequestFactory().post(
        "/api/v1/auth/login/",
        {
            "email": email,
            "password": app_password,
        },
        format="json",
    )

    response = LoginView.as_view()(request)
    application.refresh_from_db()

    assert response.status_code == 200
    assert response.data["success"] is True
    assert "session_id" in response.data
    assert application.user_id is not None


@pytest.mark.django_db
def test_reactivated_user_password_is_synced_from_latest_approved_application():
    old_password = "OldPassword#123"
    new_password = "NewPassword#456"

    existing_user = User.objects.create_user(
        email="member@example.com",
        password=old_password,
        is_active=False,
        first_name="Old",
        last_name="Member",
    )

    application = Application.objects.create(
        username="member_new",
        email="MEMBER@example.com",
        password_hash=new_password,
        first_name="New",
        last_name="Member",
        age_range=Application.AGE_RANGE_CHOICES[0][0],
        phone_number="256774000001",
        address="Kampala",
        payment_method="mtn",
        status="approved",
    )

    user, error = UserCreationService.create_user_from_application(application)

    assert error is None
    assert user is not None
    assert user.id == existing_user.id

    user.refresh_from_db()
    application.refresh_from_db()

    assert user.is_active is True
    assert user.check_password(new_password) is True
    assert application.user_id == user.id


@pytest.mark.django_db
def test_forgot_password_recovers_user_from_approved_application(monkeypatch):
    email = "recover.member@example.com"
    app_password = "RecoveredPass#123"

    application = Application.objects.create(
        username="recover_member",
        email=email,
        password_hash=app_password,
        first_name="Recover",
        last_name="Member",
        age_range=Application.AGE_RANGE_CHOICES[0][0],
        phone_number="256774000001",
        address="Kampala",
        payment_method="mtn",
        status="approved",
    )

    monkeypatch.setattr(
        "authentication.views.EmailService.send_password_reset_email",
        lambda *args, **kwargs: True,
    )

    request = APIRequestFactory().post(
        "/api/v1/auth/forgot-password/",
        {"email": email},
        format="json",
    )

    response = ForgotPasswordView.as_view()(request)
    application.refresh_from_db()

    assert response.status_code == 200
    assert response.data["success"] is True
    assert "session_id" in response.data
    assert application.user_id is not None
    assert OTP.objects.filter(session_id=response.data["session_id"]).exists()
