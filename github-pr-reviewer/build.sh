#!/bin/bash

# GitHub PR Reviewer Build Script
# Builds and deploys the container image to OpenShift registry

set -e

# Configuration
IMAGE_NAME="github-pr-reviewer"
NAMESPACE="openshift-pipelines"
FULL_IMAGE_NAME="image-registry.openshift-image-registry.svc:5000/${NAMESPACE}/${IMAGE_NAME}:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_error "Podman is not installed or not in PATH"
        exit 1
    fi
    
    # Check if oc is available
    if ! command -v oc &> /dev/null; then
        log_error "oc CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Check if logged in to OpenShift
    if ! oc whoami &> /dev/null; then
        log_error "Not logged in to OpenShift. Run 'oc login' first."
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

build_image() {
    log_info "Building container image..."
    
    # Build the image
    podman build -f containers/Containerfile \
                 -t ${IMAGE_NAME}:latest \
                 --no-cache .
    
    if [ $? -eq 0 ]; then
        log_info "Container image built successfully"
    else
        log_error "Failed to build container image"
        exit 1
    fi
}

tag_image() {
    log_info "Tagging image for OpenShift registry..."
    
    podman tag ${IMAGE_NAME}:latest ${FULL_IMAGE_NAME}
    
    if [ $? -eq 0 ]; then
        log_info "Image tagged successfully"
    else
        log_error "Failed to tag image"
        exit 1
    fi
}

push_image() {
    log_info "Pushing image to OpenShift registry..."
    
    # Ensure registry is accessible
    if ! podman pull alpine:latest &> /dev/null; then
        log_warn "Podman might need authentication for the registry"
    fi
    
    podman push ${FULL_IMAGE_NAME}
    
    if [ $? -eq 0 ]; then
        log_info "Image pushed successfully"
    else
        log_error "Failed to push image to registry"
        exit 1
    fi
}

create_namespace() {
    log_info "Ensuring namespace exists..."
    
    if ! oc get namespace ${NAMESPACE} &> /dev/null; then
        log_info "Creating namespace ${NAMESPACE}..."
        oc create namespace ${NAMESPACE}
    else
        log_info "Namespace ${NAMESPACE} already exists"
    fi
}

create_github_secret() {
    log_info "Checking GitHub token secret..."
    
    if oc get secret github-token -n ${NAMESPACE} &> /dev/null; then
        log_info "GitHub token secret already exists"
        log_warn "To update the token, run: oc delete secret github-token -n ${NAMESPACE}"
    else
        log_warn "GitHub token secret not found"
        log_info "Please create it manually:"
        echo "  oc create secret generic github-token \\"
        echo "    --from-literal=token=your_github_personal_access_token \\"
        echo "    -n ${NAMESPACE}"
    fi
}

create_ai_secret() {
    log_info "Checking AI token secret..."
    
    if oc get secret ai-token -n ${NAMESPACE} &> /dev/null; then
        log_info "AI token secret already exists"
        log_warn "To update the token, run: oc delete secret ai-token -n ${NAMESPACE}"
    else
        log_info "AI token secret (optional for AI analysis):"
        echo "  oc create secret generic ai-token \\"
        echo "    --from-literal=token=your_ai_service_token \\"
        echo "    -n ${NAMESPACE}"
        echo
        echo "Note: AI token is only needed if you want AI-powered PR analysis."
        echo "You can skip this if you want to use rule-based analysis only."
    fi
}

deploy_task() {
    log_info "Deploying Tekton task..."
    
    # Check if task already exists
    if oc get task github-pr-reviewer -n ${NAMESPACE} &> /dev/null; then
        log_info "Task already exists, updating..."
        oc apply -f github-pr-reviewer-task.yaml
    else
        log_info "Applying task definition..."
        oc apply -f github-pr-reviewer-task.yaml
    fi
    
    if [ $? -eq 0 ]; then
        log_info "Task deployed successfully"
    else
        log_error "Failed to deploy task"
        exit 1
    fi
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check image exists in registry
    if podman inspect ${FULL_IMAGE_NAME} &> /dev/null; then
        log_info "Container image is available in registry"
    else
        log_warn "Could not verify image in registry"
    fi
    
    # Check task is applied
    if oc get task github-pr-reviewer -n ${NAMESPACE} &> /dev/null; then
        log_info "Tekton task is available"
    else
        log_error "Tekton task not found"
        exit 1
    fi
}

show_next_steps() {
    log_info "Deployment completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Create GitHub token secret (if not created):"
    echo "   oc create secret generic github-token \\"
    echo "     --from-literal=token=your_github_personal_access_token \\"
    echo "     -n ${NAMESPACE}"
    echo
    echo "2. (Optional) Create AI token secret for AI-powered analysis:"
    echo "   oc create secret generic ai-token \\"
    echo "     --from-literal=token=your_ai_service_api_token \\"
    echo "     -n ${NAMESPACE}"
    echo
    echo "3. Create a PipelineRun to test the task:"
    echo "   oc create -f examples/pipeline-example.yaml -n ${NAMESPACE}"
    echo
    echo "4. Monitor task execution:"
    echo "   tkn taskrun list -n ${NAMESPACE}"
    echo
    echo "5. View logs:"
    echo "   tkn taskrun logs <taskrun-name> -n ${NAMESPACE}"
    echo
    echo "6. For webhook integration, see examples/webhook-setup.md"
    echo
    echo "AI Analysis Setup:"
    echo "- For AI-powered analysis, provide ai-endpoint and ai-token parameters"
    echo "- Supported endpoints: OpenAI, vLLM, and other OpenAI-compatible APIs"
    echo "- See README.md for detailed AI configuration examples"
}

# Main execution
main() {
    echo "GitHub PR Reviewer Build Script"
    echo "================================"
    echo
    
    check_prerequisites
    echo
    
    create_namespace
    echo
    
    build_image
    echo
    
    tag_image
    echo
    
    push_image
    echo
    
    create_github_secret
    echo
    
    create_ai_secret
    echo
    
    deploy_task
    echo
    
    verify_deployment
    echo
    
    show_next_steps
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo "  -n, --namespace  Specify OpenShift namespace (default: openshift-pipelines)"
    echo
    echo "Environment Variables:"
    echo "  CUSTOM_NAMESPACE  Override default namespace"
    echo
    echo "This script builds and deploys the GitHub PR Reviewer Tekton task to OpenShift."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            FULL_IMAGE_NAME="image-registry.openshift-image-registry.svc:5000/${NAMESPACE}/${IMAGE_NAME}:latest"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check for environment variable override
if [ -n "$CUSTOM_NAMESPACE" ]; then
    NAMESPACE="$CUSTOM_NAMESPACE"
    FULL_IMAGE_NAME="image-registry.openshift-image-registry.svc:5000/${NAMESPACE}/${IMAGE_NAME}:latest"
fi

# Run main function
main