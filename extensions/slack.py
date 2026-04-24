from __future__ import annotations

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from typing import TypedDict


class SlackConfig(TypedDict):
    oauth_token: str
    channel_id: str


def to_text(value: str | None) -> str:
    return str(value) if value is not None else str()


class SlackClient:

    def __init__(self, oauth_token: str, channel_id: str):
        self.client = WebClient(token=oauth_token)
        self.channel = channel_id

    def chat_message(self, text: str, blocks: list | None = None) -> bool:
        """메시지를 전송한다. 실패해도 예외를 올리지 않고 False를 반환한다."""
        try:
            kwargs: dict = dict(channel=self.channel, text=text)
            if blocks:
                kwargs["attachments"] = [{"blocks": blocks}]
            self.client.chat_postMessage(**kwargs)
            return True
        except SlackApiError:
            return False

    def create_table(self, rows: list[list[str]], column_settings: list[dict] = list()) -> dict:
        if not column_settings:
            column_settings = [{"align": "center"} for _ in rows[0]]
        return {
            "type": "table",
            "column_settings": column_settings,
            "rows": [[{
                "type": "raw_text",
                "text": (to_text(value) or '-'),
            } for value in row] for row in rows]
        }

    def create_ordered_list(self, elements: list[str]) -> dict:
        return {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_list",
                    "style": "ordered",
                    "elements": [{
                        "type": "rich_text_section",
                        "elements": {"type": "text", "text": to_text(value)},
                    } for value in elements]
                }
            ]
        }
