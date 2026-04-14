"""
Posts content to LinkedIn and Threads via their respective APIs.
"""

import os
import time

import requests


def post_to_linkedin(content: str) -> dict:
    """
    Publish a text post to LinkedIn using the UGC Posts API.
    Requires env vars: LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID
    """
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_id = os.getenv("LINKEDIN_PERSON_ID")

    if not access_token or not person_id:
        raise ValueError(
            "LinkedIn credentials missing. Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID in .env"
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def post_to_threads(content: str) -> dict:
    """
    Publish a text post to Threads using the Threads Graph API.
    Requires env vars: THREADS_ACCESS_TOKEN, THREADS_USER_ID

    Two-step process: create container → publish.
    """
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    user_id = os.getenv("THREADS_USER_ID")

    if not access_token or not user_id:
        raise ValueError(
            "Threads credentials missing. Set THREADS_ACCESS_TOKEN and THREADS_USER_ID in .env"
        )

    base_url = f"https://graph.threads.net/v1.0/{user_id}"

    # Step 1: Create media container
    response = requests.post(
        f"{base_url}/threads",
        params={
            "media_type": "TEXT",
            "text": content,
            "access_token": access_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    container_id = response.json()["id"]

    # Step 2: Wait for container to be ready, then publish
    time.sleep(5)

    response = requests.post(
        f"{base_url}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
