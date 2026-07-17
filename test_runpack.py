# test_runpack.py — structural validation of the Arion company runpack plugin.
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(ROOT, "plugins", "arion-company")

EXPECTED_TEAMS = {
    "executive": 4,
    "engineering": 12,
    "design": 7,
    "ai": 6,
    "issue-fixers": 5,
    "technical": 6,
    "marketing": 5,
    "sales": 4,
    "research": 3,
}

EXPECTED_SKILLS = {
    "company-onboarding",
    "orchestration-runpack",
    "fullstack-65",
    "data-schema-design",
    "design-core",
    "issue-fix-loop",
    "research-strategy",
}

EXPECTED_COMMANDS = {"onboard", "company", "build", "design", "schema", "fix", "team"}

FRONTMATTER = re.compile(r"^---\nname: (?P<name>[a-z0-9-]+)\ndescription: (?P<desc>.+)\n---\n", re.S)


def _agent_files():
    for team in EXPECTED_TEAMS:
        team_dir = os.path.join(PLUGIN, "agents", team)
        for fname in sorted(os.listdir(team_dir)):
            if fname.endswith(".md"):
                yield team, os.path.join(team_dir, fname)


def test_roster_is_exactly_52_agents():
    counts = {team: 0 for team in EXPECTED_TEAMS}
    for team, _ in _agent_files():
        counts[team] += 1
    assert counts == EXPECTED_TEAMS, f"Team roster mismatch: {counts}"
    assert sum(counts.values()) == 52


def test_every_agent_has_valid_frontmatter_and_brain_block():
    for team, path in _agent_files():
        with open(path, encoding="utf-8") as f:
            content = f.read()
        m = FRONTMATTER.match(content)
        assert m, f"{path} is missing valid name/description frontmatter"
        expected_name = os.path.splitext(os.path.basename(path))[0]
        assert m.group("name") == expected_name, f"{path}: frontmatter name != filename"
        assert "Company Brain" in content, f"{path} does not load the company brain"
        assert "Responsibilities" in content, f"{path} has no responsibilities section"


def test_all_seven_skills_exist_with_frontmatter():
    skills_dir = os.path.join(PLUGIN, "skills")
    found = {d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))}
    assert found == EXPECTED_SKILLS, f"Skill set mismatch: {found}"
    for skill in found:
        path = os.path.join(skills_dir, skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---\n") and f"name: {skill}" in content, f"{path} frontmatter invalid"


def test_all_seven_commands_exist():
    commands_dir = os.path.join(PLUGIN, "commands")
    found = {os.path.splitext(f)[0] for f in os.listdir(commands_dir) if f.endswith(".md")}
    assert found == EXPECTED_COMMANDS, f"Command set mismatch: {found}"


def test_manifests_and_template_are_valid_json():
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
        marketplace = json.load(f)
    assert marketplace["plugins"][0]["name"] == "arion-company"
    assert marketplace["plugins"][0]["source"] == "./plugins/arion-company"

    with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
        plugin = json.load(f)
    assert plugin["name"] == "arion-company"

    with open(os.path.join(ROOT, "templates", "company-profile.template.json"), encoding="utf-8") as f:
        template = json.load(f)
    for section in ("company", "brain", "brand", "tech", "credentials"):
        assert section in template, f"template missing '{section}' section"


def test_schema_review_gate_is_wired():
    """The CTO gate must appear on both sides: data-engineer submits, cto reviews."""
    with open(os.path.join(PLUGIN, "agents", "engineering", "data-engineer.md"), encoding="utf-8") as f:
        data_engineer = f.read()
    assert "cto" in data_engineer and "review" in data_engineer.lower()

    with open(os.path.join(PLUGIN, "agents", "executive", "cto.md"), encoding="utf-8") as f:
        cto = f.read()
    assert "data-schema-design" in cto

    with open(os.path.join(PLUGIN, "skills", "data-schema-design", "SKILL.md"), encoding="utf-8") as f:
        skill = f.read()
    assert "APPROVED" in skill and "MANDATORY" in skill


def test_gitignore_protects_env_secrets():
    with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
        gitignore = f.read()
    assert ".env" in gitignore.splitlines(), ".env must be gitignored before onboarding stores secrets"
