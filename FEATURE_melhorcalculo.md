# FEATURE: Sistema de Probabilidades

## 📋 Descrição

Implementação de um sistema de cálculo de probabilidades para o Minesweeper AI, permitindo ao agente fazer escolhas informadas baseadas em análise matemática ao invés de jogadas puramente aleatórias.

## 🎯 Problema Resolvido

**Antes:** Quando a AI não tinha jogadas 100% seguras, escolhia uma célula completamente a toa usando a funcao `random.choice()`, ignorando todo o conhecimento acumulado sobre o jogo.

**Depois da melhoria:** A AI analisa todas as células desconhecidas, calcula a probabilidade de cada uma ser uma mina, e escolhe a célula com menor risco de conter uma mina.

## 🔧 Alterações Implementadas

### 1. **Adicionado parâmetro `mines` ao construtor** (`__init__`)
```python
def __init__(self, height=8, width=8, mines=8):
    self.total_mines = mines
```
Necessário para calcular probabilidades globais baseadas nas minas restantes.

### 2. **Novo método: `get_unknown_cells()`**
```python
def get_unknown_cells(self):
    """Retorna células não reveladas e não marcadas como minas"""
```

### 3. **Novo método: `calculate_probabilities()`**
```python
def calculate_probabilities(self):
    """Calcula probabilidade de cada célula desconhecida ser mina"""
```
Funcao principal da feature. Utliza sentencas de conhecimento e racio de minas para uma melhor estrategia de escolha:

### 4. **Modificado o metodo `make_random_move()`**
```python
def make_random_move(self):
    """Escolhe célula com MENOR probabilidade de ser mina"""
    probabilities = self.calculate_probabilities()
    best_move = min(probabilities.items(), key=lambda x: x[1])
    return best_move[0]
```
Transforma uma escolha aleatória numa escolha informada e inteligente.

## 📊 Funcionamento do Cálculo de Probabilidade

### Estratégia 1: Análise Baseada em Sentenças
Para cada célula desconhecida, a AI verifica todas as sentenças que a incluem:

```
Exemplo:
Sentença: {(0,1), (0,2), (1,1)} = 2
Probabilidade de (0,1) ser mina = 2/3 ≈ 0.67
```

Se a célula aparece em múltiplas sentenças, faz-se a média ponderada.

### Estratégia 2: Probabilidade Global (Fallback)
Quando não há sentenças disponíveis:

```
Probabilidade = (Minas restantes) / (Células desconhecidas)

Exemplo:
8 minas totais - 3 encontradas = 5 minas restantes
40 células desconhecidas
Probabilidade = 5/40 = 0.125 (12.5%)
```

## ✅ Vantagens da Implementação

### **Decisões mais inteligentes**
- A AI não "adivinha" - usa matemática
- Minimiza o risco em cada jogada
- Aproveita todo o conhecimento acumulado


## 📝 Exemplo de Uso

```python
# Criar AI com número de minas
ai = MinesweeperAI(height=8, width=8, mines=8)

# Após algumas jogadas...
ai.add_knowledge((3, 3), 2)

# Visualizar probabilidades (debugging)
ai.print_probabilities()

# Fazer jogada inteligente
move = ai.make_random_move()  # Agora não é aleatório!
```

## ⚙️ Configuração Necessária

Atualizar `runner.py` para passar o número de minas:

```python
# Onde aparece as linhas com:
ai = MinesweeperAI(height=HEIGHT, width=WIDTH)

# Alterar para:
ai = MinesweeperAI(height=HEIGHT, width=WIDTH, mines=MINES)
```
