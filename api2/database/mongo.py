import os
from typing import Any
from typing import Optional
from urllib.parse import parse_qs, urlparse

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

load_dotenv()

_client: Optional[MongoClient] = None


def build_uri() -> str:
    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not uri:
        raise ValueError("MONGODB_URI or MONGO_URI must be set")

    return uri


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _uri_uses_tls(uri: str) -> bool:
    if uri.startswith("mongodb+srv://"):
        return True

    parsed = urlparse(uri)
    params = parse_qs(parsed.query)
    tls_values = params.get("tls", []) + params.get("ssl", [])
    return any(value.strip().lower() == "true" for value in tls_values)


def get_client() -> MongoClient:
    global _client

    if _client is None:
        uri = build_uri()
        uri_requests_tls = _uri_uses_tls(uri)
        mongo_client_options: dict[str, Any] = {
            "serverSelectionTimeoutMS": int(
                os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")
            ),
            "connectTimeoutMS": int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000")),
            "socketTimeoutMS": int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "20000")),
        }

        if uri_requests_tls:
            mongo_client_options["tls"] = True
            mongo_client_options["tlsCAFile"] = os.getenv(
                "MONGODB_TLS_CA_FILE", certifi.where()
            )

        if _env_bool("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", False):
            mongo_client_options["tlsAllowInvalidCertificates"] = True

        if _env_bool("MONGODB_TLS_ALLOW_INVALID_HOSTNAMES", False):
            mongo_client_options["tlsAllowInvalidHostnames"] = True

        _client = MongoClient(uri, **mongo_client_options)

    return _client


def close_connection():
    global _client

    if _client:
        _client.close()
        _client = None


class MongoDB:
    def __init__(self, db_name: Optional[str] = None):
        name = db_name or os.getenv("MONGODB_DB_NAME") or os.getenv("DB_NAME")
        self.collection_name = os.getenv("MONGODB_COLLECTION_NAME") or os.getenv(
            "COLLECTION_NAME"
        )

        if not name:
            raise ValueError("MONGODB_DB_NAME or DB_NAME must be set")

        if not self.collection_name:
            raise ValueError("MONGODB_COLLECTION_NAME or COLLECTION_NAME must be set")

        self.db_name = name

        self.client = get_client()
        self.db: Database = self.client[name]
        self.default_collection: Collection = self.db[self.collection_name]

        # Fail fast on startup if auth/network/collection path is invalid.
        self.client.admin.command("ping")
        self.default_collection.estimated_document_count()

    def collection(self, name: str) -> Collection:
        # set collection name for later use
        self.collection_name = name
        return self.db[name]

    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False
