#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Git Commit Tool with Gemini AI Integration
Automatically generates informative commit messages using Google's Gemini AI
"""

import subprocess
import sys
import os
import json
import argparse
from typing import List, Optional, Dict
import requests
from datetime import datetime

class SmartCommit:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the SmartCommit tool"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            print("⚠️  Warning: No Gemini API key found. Set GEMINI_API_KEY environment variable or pass --api-key")

        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    def run_git_command(self, command: List[str]) -> tuple[str, str, int]:
        """Run a git command and return stdout, stderr, and return code"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def check_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        stdout, stderr, code = self.run_git_command(['git', 'rev-parse', '--git-dir'])
        return code == 0

    def get_git_status(self) -> str:
        """Get git status information"""
        stdout, stderr, code = self.run_git_command(['git', 'status', '--porcelain'])
        if code != 0:
            raise Exception(f"Failed to get git status: {stderr}")
        return stdout

    def get_git_diff(self, staged: bool = True) -> str:
        """Get git diff (staged or unstaged changes)"""
        cmd = ['git', 'diff']
        if staged:
            cmd.append('--staged')

        stdout, stderr, code = self.run_git_command(cmd)
        if code != 0:
            print(f"Warning: Failed to get diff: {stderr}")
            return ""
        return stdout

    def get_recent_commits(self, count: int = 5) -> str:
        """Get recent commit messages for context"""
        stdout, stderr, code = self.run_git_command([
            'git', 'log', f'-{count}', '--oneline', '--no-merges'
        ])
        if code != 0:
            return ""
        return stdout

    def analyze_changes(self) -> Dict[str, any]:
        """Analyze the current changes in the repository"""
        status = self.get_git_status()
        staged_diff = self.get_git_diff(staged=True)
        unstaged_diff = self.get_git_diff(staged=False)
        recent_commits = self.get_recent_commits()

        # Parse status to categorize changes
        added_files = []
        modified_files = []
        deleted_files = []
        renamed_files = []

        for line in status.split('\n'):
            if not line.strip():
                continue

            status_code = line[:2]
            filename = line[3:]

            if 'A' in status_code:
                added_files.append(filename)
            elif 'M' in status_code:
                modified_files.append(filename)
            elif 'D' in status_code:
                deleted_files.append(filename)
            elif 'R' in status_code:
                renamed_files.append(filename)

        return {
            'added_files': added_files,
            'modified_files': modified_files,
            'deleted_files': deleted_files,
            'renamed_files': renamed_files,
            'staged_diff': staged_diff,
            'unstaged_diff': unstaged_diff,
            'recent_commits': recent_commits,
            'total_changes': len(added_files) + len(modified_files) + len(deleted_files) + len(renamed_files)
        }

    def generate_commit_message(self, changes: Dict[str, any]) -> str:
        """Generate commit message using Gemini AI"""
        if not self.api_key:
            return self.generate_fallback_message(changes)

        # Prepare context for Gemini
        context = self.prepare_context_for_ai(changes)

        prompt = f"""
You are an expert software developer tasked with writing a clear, informative git commit message.

Based on the following code changes and context, generate a commit message that follows these guidelines:
1. Use conventional commit format: type(scope): description
2. Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
3. Keep the first line under 50 characters
4. Be specific about what changed and why
5. Use imperative mood (e.g., "Add feature" not "Added feature")

Context:
{context}

Generate only the commit message, nothing else. Make it informative and professional.
"""

        try:
            response = self.call_gemini_api(prompt)
            if response:
                return response.strip()
        except Exception as e:
            print(f"⚠️  Failed to generate AI commit message: {e}")

        return self.generate_fallback_message(changes)

    def prepare_context_for_ai(self, changes: Dict[str, any]) -> str:
        """Prepare a context string for the AI"""
        context_parts = []

        # File changes summary
        if changes['added_files']:
            context_parts.append(f"Added files: {', '.join(changes['added_files'][:5])}")
        if changes['modified_files']:
            context_parts.append(f"Modified files: {', '.join(changes['modified_files'][:5])}")
        if changes['deleted_files']:
            context_parts.append(f"Deleted files: {', '.join(changes['deleted_files'][:5])}")
        if changes['renamed_files']:
            context_parts.append(f"Renamed files: {', '.join(changes['renamed_files'][:5])}")

        # Recent commits for context
        if changes['recent_commits']:
            context_parts.append(f"Recent commits:\n{changes['recent_commits']}")

        # Diff summary (truncated to avoid token limits)
        if changes['staged_diff']:
            diff_lines = changes['staged_diff'].split('\n')[:50]  # Limit to 50 lines
            context_parts.append(f"Code changes:\n" + '\n'.join(diff_lines))

        return '\n\n'.join(context_parts)

    def call_gemini_api(self, prompt: str) -> Optional[str]:
        """Call Gemini AI API"""
        headers = {
            'Content-Type': 'application/json',
        }

        data = {
            'contents': [{
                'parts': [{
                    'text': prompt
                }]
            }],
            'generationConfig': {
                'temperature': 0.3,
                'maxOutputTokens': 100,
                'topP': 0.8,
                'topK': 40
            }
        }

        url = f"{self.gemini_url}?key={self.api_key}"

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()

            # Debug: Print the response structure for troubleshooting
            # print(f"DEBUG: API Response: {json.dumps(result, indent=2)}")

            # Check for error in response
            if 'error' in result:
                raise Exception(f"API Error: {result['error'].get('message', 'Unknown error')}")

            # Extract the generated text
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        return parts[0]['text']
                elif 'text' in candidate:
                    # Alternative response format
                    return candidate['text']

            # If we get here, the response format is unexpected
            raise Exception(f"Unexpected API response format: {result}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")
        except KeyError as e:
            raise Exception(f"Response parsing error - missing key: {e}")
        except Exception as e:
            raise Exception(f"API call failed: {e}")

        return None

    def generate_fallback_message(self, changes: Dict[str, any]) -> str:
        """Generate a basic commit message without AI"""
        if changes['total_changes'] == 0:
            return "chore: update files"

        # Determine primary action
        if changes['added_files'] and not changes['modified_files'] and not changes['deleted_files']:
            if len(changes['added_files']) == 1:
                return f"feat: add {os.path.basename(changes['added_files'][0])}"
            else:
                return f"feat: add {len(changes['added_files'])} new files"

        elif changes['deleted_files'] and not changes['added_files'] and not changes['modified_files']:
            if len(changes['deleted_files']) == 1:
                return f"chore: remove {os.path.basename(changes['deleted_files'][0])}"
            else:
                return f"chore: remove {len(changes['deleted_files'])} files"

        elif changes['modified_files'] and not changes['added_files'] and not changes['deleted_files']:
            if len(changes['modified_files']) == 1:
                return f"fix: update {os.path.basename(changes['modified_files'][0])}"
            else:
                return f"fix: update {len(changes['modified_files'])} files"

        else:
            # Mixed changes
            actions = []
            if changes['added_files']:
                actions.append(f"add {len(changes['added_files'])} files")
            if changes['modified_files']:
                actions.append(f"update {len(changes['modified_files'])} files")
            if changes['deleted_files']:
                actions.append(f"remove {len(changes['deleted_files'])} files")

            return f"chore: {', '.join(actions)}"

    def stage_all_changes(self) -> bool:
        """Stage all changes"""
        stdout, stderr, code = self.run_git_command(['git', 'add', '.'])
        if code != 0:
            print(f"❌ Failed to stage changes: {stderr}")
            return False
        print("✅ Staged all changes")
        return True

    def commit_changes(self, message: str) -> bool:
        """Commit staged changes with the given message"""
        stdout, stderr, code = self.run_git_command(['git', 'commit', '-m', message])
        if code != 0:
            print(f"❌ Failed to commit: {stderr}")
            return False
        print(f"✅ Committed successfully: {message}")
        return True

    def push_changes(self, remote: str = 'origin', branch: Optional[str] = None) -> bool:
        """Push changes to remote repository"""
        cmd = ['git', 'push', remote]
        if branch:
            cmd.append(branch)

        stdout, stderr, code = self.run_git_command(cmd)
        if code != 0:
            print(f"❌ Failed to push: {stderr}")
            return False
        print(f"✅ Pushed to {remote}")
        return True

    def interactive_commit(self) -> bool:
        """Interactive commit process"""
        print("🔍 Analyzing repository changes...")

        if not self.check_git_repo():
            print("❌ Not a git repository!")
            return False

        changes = self.analyze_changes()

        if changes['total_changes'] == 0:
            print("ℹ️  No changes detected. Nothing to commit.")
            return True

        # Show summary
        print(f"\n📊 Changes Summary:")
        if changes['added_files']:
            print(f"  ➕ Added: {len(changes['added_files'])} files")
        if changes['modified_files']:
            print(f"  ✏️  Modified: {len(changes['modified_files'])} files")
        if changes['deleted_files']:
            print(f"  ➖ Deleted: {len(changes['deleted_files'])} files")
        if changes['renamed_files']:
            print(f"  🔄 Renamed: {len(changes['renamed_files'])} files")

        # Check if we have staged changes
        if not changes['staged_diff'] and changes['unstaged_diff']:
            stage = input("\n❓ Stage all changes? (y/N): ").lower().strip()
            if stage == 'y':
                if not self.stage_all_changes():
                    return False
                # Re-analyze after staging
                changes = self.analyze_changes()

        if not changes['staged_diff']:
            print("ℹ️  No staged changes to commit.")
            return True

        print("\n🤖 Generating commit message...")
        suggested_message = self.generate_commit_message(changes)

        print(f"\n💡 Suggested commit message:")
        print(f"   {suggested_message}")

        choice = input("\n❓ Use this message? (Y/n/e): ").lower().strip()

        if choice == 'n':
            custom_message = input("Enter your commit message: ").strip()
            if not custom_message:
                print("❌ Empty commit message. Aborting.")
                return False
            message = custom_message
        elif choice == 'e':
            # Open editor (simplified version)
            print("Opening editor functionality not implemented. Please enter message:")
            custom_message = input("Enter your commit message: ").strip()
            if not custom_message:
                print("❌ Empty commit message. Aborting.")
                return False
            message = custom_message
        else:
            message = suggested_message

        # Commit
        if not self.commit_changes(message):
            return False

        # Ask about pushing
        push = input("\n❓ Push to remote? (y/N): ").lower().strip()
        if push == 'y':
            return self.push_changes()

        return True

def main():
    parser = argparse.ArgumentParser(description='Smart Git Commit Tool with AI')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY env var)')
    parser.add_argument('--message', '-m', help='Custom commit message (skips AI generation)')
    parser.add_argument('--auto-stage', '-a', action='store_true', help='Automatically stage all changes')
    parser.add_argument('--push', '-p', action='store_true', help='Push after committing')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')

    args = parser.parse_args()

    smart_commit = SmartCommit(api_key=args.api_key)

    if args.dry_run:
        print("🔍 Dry run mode - analyzing changes...")
        if not smart_commit.check_git_repo():
            print("❌ Not a git repository!")
            return 1

        changes = smart_commit.analyze_changes()
        if changes['total_changes'] == 0:
            print("ℹ️  No changes detected.")
            return 0

        print(f"📊 Would commit {changes['total_changes']} changes")
        suggested_message = smart_commit.generate_commit_message(changes)
        print(f"💡 Suggested message: {suggested_message}")
        return 0

    if args.message:
        # Direct commit with provided message
        if not smart_commit.check_git_repo():
            print("❌ Not a git repository!")
            return 1

        if args.auto_stage:
            smart_commit.stage_all_changes()

        if smart_commit.commit_changes(args.message):
            if args.push:
                smart_commit.push_changes()
            return 0
        return 1

    # Interactive mode
    try:
        success = smart_commit.interactive_commit()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n❌ Aborted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
