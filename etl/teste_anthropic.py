#!/usr/bin/env python3
"""
Script para extração de informações estruturadas de relatórios de estágio em PDF
Usa pdfplumber para extração de texto e API da Anthropic para processamento
"""

import argparse
import json
import sys
from pathlib import Path
import pdfplumber
import anthropic
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Prompt para extração de informações
EXTRACTION_PROMPT = """
# Prompt para Extração de Informações de Relatórios de Estágio

Você é um assistente especializado em extrair informações estruturadas de relatórios de estágio universitário. Sua tarefa é analisar o TEXTO de um relatório de estágio e extrair as informações seguindo exatamente a estrutura do template fornecido.

## TEMPLATE DE REFERÊNCIA:
```
ESTAGIÁRIO
Nome Completo: [campo] NUSP [campo]
Curso (denominação completa): [campo]
Telefone: [campo] E-mail: [campo]

SUPERVISOR
Nome do Supervisor (Gestor): [campo]
Telefone: [campo] E-mail: [campo]

ESTÁGIO
Razão Social da Empresa: [campo]
CNPJ: [campo]
Período em que o estágio FOI realizado: [campo] a [campo]
Carga Horária Semanal do Estágio: [campo]
Carga Horária Total Realizada até o momento: [campo]

1. SOBRE A EMPRESA
[descrição da empresa]

2. SOBRE AS ATIVIDADES REALIZADAS
Atividade 1:
- Breve descrição: [campo]
- Tarefas realizadas pelo estagiário: [campo]
- Papel exercido pelo estagiário: [campo]
- Duração da atividade: [campo]
- Comentários: [campo]
- Aprendizados: [campo]

3. CONCLUSÃO
[texto da conclusão]
```

## INSTRUÇÕES CRÍTICAS:
1. **APENAS extraia informações que estão EXPLICITAMENTE presentes no texto do relatório**
2. **Compare o texto fornecido com a estrutura do template acima**
3. **NÃO invente, suponha ou complete informações ausentes**
4. **Se uma informação não estiver presente, use `null` no JSON**
5. **Mantenha a formatação original dos dados (datas, telefones, emails, etc.)**

## ESTRUTURA DE EXTRAÇÃO:

### 1. ESTAGIÁRIO
- Nome completo
- NUSP (número USP)
- Curso (denominação completa)
- Telefone
- E-mail

### 2. SUPERVISOR
- Nome completo
- Telefone
- E-mail

### 3. ESTÁGIO
- Razão social da empresa
- CNPJ
- Período de realização (data de início e fim)
- Carga horária semanal
- Carga horária total realizada

### 4. SOBRE A EMPRESA
- Descrição completa da empresa conforme relatada pelo estagiário

### 5. ATIVIDADES REALIZADAS
Para cada atividade mencionada, extrair:
- Número/identificação da atividade
- Breve descrição
- Tarefas realizadas pelo estagiário
- Papel exercido pelo estagiário
- Duração da atividade
- Comentários
- Aprendizados

### 6. CONCLUSÃO
- Texto completo da conclusão do relatório

## FORMATO DE SAÍDA:

Retorne APENAS um JSON válido na seguinte estrutura:

```json
{
  "estagiario": {
    "nome_completo": "string ou null",
    "nusp": "string ou null",
    "curso": "string ou null",
    "telefone": "string ou null",
    "email": "string ou null"
  },
  "supervisor": {
    "nome_completo": "string ou null",
    "telefone": "string ou null",
    "email": "string ou null"
  },
  "estagio": {
    "razao_social_empresa": "string ou null",
    "cnpj": "string ou null",
    "periodo_inicio": "string ou null",
    "periodo_fim": "string ou null",
    "carga_horaria_semanal": "string ou null",
    "carga_horaria_total": "string ou null"
  },
  "sobre_empresa": "string ou null",
  "atividades_realizadas": [
    {
      "numero": "string ou null",
      "descricao": "string ou null",
      "tarefas_realizadas": "string ou null",
      "papel_exercido": "string ou null",
      "duracao": "string ou null",
      "comentarios": "string ou null",
      "aprendizados": "string ou null"
    }
  ],
  "conclusao": "string ou null"
}
```

## REGRAS ESPECÍFICAS:

1. **Datas**: Mantenha o formato original (DD/MM/AAAA ou como apresentado)
2. **Telefones**: Preserve a formatação com parênteses e hífens
3. **Carga horária**: Inclua as unidades (horas) se mencionadas
4. **Textos longos**: Preserve quebras de linha importantes usando `\\n`
5. **Atividades**: Se não estiverem numeradas, use "1", "2", etc.
6. **Campos ausentes**: Use `null`, nunca strings vazias

## EXEMPLO DE COMPORTAMENTO:
- ✅ Se encontrar "Nome: João Silva" → `"nome_completo": "João Silva"`
- ✅ Se não encontrar telefone → `"telefone": null`
- ❌ Nunca faça: `"telefone": "não informado"` ou `"telefone": ""`

Agora, analise o TEXTO do relatório de estágio fornecido abaixo e retorne apenas o JSON estruturado com as informações extraídas.


"""


class RelatorioExtractor:
    """Classe para extração de informações de relatórios de estágio"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o extrator

        Args:
            api_key: Chave da API da Anthropic. Se None, será lida da variável ANTHROPIC_API_KEY
        """
        print("DEBUG: Inicializando RelatorioExtractor...")
        if api_key:
            print("DEBUG: Usando API key fornecida via parâmetro")
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            # Tenta ler da variável de ambiente
            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                raise ValueError(
                    "API key da Anthropic não fornecida. Use o parâmetro api_key ou defina ANTHROPIC_API_KEY"
                )
            self.client = anthropic.Anthropic(api_key=api_key)
        print("DEBUG: Cliente Anthropic inicializado com sucesso")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extrai texto de um arquivo PDF usando pdfplumber

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            Texto extraído do PDF
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"Erro ao extrair texto do PDF: {str(e)}")

    def extract_info_from_text(self, texto_relatorio: str) -> Dict[str, Any]:
        """
        Extrai informações estruturadas do texto do relatório usando a API da Anthropic

        Args:
            texto_relatorio: Texto do relatório extraído do PDF

        Returns:
            Dicionário com informações estruturadas
        """

        try:
            # Monta o prompt completo
            print(f"DEBUG: Texto do relatório tem {len(texto_relatorio)} caracteres")

            # prompt_completo = EXTRACTION_PROMPT.format(texto_relatorio=texto_relatorio)
            prompt_completo = (
                f"{EXTRACTION_PROMPT}\n\n**TEXTO DO RELATÓRIO:**\n{texto_relatorio}"
            )

            print(f"DEBUG: Prompt completo tem {len(prompt_completo)} caracteres")

            print("DEBUG: Preparando chamada da API...")

            try:
                # Chama a API da Anthropic
                message = self.client.messages.create(
                    # model="claude-3-7-sonnet-latest",
                    model="claude-3-5-haiku-latest",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt_completo}],
                )
                print(f"DEBUG: Chamada da API bem-sucedida")

                # Extrai a resposta
                response_text = message.content[0].text
                print(f"DEBUG: Resposta da API tem {len(response_text)} caracteres")

                # Tenta fazer parse do JSON
                try:
                    return json.loads(response_text.strip())
                except json.JSONDecodeError as e:
                    print(f"DEBUG: Erro no parse direto: {e}")
                    print(f"DEBUG: Tentando extrair JSON da resposta...")

                    # Tenta extrair JSON entre chaves
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}") + 1

                    if start_idx != -1 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        print(f"DEBUG: JSON extraído tem {len(json_str)} caracteres")

                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError as e2:
                            print(f"DEBUG: Erro no parse do JSON extraído: {e2}")
                            # Tenta encontrar um JSON válido dentro da string
                            import re

                            json_match = re.search(r"\{.*\}", json_str, re.DOTALL)
                            if json_match:
                                try:
                                    return json.loads(json_match.group())
                                except json.JSONDecodeError as e3:
                                    print(
                                        f"DEBUG: Erro no parse do JSON com regex: {e3}"
                                    )
                                    raise ValueError(
                                        f"Não foi possível fazer parse do JSON. Resposta: {response_text[:500]}..."
                                    )
                            else:
                                raise ValueError(
                                    f"Não foi possível fazer parse do JSON. Resposta: {response_text[:500]}..."
                                )
                    else:
                        raise ValueError(
                            f"Não foi possível fazer parse do JSON. Resposta: {response_text[:500]}..."
                        )
            except Exception as e:
                print(
                    f"DEBUG: Erro inesperado na extração de informações: {repr(str(e))}"
                )
                raise
        except Exception as e:
            print(f"DEBUG: Erro inesperado na extração de informações: {e}")
            raise

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Processa um PDF completo: extrai texto e informações estruturadas

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            Dicionário com informações estruturadas
        """
        # Verifica se o arquivo existe
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")

        print(f"Extraindo texto do PDF: {pdf_path}")
        texto = self.extract_text_from_pdf(pdf_path)

        if not texto.strip():
            raise ValueError("Nenhum texto foi extraído do PDF")

        print("Processando texto com a API da Anthropic...")
        informacoes = self.extract_info_from_text(texto)

        print("✅ Processamento concluído com sucesso!")
        return informacoes


def main():
    """Função principal do script"""
    parser = argparse.ArgumentParser(
        description="Extrai informações estruturadas de relatórios de estágio em PDF (único ou em lote)"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        help="Caminho para o arquivo PDF do relatório (ou omita para modo batch)",
    )
    parser.add_argument(
        "-o", "--output", help="Arquivo de saída JSON (opcional, modo único)"
    )
    parser.add_argument(
        "--batch-dir", help="Diretório com arquivos PDF para processamento em lote"
    )
    parser.add_argument(
        "--json-dir", help="Diretório de saída dos arquivos JSON no modo batch"
    )
    parser.add_argument(
        "--api-key",
        help="Chave da API da Anthropic (opcional, pode usar ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Formata o JSON de saída de forma legível"
    )

    args = parser.parse_args()

    extractor = RelatorioExtractor(api_key=args.api_key)

    if args.batch_dir and args.json_dir:
        # Modo batch: processa todos os PDFs da pasta
        batch_dir = Path(args.batch_dir)
        json_dir = Path(args.json_dir)
        json_dir.mkdir(parents=True, exist_ok=True)
        pdf_files = list(batch_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"Nenhum PDF encontrado em {batch_dir}")
            return
        for pdf_path in pdf_files:
            try:
                resultado = extractor.process_pdf(str(pdf_path))
                if args.pretty:
                    json_output = json.dumps(resultado, ensure_ascii=False, indent=2)
                else:
                    json_output = json.dumps(resultado, ensure_ascii=False)
                out_path = json_dir / (pdf_path.stem + ".json")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(json_output)
                print(f"[OK] {pdf_path.name} -> {out_path.name}")
            except Exception as e:
                print(f"[ERRO] {pdf_path.name}: {e}")
    elif args.pdf_path:
        # Modo único
        try:
            resultado = extractor.process_pdf(args.pdf_path)
            if args.pretty:
                json_output = json.dumps(resultado, ensure_ascii=False, indent=2)
            else:
                json_output = json.dumps(resultado, ensure_ascii=False)
            if args.output:
                out_path = Path(args.output)
            else:
                out_path = Path(args.pdf_path).with_suffix(".json")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Resultado salvo em: {out_path}")
        except Exception as e:
            print(f"Error!: {str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Informe um PDF ou use --batch-dir e --json-dir para modo em lote.")


if __name__ == "__main__":
    main()
