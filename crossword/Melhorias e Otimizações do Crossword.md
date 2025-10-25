# Melhorias e Otimizações do Crossword Solver


## 1. Melhorias na Qualidade do Código

Foram aplicadas práticas de código moderno para melhorar a legibilidade, a manutenção e a robustez do projeto.

### 1.1. Type Hinting (Anotações de Tipo)

*   **O que foi feito:** Anotações de tipo (`type hints`) foram adicionadas a todas as funções, métodos e variáveis de classe em ambos os ficheiros.
*   **Benefício:** Maior clareza sobre os tipos de dados esperados, permitindo a verificação estática de código (com ferramentas como `mypy`) e reduzindo potenciais erros em tempo de execução.

### 1.2. Estrutura e Legibilidade

*   **`crossword.py`:**
    *   A lógica de cálculo das células de uma variável (`self.cells`) foi movida do construtor (`__init__`) para um método privado (`_calculate_cells`), tornando o construtor mais limpo.
    *   O carregamento da estrutura do *crossword* (`self.structure`) foi simplificado com o uso de *list comprehensions*.

## 2. Otimizações de Desempenho (CSP Solver)

As mudanças mais significativas foram feitas para acelerar o processo de *backtracking* (busca) e a propagação de restrições.

### 2.1. Pré-processamento de Vocabulário (`crossword.py`)

*   **Otimização:** Em `Crossword.__init__`, o vocabulário (`self.words`) é agora pré-agrupado por comprimento num novo dicionário, `self.words_by_length`.
*   **Benefício:** O `CrosswordCreator` em `generate.py` pode inicializar os domínios de cada variável diretamente com o conjunto de palavras do comprimento correto, eliminando a necessidade de verificar o comprimento de cada palavra do vocabulário em `enforce_node_consistency`.

### 2.2. Otimização da Função `revise` (`generate.py`)

*   **Otimização:** A função `revise(x, y)` foi reescrita para usar um **conjunto de caracteres compatíveis** (`compatible_chars_y`).
*   **Benefício:** A complexidade da verificação de compatibilidade foi reduzida de $O(|D_x| \cdot |D_y|)$ para aproximadamente $O(|D_x| + |D_y|)$, onde $|D|$ é o tamanho do domínio. Isto acelera drasticamente o `ac3` e o `backtrack`.

### 2.3. Implementação de Forward Checking (FC) (`generate.py`)

*   **Otimização:** O método `backtrack` foi modificado para implementar a técnica de **Forward Checking** (FC) em vez de chamar o `ac3` completo a cada passo.
*   **O que foi feito:**
    1.  O `ac3()` completo é chamado apenas uma vez no início do `solve()`.
    2.  No `backtrack`, após atribuir um valor a uma variável (`var`), apenas os domínios dos **vizinhos não atribuídos** são revisados.
    3.  Os domínios são guardados e restaurados a cada passo de *backtracking* para garantir a integridade.
*   **Benefício:** Evitar a chamada custosa do `ac3` completo em cada nó da árvore de busca acelera significativamente a resolução do CSP, especialmente em quebra-cabeças complexos.

### 2.4. Melhoria na Função `save` (`generate.py`)

*   **Melhoria:** A função `save` foi atualizada para usar `draw.textbbox` (método mais moderno da biblioteca **Pillow**) para calcular corretamente as dimensões do texto, melhorando a centralização das letras na grelha.

## 3. Interface de Linha de Comando (CLI) Interativa

O método de execução foi alterado de argumentos de linha de comando para uma interface interativa mais amigável, ideal para ser executada no terminal do VS Code.

### 3.1. Seleção de Ficheiros

*   **O que foi feito:** A função `main` foi atualizada para usar a função `select_file_from_list`, que:
    1.  Procura automaticamente ficheiros `.txt` na subpasta `data/structure` (para estruturas) e `data/words` (para vocabulário).
    2.  Apresenta uma lista numerada desses ficheiros.
    3.  Permite ao utilizador escolher o ficheiro digitando o número correspondente.
    4.  Em caso de erro, permite a introdução manual do caminho.
*   **Benefício:** Melhora a usabilidade, eliminando a necessidade de memorizar ou digitar caminhos longos de ficheiros.

### 3.2. Saída Automática da Imagem

*   **O que foi feito:** A pergunta sobre o ficheiro de saída foi removida. O script agora **sempre** guarda a imagem do *crossword* resolvido no ficheiro `output.png` no diretório de execução, atualizando-o a cada jogo.
*   **Benefício:** Simplifica o fluxo de trabalho, garantindo que o resultado visual está sempre disponível no mesmo local.

## 4. Geração de Pistas (Clues) com IA

Foi adicionada uma funcionalidade opcional para gerar pistas criativas para as palavras do *crossword* usando um modelo de linguagem (LLM).

### 4.1. Funcionalidade e Nova API (Google Gemini)

*   **O que foi feito:**
    1.  O script pergunta ao utilizador se deseja gerar pistas após a resolução bem-sucedida.
    2.  A funcionalidade de IA foi migrada da API da OpenAI para a **API da Google Gemini** (modelo **`gemini-2.5-flash`**) para contornar problemas de quota e usar um nível gratuito mais acessível.
    3.  O utilizador insere a sua Chave API da Google Gemini quando solicitado.
    4.  A função `generate_clues_with_llm` utiliza a biblioteca `google-genai` para criar pistas em português para cada palavra usada no *crossword*.
*   **Saída:**
    *   As pistas são impressas no terminal, organizadas por "ACROSS" e "DOWN".
    *   Um novo ficheiro, **`output_clues.txt`**, é criado junto ao `output.png` com todas as pistas.
*   **Requisitos:**
    *   Requer a biblioteca `google-genai` (`pip install google-genai`).
    *   Requer uma Chave API da Google Gemini válida.

