import re
from typing import List, Optional

from pydantic import BaseModel, computed_field


class Note(BaseModel):
    url: str
    title: Optional[str] = None
    # details below
    author: Optional[str] = None
    content: Optional[str] = None
    is_video: bool = False
    like_count: Optional[int] = None
    cover_url: Optional[str] = None
    date_string: Optional[str] = None
    comments: List[str] = []

    @computed_field
    @property
    def id(self) -> Optional[str]:
        """Extract the note ID from the Xiaohongshu URL."""
        # Extract ID from URL path (between /explore/ and any query params)
        match = re.search(r"/explore/([a-zA-Z0-9]+)", self.url)
        if match:
            return match.group(1)
        return None

    # generate markdown string
    # truncate: reduce the content if needed
    def to_md(self, truncate_num=-1, comments_limit=-1) -> str:
        lines = []
        # Add title and author
        lines.append(f"Title: {self.title or 'Untitled'}")
        if self.author:
            lines.append(f"Author: {self.author}")
        if self.date_string:
            lines.append(f"Date: {self.date_string}")
        lines.append("---")

        # Add content with optional truncation
        if self.content:
            # only trigger truncation if the content.length >= limit + 100
            if truncate_num > 0 and len(self.content) >= (truncate_num + 100):
                half = truncate_num // 2
                truncated_content = f"""{self.content[:half]}
... truncated {len(self.content) - truncate_num} characters ...
{self.content[-half:]}"""
                lines.append(truncated_content)
            else:
                lines.append(self.content)
        else:
            lines.append("*No content available*")

        lines.append("---")

        # Add comments section
        lines.append("Comments:")
        if self.comments:
            for comment in self.comments[:comments_limit]:
                lines.append(f"- {comment[:truncate_num]}")
        else:
            lines.append("*No comments available*")

        return "\n".join(lines)
