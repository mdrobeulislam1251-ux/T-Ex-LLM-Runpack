# test_system_core.py
import os
import re

def test_verify_manifest_completeness():
    """Verify that the 65-skill system engineer architecture file is present and completely detailed."""
    skill_manifest_path = "E:\\Robeul's Ai Assistant\\App Dev and Engineering Team\\SKILL.md"
    
    # 1. Assert file exists (Fails if Claude skips generating the asset)
    assert os.path.exists(skill_manifest_path) is True, "SKILL.md has not been generated inside the Engineering workspace!"
    
    with open(skill_manifest_path, "r", encoding="utf-8") as file:
        content = file.read()
        
        # 2. Count distinct skill declarations listed inside the manifest
        skills_found = re.findall(r"\d+\.\s+.*", content)
        print(f"\n[Diagnostic] System detected {len(skills_found)} functional skills defined.")
        
        # 3. Assert full 65-skill architectural package is active
        assert len(skills_found) >= 65, f"AI Laziness Detected: Core manifest only contains {len(skills_found)} out of 65 requested competencies."
        
        # 4. Check for Data Security Package components explicitly
        assert "Row-Level Security" in content, "Data Security Package is missing Database RLS parameters."
        assert "Zero-Trust" in content, "Data Security Package is missing Zero-Trust Architecture parameters."
