"""Write the API schema to frontend/openapi.json (input for the frontend's typed client).

cd backend && .venv/bin/python -m scripts.export_openapi
"""

import json

from app.core.config import PROJECT_ROOT
from app.main import create_app


def main() -> None:
    target = PROJECT_ROOT / "frontend" / "openapi.json"
    target.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
