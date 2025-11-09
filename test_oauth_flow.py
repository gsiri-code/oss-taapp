# #!/usr/bin/env python3
# """Simple script to test the OAuth flow.

# This script helps verify that the OAuth flow is working correctly.
# Run it after starting the FastAPI service.
# """

# import sys
# from pathlib import Path

# import requests

# # Add src directories to path
# project_root = Path(__file__).parent
# sys.path.insert(0, str(project_root / "src" / "task_client_service" / "src"))
# sys.path.insert(0, str(project_root / "src" / "gtask_client_impl" / "src"))


# def test_oauth_flow(base_url: str = "http://localhost:8001") -> None:
#     """Test the OAuth flow endpoints."""
#     session = requests.Session()

#     print("=" * 60)
#     print("Testing OAuth Flow")
#     print("=" * 60)

#     # Test 1: Check if service is running
#     print("\n1. Checking if service is running...")
#     try:
#         response = session.get(f"{base_url}/docs", timeout=5)
#         if response.status_code == 200:
#             print("   ✓ Service is running")
#         else:
#             print(f"   ✗ Service returned status {response.status_code}")
#             return
#     except requests.exceptions.ConnectionError:
#         print(f"   ✗ Cannot connect to {base_url}")
#         print("   Make sure the service is running:")
#         print("   uv run uvicorn task_client_service.fast_api_service:app --reload --port 8001")
#         return
#     except Exception as e:
#         print(f"   ✗ Error: {e}")
#         return

#     # Test 2: Check login endpoint
#     print("\n2. Testing /auth/login endpoint...")
#     try:
#         response = session.get(f"{base_url}/auth/login", allow_redirects=False, timeout=5)
#         if response.status_code == 307:  # Temporary redirect
#             redirect_url = response.headers.get("Location", "")
#             if "accounts.google.com" in redirect_url:
#                 print("   ✓ Login endpoint redirects to Google OAuth")
#                 print(f"   Redirect URL: {redirect_url[:80]}...")
#             else:
#                 print(f"   ⚠ Unexpected redirect: {redirect_url}")
#         else:
#             print(f"   ✗ Unexpected status code: {response.status_code}")
#     except Exception as e:
#         print(f"   ✗ Error: {e}")

#     # Test 3: Check if credentials endpoint exists (should fail without auth)
#     print("\n3. Testing /auth/_give_session_creds endpoint (should fail without auth)...")
#     try:
#         response = session.get(f"{base_url}/auth/_give_session_creds", timeout=5)
#         if response.status_code == 401:
#             print("   ✓ Endpoint exists and correctly returns 401 when not authenticated")
#         elif response.status_code == 200:
#             print("   ✓ Credentials found in session!")
#             creds = response.json()
#             print(f"   Token: {creds.get('token', 'None')[:30]}...")
#         else:
#             print(f"   ⚠ Unexpected status code: {response.status_code}")
#     except Exception as e:
#         print(f"   ✗ Error: {e}")

#     # Test 4: Check callback endpoint exists
#     print("\n4. Testing /auth/callback endpoint...")
#     try:
#         # Without a code, it should fail gracefully
#         response = session.get(f"{base_url}/auth/callback", timeout=5)
#         if response.status_code in (400, 500):
#             print("   ✓ Callback endpoint exists (fails without auth code as expected)")
#         else:
#             print(f"   ⚠ Unexpected status code: {response.status_code}")
#     except Exception as e:
#         print(f"   ✗ Error: {e}")

#     # Test 5: Check if credentials.json exists
#     print("\n5. Checking for credentials.json...")
#     creds_file = project_root / "credentials.json"
#     if creds_file.exists():
#         print(f"   ✓ Found credentials.json at {creds_file}")
#     else:
#         print(f"   ✗ credentials.json not found at {creds_file}")
#         print("   You need to download OAuth credentials from Google Cloud Console")

#     print("\n" + "=" * 60)
#     print("Manual Testing Steps:")
#     print("=" * 60)
#     print("1. Open your browser and go to:")
#     print(f"   {base_url}/auth/login")
#     print("\n2. Complete the Google OAuth flow in your browser")
#     print("\n3. After authentication, run this script again to verify credentials")
#     print("\n4. Or test with curl:")
#     print(f"   curl -v -c cookies.txt -b cookies.txt {base_url}/auth/_give_session_creds")
#     print("=" * 60)


# if __name__ == "__main__":
#     import argparse

#     parser = argparse.ArgumentParser(description="Test OAuth flow")
#     parser.add_argument(
#         "--base-url",
#         default="http://localhost:8001",
#         help="Base URL of the FastAPI service (default: http://localhost:8001)",
#     )
#     args = parser.parse_args()

#     test_oauth_flow(args.base_url)
