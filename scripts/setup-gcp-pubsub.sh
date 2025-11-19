#!/bin/bash

GOOGLE_CLOUD_PROJECT=$(gcloud config get project)
GOOGLE_CLOUD_PROJECT_NUMBER=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT --format='value(projectNumber)')

# Configuration - Update these values according to your GKE cluster
GKE_CLUSTER_NAME="${GKE_CLUSTER_NAME:-medisupply-cluster}"  # Set via env var or use default
GKE_CLUSTER_REGION="${GKE_CLUSTER_REGION:-us-central1}"     # Set via env var or use default
GKE_NAMESPACE="${GKE_NAMESPACE:-default}"                   # Set via env var or use default
EVENTARC_LOCATION="${EVENTARC_LOCATION:-us-central1}"       # Eventarc trigger location

# Service Account configuration
# According to Eventarc route-trigger documentation, use a user-managed service account
# Format: SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com
SERVICE_ACCOUNT_NAME="medisupply-service-account"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com"

# Create Service Account if it doesn't exist
echo "🔐 Creating/checking Service Account..."
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --quiet 2>/dev/null; then
    echo "Creating Service Account: $SERVICE_ACCOUNT_EMAIL"
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --display-name="Medisupply Service Account" \
        --description="Service account for Medisupply"
else
    echo "Service Account already exists: $SERVICE_ACCOUNT_EMAIL"
fi

echo "🔑 Granting Pub/Sub permissions..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/pubsub.publisher"

echo "🔑 Granting Secret Manager access..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

echo "🔑 Granting Eventarc Event Receiver permissions..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/eventarc.eventReceiver"

echo "🔑 Granting Eventarc Service Agent permissions..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/eventarc.serviceAgent"

echo "🔑 Granting GKE Service Agent permissions..."
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/container.serviceAgent"

# Function to setup Workload Identity binding
setup_workload_identity() {
    local ksa_name=$1
    local namespace="${2:-default}"
    
    echo "🔗 Setting up Workload Identity binding for $ksa_name..."
    
    # Check if kubectl is available
    if ! kubectl cluster-info &>/dev/null; then
        echo "⚠️  kubectl not available, skipping automatic Workload Identity setup"
        echo "   You'll need to set it up manually (see instructions below)"
        return 1
    fi
    
    # Get Workload Identity pool
    local workload_pool=$(gcloud container clusters describe $GKE_CLUSTER_NAME \
        --region=$GKE_CLUSTER_REGION \
        --format='value(workloadIdentityConfig.workloadPool)' 2>/dev/null)
    
    if [ -z "$workload_pool" ]; then
        echo "⚠️  Workload Identity not enabled on cluster or cannot determine pool"
        echo "   Ensure Workload Identity is enabled on your GKE cluster"
        return 1
    fi
    
    # Bind the Kubernetes ServiceAccount to the GCP service account
    local member="serviceAccount:${workload_pool}[${namespace}/${ksa_name}]"
    
    echo "   Binding KSA $namespace/$ksa_name to GCP SA $SERVICE_ACCOUNT_EMAIL"
    if gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT_EMAIL \
        --role roles/iam.workloadIdentityUser \
        --member "$member" \
        --condition=None 2>&1; then
        echo "✅ Workload Identity binding created for $ksa_name"
        return 0
    else
        echo "⚠️  Failed to create Workload Identity binding (may already exist)"
        return 1
    fi
}

# Setup Workload Identity for GKE services
echo "🔗 Setting up Workload Identity bindings..."
echo "   This allows Kubernetes ServiceAccounts to use the GCP service account"
echo ""

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable eventarc.googleapis.com --quiet 2>/dev/null || echo "Eventarc API already enabled or failed to enable"
gcloud services enable pubsub.googleapis.com --quiet 2>/dev/null || echo "Pub/Sub API already enabled or failed to enable"
gcloud services enable container.googleapis.com --quiet 2>/dev/null || echo "GKE API already enabled or failed to enable"

# Create topics if they don't exist
echo "📢 Creating/checking Topics..."
if ! gcloud pubsub topics describe create-order-command --quiet 2>/dev/null; then
    echo "Creating Topic: create-order-command"
    gcloud pubsub topics create create-order-command
else
    echo "Topic already exists: create-order-command"
fi

if ! gcloud pubsub topics describe order-created --quiet 2>/dev/null; then
    echo "Creating Topic: order-created"
    gcloud pubsub topics create order-created
else
    echo "Topic already exists: order-created"
fi

if ! gcloud pubsub topics describe order-projection-created --quiet 2>/dev/null; then
    echo "Creating Topic: order-projection-created"
    gcloud pubsub topics create order-projection-created
else
    echo "Topic already exists: order-projection-created"
fi

if ! gcloud pubsub topics describe inventory-events --quiet 2>/dev/null; then
    echo "Creating Topic: inventory-events"
    gcloud pubsub topics create inventory-events
else
    echo "Topic already exists: inventory-events"
fi

# Function to check if a GKE service exists
check_gke_service() {
    local service_name=$1
    echo "Checking if service '$service_name' exists in GKE cluster..."
    
    if kubectl get service $service_name -n $GKE_NAMESPACE &>/dev/null; then
        echo "✅ Service '$service_name' found in cluster"
        return 0
    else
        echo "⚠️  Service '$service_name' not found in cluster"
        return 1
    fi
}

# Function to check if GKE cluster is registered with Eventarc
check_eventarc_registration() {
    echo "🔍 Checking if GKE cluster is registered with Eventarc..."
    
    # Try to list triggers to see if Eventarc is properly configured
    if gcloud eventarc triggers list --location=$EVENTARC_LOCATION &>/dev/null; then
        echo "✅ Eventarc API is accessible"
        return 0
    else
        echo "⚠️  Warning: Eventarc may not be properly configured for this cluster"
        return 1
    fi
}

# Function to create an Eventarc trigger
create_eventarc_trigger() {
    local trigger_name=$1
    local service_name=$2
    local topic_name=$3
    local path=$4
    
    echo ""
    echo "📌 Setting up trigger: $trigger_name"
    
    # Check if service exists first
    if ! check_gke_service $service_name; then
        echo "⏭️  Skipping trigger creation - deploy '$service_name' service first"
        echo "   Then re-run this script to create the trigger"
        return 1
    fi
    
    # Check service type - According to Eventarc docs, ClusterIP is recommended
    local service_type=$(kubectl get service $service_name -n $GKE_NAMESPACE -o jsonpath='{.spec.type}' 2>/dev/null)
    if [ "$service_type" != "ClusterIP" ]; then
        echo "⚠️  Warning: Service '$service_name' is $service_type type"
        echo "   According to Eventarc documentation, ClusterIP is recommended for GKE services"
        echo "   Current type: $service_type"
    fi
    
    # Check if trigger already exists
    if gcloud eventarc triggers describe $trigger_name --location=$EVENTARC_LOCATION --quiet 2>/dev/null; then
        echo "✅ Trigger already exists: $trigger_name"
        return 0
    fi
    
    # Create the trigger
    # According to Eventarc route-trigger documentation, use a user-managed service account
    # Reference: https://docs.cloud.google.com/eventarc/standard/docs/gke/route-trigger-cloud-pubsub
    echo "Creating Eventarc trigger: $trigger_name"
    echo "Using service account: $SERVICE_ACCOUNT_EMAIL (user-managed service account)"
    local output=$(gcloud eventarc triggers create $trigger_name \
        --location=$EVENTARC_LOCATION \
        --destination-gke-cluster=$GKE_CLUSTER_NAME \
        --destination-gke-location=$GKE_CLUSTER_REGION \
        --destination-gke-namespace=$GKE_NAMESPACE \
        --destination-gke-service=$service_name \
        --destination-gke-path=$path \
        --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
        --transport-topic=projects/$GOOGLE_CLOUD_PROJECT/topics/$topic_name \
        --service-account=$SERVICE_ACCOUNT_EMAIL 2>&1)
    
    if [ $? -eq 0 ]; then
        echo "✅ Created trigger: $trigger_name"
        return 0
    else
        echo "❌ Failed to create trigger: $trigger_name"
        echo "   Error output: $output"
        
        # Check for common issues
        if echo "$output" | grep -q "Invalid resource state"; then
            echo ""
            echo "🔧 Troubleshooting steps (based on official docs):"
            echo "   1. Ensure services are ClusterIP type (not NodePort):"
            echo "      kubectl get service $service_name -n $GKE_NAMESPACE"
            echo "      If NodePort, convert to ClusterIP as per docs:"
            echo "      https://docs.cloud.google.com/eventarc/standard/docs/gke/route-trigger-cloud-pubsub"
            echo "   2. Verify the service account exists:"
            echo "      gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL"
            echo "   3. Ensure Eventarc API is enabled:"
            echo "      gcloud services enable eventarc.googleapis.com"
            echo "   4. Check Eventarc documentation:"
            echo "      https://docs.cloud.google.com/eventarc/standard/docs/gke/route-trigger-cloud-pubsub"
        fi
        return 1
    fi
}

# Create Eventarc triggers for GKE services
echo ""
echo "🎯 Creating/checking Eventarc Triggers for GKE services..."
echo "Using cluster: $GKE_CLUSTER_NAME in region: $GKE_CLUSTER_REGION"
echo ""

# Check kubectl connectivity
echo "Verifying kubectl access to cluster..."
if ! kubectl cluster-info &>/dev/null; then
    echo "⚠️  Warning: Cannot connect to GKE cluster"
    echo "   Make sure you're authenticated:"
    echo "   gcloud container clusters get-credentials $GKE_CLUSTER_NAME --region=$GKE_CLUSTER_REGION"
    echo ""
    echo "⏭️  Skipping Eventarc trigger creation"
    echo "   Topics and service account are ready. Create triggers after deploying services."
    SKIP_TRIGGERS=true
else
    echo "✅ Connected to cluster"
    
    # Check Eventarc registration
    if ! check_eventarc_registration; then
        echo ""
        echo "⚠️  Eventarc may not be properly configured for this cluster"
        echo "   This might cause trigger creation to fail"
        echo ""
        echo "   To register your cluster with Eventarc, you may need to:"
        echo "   1. Enable Anthos API: gcloud services enable anthos.googleapis.com"
        echo "   2. Register the cluster with Eventarc"
        echo "   3. Ensure Workload Identity is enabled on the cluster"
        echo ""
    fi
    
    SKIP_TRIGGERS=false
fi

if [ "$SKIP_TRIGGERS" = false ]; then
    # Setup Workload Identity for services that need Pub/Sub access
    echo "Setting up Workload Identity for services..."
    setup_workload_identity "ordenes-commands-api-sa" "default"
    setup_workload_identity "ordenes-commands-handlers-sa" "default"
    setup_workload_identity "ordenes-queries-projection-sa" "default"
    setup_workload_identity "auditoria-sa" "default"
    echo ""
    
    # Trigger 1: create-order-command -> ordenes-commands-handlers-service
    create_eventarc_trigger "create-order-command-trigger" "ordenes-commands-handlers-service" "create-order-command" "/"
    
    # Trigger 2: order-created -> ordenes-queries-projection-service
    create_eventarc_trigger "order-created-trigger" "ordenes-queries-projection-service" "order-created" "/"
    
    # Trigger 3: order-projection-created -> ordenes-queries-api-service (cache invalidation)
    create_eventarc_trigger "order-projection-created-trigger" "ordenes-queries-api-service" "order-projection-created" "/orders/cache-invalidation"
    
    # Trigger 4: inventory-events -> auditoria-service
    create_eventarc_trigger "inventory-events-audit-trigger" "auditoria-service" "inventory-events" "/api/auditoria/eventos/inventario"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Summary:"
echo "  - Service Account: $SERVICE_ACCOUNT_EMAIL (user-managed service account)"
echo "  - Topics: create-order-command, order-created, order-projection-created, inventory-events"
echo ""
echo "⚠️  Important: According to Eventarc documentation, services should be ClusterIP type"
echo "   Your services are currently NodePort. Consider updating them to ClusterIP:"
echo "   https://docs.cloud.google.com/eventarc/standard/docs/gke/route-trigger-cloud-pubsub"

if [ "$SKIP_TRIGGERS" = true ]; then
    echo "  - Eventarc Triggers: Skipped (deploy services first)"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Deploy your services to GKE:"
    echo "     - ordenes-commands-handlers-service"
    echo "     - ordenes-queries-projection-service"
    echo "     - ordenes-queries-api-service"
    echo "     - auditoria-service"
    echo ""
    echo "  2. Re-run this script to create Eventarc triggers:"
    echo "     ./setup-gcp-pubsub.sh"
else
    echo "  - Eventarc Triggers: Check output above for status"
    echo ""
    echo "🔍 To verify triggers, run:"
    echo "  gcloud eventarc triggers list --location=$EVENTARC_LOCATION"
    echo ""
    echo "⚠️  Note: Triggers may take up to 2 minutes to become active"
    echo ""
    echo "🧪 To test, publish a message:"
    echo "  gcloud pubsub topics publish create-order-command --message='{\"test\": true}'"
    echo ""
    echo "🔧 If triggers failed to create, check the official documentation:"
    echo "   https://docs.cloud.google.com/eventarc/standard/docs/gke/route-trigger-cloud-pubsub"
    echo ""
    echo "   Common issues:"
    echo "   1. Services should be ClusterIP type (not NodePort)"
    echo "   2. Using user-managed service account: $SERVICE_ACCOUNT_EMAIL"
    echo "   3. Ensure Eventarc API is enabled"
    echo "   4. Services must be exposed as Kubernetes services (ClusterIP)"
fi