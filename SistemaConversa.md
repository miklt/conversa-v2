# Sistema Conversa Estagios

Eu tenho um conjunto de relatórios de estágios do curso de engenharia elétrica, ênfase computação. Eles estão em diversas pastas do google drive e a maioria são passiveis de leitura (posso selecionar o texto do pdf). Eu preciso fazer um sistema web no qual o usuário consiga 'conversar' com os documentos dos relatórios de estágio fazendo perguntas e obtendo respostas restritas ao conteúdo desses documentos. O sistema deve fornecer informações sobre os projetos, empresas e estágios em si, restringindo fornecer informações pessoais dos estagiários ou gestores.
Eu espero ter interações do seguinte tipo:

- Usuário: "Em 2025, qual foi a linguagem de programação mais usada nos estágios?"
- Sistema: "Em geral foi python, seguido de typescript e c#"
- Usuário: "E qual o tipo de projeto mais comum?"
- Sistema: "Em geral são aplicações web"
- Sistema: "Tem mais alguma dúvida?"
- Usuário: "não, obrigado"
- Sistema: "Ok, até a próxima"

É claro que podem ter interações mais detalhadas ou mais simples.

O que preciso de você é sugerir um plano para desenvolver este sistema.
Em termos de arquitetura,ele precisa ter frontend em react/vite e backend em python/fastapi e banco de dados postgresql com plugin vectordb ou outra solução para busca vetorial de textos.
Eu já tenho um conjunto de relatórios organizados em json como o seguinte exemplo:

``` json
{
"estagiario": {
"nome_completo": "André Dias Silva Terra",
"nusp": "13648765",
"curso": "Engenharia de Computação",
"telefone": "11991011409",
"email": "andre.terra@usp.br"
},
"supervisor": {
"nome_completo": "Wagner Rodrigo Dantas dos Santos",
"telefone": "79988795804",
"email": "wagner.dantas@btgpactual.com"
},
"estagio": {
"razao_social_empresa": "BANCO BTG PACTUAL S.A - SP",
"cnpj": "30.306.294/0002-26",
"periodo_inicio": "5/05/2025",
"periodo_fim": "29/08/2025",
"carga_horaria_semanal": "40 horas",
"carga_horaria_total": "600 horas"
},
"sobre_empresa": "Realizei meu estágio no BTG Pactual, que é um banco que oferece diversas soluções financeiras. Atuei no setor de IT Banking, na área de cartões com foco em faturas.",
"atividades_realizadas": [
{
"numero": "1",
"descricao": "Pagamento de faturas lastreado em investimentos",
"tarefas_realizadas": "Fui responsável por diversas atividades nesse projeto, como as seguintes: fluxo que dado o valor do novo limite do cliente entende qual oferta iremos o oferecer; montagem dos parâmetros de tela para o frontend; antecipação de valores pendentes para fatura em cenários de cancelamento de cartão; CRUD's para tabelas do projeto; testes unitários e resolução de bugs durante o desenvolvimento.",
"papel_exercido": "Desenvolvedor Backend",
"duracao": "2,5 meses",
"comentarios": "Fui introduzido num projeto relevante para equipe e para o banco e entendi como é feito um desenvolvimento em larga escala. Também tive contato com as demandas da equipe de produtos.",
"aprendizados": "Kotlin, Spring Boot, Rest Api's, integrações com AWS, padrão microsserviços, arquitetura para um grande projeto, testes unitários, debug via logs, funcionamento de faturas e cartões de crédito, entre outros."
},
{
"numero": "2",
"descricao": "Melhoria de performance cache cognito",
"tarefas_realizadas": "Implementação de cache com expiração dinâmica dado valor passado pelo cognito da AWS, em vários serviços. Com isso, reduzimos o gasto com essa ferramenta da AWS.",
"papel_exercido": "Desenvolvedor Backend",
"duracao": "3 semanas",
"comentarios": null,
"aprendizados": "Kotlin, Spring Boot, Rest Api's, integrações com AWS, funcionamento de cache, debug via logs, ferramenta COGNITO, entre outros."
}
],
"conclusao": "Aprendi como funciona o desenvolvimento de software de um projeto de larga escala, ou seja, como sua arquitetura é planejada. Melhorei minhas habilidades técnicas enquanto engenheiro de computação, com foco em Kotlin/Spring Boot. Também aprendi as regras de negócio relacionadas a cartão de crédito e faturas."
}
```

## Mais detalhes

Em termos do armazenamento/recuperação dos dados, avalie as seguintes opções e/ou proponha outras para eu poder desenvolver o sistema de bate papo com os arquivos.

a) Para cada relatório, armazenar ele da seguinte forma, uma coluna json com o conteúdo completo do json correspondente ao relatório, fazer um embedding das seções (incluindo as subseções): "estágio", "sobre_empresa", "atividades_realizadas","conclusão". Incluir uma coluna com "ano" (que é obtido a partir do período do estágio),"ordinal_estagio" (que vai ser passado para cada relatório e pode ser 1,2,3,4 ou 5 e se refere ao primeiro, segundo, terceiro, quarto ou quinto estágio do aluno), "curso" (quadrimestral), engenharia elétrica (semestral). 

b) Podemos criar tabelas adicionais onde temos termos normalizados como o exemplo a seguir: 

``` termos_tecnicos (termo, tipo, termo_normalizado) Values
   ('Python', 'linguagem', 'python'),
    ('JavaScript', 'linguagem', 'javascript'),
    ('React', 'framework', 'react'),
    ('React.js', 'framework', 'reactjs'),
    ('React Native', 'framework', 'react_native'),
    ('Angular', 'framework', 'angular'),
    ('Django', 'framework', 'django'),
    ('Flask', 'framework', 'flask'),
    ('FastAPI', 'framework', 'fastapi'),
    ('Git', 'ferramenta', 'git'),
    ('GitHub', 'ferramenta', 'github'),
    ('GitLab', 'ferramenta', 'gitlab'),
     ('AWS', 'plataforma', 'aws'),
    ('Amazon Web Services', 'plataforma', 'amazon_web_services'),
    ('Azure', 'plataforma', 'azure'),
    ('PostgreSQL', 'banco_dados', 'postgresql'),
    ('Postgres', 'banco_dados', 'postgres'),
    ('MySQL', 'banco_dados', 'mysql'),
    ('MariaDB', 'banco_dados', 'mariadb'),
    ('Scrum', 'tecnica', 'scrum'),
    ('Kanban', 'tecnica', 'kanban'),
    ('Agile', 'tecnica', 'agile'),
    ('Sistema Web', 'tipo_projeto', 'sistema_web'),
    ('Mobile App', 'tipo_projeto', 'mobile_app'),
    ('Data Science', 'tipo_projeto', 'data_science')
```

Desta forma podemos incluir uma coluna ou relacioanmento entre os termos que aparecem nas atividades do relatório e esses termos técnicos normalizados.


Inicialmente podemos fazer um teste via linha de comando e depois vamos para a implementação web do sistema. Preciso de um plano detalhado, schemas de dados