import urllib.request
import urllib.error
import json
from sqlalchemy import create_engine, text
from app.config import settings

BASE_URL = "http://127.0.0.1:8001"

def run_test():
    print("--- STARTING AUTHENTICATION FLOW VERIFICATION ---")

    # Clean up test user if it already exists
    username = "auth_test_user_unique"
    email = "auth_test_user_unique@example.com"
    password = "SuperSecurePassword123!"

    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM users WHERE username = :u OR email = :e"), {"u": username, "e": email})
        conn.commit()
    print("1. Cleaned up any old test users.")

    # A. Register a test user
    register_data = {
        "username": username,
        "email": email,
        "password": password,
        "name": "Auth Test User"
    }
    
    req = urllib.request.Request(
        f"{BASE_URL}/auth/register",
        data=json.dumps(register_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            reg_resp = json.loads(resp.read().decode())
            print("2. Registration request successful.")
            print("Response:", reg_resp)
    except urllib.error.HTTPError as e:
        print("Registration failed with status code:", e.code)
        print("Detail:", e.read().decode())
        return

    # C. Verify password/password_hash is not returned in the API response
    assert "password" not in reg_resp, "password was returned in API response"
    assert "password_hash" not in reg_resp, "password_hash was returned in API response"
    print("3. Verified neither 'password' nor 'password_hash' is in the registration response.")

    # B. Verify the password is hashed in PostgreSQL
    with engine.connect() as conn:
        res = conn.execute(text("SELECT password_hash FROM users WHERE username = :u"), {"u": username}).fetchone()
        assert res is not None, "Test user not found in database"
        pwd_hash = res[0]
        assert pwd_hash != password, "Password was stored in plain text!"
        assert pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$"), f"Password hash doesn't look like bcrypt: {pwd_hash}"
        print("4. Verified password is hashed in PostgreSQL using bcrypt (starts with $2b$).")

    # D. Login using the test user
    # E. Verify a JWT access token is returned
    login_data = {
        "username": username,
        "password": password
    }
    req = urllib.request.Request(
        f"{BASE_URL}/auth/login",
        data=json.dumps(login_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            login_resp = json.loads(resp.read().decode())
            print("5. Login successful.")
            print("Response:", login_resp)
            assert "access_token" in login_resp, "Access token not found in login response"
            assert login_resp["token_type"] == "bearer", "Token type is not bearer"
            token = login_resp["access_token"]
            print("6. Verified JWT access token is returned with token_type='bearer'.")
    except urllib.error.HTTPError as e:
        print("Login failed with status code:", e.code)
        print("Detail:", e.read().decode())
        return

    # F. Use the JWT to call /auth/me
    # G. Verify /auth/me returns the authenticated user
    req = urllib.request.Request(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            me_resp = json.loads(resp.read().decode())
            print("7. /auth/me request successful.")
            print("Response:", me_resp)
            assert me_resp["username"] == username, "Returned username does not match"
            assert me_resp["email"] == email, "Returned email does not match"
            assert "password" not in me_resp, "password returned in /auth/me"
            assert "password_hash" not in me_resp, "password_hash returned in /auth/me"
            print("8. Verified /auth/me returns the correct authenticated user details without credentials.")
    except urllib.error.HTTPError as e:
        print("/auth/me failed with status code:", e.code)
        print("Detail:", e.read().decode())
        return

    # H. Call /auth/me without a token and verify it returns 401
    req = urllib.request.Request(
        f"{BASE_URL}/auth/me",
        method="GET"
    )
    try:
        urllib.request.urlopen(req)
        print("ERROR: /auth/me succeeded without a token!")
        return
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401 unauthorized without token, got {e.code}"
        print("9. Verified calling /auth/me without a token correctly returns 401.")

    # I. Call /auth/me with an invalid token and verify it returns 401
    req = urllib.request.Request(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": "Bearer invalidtoken123"},
        method="GET"
    )
    try:
        urllib.request.urlopen(req)
        print("ERROR: /auth/me succeeded with invalid token!")
        return
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401 unauthorized with invalid token, got {e.code}"
        print("10. Verified calling /auth/me with an invalid token correctly returns 401.")

    # J. Verify incorrect login credentials are rejected
    bad_login_data = {
        "username": username,
        "password": "wrongpassword"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/auth/login",
        data=json.dumps(bad_login_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req)
        print("ERROR: Login succeeded with incorrect password!")
        return
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401 unauthorized for wrong password, got {e.code}"
        print("11. Verified incorrect login credentials are rejected with 401.")

    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_test()
