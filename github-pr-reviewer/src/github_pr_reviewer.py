#!/usr/bin/env python3
"""
GitHub Pull Request Reviewer
Automatically reviews pull requests using GitHub API
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from requests.auth import HTTPBasicAuth


class GitHubPRReviewer:
    """Main class for GitHub PR review functionality"""

    def __init__(self, github_token: str, base_url: str = "https://api.github.com", 
                 ai_endpoint: Optional[str] = None, ai_token: Optional[str] = None,
                 ai_model: str = "gpt-3.5-turbo", ai_temperature: float = 0.1):
        """
        Initialize the GitHub PR Reviewer
        
        Args:
            github_token: GitHub personal access token
            base_url: GitHub API base URL
            ai_endpoint: OpenAI-compatible AI endpoint URL
            ai_token: AI service API token
            ai_model: AI model name to use
            ai_temperature: AI response temperature
        """
        self.github_token = github_token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Tekton-PR-Reviewer/1.0"
        }
        
        # AI configuration
        self.ai_endpoint = ai_endpoint
        self.ai_token = ai_token
        self.ai_model = ai_model
        self.ai_temperature = ai_temperature
        self.ai_enabled = bool(ai_endpoint and ai_token)
        
        if self.ai_enabled:
            self.ai_headers = {
                "Authorization": f"Bearer {ai_token}",
                "Content-Type": "application/json",
                "User-Agent": "Tekton-PR-Reviewer-AI/1.0"
            }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if self.ai_enabled:
            self.logger.info(f"AI analysis enabled with endpoint: {ai_endpoint}")
        else:
            self.logger.info("AI analysis disabled - using rule-based analysis only")

    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get detailed information about a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            Dictionary containing PR details
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get PR details: {e}")
            raise

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get list of files changed in the pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of file dictionaries
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get PR files: {e}")
            raise

    def analyze_code_changes(self, pr_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze code changes and identify potential issues
        
        Args:
            pr_files: List of files changed in the PR
            
        Returns:
            Dictionary containing analysis results
        """
        analysis = {
            "total_files": len(pr_files),
            "file_types": {},
            "large_files": [],
            "potential_issues": [],
            "security_concerns": []
        }
        
        for file_info in pr_files:
            filename = file_info["filename"]
            status = file_info["status"]
            additions = file_info.get("additions", 0)
            deletions = file_info.get("deletions", 0)
            
            # Track file types
            extension = filename.split(".")[-1] if "." in filename else "no_extension"
            analysis["file_types"][extension] = analysis["file_types"].get(extension, 0) + 1
            
            # Identify large files
            if additions + deletions > 1000:
                analysis["large_files"].append({
                    "filename": filename,
                    "changes": additions + deletions,
                    "status": status
                })
            
            # Security and quality checks
            self._check_security_issues(filename, file_info, analysis)
        
        return analysis

    def _check_security_issues(self, filename: str, file_info: Dict[str, Any], analysis: Dict[str, Any]):
        """Check for security and quality issues in file changes"""
        
        # Check for potential security issues
        if any(pattern in filename.lower() for pattern in ["password", "key", "secret", "token"]):
            analysis["security_concerns"].append({
                "type": "credential_leak",
                "file": filename,
                "message": "Potential credential or secret in filename"
            })
        
        # Check for common security files
        if filename.endswith((".pem", ".key", ".p12", ".pfx")):
            analysis["security_concerns"].append({
                "type": "key_file",
                "file": filename,
                "message": "Key file added or modified"
            })
        
        # Check file size for suspicious patterns
        if file_info.get("additions", 0) > 10000:
            analysis["potential_issues"].append({
                "type": "large_addition",
                "file": filename,
                "message": f"Large number of lines added: {file_info.get('additions', 0)}"
            })

    def get_file_diff(self, owner: str, repo: str, pr_number: int, filename: str) -> str:
        """
        Get the diff content for a specific file in the PR
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            filename: File to get diff for
            
        Returns:
            File diff content
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            files_data = response.json()
            
            # Find the specific file
            for file_info in files_data:
                if file_info["filename"] == filename:
                    # Get the raw diff
                    diff_url = file_info.get("contents_url")
                    if diff_url:
                        diff_response = requests.get(diff_url + "?ref=" + 
                                                   requests.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}", 
                                                              headers=self.headers).json()["head"]["sha"], 
                                                   headers=self.headers)
                        if diff_response.status_code == 200:
                            return diff_response.text
                    break
            
            return ""
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get file diff for {filename}: {e}")
            return ""

    def analyze_with_ai(self, pr_details: Dict[str, Any], pr_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze PR using AI for more sophisticated insights
        
        Args:
            pr_details: PR details dictionary
            pr_files: List of files changed in the PR
            
        Returns:
            Dictionary containing AI analysis results
        """
        if not self.ai_enabled:
            return {"ai_analysis": "disabled", "insights": []}
        
        ai_analysis = {
            "ai_analysis": "enabled",
            "insights": [],
            "code_quality_score": None,
            "architecture_feedback": [],
            "performance_concerns": [],
            "best_practices": []
        }
        
        try:
            # Prepare analysis prompt
            prompt = self._prepare_ai_prompt(pr_details, pr_files)
            
            # Get AI response
            ai_response = self._call_ai_api(prompt)
            
            if ai_response:
                # Parse AI response
                parsed_ai = self._parse_ai_response(ai_response)
                ai_analysis.update(parsed_ai)
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            ai_analysis["error"] = str(e)
            ai_analysis["fallback"] = True
        
        return ai_analysis

    def _prepare_ai_prompt(self, pr_details: Dict[str, Any], pr_files: List[Dict[str, Any]]) -> str:
        """Prepare a comprehensive prompt for AI analysis"""
        
        file_summary = []
        for file_info in pr_files[:10]:  # Limit to first 10 files for token efficiency
            file_summary.append({
                "filename": file_info["filename"],
                "status": file_info["status"],
                "changes": file_info.get("additions", 0) + file_info.get("deletions", 0)
            })
        
        prompt = f"""
        Analyze this GitHub Pull Request for code quality, security, and best practices.
        
        PR Details:
        - Title: {pr_details.get('title', 'N/A')}
        - Description: {pr_details.get('body', 'N/A')[:500] if pr_details.get('body') else 'N/A'}
        - Author: {pr_details.get('user', {}).get('login', 'N/A')}
        - Files changed: {len(pr_files)}
        
        File Summary (top 10):
        {json.dumps(file_summary, indent=2)}
        
        Please provide analysis in the following JSON format:
        {{
            "overall_score": <1-10 score>,
            "code_quality_insights": ["insight1", "insight2"],
            "security_concerns": ["concern1", "concern2"],
            "performance_observations": ["observation1"],
            "architecture_feedback": ["feedback1"],
            "best_practices": ["practice1"],
            "recommendations": ["rec1", "rec2"]
        }}
        
        Focus on:
        1. Security vulnerabilities
        2. Code quality and maintainability
        3. Performance implications
        4. Architecture and design patterns
        5. Best practices and conventions
        """
        
        return prompt

    def _call_ai_api(self, prompt: str) -> Optional[str]:
        """Call the AI API with the prepared prompt"""
        if not self.ai_enabled:
            return None
        
        payload = {
            "model": self.ai_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert code reviewer analyzing GitHub pull requests. Provide detailed, constructive feedback focusing on security, quality, and best practices. Respond with valid JSON only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": self.ai_temperature,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                self.ai_endpoint.rstrip('/') + "/v1/chat/completions",
                headers=self.ai_headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract AI response
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"AI API call failed: {e}")
            return None

    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response and extract structured insights"""
        try:
            # Try to parse as JSON
            import json
            ai_data = json.loads(ai_response)
            
            return {
                "overall_score": ai_data.get("overall_score"),
                "insights": ai_data.get("code_quality_insights", []),
                "security_concerns": ai_data.get("security_concerns", []),
                "performance_observations": ai_data.get("performance_observations", []),
                "architecture_feedback": ai_data.get("architecture_feedback", []),
                "best_practices": ai_data.get("best_practices", []),
                "recommendations": ai_data.get("recommendations", [])
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse AI response as JSON: {e}")
            # Return as raw text if JSON parsing fails
            return {
                "raw_analysis": ai_response,
                "insights": [f"AI Analysis: {ai_response[:200]}..."],
                "security_concerns": [],
                "performance_observations": [],
                "architecture_feedback": [],
                "best_practices": [],
                "recommendations": []
            }

    def generate_review_comment(self, pr_details: Dict[str, Any], analysis: Dict[str, Any], 
                               ai_analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a comprehensive review comment
        
        Args:
            pr_details: PR details dictionary
            analysis: Analysis results dictionary
            ai_analysis: AI analysis results dictionary (optional)
            
        Returns:
            Formatted review comment
        """
        comment_lines = [
            f"## 🤖 Automated PR Review - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"**PR:** #{pr_details['number']} - {pr_details['title']}",
            f"**Author:** {pr_details['user']['login']}",
            f"**Files Changed:** {analysis['total_files']}",
        ]
        
        # Add AI analysis info if available
        if ai_analysis and ai_analysis.get('ai_analysis') == 'enabled':
            comment_lines.extend([
                f"**AI Score:** {ai_analysis.get('overall_score', 'N/A')}/10",
                ""
            ])
        
        comment_lines.append("")
        
        # Add AI insights section if available
        if ai_analysis and ai_analysis.get('ai_analysis') == 'enabled':
            comment_lines.extend([
                "### 🧠 AI Analysis",
                ""
            ])
            
            if ai_analysis.get('insights'):
                comment_lines.extend([
                    "**Code Quality Insights:**",
                    ""
                ])
                for insight in ai_analysis['insights']:
                    comment_lines.append(f"- {insight}")
                comment_lines.append("")
            
            if ai_analysis.get('architecture_feedback'):
                comment_lines.extend([
                    "**Architecture Feedback:**",
                    ""
                ])
                for feedback in ai_analysis['architecture_feedback']:
                    comment_lines.append(f"- {feedback}")
                comment_lines.append("")
            
            if ai_analysis.get('performance_observations'):
                comment_lines.extend([
                    "**Performance Observations:**",
                    ""
                ])
                for obs in ai_analysis['performance_observations']:
                    comment_lines.append(f"- {obs}")
                comment_lines.append("")
            
            if ai_analysis.get('best_practices'):
                comment_lines.extend([
                    "**Best Practices:**",
                    ""
                ])
                for practice in ai_analysis['best_practices']:
                    comment_lines.append(f"- {practice}")
                comment_lines.append("")
        
        # Add file type breakdown
        if analysis['file_types']:
            comment_lines.extend([
                "### 📊 File Type Summary",
                ""
            ])
            for file_type, count in sorted(analysis['file_types'].items(), key=lambda x: x[1], reverse=True):
                comment_lines.append(f"- `{file_type}`: {count} file(s)")
            comment_lines.append("")
        
        # Add potential issues
        if analysis['potential_issues']:
            comment_lines.extend([
                "### ⚠️ Potential Issues",
                ""
            ])
            for issue in analysis['potential_issues']:
                comment_lines.append(f"- **{issue['type']}** in `{issue['file']}`: {issue['message']}")
            comment_lines.append("")
        
        # Add security concerns
        if analysis['security_concerns']:
            comment_lines.extend([
                "### 🔒 Security Concerns",
                ""
            ])
            for concern in analysis['security_concerns']:
                comment_lines.append(f"- **{concern['type']}** in `{concern['file']}`: {concern['message']}")
            comment_lines.append("")
        
        # Add large files
        if analysis['large_files']:
            comment_lines.extend([
                "### 📦 Large Files",
                "",
                "These files have significant changes:",
                ""
            ])
            for file_info in analysis['large_files']:
                comment_lines.append(f"- `{file_info['filename']}`: {file_info['changes']} changes")
            comment_lines.append("")
        
        # Add AI security concerns if available
        if ai_analysis and ai_analysis.get('ai_analysis') == 'enabled' and ai_analysis.get('security_concerns'):
            comment_lines.extend([
                "### 🔐 AI Security Analysis",
                ""
            ])
            for concern in ai_analysis['security_concerns']:
                comment_lines.append(f"- {concern}")
            comment_lines.append("")
        
        # Add recommendations
        comment_lines.extend([
            "### 💡 Recommendations",
            ""
        ])
        
        # Add AI recommendations if available
        if ai_analysis and ai_analysis.get('recommendations'):
            for rec in ai_analysis['recommendations']:
                comment_lines.append(f"- {rec}")
            comment_lines.append("")
        
        # Add standard recommendations
        standard_recs = [
            "Review security concerns carefully",
            "Consider breaking large files into smaller commits", 
            "Ensure adequate test coverage for changes",
            "Verify that no secrets or credentials are exposed"
        ]
        
        for rec in standard_recs:
            comment_lines.append(f"- {rec}")
        comment_lines.append("")
        
        # Add footer based on AI analysis
        if ai_analysis and ai_analysis.get('ai_analysis') == 'enabled':
            if ai_analysis.get('overall_score', 0) >= 7:
                comment_lines.append("✅ **High-quality PR with AI approval.**")
            else:
                comment_lines.append("⚠️ **AI suggests review before merging.**")
        elif pr_details.get('draft'):
            comment_lines.append("📝 **Note:** This is a draft PR and may need additional review.")
        else:
            comment_lines.append("✅ **Automated review completed successfully.**")
        
        return "\n".join(comment_lines)

    def submit_review(self, owner: str, repo: str, pr_number: int, body: str, event: str = "COMMENT") -> bool:
        """
        Submit a review comment to the pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Review comment body
            event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES)
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        
        data = {
            "body": body,
            "event": event
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            self.logger.info(f"Review submitted successfully for PR #{pr_number}")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to submit review: {e}")
            return False

    def run_review(self, owner: str, repo: str, pr_number: int) -> bool:
        """
        Run complete review process
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting review for PR #{pr_number} in {owner}/{repo}")
            
            # Get PR details
            pr_details = self.get_pr_details(owner, repo, pr_number)
            self.logger.info(f"PR Title: {pr_details['title']}")
            
            # Get PR files
            pr_files = self.get_pr_files(owner, repo, pr_number)
            self.logger.info(f"Files changed: {len(pr_files)}")
            
            # Analyze changes (rule-based)
            analysis = self.analyze_code_changes(pr_files)
            
            # AI Analysis (if enabled)
            ai_analysis = {}
            if self.ai_enabled:
                self.logger.info("Starting AI analysis...")
                ai_analysis = self.analyze_with_ai(pr_details, pr_files)
                if ai_analysis.get('error'):
                    self.logger.warning(f"AI analysis failed: {ai_analysis['error']}")
                else:
                    self.logger.info("AI analysis completed successfully")
            
            # Generate review comment (with AI insights if available)
            review_comment = self.generate_review_comment(pr_details, analysis, ai_analysis)
            
            # Submit review
            success = self.submit_review(owner, repo, pr_number, review_comment)
            
            if success:
                self.logger.info("Review process completed successfully")
                
                # Output analysis as JSON for downstream processing
                output_data = {
                    "success": True,
                    "pr_number": pr_number,
                    "analysis": analysis,
                    "ai_analysis": ai_analysis,
                    "review_submitted": True
                }
                print("GITHUB_PR_ANALYSIS_OUTPUT:")
                print(json.dumps(output_data, indent=2))
            else:
                self.logger.error("Failed to submit review")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Review process failed: {e}")
            output_data = {
                "success": False,
                "pr_number": pr_number,
                "error": str(e),
                "review_submitted": False
            }
            print("GITHUB_PR_ANALYSIS_OUTPUT:")
            print(json.dumps(output_data, indent=2))
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GitHub PR Reviewer")
    parser.add_argument("--owner", required=True, help="Repository owner")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument("--pr-number", type=int, required=True, help="Pull request number")
    parser.add_argument("--github-token", required=True, help="GitHub token")
    parser.add_argument("--api-url", default="https://api.github.com", help="GitHub API URL")
    
    # AI-related arguments
    parser.add_argument("--ai-endpoint", help="OpenAI-compatible AI endpoint URL")
    parser.add_argument("--ai-token", help="AI service API token")
    parser.add_argument("--ai-model", default="gpt-3.5-turbo", help="AI model name")
    parser.add_argument("--ai-temperature", type=float, default=0.1, help="AI temperature")
    
    args = parser.parse_args()
    
    # Validate GitHub token
    if not args.github_token:
        print("Error: GitHub token is required", file=sys.stderr)
        sys.exit(1)
    
    # Validate AI parameters consistency
    if (args.ai_endpoint and not args.ai_token) or (args.ai_token and not args.ai_endpoint):
        print("Error: Both --ai-endpoint and --ai-token must be provided together", file=sys.stderr)
        sys.exit(1)
    
    # Initialize reviewer with AI capabilities
    reviewer = GitHubPRReviewer(
        github_token=args.github_token, 
        base_url=args.api_url,
        ai_endpoint=args.ai_endpoint,
        ai_token=args.ai_token,
        ai_model=args.ai_model,
        ai_temperature=args.ai_temperature
    )
    
    success = reviewer.run_review(args.owner, args.repo, args.pr_number)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()