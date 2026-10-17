# Webhook Integration Setup

This guide shows how to set up GitHub webhooks to automatically trigger the GitHub PR Reviewer pipeline when pull requests are created or updated.

## Overview

The integration uses OpenShift Pipelines (Tekton) Triggers to create an HTTP endpoint that receives GitHub webhook events and starts pipeline runs.

## Components Needed

1. **EventListener**: Receives webhooks from GitHub
2. **TriggerTemplate**: Defines how to create PipelineRuns from webhook data
3. **TriggerBinding**: Extracts parameters from webhook payload
4. **GitHub Webhook**: Configured on your repository

## Setup Steps

### 1. Create TriggerBinding

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-pr-binding
  namespace: openshift-pipelines
spec:
  params:
    - name: github-owner
      value: $(body.repository.owner.login)
    - name: github-repo
      value: $(body.repository.name)
    - name: pr-number
      value: $(body.number)
```

### 2. Create TriggerTemplate

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: github-pr-template
  namespace: openshift-pipelines
spec:
  params:
    - name: github-owner
    - name: github-repo
    - name: pr-number
    - name: review-type
      default: "COMMENT"
    - name: github-token-secret
      default: "github-token"
  
  resourcetemplates:
    - apiVersion: tekton.dev/v1beta1
      kind: PipelineRun
      metadata:
        generateName: github-pr-review-$(uid)-
        namespace: openshift-pipelines
        labels:
          app.kubernetes.io/part-of: github-pr-review
          tekton.dev/event: github-pr
      spec:
        pipelineRef:
          name: github-pr-review-pipeline
        params:
          - name: github-owner
            value: $(tt.params.github-owner)
          - name: github-repo
            value: $(tt.params.github-repo)
          - name: pr-number
            value: $(tt.params.pr-number)
          - name: review-type
            value: $(tt.params.review-type)
        workspaces:
          - name: output-workspace
          - name: github-token-workspace
            secret:
              secretName: $(tt.params.github-token-secret)
```

### 3. Create EventListener

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-pr-listener
  namespace: openshift-pipelines
spec:
  serviceAccountName: pipeline
  triggers:
    - name: github-pr-trigger
      triggerRef:
        name: github-pr-trigger
```

### 4. Create Trigger

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: Trigger
metadata:
  name: github-pr-trigger
  namespace: openshift-pipelines
spec:
  bindings:
    - ref: github-pr-binding
  template:
    ref: github-pr-template
  interceptors:
    - github:
        secretRef:
          secretName: github-webhook-secret
          secretKey: webhook-secret
        eventTypes:
          - pull_request
```

### 5. Create GitHub Webhook Secret

```bash
# Generate a random secret
WEBHOOK_SECRET=$(openssl rand -hex 20)
echo "Generated secret: $WEBHOOK_SECRET"

# Create the secret
oc create secret generic github-webhook-secret \
  --from-literal=webhook-secret=$WEBHOOK_SECRET \
  -n openshift-pipelines
```

### 6. Get EventListener URL

```bash
# Get the route URL
EL_ROUTE=$(oc get route el-github-pr-listener -n openshift-pipelines -o jsonpath='{.spec.host}')
WEBHOOK_URL="https://${EL_ROUTE}"

echo "EventListener URL: $WEBHOOK_URL"
```

### 7. Configure GitHub Webhook

1. Go to your GitHub repository
2. Navigate to **Settings** → **Webhooks**
3. Click **Add webhook**
4. Configure:
   - **Payload URL**: `https://<your-el-route-domain>`
   - **Content type**: `application/json`
   - **Secret**: Use the secret you generated above
   - **Which events**: Select "Let me select individual events"
   - **Pull requests**: ✅ Check this
   - **Active**: ✅ Check this

## Event Types

The webhook listens for the following GitHub events:

- **Pull request opened**: When a new PR is created
- **Pull request synchronized**: When PR is updated with new commits
- **Pull request reopened**: When closed PR is reopened

## Filtering Events

You can modify the Trigger to filter specific events:

```yaml
spec:
  interceptors:
    - github:
        secretRef:
          secretName: github-webhook-secret
          secretKey: webhook-secret
        eventTypes:
          - pull_request
        config:
          filter: >
            body.action == 'opened' || body.action == 'synchronize'
```

## Security Considerations

1. **Webhook Secret**: Always use a secret to verify webhook authenticity
2. **TLS**: Ensure your EventListener route uses HTTPS
3. **RBAC**: Ensure your service account has minimal permissions
4. **Network Policies**: Restrict ingress to necessary namespaces

## Testing

### Manual Test

```bash
# Send a test webhook payload
curl -X POST \
  https://your-el-route.com \
  -H 'Content-Type: application/json' \
  -H 'X-GitHub-Event: pull_request' \
  -d '{
    "action": "opened",
    "repository": {
      "owner": {"login": "your-username"},
      "name": "your-repo"
    },
    "number": 42
  }'
```

### Check PipelineRun Status

```bash
# List recent PipelineRuns
tkn pipelinerun list -n openshift-pipelines

# Check logs
tkn pipelinerun logs <pipelinerun-name> -n openshift-pipelines
```

## Troubleshooting

### Webhook Not Triggering

1. Check EventListener route is accessible
2. Verify GitHub webhook configuration
3. Check EventListener logs: `oc logs -l eventlistener=github-pr-listener -n openshift-pipelines`

### TriggerBinding Issues

1. Verify webhook payload structure
2. Check TriggerBinding extracts correct fields
3. Validate JSONPath expressions

### PipelineRun Failures

1. Check parameters are being passed correctly
2. Verify GitHub token secret exists and has correct permissions
3. Review task logs for specific errors

## Production Considerations

1. **Rate Limiting**: Implement rate limiting to prevent abuse
2. **Logging**: Configure comprehensive logging for debugging
3. **Monitoring**: Set up alerts for failed webhook deliveries
4. **Backup**: Have a manual trigger method as backup
5. **Testing**: Test webhook integration in staging environment first

## Alternative: GitHub App Integration

For more advanced scenarios, consider using a GitHub App instead of webhooks:

- More granular permissions
- Better security
- Webhook reliability
- Installation management

This would require additional setup but provides more robust integration capabilities.