import os
import json
from typing import Dict, Any
from datetime import datetime, date
from google.cloud import pubsub_v1
from google.auth import default
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class PubSubService:
    """
    Google Cloud Pub/Sub client for publishing messages.
    Uses service account in Cloud Run, credentials.json locally.
    """

    def __init__(self, project_id: str = None, topic_name: str = None):
        """
        Initialize the PubSubService.

        Args:
            project_id: Google Cloud Project ID. If not provided, will use environment variable.
            topic_name: Pub/Sub topic name. If not provided, will use environment variable or default.
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        self.topic_name = topic_name or os.getenv("PUBSUB_TOPIC_NAME", "order-projection-created")
        self._publisher = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Pub/Sub publisher client with appropriate credentials."""
        try:
            # Check if using emulator
            emulator_host = os.getenv("PUBSUB_EMULATOR_HOST")
            
            if emulator_host:
                self._publisher = pubsub_v1.PublisherClient()
                logger.info(f"PubSub client initialized with emulator at {emulator_host}")
            elif os.path.exists("credentials.json"):
                credentials = Credentials.from_service_account_file("credentials.json")
                self._publisher = pubsub_v1.PublisherClient(credentials=credentials)
                logger.info("PubSub client initialized with service account file")
            else:
                credentials, project = default()
                self._publisher = pubsub_v1.PublisherClient(credentials=credentials)
                if not self.project_id:
                    self.project_id = project
                logger.info("PubSub client initialized with default credentials")

        except Exception as e:
            # In test/dev environments without GCP credentials, allow graceful degradation
            logger.warning(f"Failed to initialize PubSub client: {str(e)}")
            logger.warning("PubSub events will not be published. This is expected in test environments.")
            self._publisher = None

    def publish_projection_created_event(self, projection_data: Dict[str, Any]) -> bool:
        """
        Publish an order projection created event to the configured topic.

        Args:
            projection_data: Dictionary containing the projection data that was created/updated
                Expected keys: order_id, client_id, numero_orden

        Returns:
            True if the message was published successfully, False otherwise
        """
        try:
            if not self._publisher or not self.project_id:
                logger.error("PubSub client not properly initialized")
                return False

            # Extract key information for cache invalidation
            event_payload = {
                "event_type": "order_projection_created",
                "timestamp": datetime.utcnow().isoformat(),
                "order_id": projection_data.get("id"),
                "client_id": projection_data.get("id_cliente"),
                "numero_orden": projection_data.get("numero_orden"),
            }

            # Convert to JSON using custom encoder that handles datetime objects
            message_json = json.dumps(event_payload, cls=DateTimeEncoder)
            message_bytes = message_json.encode("utf-8")

            topic_path = self._publisher.topic_path(self.project_id, self.topic_name)

            future = self._publisher.publish(topic_path, message_bytes)
            message_id = future.result()

            logger.info(
                f"Order projection created event published successfully for order {event_payload.get('numero_orden')} with message ID: {message_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error publishing order projection created event: {str(e)}")
            return False

    def check_topic_exists(self) -> bool:
        """
        Check if the configured topic exists.

        Returns:
            True if the topic exists, False otherwise
        """
        try:
            if not self._publisher or not self.project_id:
                return False

            topic_path = self._publisher.topic_path(self.project_id, self.topic_name)

            # Try to get the topic
            self._publisher.get_topic(request={"topic": topic_path})
            logger.info(f"Topic {self.topic_name} exists")
            return True

        except Exception as e:
            logger.warning(f"Topic {self.topic_name} does not exist or error checking: {str(e)}")
            return False


def get_pubsub_service() -> PubSubService:
    """Factory function to create PubSubService instance"""
    return PubSubService()

