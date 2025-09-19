#!/usr/bin/env python3
"""
Renderiza blocos Mermaid (```mermaid) de um arquivo Markdown em SVGs e
substitui os blocos por imagens no Markdown de saída.

Uso:
  python scripts/render_mermaid.py <input_md> <output_md>

Saída:
  - Cria pasta docs/diagrams (se não existir)
  - Gera arquivos .mmd para cada diagrama e os renderiza em .svg via mermaid-cli (mmdc)
  - Escreve um novo Markdown com referências às imagens geradas
"""
import sys
import os
import re
import subprocess
from pathlib import Path


def extract_and_render(input_md: Path, output_md: Path, diagrams_dir: Path) -> None:
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    with input_md.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    out_lines = []
    in_mermaid = False
    buf = []
    diagram_idx = 0

    fence_re = re.compile(r"^```\s*$")

    for line in lines:
        if not in_mermaid:
            # Start of a mermaid block?
            if line.strip().lower().startswith("```mermaid"):
                in_mermaid = True
                buf = []
                continue
            else:
                out_lines.append(line)
        else:
            # Inside mermaid: look for closing fence
            if fence_re.match(line):
                # finalize this diagram
                diagram_idx += 1
                mmd_path = diagrams_dir / f"diagram_{diagram_idx}.mmd"
                svg_path = diagrams_dir / f"diagram_{diagram_idx}.svg"
                png_path = diagrams_dir / f"diagram_{diagram_idx}.png"

                # Sanitize known problematic tokens for Mermaid parser
                content = "".join(buf)
                # Detect diagram type from first non-empty line
                first_line = next((ln.strip() for ln in content.splitlines() if ln.strip()), "")
                if first_line.lower().startswith("flowchart"):
                    # Avoid parentheses inside node labels like Vector(1536)
                    content = content.replace("(1536)", " 1536")
                    # Normalize shapes to simple rectangles to avoid parsing issues with [/ ... /]
                    content = re.sub(r"\[/", "[", content)
                    content = re.sub(r"/\]", "]", content)
                    # Convert escaped newlines inside labels to HTML line breaks
                    content = content.replace("\\n", "<br/>")
                    # Replace route parameters like /{id} by /:id to avoid diamond token
                    content = re.sub(r"/\{([^}]+)\}", r"/:\1", content)
                if first_line.lower().startswith("erdiagram"):
                    # erDiagram types don't like parentheses in type names inside attribute types
                    content = re.sub(r"vector\(1536\)", "vector_1536", content, flags=re.IGNORECASE)
                
                mmd_path.write_text(content, encoding='utf-8')

                # Render via mermaid-cli (mmdc)
                try:
                    # Render SVG
                    subprocess.run([
                        "mmdc", "-i", str(mmd_path), "-o", str(svg_path),
                        "-b", "transparent", "-t", "default"
                    ], check=True)
                    # Render PNG (better compatibility with PDF engines)
                    subprocess.run([
                        "mmdc", "-i", str(mmd_path), "-o", str(png_path),
                        "-b", "transparent", "-t", "default"
                    ], check=True)
                except FileNotFoundError:
                    print("Erro: mmdc (mermaid-cli) não encontrado no PATH. Instale com: npm install -g @mermaid-js/mermaid-cli", file=sys.stderr)
                    sys.exit(1)
                except subprocess.CalledProcessError as e:
                    print(f"Erro ao renderizar {mmd_path}: {e}", file=sys.stderr)
                    sys.exit(e.returncode)

                # Inserir referência de imagem relativa ao output_md dentro de docs/
                # Assumindo que output_md está em docs/, usar caminho relativo "diagrams/..."
                # Prefer PNG for downstream conversion compatibility
                rel_path = f"diagrams/{png_path.name}"
                out_lines.append(f"\n![Diagrama {diagram_idx}]({rel_path})\n\n")

                in_mermaid = False
                buf = []
            else:
                buf.append(line)

    # Se arquivo acabou ainda dentro de bloco mermaid, fecha com código bruto
    if in_mermaid and buf:
        out_lines.append("```mermaid\n")
        out_lines.extend(buf)
        out_lines.append("```\n")

    output_md.write_text("".join(out_lines), encoding='utf-8')


def main():
    if len(sys.argv) != 3:
        print("Uso: python scripts/render_mermaid.py <input_md> <output_md>", file=sys.stderr)
        sys.exit(1)

    input_md = Path(sys.argv[1]).resolve()
    output_md = Path(sys.argv[2]).resolve()

    if not input_md.exists():
        print(f"Arquivo não encontrado: {input_md}", file=sys.stderr)
        sys.exit(1)

    # Diretório de diagramas ao lado do output dentro de docs/
    diagrams_dir = output_md.parent / "diagrams"

    extract_and_render(input_md, output_md, diagrams_dir)
    print(f"Renderização concluída: {output_md}")


if __name__ == "__main__":
    main()
