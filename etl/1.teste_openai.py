import os
import json
import pdfplumber
from openai import OpenAI

# Inicializar cliente OpenAI
client = OpenAI(api_key="SUA_API_KEY_AQUI")

# Caminhos
PASTA_PDFS = "/home/m/pcs/conversa-estagios-v2/arquivos/relatorios_pdf"
ARQUIVO_TEMPLATE = "/home/m/pcs/conversa-estagios-v2/arquivos/template/template.txt"
PASTA_SAIDA = "/home/m/pcs/conversa-estagios-v2/arquivos/json_saida"

# Garantir que a pasta de saída existe
os.makedirs(PASTA_SAIDA, exist_ok=True)

# Carregar template
with open(ARQUIVO_TEMPLATE, "r", encoding="utf-8") as f:
    template_texto = f.read()

# Prompt fixo (baseado no que montamos antes)
PROMPT_BASE = """
Você receberá dois insumos:
1. O conteúdo de um template de relatório de estágio (em texto).
2. O conteúdo de um relatório de estágio preenchido por um aluno (em texto extraído de PDF).

Seu objetivo é:
- Não inventar informações. Apenas extrair o que está explicitamente presente no relatório.
- Usar o template como guia de quais informações buscar.
- Retornar a saída em formato JSON estruturado, com os seguintes campos:

{
  "estagiario": {
    "nome": "",
    "nusp": "",
    "curso": "",
    "telefone": "",
    "email": ""
  },
  "supervisor": {
    "nome": "",
    "telefone": "",
    "email": ""
  },
  "estagio": {
    "empresa_razao_social": "",
    "empresa_cnpj": "",
    "periodo": {
      "inicio": "",
      "fim": ""
    },
    "carga_horaria_semanal": "",
    "carga_horaria_total": ""
  },
  "empresa": {
    "descricao": ""
  },
  "atividades": [
    {
      "descricao_breve": "",
      "tarefas": [],
      "papel": "",
      "duracao": "",
      "comentarios": "",
      "aprendizados": ""
    }
  ],
  "conclusao": ""
}

Regras:
- Preencher apenas com informações encontradas no relatório do aluno.
- Caso uma seção não esteja descrita ou não siga o formato esperado, extrair o que for possível e deixar campos vazios ("").
- Para as atividades, mesmo que o texto não esteja estruturado, tentar extrair subtópicos como descrição, tarefas, papel, duração, comentários e aprendizados, quando presentes.

Agora processe os documentos fornecidos (template e relatório preenchido) e devolva somente o JSON final.
"""


def extrair_texto_pdf(caminho_pdf):
    texto = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto += pagina.extract_text() + "\n"
    return texto


def processar_relatorio(pdf_path):
    # Extrair texto do PDF
    conteudo_pdf = extrair_texto_pdf(pdf_path)

    # Criar prompt final
    prompt = (
        f"{PROMPT_BASE}\n\nTemplate:\n{template_texto}\n\nRelatório:\n{conteudo_pdf}"
    )

    # Enviar para a API
    resposta = client.chat.completions.create(
        model="gpt-4.1",  # você pode trocar para gpt-4o-mini para reduzir custo
        messages=[
            {
                "role": "system",
                "content": "Você é um assistente especializado em extração de informações de documentos acadêmicos.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    # Pegar o JSON retornado
    try:
        dados = json.loads(resposta.choices[0].message.content)
    except json.JSONDecodeError:
        print(
            f"⚠ Erro ao interpretar JSON no arquivo {pdf_path}. Salvando como texto bruto."
        )
        dados = {"raw_output": resposta.choices[0].message.content}

    return dados


def main():
    for arquivo in os.listdir(PASTA_PDFS):
        if arquivo.endswith(".pdf"):
            caminho_pdf = os.path.join(PASTA_PDFS, arquivo)
            print(f"🔎 Processando {arquivo}...")

            resultado = processar_relatorio(caminho_pdf)

            # Nome de saída
            nome_saida = os.path.splitext(arquivo)[0] + ".json"
            caminho_saida = os.path.join(PASTA_SAIDA, nome_saida)

            # Salvar JSON
            with open(caminho_saida, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)

            print(f"✅ Resultado salvo em {caminho_saida}")


if __name__ == "__main__":
    main()
