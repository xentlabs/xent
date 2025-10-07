#!/usr/bin/env python3
"""Utility script for transforming tweet data stored in JSON files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Modify tweets stored in a JSON file and write the result to another file."
    )
    parser.add_argument("input_file", type=Path, help="Path to the input JSON file")
    parser.add_argument(
        "output_file", type=Path, help="Path to write the modified JSON"
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


LINK_PATTERN = re.compile(r"https?://\S+")
LEADING_TAGS_PATTERN = re.compile(r"^(?P<tags>(?:@[\w_]+\s*)+)")


def modify_full_text(text: str) -> str:
    """Apply the tweet text transformations specified by the pipeline."""
    without_links = LINK_PATTERN.sub("", text)

    match = LEADING_TAGS_PATTERN.match(without_links)
    if match:
        tags_segment = match.group("tags").strip()
        tags = tags_segment.split()
        if len(tags) > 1:
            remainder = without_links[match.end():].lstrip()
            without_links = tags[0]
            if remainder:
                without_links = f"{without_links} {remainder}"

    return without_links.strip()


def process_tweets(tweets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    processed: list[dict[str, Any]] = []
    for entry in tweets:
        tweet_payload = entry.get("tweet")
        if not isinstance(tweet_payload, dict):
            continue

        full_text = tweet_payload.get("full_text")
        if not isinstance(full_text, str):
            continue

        updated_text = modify_full_text(full_text)
        if not updated_text:
            continue

        tweet_payload["full_text"] = updated_text
        processed.append(entry)

    return processed


def main() -> None:
    args = parse_args()

    data = load_json(args.input_file)
    tweets = data.get("tweets")

    if not isinstance(tweets, list):
        raise ValueError("Expected 'tweets' to be a list in the input JSON data")

    data["tweets"] = process_tweets(tweets)

    with args.output_file.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
