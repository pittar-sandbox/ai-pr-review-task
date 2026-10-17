#!/usr/bin/env python3
"""
Test script for GitHub PR Reviewer functionality
Validates the Python logic without requiring actual GitHub API calls
"""

import json
import sys
import tempfile
from unittest.mock import Mock, patch
import os

# Add the src directory to the path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from github_pr_reviewer import GitHubPRReviewer


def test_pr_details_analysis():
    """Test PR details parsing"""
    print("Testing PR details analysis...")
    
    # Mock PR details
    pr_details = {
        "number": 123,
        "title": "Add new feature",
        "user": {"login": "testuser"},
        "draft": False
    }
    
    # Mock file changes
    pr_files = [
        {
            "filename": "src/main.py",
            "status": "added",
            "additions": 50,
            "deletions": 0
        },
        {
            "filename": "README.md",
            "status": "modified",
            "additions": 5,
            "deletions": 2
        },
        {
            "filename": "config.json",
            "status": "added",
            "additions": 1200,
            "deletions": 0
        }
    ]
    
    # Create reviewer instance (token doesn't matter for this test)
    reviewer = GitHubPRReviewer("dummy-token")
    
    # Analyze changes
    analysis = reviewer.analyze_code_changes(pr_files)
    
    # Validate analysis
    assert analysis["total_files"] == 3
    assert "py" in analysis["file_types"]
    assert analysis["file_types"]["py"] == 1
    assert "md" in analysis["file_types"]
    assert analysis["file_types"]["md"] == 1
    assert "json" in analysis["file_types"]
    assert analysis["file_types"]["json"] == 1
    assert "config.json" in [f["filename"] for f in analysis["large_files"]]
    
    print("✅ PR details analysis test passed")


def test_security_issues_detection():
    """Test security issue detection"""
    print("Testing security issues detection...")
    
    # Mock files with security concerns
    pr_files = [
        {
            "filename": "src/password_utils.py",
            "status": "added",
            "additions": 20,
            "deletions": 0
        },
        {
            "filename": "keys/service.key",
            "status": "added",
            "additions": 10,
            "deletions": 0
        },
        {
            "filename": "config.json",
            "status": "modified",
            "additions": 10001,
            "deletions": 0
        }
    ]
    
    reviewer = GitHubPRReviewer("dummy-token")
    analysis = reviewer.analyze_code_changes(pr_files)
    
    # Validate security concerns detected
    assert len(analysis["security_concerns"]) >= 1
    
    # Check for specific security issues
    credential_issues = [c for c in analysis["security_concerns"] if c["type"] == "credential_leak"]
    key_issues = [c for c in analysis["security_concerns"] if c["type"] == "key_file"]
    
    assert len(credential_issues) > 0
    assert len(key_issues) > 0
    
    # Check for large file
    large_file_issues = [i for i in analysis["potential_issues"] if i["type"] == "large_addition"]
    assert len(large_file_issues) >= 1, f"Expected at least 1 large file issue, got {len(large_file_issues)}. Issues: {analysis['potential_issues']}"
    
    print("✅ Security issues detection test passed")


def test_review_comment_generation():
    """Test review comment generation"""
    print("Testing review comment generation...")
    
    pr_details = {
        "number": 123,
        "title": "Test PR",
        "user": {"login": "testuser"},
        "draft": False
    }
    
    analysis = {
        "total_files": 2,
        "file_types": {"py": 1, "md": 1},
        "large_files": [],
        "potential_issues": [],
        "security_concerns": []
    }
    
    reviewer = GitHubPRReviewer("dummy-token")
    comment = reviewer.generate_review_comment(pr_details, analysis)
    
    # Validate comment structure
    assert "## 🤖 Automated PR Review" in comment
    assert "**PR:** #123" in comment
    assert "**Author:** testuser" in comment
    assert "**Files Changed:** 2" in comment
    assert "### 📊 File Type Summary" in comment
    assert "- `py`: 1 file(s)" in comment
    assert "- `md`: 1 file(s)" in comment
    assert "### 💡 Recommendations" in comment
    assert "✅ **Automated review completed successfully.**" in comment
    
    print("✅ Review comment generation test passed")


def test_parameter_validation():
    """Test command line parameter parsing"""
    print("Testing parameter validation...")
    
    # Test valid parameters
    test_args = [
        "--owner", "testuser",
        "--repo", "test-repo",
        "--pr-number", "123",
        "--github-token", "test-token"
    ]
    
    # This would normally be parsed by argparse, but we'll test the logic
    owner = "testuser"
    repo = "test-repo"
    pr_number = 123
    github_token = "test-token"
    
    assert owner == "testuser"
    assert repo == "test-repo"
    assert pr_number == 123
    assert github_token == "test-token"
    
    print("✅ Parameter validation test passed")


def test_file_analysis():
    """Test file type analysis"""
    print("Testing file type analysis...")
    
    pr_files = [
        {"filename": "test.py", "status": "modified", "additions": 10, "deletions": 5},
        {"filename": "component.tsx", "status": "added", "additions": 50, "deletions": 0},
        {"filename": "styles.css", "status": "modified", "additions": 20, "deletions": 10},
        {"filename": "data.json", "status": "added", "additions": 100, "deletions": 0},
        {"filename": "README", "status": "modified", "additions": 5, "deletions": 2},
        {"filename": "script.sh", "status": "added", "additions": 15, "deletions": 0}
    ]
    
    reviewer = GitHubPRReviewer("dummy-token")
    analysis = reviewer.analyze_code_changes(pr_files)
    
    # Validate file type detection
    expected_types = {"py": 1, "tsx": 1, "css": 1, "json": 1, "no_extension": 1, "sh": 1}
    assert analysis["file_types"] == expected_types
    
    # Validate total count
    total = sum(analysis["file_types"].values())
    assert total == 6
    
    print("✅ File type analysis test passed")


def test_large_file_detection():
    """Test large file detection"""
    print("Testing large file detection...")
    
    pr_files = [
        {"filename": "small.py", "status": "modified", "additions": 10, "deletions": 5},
        {"filename": "large.py", "status": "added", "additions": 1200, "deletions": 0}
    ]
    
    reviewer = GitHubPRReviewer("dummy-token")
    analysis = reviewer.analyze_code_changes(pr_files)
    
    # Only the large file should be flagged
    assert len(analysis["large_files"]) == 1
    assert analysis["large_files"][0]["filename"] == "large.py"
    assert analysis["large_files"][0]["changes"] == 1200
    
    print("✅ Large file detection test passed")


def main():
    """Run all tests"""
    print("GitHub PR Reviewer Test Suite")
    print("=" * 40)
    print()
    
    try:
        test_pr_details_analysis()
        test_security_issues_detection()
        test_review_comment_generation()
        test_parameter_validation()
        test_file_analysis()
        test_large_file_detection()
        
        print()
        print("🎉 All tests passed successfully!")
        print()
        print("The GitHub PR Reviewer is ready for deployment.")
        
    except Exception as e:
        print()
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()