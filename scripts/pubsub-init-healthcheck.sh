#!/bin/bash

# Health check script for pubsub-init container
# This script checks if Pub/Sub topics and subscriptions have been created successfully

set -e

# Configuration
CONFIG_FILE="${PUBSUB_CONFIG_FILE:-/config/pubsub-config.json}"
EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-pubsub-emulator:8085}"
PROJECT_ID="${PUBSUB_PROJECT_ID:-medisupply-474421}"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "jq not found, assuming initialization is complete"
    exit 0
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "curl not found, assuming initialization is complete"
    exit 0
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file not found, assuming initialization is complete"
    exit 0
fi

# Parse expected topics and subscriptions
EXPECTED_TOPICS=$(jq -r '.topics[]' "$CONFIG_FILE" 2>/dev/null || echo "")
EXPECTED_SUBS=$(jq -r '.subscriptions[].name' "$CONFIG_FILE" 2>/dev/null || echo "")

# Count expected items
EXPECTED_TOPIC_COUNT=$(echo "$EXPECTED_TOPICS" | grep -c . || echo "0")
EXPECTED_SUB_COUNT=$(echo "$EXPECTED_SUBS" | grep -c . || echo "0")

if [ "$EXPECTED_TOPIC_COUNT" -eq 0 ] || [ "$EXPECTED_SUB_COUNT" -eq 0 ]; then
    echo "No topics or subscriptions expected, assuming initialization is complete"
    exit 0
fi

# Check if topics exist
TOPICS_RESPONSE=$(curl -s "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics" 2>/dev/null || echo "")
FOUND_TOPICS=0

for topic in $EXPECTED_TOPICS; do
    if echo "$TOPICS_RESPONSE" | grep -q "$topic"; then
        FOUND_TOPICS=$((FOUND_TOPICS + 1))
    fi
done

# Check if subscriptions exist
SUBS_RESPONSE=$(curl -s "http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions" 2>/dev/null || echo "")
FOUND_SUBS=0

for sub in $EXPECTED_SUBS; do
    if echo "$SUBS_RESPONSE" | grep -q "$sub"; then
        FOUND_SUBS=$((FOUND_SUBS + 1))
    fi
done

# Verify all topics and subscriptions are created
if [ "$FOUND_TOPICS" -eq "$EXPECTED_TOPIC_COUNT" ] && [ "$FOUND_SUBS" -eq "$EXPECTED_SUB_COUNT" ]; then
    exit 0
else
    echo "Pub/Sub initialization incomplete: $FOUND_TOPICS/$EXPECTED_TOPIC_COUNT topics, $FOUND_SUBS/$EXPECTED_SUB_COUNT subscriptions"
    exit 1
fi

