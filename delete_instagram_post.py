import argparse
import os

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--post_id", required=True)
    args = parser.parse_args()

    base_url = os.environ.get("PAGES_BASE_URL", "").rstrip("/")
    admin_pass = os.environ.get("ADMIN_PASS", "")
    if not base_url or not admin_pass:
        raise RuntimeError("PAGES_BASE_URL and ADMIN_PASS are required.")

    res = requests.post(
        f"{base_url}/api/delete-instagram-post",
        json={"post_id": args.post_id},
        headers={"X-Admin-Password": admin_pass},
        timeout=60,
    )
    print(f"[delete] response: {res.status_code} {res.text}")
    res.raise_for_status()


if __name__ == "__main__":
    main()
