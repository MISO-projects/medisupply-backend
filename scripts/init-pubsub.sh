#!/bin/bash

set -e

echo "Waiting for Pub/Sub emulator to be ready..."
sleep 5

# Install dependencies first
echo "Installing dependencies..."
apk add --no-cache curl jq 2>/dev/null || apt-get update && apt-get install -y curl jq 2>/dev/null || yum install -y curl jq 2>/dev/null || true

# ============================================================================
# CONFIGURATION FILE
# ============================================================================
CONFIG_FILE="${PUBSUB_CONFIG_FILE:-/config/pubsub-config.json}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: Configuration file not found: $CONFIG_FILE"
  exit 1
fi

echo "Loading configuration from: $CONFIG_FILE"

# Parse JSON configuration using jq
PROJECT_ID=$(jq -r '.project_id // "medisupply-474421"' "$CONFIG_FILE")
EMULATOR_HOST=$(jq -r '.emulator_host // "pubsub-emulator:8085"' "$CONFIG_FILE")

# Override with environment variables if set
PROJECT_ID="${PUBSUB_PROJECT_ID:-$PROJECT_ID}"
EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-$EMULATOR_HOST}"

echo "Initializing Pub/Sub for project: $PROJECT_ID"
echo "Emulator host: $EMULATOR_HOST"

# Wait for emulator to be fully ready
echo "Waiting for Pub/Sub emulator..."
max_retries=30
retry_count=0
until curl -f "http://${EMULATOR_HOST}" > /dev/null 2>&1; do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo "ERROR: Pub/Sub emulator not ready after $max_retries attempts"
    exit 1
  fi
  echo "  Attempt $retry_count/$max_retries..."
  sleep 2
done
echo "✓ Pub/Sub emulator is ready!"

# Wait for services to be ready (if health checks are defined)
health_checks_count=$(jq '.healthChecks | length' "$CONFIG_FILE")
if [ "$health_checks_count" -gt 0 ]; then
  echo ""
  echo "Waiting for services to be ready..."
  
  for i in $(seq 0 $((health_checks_count - 1))); do
    service_name=$(jq -r ".healthChecks[$i].service" "$CONFIG_FILE")
    health_endpoint=$(jq -r ".healthChecks[$i].endpoint" "$CONFIG_FILE")
    
    retry_count=0
    until curl -f "http://${health_endpoint}" > /dev/null 2>&1; do
      retry_count=$((retry_count + 1))
      if [ $retry_count -ge $max_retries ]; then
        echo "WARNING: $service_name not ready, continuing anyway..."
        break
      fi
      if [ $retry_count -eq 1 ]; then
        echo "  Waiting for $service_name..."
      fi
      sleep 2
    done
    
    if [ $retry_count -lt $max_retries ]; then
      echo "✓ $service_name is ready"
    fi
  done
fi

# Create topics
echo ""
echo "Creating topics..."
topics_count=$(jq '.topics | length' "$CONFIG_FILE")

for i in $(seq 0 $((topics_count - 1))); do
  topic=$(jq -r ".topics[$i]" "$CONFIG_FILE")
  
  curl -s -X PUT "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics/${topic}" \
    -H "Content-Type: application/json" \
    > /dev/null 2>&1 && echo "✓ Topic '${topic}' created" || echo "✓ Topic '${topic}' already exists"
done

# Create subscriptions
echo ""
echo "Creating push subscriptions..."
subs_count=$(jq '.subscriptions | length' "$CONFIG_FILE")

for i in $(seq 0 $((subs_count - 1))); do
  sub_name=$(jq -r ".subscriptions[$i].name" "$CONFIG_FILE")
  topic=$(jq -r ".subscriptions[$i].topic" "$CONFIG_FILE")
  push_endpoint=$(jq -r ".subscriptions[$i].pushEndpoint" "$CONFIG_FILE")
  ack_deadline=$(jq -r ".subscriptions[$i].ackDeadlineSeconds // 60" "$CONFIG_FILE")
  
  curl -s -X PUT "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/${sub_name}" \
    -H "Content-Type: application/json" \
    -d '{
      "topic": "projects/'${PROJECT_ID}'/topics/'${topic}'",
      "pushConfig": {
        "pushEndpoint": "http://'${push_endpoint}'/"
      },
      "ackDeadlineSeconds": '${ack_deadline}'
    }' \
    > /dev/null 2>&1 && echo "✓ Subscription '${sub_name}' created (${topic} → ${push_endpoint})" || echo "✓ Subscription '${sub_name}' already exists"
done

# Verify setup
echo ""
echo "Pub/Sub setup complete!"
echo ""
echo "Verifying topics exist:"
topics_response=$(curl -s "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics")
for i in $(seq 0 $((topics_count - 1))); do
  topic=$(jq -r ".topics[$i]" "$CONFIG_FILE")
  echo "$topics_response" | grep -q "$topic" && echo "  ✓ $topic" || echo "  ✗ $topic"
done

echo ""
echo "Verifying subscriptions exist:"
subs_response=$(curl -s "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions")
for i in $(seq 0 $((subs_count - 1))); do
  sub_name=$(jq -r ".subscriptions[$i].name" "$CONFIG_FILE")
  echo "$subs_response" | grep -q "$sub_name" && echo "  ✓ $sub_name" || echo "  ✗ $sub_name"
done

echo ""
echo "Event flow configured:"
for i in $(seq 0 $((subs_count - 1))); do
  topic=$(jq -r ".subscriptions[$i].topic" "$CONFIG_FILE")
  push_endpoint=$(jq -r ".subscriptions[$i].pushEndpoint" "$CONFIG_FILE")
  service_name=$(echo "$push_endpoint" | cut -d':' -f1)
  echo "  $((i + 1)). [${topic}] → ${service_name}"
done

echo ""
echo "Initialization complete! Keep this container running..."

# Keep the container running to maintain subscriptions
tail -f /dev/null
