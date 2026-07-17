# router.py
import os
import re
import sys

class ArionRouter:
    def __init__(self, root_path=None):
        # Default to this repo's root so the router works on any machine/OS;
        # pass an explicit root_path to route into a different workspace.
        self.root_path = root_path or os.path.dirname(os.path.abspath(__file__))
        self.tracks = {
            "engineering": os.path.join(self.root_path, "App Dev and Engineering Team"),
            "assistant": os.path.join(self.root_path, "Robeul's Workspace Assistant")
        }

    def analyze_intent(self, prompt: str) -> str:
        """Parses keywords to route tasks to their isolated workspace sandboxes."""
        prompt_lower = prompt.lower()

        # Hardened Domain Mapping Regex
        if any(w in prompt_lower for w in ["gmail", "email", "mail", "inbox"]):
            return os.path.join(self.tracks["assistant"], "gmail")
        elif any(w in prompt_lower for w in ["asana", "project", "board", "ticket"]):
            return os.path.join(self.tracks["assistant"], "asana")
        elif any(w in prompt_lower for w in ["task", "todo", "schedule"]):
            return os.path.join(self.tracks["assistant"], "tasks")
        elif any(w in prompt_lower for w in ["support", "client", "help"]):
            return os.path.join(self.tracks["assistant"], "support")
        elif any(w in prompt_lower for w in ["build", "deploy", "compile", "ssh", "playwright"]):
            return self.tracks["engineering"]

        return self.tracks["assistant"]

    def execute_safely(self, target_dir: str) -> bool:
        """Ensures Zero-Trust path directory containment before firing hooks."""
        normalized_target = os.path.abspath(target_dir)
        normalized_root = os.path.abspath(self.root_path)

        # Directory Traversal Protection (DevSecOps Competency)
        if not normalized_target.startswith(normalized_root):
            raise PermissionError("Security Breach: Attempted path traversal out of Arion sandbox.")

        if not os.path.exists(normalized_target):
            os.makedirs(normalized_target, exist_ok=True)
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        router = ArionRouter()
        target = router.analyze_intent(" ".join(sys.argv[1:]))
        router.execute_safely(target)
        print(f"[Arion Route Active]: {target}")
