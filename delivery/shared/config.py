from typing import Optional
# ===== shared/config.py =====

import json
import os

from cryptography.fernet import Fernet, InvalidToken


class Config:
    def __init__(self, config_path: str = "config.json", key_path: str = ".key"):
        self.config_path = config_path
        self.key_path = key_path
        self._fernet = None

        key = self._load_key()
        self._fernet = Fernet(key)

        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump({}, f)

    def _load_key(self) -> bytes:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return f.read().strip()
        return self._generate_key()

    def _generate_key(self) -> bytes:
        key = Fernet.generate_key()
        with open(self.key_path, "wb") as f:
            f.write(key)
        return key

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    def get(self, key: str) -> Optional[str]:
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
        if key not in data:
            return None
        try:
            return self._decrypt(data[key])
        except InvalidToken:
            return data[key]

    def set(self, key: str, value: str) -> None:
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
        data[key] = self._encrypt(value)
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_all(self) -> dict:
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
        result = {}
        for k, v in data.items():
            try:
                result[k] = self._decrypt(v)
            except InvalidToken:
                result[k] = v
        return result

    def is_complete(self) -> bool:
        return bool(self.get("output_folder"))