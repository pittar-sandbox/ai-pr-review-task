# GitHub PR Reviewer - Deployment Guide

## Quick Start

This guide will help you deploy the GitHub PR Reviewer Tekton task to your OpenShift 4.22+ cluster.

## Prerequisites

- OpenShift 4.22+ cluster
- OpenShift Pipelines (Tekton) installed
- `oc` CLI configured and logged in
- `podman` for building container images
- GitHub Personal Access Token with `pull_request` scope

## 1. Build and Deploy Container Image

### Option A: Use the build script

```bash
# Make the build script executable
chmod +x build.sh

# Run the build script
./build.sh
```

### Option B: Manual deployment

```bash
# Build the container image
podman build -f containers/Containerfile -t github-pr-reviewer:latest .

# Tag for OpenShift registry
podman tag github-pr-reviewer:latest \
  image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest

# Push to OpenShift registry
podman push image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest
```

## 2. Create GitHub Token Secret

```bash
# Create namespace (if needed)
oc new-project openshift-pipelines

# Create GitHub token secret
oc create secret generic github-token \
  --from-literal=token=your_github_personal_access_token \
  --namespace=openshift-pipelines
```

## 3. Deploy Tekton Task

```bash
# Apply the task definition
oc apply -f github-pr-reviewer-task.yaml
```

## 4. Test the Task

Create a test PipelineRun:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: test-pr-review-
  namespace: openshift-pipelines
spec:
  pipelineRef:
    name: github-pr-review-pipeline
  params:
    - name: github-owner
      value: "your-username"
    - name: github-repo
      value: "your-repo"
    - name: pr-number
      value: "123"
  workspaces:
    - name: github-token-workspace
      secret:
        secretName: github-token
```

Apply it:

```bash
oc apply -f examples/pipeline-example.yaml -n openshift-pipelines
```

## 5. Set Up Webhook Integration (Optional)

For automatic PR review triggering, see `examples/webhook-setup.md`.

## Monitoring and Debugging

### Check task deployment

```bash
oc get task github-pr-reviewer -n openshift-pipelines
```

### View task logs

```bash
tkn taskrun logs <taskrun-name> -n openshift-pipelines
```

### Monitor pipeline runs

```bash
tkn pipelinerun list -n openshift-pipelines
```

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub PR     │───▶│   Webhook        │───▶│ EventListener   │
│   Created/      │    │   Event          │    │ (OpenShift)     │
│   Updated       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TriggerTemplate                               │
│              (Creates PipelineRun)                              │
└─────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PipelineRun                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           github-pr-review-pipeline                       │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │         github-pr-reviewer Task                   │  │ │
│  │  │                                                     │  │ │
│  │  │  1. Extract GitHub token                          │  │ │
│  │  │  2. Run PR analysis (Python)                      │  │ │
│  │  │  3. Submit review to GitHub                      │  │ │
│  │  │  4. Publish results                              │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Automated Code Analysis**: Analyzes PR files for potential issues
- **Security Scanning**: Detects credential leaks and security-sensitive files
- **Comprehensive Reporting**: Generates detailed review comments
- **OpenShift Native**: Optimized for OpenShift 4.22+ and Pipelines
- **Secure**: Runs with non-root user and security context constraints
- **Webhook Integration**: Automatic triggering on PR events

## Security

- Non-root user execution (UID 1001)
- Minimal container permissions
- Secure token handling via Kubernetes secrets
- Read-only root filesystem (where possible)
- Dropped container capabilities

## Troubleshooting

### Container Image Pull Failed

```bash
# Check if image exists in registry
oc get imagestream github-pr-reviewer -n openshift-pipelines

# Verify registry access
podman pull image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest
```

### GitHub Token Issues

```bash
# Verify secret exists
oc get secret github-token -n openshift-pipelines

# Check token format (should be base64 encoded)
oc get secret github-token -o jsonpath='{.data.token}' -n openshift-pipelines | base64 -d
```

### Task Run Failures

```bash
# Check taskrun status
tkn taskrun describe <taskrun-name> -n openshift-pipelines

# View detailed logs
tkn taskrun logs <taskrun-name> -n openshift-pipelines --all
```

## Next Steps

1. **Customize Analysis**: Modify the Python script to add custom review rules
2. **Integrate Notifications**: Add Slack/email notifications for review completion
3. **Scale Testing**: Test with high-volume PR scenarios
4. **Monitor Performance**: Set up metrics and alerting for the integration

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review OpenShift Pipelines documentation
3. Check GitHub API documentation for integration issues
4. Review the main README.md for detailed information