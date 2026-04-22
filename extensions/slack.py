from __future__ import annotations

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from typing import TypedDict


class SlackConfig(TypedDict):
    oauth_token: str
    channel_id: str


class SlackClient:

    def __init__(self, oauth_token: str, channel_id: str):
        self.client = WebClient(token=oauth_token)
        self.channel = channel_id

    def chat_message(self, text: str, blocks: list | None = None) -> bool:
        """메시지를 전송한다. 실패해도 예외를 올리지 않고 False를 반환한다."""
        try:
            kwargs: dict = dict(channel=self.channel, text=text)
            if blocks:
                kwargs["blocks"] = blocks
            self.client.chat_postMessage(**kwargs)
            return True
        except SlackApiError:
            return False
