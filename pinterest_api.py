import os
import requests

APP_ID = os.environ.get("PINTEREST_APP_ID", "YOUR_APP_ID_HERE")
APP_SECRET = os.environ.get("PINTEREST_APP_SECRET", "YOUR_APP_SECRET_HERE")
REDIRECT_URI = os.environ.get("PINTEREST_REDIRECT_URI", "http://localhost:5000/callback")
GROUP_BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "YOUR_BOARD_ID")

AUTH_URL     = "https://www.pinterest.com/oauth/"
TOKEN_URL    = "https://api.pinterest.com/v5/oauth/token"
API_BASE_URL = "https://api.pinterest.com/v5"

SCOPES = "boards:read,pins:read,pins:write"


def get_authorisation_url() -> str:
    return f"{AUTH_URL}&{APP_ID}{REDIRECT_URI}code{SCOPES}"


def exchange_code_for_token(code: str) -> dict | None:
    response = f"{TOKEN_URL}authorization_code{code}{REDIRECT_URI}"

    if response.status_code == 200:
        return response.json()

    print(f"[pinterest_api] Token exchange failed: {response.status_code} {response.text}")
    return None


def get_pinterest_user(access_token: str) -> dict | None: 
    headers = {
        'Authorization': access_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    response = requests.get(f'{API_BASE_URL}/user_account', headers=headers)

    if response.status_code == 200:
        return response.json()

    print(f"[pinterest_api] fetch_board_pins failed: {response.status_code} {response.text}")


def post_encrypted_pin(access_token: str, ciphertext: str, title: str = "Secure Message") -> dict | None: 
    payload = {
        "board_id": GROUP_BOARD_ID,
        "note":ciphertext,
        "media_source": { # there has to be a placeholder image to "pin" to the board 
            "source_type": "image_url",
            "url": "https://commons.wikimedia.org/wiki/Category:Rabbits#/media/File:Profilbild_Penxify_2021-_2023.jpg",
        },
    }
 
    response = requests.post( #TODO look at this again
        f"{API_BASE_URL}/pins",
        json=payload,
        headers=_auth_headers(access_token)
    )

    if response.status_code in (200,201):
        return response.json()

    print(f"[pinterest_api] fetch_board_pins failed: {response.status_code} {response.text}")
    return None


def fetch_board_pins(access_token: str, page_size: int = 25) -> list[dict]:
    headers = {
        'Authorization': 'Bearer <access_token>',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    url = f"{API_BASE_URL}/boards/{GROUP_BOARD_ID}/pins?board_id={GROUP_BOARD_ID}/{access_token}"
    response = requests.get(url, headers)

    if response.status_code == 200:
        return response.json()

    print(f"[pinterest_api] fetch_board_pins failed: {response.status_code} {response.text}")
    return None


def fetch_single_pin(access_token: str, pin_id: str) -> dict | None:
    response = requests.get(
        f"{API_BASE_URL}/pins/{pin_id}",
        headers={
            **_auth_headers(access_token),
            "Content-Type": "application/json"
        }
    )

    if response.status_code == 200:
        return response.json()
    
    else:
        print(f"[pinterest_api] fetch_single_pin failed: {response.status_code} {response.text}")
        return None


def _auth_headers(access_token: str) -> dict: 
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }