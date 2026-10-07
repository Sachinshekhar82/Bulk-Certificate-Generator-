#!/usr/bin/env python3
"""
Helper script to push the Bulk Certificate Generator project to GitHub:
https://github.com/Sachinshekhar82/Bulk-Certificate-Generator-.git

Usage:
    python push_to_github.py [GITHUB_TOKEN]
Or set environment variable:
    $env:GITHUB_TOKEN="ghp_your_token_here"
    python push_to_github.py
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Sachinshekhar82/Bulk-Certificate-Generator-.git"


def get_git_executable() -> str:
    """Finds git executable from PATH or local MinGit installation."""
    mingit_path = Path.home() / "AppData" / "Local" / "Programs" / "MinGit" / "cmd" / "git.exe"
    if mingit_path.exists():
        return str(mingit_path)
    return "git"


def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1].strip()

    git_exe = get_git_executable()

    # Try using git CLI if available
    try:
        code, stdout, _ = run_cmd([git_exe, "--version"])
        if code == 0:
            print(f"Using {stdout}")
            # Ensure branch is main
            run_cmd([git_exe, "branch", "-M", "main"])

            # Configure remote
            if token:
                auth_url = f"https://x-access-token:{token}@github.com/Sachinshekhar82/Bulk-Certificate-Generator-.git"
                run_cmd([git_exe, "remote", "remove", "origin"])
                run_cmd([git_exe, "remote", "add", "origin", auth_url])
                print("Pushing to GitHub with provided token...")
                pcode, pout, perr = run_cmd([git_exe, "push", "-u", "origin", "main", "--force"])
                if pcode == 0:
                    print("SUCCESS! Successfully pushed to https://github.com/Sachinshekhar82/Bulk-Certificate-Generator-")
                    # Clean up credential in remote url
                    run_cmd([git_exe, "remote", "set-url", "origin", REPO_URL])
                    return 0
                else:
                    print(f"Push failed: {perr or pout}")
            else:
                # Try regular push (uses git credential manager if available)
                run_cmd([git_exe, "remote", "remove", "origin"])
                run_cmd([git_exe, "remote", "add", "origin", REPO_URL])
                print("Attempting git push with system credentials...")
                pcode, pout, perr = run_cmd([git_exe, "push", "-u", "origin", "main"])
                if pcode == 0:
                    print("SUCCESS! Successfully pushed to https://github.com/Sachinshekhar82/Bulk-Certificate-Generator-")
                    return 0
                else:
                    print(f"\nCould not push without token:\n{perr or pout}")
    except FileNotFoundError:
        pass

    # Fallback to pure-Python dulwich push
    try:
        from dulwich import porcelain
        from dulwich.repo import Repo

        r = Repo(".")
        r[b"refs/heads/main"] = r.head()

        if token:
            auth_url = f"https://x-access-token:{token}@github.com/Sachinshekhar82/Bulk-Certificate-Generator-.git"
            print("Pushing with dulwich...")
            porcelain.push(r, auth_url, refspecs=b"refs/heads/main:refs/heads/main")
            print("SUCCESS! Successfully pushed to https://github.com/Sachinshekhar82/Bulk-Certificate-Generator-")
            return 0
        else:
            print("\nGitHub requires authentication to push.")
            print("Please run:")
            print("  python push_to_github.py <YOUR_GITHUB_TOKEN>")
            print("Or in PowerShell:")
            print("  $env:GITHUB_TOKEN='ghp_your_token_here'")
            print("  python push_to_github.py")
            return 1
    except Exception as e:
        print(f"Dulwich push error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
