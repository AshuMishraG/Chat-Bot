import json
import os
from typing import Any

from fastapi.responses import JSONResponse


class PrettyJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        # Only pretty-print in development
        if os.getenv("ENV", "dev") == "dev":
            return json.dumps(
                content,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
                separators=(", ", ": "),
            ).encode("utf-8")
        return super().render(content)
