import json
import sys
from os.path import basename


def is_dot_env(path: object) -> bool:
    if not path or not isinstance(path, str):
        return False
    return basename(path).lower() == ".env"


def deny() -> None:
    print(
        json.dumps(
            {
                "permission": "deny",
                "user_message": (
                    "Reading `.env` is blocked by `.cursor/hooks/block_env_read.py`. "
                    "Use documented sample env files or configure secrets outside the agent."
                ),
            }
        )
    )


def main() -> None:
    data = json.load(sys.stdin)
    if is_dot_env(data.get("file_path")):
        deny()
        return
    for att in data.get("attachments") or []:
        if att.get("type") == "file" and is_dot_env(att.get("file_path")):
            deny()
            return
    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
