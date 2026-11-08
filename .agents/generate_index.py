"""generate_index.py — catalogo da inteligencia local (.agents). Gerado pelo init_repo do Sarak."""
import os
import re
from pathlib import Path


def extract_description(skill_md_path: Path) -> str:
    """Le o campo `description` do frontmatter de um SKILL.md."""
    try:
        with open(skill_md_path, "r", encoding="utf-8") as file:
            match = re.search(r'^description:\s*(.+)$', file.read(), re.MULTILINE)
            return match.group(1).strip() if match else "Descricao nao encontrada."
    except OSError:
        return "Descricao nao encontrada."


def main() -> None:
    base_dir = Path(__file__).parent
    lines = ["# Catalogo de Inteligencia Local (.agents)\n",
             "Arquivo auto-gerado. Lista as regras de negocio deste projeto para as IAs.\n",
             "## Skills\n"]

    skills_dir = base_dir / "skills"
    if skills_dir.exists():
        for skill_folder in sorted(os.listdir(skills_dir)):
            skill_md = skills_dir / skill_folder / "SKILL.md"
            if skill_md.exists():
                desc = extract_description(skill_md)
                lines.append(f"- **{skill_folder}**: {desc}\n  - *Caminho*: `.agents/skills/{skill_folder}/SKILL.md`\n")

    lines.append("\n## Comandos Customizados\n")
    commands_dir = base_dir / "commands"
    if commands_dir.exists():
        for cmd_file in sorted(os.listdir(commands_dir)):
            if cmd_file.endswith(".md"):
                lines.append(f"- **/{cmd_file[:-3]}**: `.agents/commands/{cmd_file}`\n")

    lines.append("\n## Subagentes\n")
    agents_dir = base_dir / "agents"
    if agents_dir.exists():
        for agent_file in sorted(os.listdir(agents_dir)):
            if agent_file.endswith(".md"):
                lines.append(f"- **{agent_file[:-3]}**: `.agents/agents/{agent_file}`\n")

    (base_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")
    print("[OK] Index generated at .agents/index.md")

if __name__ == "__main__":
    main()
