import os
from typing import Any

import certifi
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from api2.debug import debug_kv, get_logger


logger = get_logger("services.data_store")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "fluxmod")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "app_data")
MONGODB_DOCUMENT_ID = os.getenv("MONGODB_DOCUMENT_ID", "singleton")

_mongo_client: MongoClient | None = None


def default_data() -> dict[str, Any]:
    """Return the baseline data shape stored in MongoDB."""
    return {"guilds": {}, "rules": []}


def _get_collection() -> Collection:
    global _mongo_client
    if _mongo_client is None:
        mongo_client_options: dict[str, Any] = {
            "serverSelectionTimeoutMS": int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")),
            "connectTimeoutMS": int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000")),
            "socketTimeoutMS": int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "20000")),
        }

        if MONGODB_URI.startswith("mongodb+srv://"):
            mongo_client_options["tls"] = True
            mongo_client_options["tlsCAFile"] = certifi.where()

        _mongo_client = MongoClient(MONGODB_URI, **mongo_client_options)
        _mongo_client.admin.command("ping")
        logger.info("Connected to MongoDB database '%s'", MONGODB_DB_NAME)
    return _mongo_client[MONGODB_DB_NAME][MONGODB_COLLECTION_NAME]


def ensure_data_file() -> None:
    """Ensure the MongoDB singleton document exists."""
    try:
        collection = _get_collection()
        existing = collection.find_one({"_id": MONGODB_DOCUMENT_ID})
        if existing is not None:
            return

        collection.insert_one({"_id": MONGODB_DOCUMENT_ID, **default_data()})
        logger.info(
            "Created MongoDB data document '%s' in %s.%s",
            MONGODB_DOCUMENT_ID,
            MONGODB_DB_NAME,
            MONGODB_COLLECTION_NAME,
        )
    except PyMongoError as exc:
        logger.exception("MongoDB initialization failed during startup: %s", exc)


def load_data() -> dict[str, Any]:
    """Load persisted backend data from MongoDB."""
    try:
        collection = _get_collection()
        loaded = collection.find_one({"_id": MONGODB_DOCUMENT_ID}, {"_id": 0})
    except PyMongoError as exc:
        logger.exception("MongoDB load failed: %s", exc)
        return default_data()

    if not isinstance(loaded, dict):
        debug_kv(logger, "MongoDB data document missing; returning defaults")
        return default_data()

    debug_kv(
        logger,
        "MongoDB data loaded",
        guild_count=len(loaded.get("guilds", {})) if isinstance(loaded, dict) else None,
        rule_count=len(loaded.get("rules", [])) if isinstance(loaded, dict) else None,
    )
    return loaded


def save_data(data: dict[str, Any]) -> None:
    """Persist backend data into MongoDB."""
    try:
        collection = _get_collection()
        collection.replace_one({"_id": MONGODB_DOCUMENT_ID}, {"_id": MONGODB_DOCUMENT_ID, **data}, upsert=True)
    except PyMongoError as exc:
        logger.exception("MongoDB save failed: %s", exc)
        return

    debug_kv(
        logger,
        "MongoDB data saved",
        guild_count=len(data.get("guilds", {})),
        rule_count=len(data.get("rules", [])),
    )
