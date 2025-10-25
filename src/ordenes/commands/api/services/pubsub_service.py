import os
import json
from typing import Dict, Any
from datetime import datetime, date
from google.cloud import pubsub_v1
from google.auth import default
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()


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
        self.topic_name = topic_name or os.getenv("PUBSUB_TOPIC_NAME", "create-order-command")
        self._publisher = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Pub/Sub publisher client with appropriate credentials."""
        try:
            # Check if using emulator
            emulator_host = os.getenv("PUBSUB_EMULATOR_HOST")
            
            if emulator_host:
                self._publisher = pubsub_v1.PublisherClient()
                print(f"PubSub client initialized with emulator at {emulator_host}")
            elif os.path.exists("credentials.json"):
                credentials = Credentials.from_service_account_file("credentials.json")
                self._publisher = pubsub_v1.PublisherClient(credentials=credentials)
                print("PubSub client initialized with service account file")
            else:
                credentials, project = default()
                self._publisher = pubsub_v1.PublisherClient(credentials=credentials)
                if not self.project_id:
                    self.project_id = project
                print("PubSub client initialized with default credentials")

        except Exception as e:
            raise Exception(f"Failed to initialize PubSub client: {str(e)}")

    def publish_create_order_command(self, order_data: Dict[str, Any]) -> bool:
        """
        Publish a create order command to the configured topic.

        Args:
            order_data: Dictionary containing the order data that was processed

        Returns:
            True if the message was published successfully, False otherwise
        """
        try:
            if not self._publisher or not self.project_id:
                print("PubSub client not properly initialized")
                return False

            # Convert to JSON using custom encoder that handles datetime objects
            message_json = json.dumps(order_data, cls=DateTimeEncoder)
            message_bytes = message_json.encode("utf-8")

            topic_path = self._publisher.topic_path(self.project_id, self.topic_name)

            future = self._publisher.publish(topic_path, message_bytes)
            message_id = future.result()  

            print(
                f"Create order command published successfully with message ID: {message_id}"
            )
            return True

        except Exception as e:
            print(f"Error publishing create order command: {str(e)}")
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
            print(f"Topic {self.topic_name} exists")
            return True

        except Exception as e:
            print(f"Topic {self.topic_name} does not exist or error checking: {str(e)}")
            return False