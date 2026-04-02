"""
Thin wrapper around the Threads API.

Threads publishing is a two-step process:
  1. Create a media container  → returns creation_id
  2. Publish the container     → returns post id

Docs: https://developers.facebook.com/docs/threads/posts
"""

import logging
import os
import time

import requests

log = logging.getLogger("beingvortex.threads")

BASE_URL = "https://graph.threads.net/v1.0"
PUBLISH_DELAY_SECS = 5  # Threads recommends a small pause between steps


class ThreadsClient:
    def __init__(self):
        self.access_token = os.environ["THREADS_ACCESS_TOKEN"]
        self.user_id = os.environ["THREADS_USER_ID"]

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def publish_text(self, text: str) -> str | None:
        """
        Create and publish a plain-text Threads post.
        Returns the post ID on success, None on failure.
        """
        creation_id = self._create_container(text)
        if not creation_id:
            return None

        time.sleep(PUBLISH_DELAY_SECS)
        return self._publish_container(creation_id)

    def whoami(self) -> dict:
        """Return basic profile info — useful to verify credentials."""
        return self._get("me", {"fields": "id,username,name"})

    # ------------------------------------------------------------------ #
    #  Private                                                             #
    # ------------------------------------------------------------------ #

    def _create_container(self, text: str) -> str | None:
        """Step 1: create a media container. Returns creation_id or None."""
        try:
            data = self._post(
                f"{self.user_id}/threads",
                {"media_type": "TEXT", "text": text},
            )
            creation_id = data.get("id")
            log.debug(f"Container created: {creation_id}")
            return creation_id
        except requests.HTTPError as exc:
            log.error(
                f"Failed to create Threads container: "
                f"{exc.response.status_code} — {exc.response.text}"
            )
            return None

    def _publish_container(self, creation_id: str) -> str | None:
        """Step 2: publish the container. Returns post ID or None."""
        try:
            data = self._post(
                f"{self.user_id}/threads/publish",
                {"creation_id": creation_id},
            )
            post_id = data.get("id")
            log.debug(f"Published post: {post_id}")
            return post_id
        except requests.HTTPError as exc:
            log.error(
                f"Failed to publish Threads container: "
                f"{exc.response.status_code} — {exc.response.text}"
            )
            return None

    def _post(self, endpoint: str, params: dict) -> dict:
        params = {**params, "access_token": self.access_token}
        response = requests.post(
            f"{BASE_URL}/{endpoint}",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        p = {"access_token": self.access_token, **(params or {})}
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=p,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
