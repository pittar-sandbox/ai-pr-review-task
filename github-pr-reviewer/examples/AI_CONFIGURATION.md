# AI Configuration Examples

This document provides examples for configuring AI-powered analysis in the GitHub PR Reviewer.

## Supported AI Services

### OpenAI
```yaml
ai-endpoint: "https://api.openai.com/v1"
ai-model: "gpt-3.5-turbo"
# or ai-model: "gpt-4"
```

### vLLM (Self-hosted)
```yaml
ai-endpoint: "https://your-vllm-server.com/v1"
ai-model: "meta-llama/Llama-2-7b-chat-hf"
# or your custom model
```

### Other OpenAI-Compatible Services
```yaml
ai-endpoint: "https://your-ai-service.com/v1"
ai-model: "your-model-name"
```

## Pipeline Examples

### Minimal AI Configuration
```yaml
params:
  - name: ai-endpoint
    value: "https://api.openai.com/v1"
  - name: ai-model
    value: "gpt-3.5-turbo"
```

### Advanced AI Configuration
```yaml
params:
  - name: ai-endpoint
    value: "https://your-vllm-server.com/v1"
  - name: ai-model
    value: "meta-llama/Llama-2-13b-chat-hf"
  - name: ai-temperature
    value: "0.2"
```

### Environment Variables
```bash
# For local testing
export AI_TOKEN="your-ai-api-token"
export AI_ENDPOINT="https://api.openai.com/v1"
export AI_MODEL="gpt-4"
```

## AI Analysis Features

When AI analysis is enabled, the PR review will include:

1. **Overall Quality Score** (1-10 scale)
2. **Code Quality Insights**
3. **Security Analysis** 
4. **Performance Observations**
5. **Architecture Feedback**
6. **Best Practices Recommendations**
7. **Detailed Suggestions**

## AI Token Security

- Store AI tokens in Kubernetes secrets (recommended)
- Use workspaces for secure token mounting
- Never commit tokens to version control
- Rotate tokens regularly
- Use least-privilege API keys

## Troubleshooting

### AI Endpoint Issues
- Verify endpoint URL is correct and accessible
- Check if the endpoint supports OpenAI-compatible API
- Ensure proper authentication headers

### Token Issues  
- Verify token has proper permissions
- Check token expiration/validity
- Ensure token matches the endpoint service

### Model Issues
- Verify model name is available on your endpoint
- Check model compatibility with your AI service
- Ensure sufficient quota/limits

### Rate Limiting
- AI services often have rate limits
- Implement retry logic for production use
- Consider token bucket for high-volume scenarios