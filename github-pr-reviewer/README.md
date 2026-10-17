# GitHub PR Reviewer Tekton Task

This Tekton task automatically reviews GitHub pull requests by analyzing code changes and providing structured feedback. It integrates with OpenShift Pipelines and is triggered by GitHub webhooks.

## Features

- **Automated Code Analysis**: Analyzes PR files for potential issues, security concerns, and code quality
- **AI-Powered Insights**: Optional AI analysis using OpenAI-compatible endpoints (vLLM, OpenAI, etc.)
- **Security Scanning**: Identifies potential credential leaks and security-sensitive files
- **Comprehensive Reporting**: Generates detailed review comments with AI and rule-based analysis
- **OpenShift Native**: Designed specifically for OpenShift 4.22 with OpenShift Pipelines
- **Secure by Default**: Runs with non-root user and security context constraints

## Components

1. **Python Reviewer** (`src/github_pr_reviewer.py`): Core logic for PR analysis
2. **Container Image** (`containers/Containerfile`): UBI 9-based container with dependencies
3. **Tekton Task** (`github-pr-reviewer-task.yaml`): Pipeline task definition
4. **Documentation**: Usage guides and examples

## Prerequisites

- OpenShift 4.22+ cluster
- OpenShift Pipelines (Tekton) installed
- GitHub personal access token with `pull_request` scope
- Container registry access (for building and storing images)
- **Optional**: OpenAI-compatible AI endpoint (vLLM, OpenAI, etc.) and API token for AI-powered analysis

## Installation

### 1. Build Container Image

```bash
# Build the container image
podman build -f containers/Containerfile -t github-pr-reviewer:latest .

# Tag for your OpenShift registry
podman tag github-pr-reviewer:latest image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest

# Push to OpenShift registry
podman push image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest
```

### 2. Create GitHub Token Secret

```bash
# Create namespace (if needed)
oc new-project openshift-pipelines

# Create GitHub token secret
oc create secret generic github-token \
  --from-literal=token=your_github_personal_access_token \
  --namespace=openshift-pipelines
```

### 3. Create AI Token Secret (Optional for AI Analysis)

```bash
# Create AI token secret (only needed if you want AI-powered analysis)
oc create secret generic ai-token \
  --from-literal=token=your_ai_service_api_token \
  --namespace=openshift-pipelines

# Example endpoints that work:
# - OpenAI: https://api.openai.com/v1
# - vLLM: https://your-vllm-endpoint.com/v1
# - Other OpenAI-compatible APIs
```

### 4. Apply Tekton Task

```bash
# Apply the task definition
oc apply -f github-pr-reviewer-task.yaml
```

## Usage

### Basic Pipeline Example

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: github-pr-review-pipeline
  namespace: openshift-pipelines
spec:
  params:
    - name: github-owner
      type: string
    - name: github-repo
      type: string
    - name: pr-number
      type: string
  
  tasks:
    - name: pr-review
      taskRef:
        name: github-pr-reviewer
      params:
        - name: owner
          value: $(params.github-owner)
        - name: repo
          value: $(params.github-repo)
        - name: pr-number
          value: $(params.pr-number)
        - name: image
          value: image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest
      workspaces:
        - name: github-token
          secret:
            secretName: github-token
```

### AI-Enhanced Pipeline Example

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: github-pr-review-pipeline-ai
  namespace: openshift-pipelines
spec:
  params:
    - name: github-owner
      type: string
    - name: github-repo
      type: string
    - name: pr-number
      type: string
    - name: ai-endpoint
      type: string
      default: "https://api.openai.com/v1"
    - name: ai-model
      type: string
      default: "gpt-3.5-turbo"
  
  tasks:
    - name: pr-review
      taskRef:
        name: github-pr-reviewer
      params:
        - name: owner
          value: $(params.github-owner)
        - name: repo
          value: $(params.github-repo)
        - name: pr-number
          value: $(params.pr-number)
        - name: ai-endpoint
          value: $(params.ai-endpoint)
        - name: ai-model
          value: $(params.ai-model)
        - name: image
          value: image-registry.openshift-image-registry.svc:5000/openshift-pipelines/github-pr-reviewer:latest
      workspaces:
        - name: github-token
          secret:
            secretName: github-token
        - name: ai-token
          secret:
            secretName: ai-token
```

### Webhook Trigger Example

For integration with GitHub webhooks, you can use EventListeners and Triggers:

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
    - name: github-token-secret
      default: github-token
  
  resourcetemplates:
    - apiVersion: tekton.dev/v1beta1
      kind: PipelineRun
      metadata:
        generateName: github-pr-review-$(uid)-
        namespace: openshift-pipelines
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
        workspaces:
          - name: github-token
            secret:
              secretName: $(tt.params.github-token-secret)
```

## Parameters

### Standard Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `github-token-secret` | string | No | `github-token` | Secret name containing GitHub token |
| `github-token-key` | string | No | `token` | Secret key containing GitHub token |
| `owner` | string | Yes | - | GitHub repository owner |
| `repo` | string | Yes | - | GitHub repository name |
| `pr-number` | string | Yes | - | Pull request number |
| `api-url` | string | No | `https://api.github.com` | GitHub API URL |
| `review-type` | string | No | `COMMENT` | Review event type |
| `image` | string | No | - | Container image to use |
| `verbosity` | string | No | `INFO` | Log verbosity level |

### AI Analysis Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ai-endpoint` | string | No | - | OpenAI-compatible AI endpoint URL |
| `ai-token-secret` | string | No | `ai-token` | Secret name containing AI token |
| `ai-token-key` | string | No | `token` | Secret key containing AI token |
| `ai-model` | string | No | `gpt-3.5-turbo` | AI model name to use |
| `ai-temperature` | string | No | `0.1` | AI temperature for responses |

## AI Analysis

The GitHub PR Reviewer supports AI-powered analysis using OpenAI-compatible endpoints. This provides more sophisticated insights beyond rule-based analysis.

### Supported AI Services

- **OpenAI GPT models** (GPT-3.5, GPT-4, etc.)
- **vLLM** (self-hosted or managed)
- **Other OpenAI-compatible APIs**

### AI Analysis Features

- **Code Quality Scoring**: AI assigns a score (1-10) to the PR
- **Architecture Feedback**: AI insights on code structure and design
- **Performance Analysis**: AI identifies potential performance issues
- **Best Practices**: AI suggests improvements and best practices
- **Security Analysis**: AI can identify security vulnerabilities
- **Comprehensive Recommendations**: AI provides detailed suggestions

### AI Configuration

To enable AI analysis, provide:
1. **AI Endpoint**: OpenAI-compatible API endpoint URL
2. **AI Token**: API token for the AI service
3. **Model Name**: Specific model to use (optional, defaults to gpt-3.5-turbo)

Example AI endpoint configurations:
```yaml
# OpenAI
ai-endpoint: "https://api.openai.com/v1"

# vLLM (self-hosted)
ai-endpoint: "https://your-vllm-server.com/v1"

# Other compatible services
ai-endpoint: "https://your-ai-service.com/v1"
```

## Workspaces

| Workspace | Purpose | Required |
|-----------|---------|----------|
| `output` | Output artifacts and analysis results | No |
| `github-token` | GitHub token secret | No |

## Outputs

The task generates several outputs:

1. **GitHub Review Comment**: Automatically posted to the PR
2. **Analysis Results**: JSON output with detailed analysis
3. **Review Summary**: Text summary in output workspace

## Security Considerations

- Runs as non-root user (UID 1001)
- Read-only root filesystem (where possible)
- Dropped all capabilities
- No privilege escalation
- Token handled securely through workspaces/secrets

## Troubleshooting

### Common Issues

1. **GitHub Token Not Found**
   - Verify secret exists: `oc get secret github-token`
   - Check secret contains `token` key
   - Ensure workspace is properly mounted

2. **AI Analysis Issues**
   - Verify AI endpoint is accessible and correct
   - Check AI token secret: `oc get secret ai-token`
   - Ensure AI token has proper permissions
   - Verify AI model name is valid for your endpoint
   - Check AI service rate limits and quotas

3. **Container Image Pull Failures**
   - Verify image exists in registry
   - Check image pull policy
   - Ensure registry is accessible

4. **Permission Denied**
   - Verify service account has necessary permissions
   - Check RBAC settings for Tekton

### Logs

```bash
# View task logs
tkn taskrun logs <taskrun-name> -n openshift-pipelines

# View specific step logs
tkn taskrun logs <taskrun-name> -s step-name -n openshift-pipelines
```

## GitHub Setup

1. **Create Personal Access Token**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Generate new token with `pull_request` scope
   - Copy token securely

2. **Configure Webhook**:
   - Go to repository → Settings → Webhooks
   - Add webhook for `pull_request` events
   - Set payload URL to your EventListener
   - Use content type `application/json`

## Development

### Local Testing

```bash
# Test Python script locally (rule-based analysis only)
export GITHUB_TOKEN="your_token"
python3 src/github_pr_reviewer.py \
  --owner your-username \
  --repo your-repo \
  --pr-number 123 \
  --github-token $GITHUB_TOKEN

# Test with AI analysis
export GITHUB_TOKEN="your_token"
export AI_TOKEN="your_ai_token"
python3 src/github_pr_reviewer.py \
  --owner your-username \
  --repo your-repo \
  --pr-number 123 \
  --github-token $GITHUB_TOKEN \
  --ai-endpoint https://api.openai.com/v1 \
  --ai-token $AI_TOKEN \
  --ai-model gpt-3.5-turbo
```

### Container Testing

```bash
# Test container locally (rule-based analysis only)
podman run --rm -e GITHUB_TOKEN=$GITHUB_TOKEN \
  github-pr-reviewer:latest \
  --owner your-username \
  --repo your-repo \
  --pr-number 123

# Test with AI analysis
podman run --rm \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e AI_TOKEN=$AI_TOKEN \
  github-pr-reviewer:latest \
  --owner your-username \
  --repo your-repo \
  --pr-number 123 \
  --ai-endpoint https://api.openai.com/v1 \
  --ai-model gpt-3.5-turbo
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.