import sys
import os
import re
from collections import deque
from typing import Dict, Set, List, Optional, Tuple, Any

from crossword import Variable, Crossword

# Define types for clarity
Assignment = Dict[Variable, str]
Domain = Dict[Variable, Set[str]]


class CrosswordCreator:
    def __init__(self, crossword: Crossword):
        """
        Create new CSP crossword generator.
        """
        self.crossword = crossword
        self.domains: Domain = {}
        
        for var in self.crossword.variables:
            # Use the pre-filtered set of words for the correct length
            self.domains[var] = self.crossword.words_by_length.get(var.length, set()).copy()

    def letter_grid(self, assignment: Assignment) -> List[List[Optional[str]]]:
        letters: List[List[Optional[str]]] = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment: Assignment) -> None:
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        # Melhoria na impressão para melhor visualização na CLI
        print("\n" + "=" * (self.crossword.width * 2 + 2))
        for i in range(self.crossword.height):
            print("█", end="")
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end=" ")
                else:
                    print("█", end=" ")
            print("█")
        print("=" * (self.crossword.width * 2 + 2) + "\n")

    def save(self, assignment: Assignment, filename: str) -> None:
        """
        Save crossword assignment to an image file.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("Pillow library not installed. Cannot save image.")
            return

        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        try:
            font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        except IOError:
            font = ImageFont.load_default()
            print("Warning: Could not load OpenSans-Regular.ttf. Using default font.")
            
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        # Use getbbox for modern Pillow versions
                        bbox = draw.textbbox((0, 0), letters[i][j], font=font)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self) -> Optional[Assignment]:
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self) -> None:
        for variable in self.domains:
            self.domains[variable] = {
                word for word in self.domains[variable] if len(word) == variable.length
            }

    def revise(self, x: Variable, y: Variable) -> bool:
        revised = False
        overlap = self.crossword.overlaps.get((x, y))
        
        if overlap is None:
            return False
        
        i, j = overlap  # i is index in x, j is index in y
        
        # Optimization: Find all characters present at position j in domain y
        compatible_chars_y = {word_y[j] for word_y in self.domains[y]}
        
        words_to_remove = set()
        for word_x in self.domains[x]:
            # Check if word_x's character at position i is compatible with any char in y's domain
            if word_x[i] not in compatible_chars_y:
                words_to_remove.add(word_x)
        
        if words_to_remove:
            self.domains[x] -= words_to_remove
            revised = True
        
        return revised

    def ac3(self, arcs: Optional[List[Tuple[Variable, Variable]]] = None) -> bool:
        if arcs is None:
            queue = deque()
            for x in self.crossword.variables:
                for y in self.crossword.variables:
                    if x != y and self.crossword.overlaps.get((x, y)) is not None:
                        queue.append((x, y))
        else:
            queue = deque(arcs)
        
        while queue:
            x, y = queue.popleft()
            
            if self.revise(x, y):
                if not self.domains[x]:
                    return False
                
                for z in self.crossword.neighbors(x):
                    if z != y:
                        queue.append((z, x))
        
        return True

    def assignment_complete(self, assignment: Assignment) -> bool:
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment: Assignment) -> bool:
        # 1. Check if all values are distinct
        values = list(assignment.values())
        if len(values) != len(set(values)):
            return False
        
        # 2. Check for conflicts between neighboring variables
        for v1 in assignment:
            for v2 in self.crossword.neighbors(v1):
                if v2 in assignment:
                    overlap = self.crossword.overlaps.get((v1, v2))
                    if overlap is not None:
                        i, j = overlap
                        if assignment[v1][i] != assignment[v2][j]:
                            return False
        
        return True

    def order_domain_values(self, var: Variable, assignment: Assignment) -> List[str]:
        def count_eliminations(value: str) -> int:
            """Count how many values this choice eliminates from unassigned neighbors"""
            eliminations = 0
            
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in assignment:
                    overlap = self.crossword.overlaps.get((var, neighbor))
                    if overlap is not None:
                        i, j = overlap
                        
                        # Count how many values in neighbor's domain would be eliminated
                        for neighbor_value in self.domains[neighbor]:
                            if value[i] != neighbor_value[j]:
                                eliminations += 1
            
            return eliminations
        
        # Sort values by number of eliminations (ascending order)
        return sorted(list(self.domains[var]), key=count_eliminations)

    def select_unassigned_variable(self, assignment: Assignment) -> Optional[Variable]:
        unassigned = [v for v in self.crossword.variables if v not in assignment]
        
        if not unassigned:
            return None
        
        # Sort by: 1) fewest remaining values (MRV), 2) highest degree (tie-breaker)
        def sort_key(variable: Variable) -> Tuple[int, int]:
            return (len(self.domains[variable]), -len(self.crossword.neighbors(variable)))
        
        return min(unassigned, key=sort_key)

    def backtrack(self, assignment: Assignment) -> Optional[Assignment]:
        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)
        
        if var is None:
            return None
        
        # Try each value in the domain of var (ordered by LCV)
        for value in self.order_domain_values(var, assignment):
            
            # 1. Check local consistency (only against already assigned neighbors)
            temp_assignment = assignment.copy()
            temp_assignment[var] = value
            if not self.consistent(temp_assignment):
                continue

            # 2. Forward Checking: Propagate constraints to unassigned neighbors
            # Save current domains to restore them on backtrack
            old_domains: Domain = {v: self.domains[v].copy() for v in self.crossword.variables}
            
            # Assume consistent until proven otherwise
            is_consistent = True
            
            # Temporarily set the domain of the assigned variable to the chosen value
            self.domains[var] = {value}
            
            # Enforce consistency on unassigned neighbors
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in temp_assignment:
                    # Revise the neighbor's domain based on the new assignment of var
                    if self.revise(neighbor, var):
                        # If a neighbor's domain becomes empty, this path is inconsistent
                        if not self.domains[neighbor]:
                            is_consistent = False
                            break
            
            if is_consistent:
                # If forward checking passed, continue with backtracking search
                result = self.backtrack(temp_assignment)
                if result is not None:
                    return result
            
            # 3. Restore domains (Backtrack)
            self.domains = old_domains
        
        return None

# --- Funções CLI Interativas ---

def select_file_from_list(prompt: str, search_path: str, extension_regex: str) -> str:
    """
    Lists files in the specified search path matching the regex and allows the user
    to select one by number.
    """
    full_search_path = os.path.abspath(search_path)
    
    files = []
    if os.path.isdir(full_search_path):
        files = [
            os.path.join(search_path, f)
            for f in os.listdir(full_search_path)
            if re.match(extension_regex, f, re.IGNORECASE)
        ]
    
    if not files:
        print(f"\n[ERRO] Não foram encontrados ficheiros correspondentes a '{extension_regex}' no diretório '{full_search_path}'.")
        print("Por favor, verifique se o caminho está correto ou digite o caminho completo do ficheiro.")
        manual_input = input(f"Caminho para o ficheiro ({prompt}): ").strip()
        if os.path.exists(manual_input):
            return manual_input
        else:
            raise FileNotFoundError(f"O ficheiro '{manual_input}' não foi encontrado.")

    print(f"\n{prompt} - Ficheiros disponíveis em '{search_path}':")
    
    files.sort() 
    
    for i, file in enumerate(files):
        display_name = os.path.basename(file)
        print(f"  [{i + 1}] {display_name}")
    
    while True:
        choice = input("Digite o NÚMERO do ficheiro ou o CAMINHO completo: ").strip()
        
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(files):
                return files[index] 
            else:
                print("Escolha inválida. Por favor, digite um número da lista.")
        elif os.path.exists(choice):
            return choice
        else:
            print(f"Escolha inválida ou ficheiro não encontrado no caminho '{choice}'.")


def main():

    print("\n" + "="*50)
    print("= Crossword Solver AI - Interface de Linha de Comando =")
    print("="*50)

    try:
        structure_file = select_file_from_list(
            prompt="Ficheiro de ESTRUTURA", 
            search_path=os.path.join("data", "structure"), 
            extension_regex=r".*\.txt$" 
        )
        words_file = select_file_from_list(
            prompt="Ficheiro de VOCABULÁRIO", 
            search_path=os.path.join("data", "words"), 
            extension_regex=r".*\.txt$" 
        )
    except Exception as e:
        print(f"\n[ERRO] Falha ao listar ficheiros: {e}")
        return

    output_image = "output.png" 

    try:
        # 1. Generate crossword
        print("\n[INFO] A carregar ficheiros e a processar estrutura...")
        crossword = Crossword(structure_file, words_file)
        creator = CrosswordCreator(crossword)
        
        # 2. Solve the Crossword
        print("[INFO] A iniciar o algoritmo de resolução (CSP com Forward Checking)...")
        assignment = creator.solve()

        # 3. Print result
        if assignment is None:
            print("\n[RESULTADO] Não foi encontrada nenhuma solução para o problema de Crossword.")
        else:
            print("\n[RESULTADO] Solução Encontrada! A imprimir no terminal:")
            creator.print(assignment)
            
            if output_image:
                print(f"[INFO] A guardar a imagem do Crossword em: {output_image}")
                creator.save(assignment, output_image)
                print("[INFO] Imagem guardada com sucesso.")

    except FileNotFoundError as e:
        print(f"\n[ERRO FATAL] Um ficheiro necessário não foi encontrado: {e}")
    except Exception as e:
        print(f"\n[ERRO FATAL] Ocorreu um erro inesperado durante o processamento: {e}")
    finally:
        print("\n" + "="*50)
        print("= Fim da Execução =")
        print("="*50)


if __name__ == "__main__":
    main()
