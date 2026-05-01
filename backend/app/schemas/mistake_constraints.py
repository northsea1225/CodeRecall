from typing import Annotated

from pydantic import StringConstraints

MAX_TITLE_LEN = 200
MAX_MARKDOWN_LEN = 50000
MAX_ERROR_REASON_LEN = 10000
MAX_LANGUAGE_LEN = 50
MAX_SOURCE_LEN = 200

MistakeTitle = Annotated[str, StringConstraints(max_length=MAX_TITLE_LEN)]
MistakeMarkdown = Annotated[str, StringConstraints(max_length=MAX_MARKDOWN_LEN)]
MistakeErrorReason = Annotated[str, StringConstraints(max_length=MAX_ERROR_REASON_LEN)]
MistakeLanguage = Annotated[str, StringConstraints(max_length=MAX_LANGUAGE_LEN)]
MistakeSource = Annotated[str, StringConstraints(max_length=MAX_SOURCE_LEN)]
