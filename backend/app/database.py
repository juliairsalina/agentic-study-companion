from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError

from app.config import settings


_client: Optional[CosmosClient] = None
_database = None
_container = None


def get_container():
    """
    Creates and returns the Cosmos DB container.
    This is used by upload.py and study.py.
    """

    global _client, _database, _container

    if _container is not None:
        return _container

    if not settings.COSMOS_DB_ENDPOINT or not settings.COSMOS_DB_KEY:
        raise RuntimeError(
            "Cosmos DB is not configured. Please set COSMOS_DB_ENDPOINT and COSMOS_DB_KEY in .env."
        )

    _client = CosmosClient(
        url=settings.COSMOS_DB_ENDPOINT,
        credential=settings.COSMOS_DB_KEY,
    )

    _database = _client.create_database_if_not_exists(
        id=settings.COSMOS_DB_DATABASE
    )

    _container = _database.create_container_if_not_exists(
        id=settings.COSMOS_DB_CONTAINER,
        partition_key=PartitionKey(path="/userId"),
    )

    return _container


def create_study_session(
    filename: str,
    instruction: str,
    saved_path: str,
    extracted_text: str,
    summary: str,
    topics: List[str],
    questions: List[Dict[str, Any]],
    user_id: str = "demo-user",
) -> Dict[str, Any]:
    """
    Saves one uploaded PDF study session.
    One document = one PDF session with generated flashcards.
    """

    container = get_container()

    now = datetime.now(timezone.utc).isoformat()

    session_doc = {
        "id": f"session-{uuid4()}",
        "userId": user_id,
        "filename": filename,
        "instruction": instruction,
        "savedPath": saved_path,
        "summary": summary,
        "topics": topics,
        "questions": questions,
        "answers": [],
        "evaluations": [],
        "workflowDecisions": [],
        "textPreview": extracted_text[:1500],
        "textLength": len(extracted_text),
        "createdAt": now,
        "updatedAt": now,
        "type": "study_session",
    }

    container.create_item(body=session_doc)

    return session_doc


def list_study_sessions(user_id: str = "demo-user") -> List[Dict[str, Any]]:
    """
    Returns saved sessions for old flashcards page.
    This returns lightweight session info, not full extracted text.
    """

    container = get_container()

    query = """
    SELECT
        c.id,
        c.userId,
        c.filename,
        c.instruction,
        c.summary,
        c.topics,
        c.questions,
        c.createdAt,
        c.updatedAt
    FROM c
    WHERE c.userId = @userId AND c.type = @type
    ORDER BY c.createdAt DESC
    """

    params = [
        {"name": "@userId", "value": user_id},
        {"name": "@type", "value": "study_session"},
    ]

    return list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )


def get_study_session(session_id: str, user_id: str = "demo-user") -> Dict[str, Any]:
    """
    Gets one full study session by id.
    """

    container = get_container()

    try:
        return container.read_item(
            item=session_id,
            partition_key=user_id,
        )
    except CosmosHttpResponseError:
        raise RuntimeError("Study session not found.")


def add_evaluation_to_session(
    session_id: str,
    question_id: str,
    transcript: str,
    evaluation: Dict[str, Any],
    workflow_decision: Dict[str, Any],
    user_id: str = "demo-user",
) -> Dict[str, Any]:
    """
    Stores answer, CoachAgent result, and WorkflowAgent decision.
    """

    container = get_container()

    session = container.read_item(
        item=session_id,
        partition_key=user_id,
    )

    now = datetime.now(timezone.utc).isoformat()

    answer_item = {
        "questionId": question_id,
        "transcript": transcript,
        "createdAt": now,
    }

    session.setdefault("answers", [])
    session.setdefault("evaluations", [])
    session.setdefault("workflowDecisions", [])

    session["answers"] = [
        item for item in session["answers"]
        if item.get("questionId") != question_id
    ]
    session["evaluations"] = [
        item for item in session["evaluations"]
        if item.get("questionId") != question_id
    ]
    session["workflowDecisions"] = [
        item for item in session["workflowDecisions"]
        if item.get("questionId") != question_id
    ]

    session["answers"].append(answer_item)
    session["evaluations"].append(evaluation)
    session["workflowDecisions"].append(workflow_decision)
    session["updatedAt"] = now

    container.upsert_item(body=session)

    return session