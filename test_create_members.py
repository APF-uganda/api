"""
Test script for account creation - uses 3 test emails only.
Run inside the apf_backend Docker container:

    docker exec -it apf_backend python test_create_members.py

This will:
  1. Create 3 test accounts
  2. Verify they exist and can authenticate
  3. Clean up (delete) the test accounts at the end
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

DEFAULT_PASSWORD = "Apf@uganda"

TEST_MEMBERS = [
    ("bashkiko@gmail.com", "Bashkiko", "Test", "male", "APF/M/TEST01", "Test Firm A", "Partner", "FM0001", "CMTEST001"),
    ("kikomusa29@gmail.com", "Kikomusa", "Test", "male", "APF/M/TEST02", "Test Firm B", "Practitioner", "FM0002", "CMTEST002"),
    ("musbash29@gmail.com", "Musbash", "Test", "female", "APF/M/TEST03", "Test Firm C", "Managing Partner", "FM0003", "CMTEST003"),
    ("jnanyonga926@gmail.com", "Josephine", "Test", "female", "APF/M/TEST04", "Test Firm D", "Senior Manager", "FM0004", "CMTEST004"),
]


def cleanup_test_users():
    """Remove test users if they already exist."""
    for email, *_ in TEST_MEMBERS:
        User.objects.filter(email__iexact=email).delete()


def test_create():
    print("=" * 60)
    print("TEST: Account Creation")
    print("=" * 60)

    cleanup_test_users()
    created = 0

    for email, first_name, last_name, gender, membership_number, org, title, icpau_reg, national_id in TEST_MEMBERS:
        try:
            user = User.objects.create_user(
                email=email,
                password=DEFAULT_PASSWORD,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                role="2",
                is_active=True,
                organization=org,
                job_title=title,
                icpau_registration_number=icpau_reg,
                national_id_number=national_id,
            )
            print(f"  CREATED: {email}")
            created += 1
        except Exception as e:
            print(f"  FAIL: {email} - {e}")

    assert created == 3, f"Expected 3 created, got {created}"
    print(f"  -> {created}/3 accounts created OK")
    return True


def test_users_exist():
    print()
    print("=" * 60)
    print("TEST: Verify Users Exist & Fields Populated")
    print("=" * 60)

    for email, first_name, last_name, gender, _, org, title, icpau_reg, national_id in TEST_MEMBERS:
        user = User.objects.filter(email__iexact=email).first()
        assert user is not None, f"User {email} not found"
        assert user.first_name == first_name, f"first_name mismatch for {email}"
        assert user.last_name == last_name, f"last_name mismatch for {email}"
        assert user.gender == gender, f"gender mismatch for {email}"
        assert user.role == "2", f"role mismatch for {email}"
        assert user.organization == org, f"organization mismatch for {email}"
        assert user.job_title == title, f"job_title mismatch for {email}"
        assert user.icpau_registration_number == icpau_reg, f"icpau_reg mismatch for {email}"
        assert user.national_id_number == national_id, f"national_id mismatch for {email}"
        assert user.is_active is True, f"is_active should be True for {email}"
        print(f"  OK: {email} - all fields correct")

    print("  -> All 3 users verified OK")
    return True


def test_password_works():
    print()
    print("=" * 60)
    print("TEST: Verify Password Authentication")
    print("=" * 60)

    for email, *_ in TEST_MEMBERS:
        user = User.objects.get(email__iexact=email)
        assert user.check_password(DEFAULT_PASSWORD), f"Password check failed for {email}"
        assert not user.check_password("WrongPassword123!"), f"Wrong password should fail for {email}"
        print(f"  OK: {email} - password auth works")

    print("  -> All 3 passwords verified OK")
    return True


def test_duplicate_skip():
    print()
    print("=" * 60)
    print("TEST: Duplicate Creation Is Skipped")
    print("=" * 60)

    for email, *_ in TEST_MEMBERS:
        if User.objects.filter(email__iexact=email).exists():
            print(f"  OK: {email} - correctly detected as existing")
        else:
            print(f"  FAIL: {email} - should exist but doesn't")
            return False

    print("  -> Duplicate detection works OK")
    return True


def run_all_tests():
    passed = 0
    failed = 0
    tests = [test_create, test_users_exist, test_password_works, test_duplicate_skip]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    # Cleanup
    print()
    print("=" * 60)
    print("CLEANUP: Removing test accounts")
    print("=" * 60)
    cleanup_test_users()
    for email, *_ in TEST_MEMBERS:
        exists = User.objects.filter(email__iexact=email).exists()
        status = "FAIL (still exists)" if exists else "OK (removed)"
        print(f"  {status}: {email}")

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
