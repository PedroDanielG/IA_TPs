# FEATURE: Mapa de Calor de Probabilidades

## 📋 Descrição

Implementação de um sistema visual de mapa de calor (heatmap) que representa as probabilidades calculadas pela IA de cada célula conter uma mina, com cores, percentagens e uma animação.

## 🔧 Alterações Implementadas

### 1. **Novo método: `get_probability_color()`** (minesweeper.py)
```python
def get_probability_color(self, probability):
    """
    Devolvue uma cor baseada na probabilidade de ser mina.
    Verde (baixa) | Amarelo (media) | Vermelho (alta)
    """
```

Converte valores de probabilidade num gradient de cores:
- **0-33%**: Verde → Amarelo (células mais seguras)
- **34-66%**: Amarelo → Laranja (risco moderado)
- **67-100%**: Laranja → Vermelho (células perigosas)

### 2. **Nova função: `draw_heatmap_overlay()`** (runner.py)
```python
def draw_heatmap_overlay(screen, ai, cells, cell_size, pulse_alpha):
    """Desenha o overlay do heatmap de probabilidades"""
```

Faz o seguinte:
- Obtem probabilidades da IA
- Aplica cores às células
- Desenha overlays transparentes
- Adiciona texto com percentagens

### 3. **Sistema de animação pulsing**
```python
pulse_timer += 0.1
pulse_alpha = (math.sin(pulse_timer) + 1) / 2 
```

Cria um efeito de "respiração" nas células.

### 4. **Botão de alternância "Show Map / Hide Map"**
```python
show_heatmap = False

if heatmapButton.collidepoint(mouse):
    show_heatmap = not show_heatmap
```

Permite activar/desactivar o heatmap durante o jogo.

### 5. **Integração visual no loop principal**
```python

if show_heatmap and not lost:
    draw_heatmap_overlay(screen, ai, cells, cell_size, pulse_alpha)
```

## ✅ Vantagens da Implementação

- Visualização imediata do "raciocínio" da IA
- Identificação rápida de zonas seguras e perigosas
- Ferramenta educativa para compreender probabilidades

## ⚙️ Dependências Adicionais

### **Biblioteca math** (runner.py)
```python
import math
```
Necessária para a função `math.sin()` utilizada na animação pulsante.

### **Configuração de Cores**
```python
BLUE = (100, 150, 255)  # Cor do botão quando activado
```