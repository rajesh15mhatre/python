"""
This is the utils module
"""
from pathlib import Path


def get_project_root():
    current_dir = Path.cwd()
    return current_dir.parents[len(current_dir.parents) - 1]

def get_git_directory():
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        git_dir = current_dir / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return git_dir.parent
        current_dir = current_dir.parent
    return None

if __name__ == "__main__":
    #arguments = docopt(__doc__)
    print("test")
