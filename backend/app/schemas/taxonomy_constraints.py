from typing import Annotated

from pydantic import StringConstraints

CATEGORY_NAME_MAX = 100
CATEGORY_DESC_MAX = 500
TAG_NAME_MAX = 100

CategoryName = Annotated[str, StringConstraints(min_length=1, max_length=CATEGORY_NAME_MAX)]
CategoryDescription = Annotated[str, StringConstraints(max_length=CATEGORY_DESC_MAX)]
TagName = Annotated[str, StringConstraints(min_length=1, max_length=TAG_NAME_MAX)]
