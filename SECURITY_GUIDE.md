# Security Best Practices Guide

## 🚨 **NEVER Commit These to Git:**

### API Tokens & Keys
- GitHub tokens: `ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
- OpenAI API keys: `sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
- Any other service API keys
- Bearer tokens or JWTs
- Database connection strings with passwords
- Cloud provider credentials (AWS keys, etc.)

### Real Examples to Avoid:
```bash
❌ BAD - Never commit these:
ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
sk-1234567890abcdef1234567890abcdef1234567890abcdef
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### ✅ **Good Examples:**
```bash
✅ GOOD - Safe placeholders:
--github-token <your-token-here>
--ai-token <your-api-key-here>
GITHUB_TOKEN="your_github_token"
AI_TOKEN="your_ai_service_token"
```

## **How to Prevent Token Leaks:**

### 1. Use Environment Variables
```bash
export GITHUB_TOKEN="your_token_here"
export AI_TOKEN="your_ai_token_here"

# Use in code:
token = os.environ.get("GITHUB_TOKEN")
```

### 2. Use Secret Management
```yaml
# Kubernetes/OpenShift secrets
apiVersion: v1
kind: Secret
metadata:
  name: github-token
type: Opaque
data:
  token: <base64-encoded-token>
```

### 3. Never Hardcode in Examples
```python
❌ BAD:
token = "ghp_real_token_here"

✅ GOOD:
token = os.environ.get("GITHUB_TOKEN", "placeholder_token")
```

### 4. Use Git Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
repos:
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
  - id: detect-secrets
    args: ['--baseline', '.secrets.baseline']
```

## **If You Accidentally Commit a Token:**

### 1. **Immediately Revoke the Token**
- GitHub: Settings → Developer settings → Personal access tokens → Delete
- OpenAI: API keys section → Delete key
- Other services: Check their dashboard/settings

### 2. **Remove from Repository**
```bash
# Remove from current commit
git rm sensitive_file
git commit -m "Remove sensitive data"

# Or if already pushed, you need to rewrite history:
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/sensitive/file' \
  --prune-empty --tag-name-filter cat -- --all
```

### 3. **Force Push (Use with Caution)**
```bash
git push origin --force
```

### 4. **Notify Your Team**
- Let team members know about the incident
- Check if the token was used inappropriately
- Review access logs if available

## **GitHub's Automatic Protection:**

GitHub automatically:
- Scans repositories for exposed tokens
- Sends alerts to repository owners
- Can block pushes containing known token patterns
- May contact service providers to revoke compromised tokens

## **Safe Testing Practices:**

### 1. Use Test/Dummy Tokens
```python
# In tests
reviewer = GitHubPRReviewer("dummy-token-for-testing")

# Not real tokens
reviewer = GitHubPRReviewer("ghp_real_token_never_commit")
```

### 2. Mock External Services
```python
from unittest.mock import patch

@patch('requests.get')
def test_github_api(mock_get):
    mock_get.return_value.json.return_value = {"test": "data"}
    # Test your code
```

### 3. Document Setup, Don't Embed
```
README.md:
1. Get your GitHub token from: https://github.com/settings/tokens
2. Create secret: oc create secret generic github-token --from-literal=token=YOUR_TOKEN
3. Don't commit your actual token!
```

## **Red Flags to Watch For:**
- Long alphanumeric strings (40+ characters)
- Strings starting with `ghp_`, `sk-`, `Bearer`
- URLs with embedded tokens
- Configuration files with real credentials
- Log files containing authentication data

---

**Remember: When in doubt, don't commit it!**