import sys
import os
import re
import json
from collections import deque
from typing import Dict, Set, List, Optional, Tuple, Any

# Import the Google GenAI client for LLM interaction
from google import genai

from crossword import Variable, Crossword

# Define types for clarity
Assignment = Dict[Variable, str]
Domain = Dict[Variable, Set[str]]

# Hardcoded output file path
OUTPUT_IMAGE_FILE = "output.png"

# Global variable to store generated clues
CLUES: Dict[str, str] = {}


class CrosswordCreator:

    def __init__(self, crossword: Crossword):
        """
        Create new CSP crossword generator.
        """
        self.crossword = crossword
        self.domains: Domain = {}
        
        # Initialize domains: using words_by_length from the refactored Crossword
        for var in self.crossword.variables:
            # Use the pre-filtered set of words for the correct length
            self.domains[var] = self.crossword.words_by_length.get(var.length, set()).copy()

    def letter_grid(self, assignment: Assignment) -> List[List[Optional[str]]]:
        """
        Return 2D array representing a given assignment.
        """
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

    def print(self, assignment: Assignment, clues: Optional[Dict[str, str]] = None) -> None:
        """
        Print crossword assignment and optional clues to the terminal.
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
        
        if clues:
            print("\n--- PISTAS GERADAS POR IA ---\n")
            # Group clues by direction (Across/Down)
            across_clues = []
            down_clues = []
            
            # Sort variables for consistent clue numbering
            sorted_vars = sorted(assignment.keys(), key=lambda v: (v.i, v.j, v.direction))
            
            for i, var in enumerate(sorted_vars):
                word = assignment[var]
                clue = clues.get(word.upper()) # Clues are stored in uppercase
                
                if clue:
                    clue_entry = f"({var.i+1},{var.j+1}) {word.upper()}: {clue}"
                    if var.direction == Variable.ACROSS:
                        across_clues.append(clue_entry)
                    else:
                        down_clues.append(clue_entry)
            
            print("ACROSS (Horizontal):")
            for clue in across_clues:
                print(f"  {clue}")
            
            print("\nDOWN (Vertical):")
            for clue in down_clues:
                print(f"  {clue}")
            print("\n" + "=" * (self.crossword.width * 2 + 2) + "\n")


    def save(self, assignment: Assignment, filename: str, clues: Optional[Dict[str, str]] = None) -> None:
        """
        Save crossword assignment to an image file.
        """
        # NOTE: This function requires the Pillow library and the specific font file
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
        
        # Save clues to a separate text file
        if clues:
            clues_filename = os.path.splitext(filename)[0] + "_clues.txt"
            with open(clues_filename, "w", encoding="utf-8") as f:
                f.write("--- PISTAS GERADAS POR IA ---\n\n")
                
                across_clues = []
                down_clues = []
                
                sorted_vars = sorted(assignment.keys(), key=lambda v: (v.i, v.j, v.direction))
                
                for i, var in enumerate(sorted_vars):
                    word = assignment[var]
                    clue = clues.get(word.upper())
                    
                    if clue:
                        clue_entry = f"({var.i+1},{var.j+1}) {word.upper()}: {clue}\n"
                        if var.direction == Variable.ACROSS:
                            across_clues.append(clue_entry)
                        else:
                            down_clues.append(clue_entry)
                
                f.write("ACROSS (Horizontal):\n")
                f.writelines(across_clues)
                f.write("\nDOWN (Vertical):\n")
                f.writelines(down_clues)
            
            print(f"[INFO] Pistas guardadas em: {clues_filename}")


    def solve(self) -> Optional[Assignment]:
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self) -> None:
        """
        This function is now largely redundant due to pre-filtering in __init__
        but is kept for completeness. It ensures all words in a variable's domain
        match its required length.
        """
        for variable in self.domains:
            self.domains[variable] = {
                word for word in self.domains[variable] if len(word) == variable.length
            }

    def revise(self, x: Variable, y: Variable) -> bool:
        """
        Make variable `x` arc consistent with variable `y`.
        Return True if a revision was made to the domain of `x`; return False otherwise.
        """
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
        """
        Update `self.domains` such that each variable is arc consistent.
        """
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
        """
        Return True if `assignment` is complete.
        """
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment: Assignment) -> bool:
        """
        Return True if `assignment` is consistent.
        """
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
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables (LCV heuristic).
        """
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
        """
        Return an unassigned variable using the MRV (Minimum Remaining Value)
        and Degree heuristics.
        """
        unassigned = [v for v in self.crossword.variables if v not in assignment]
        
        if not unassigned:
            return None
        
        # Sort by: 1) fewest remaining values (MRV), 2) highest degree (tie-breaker)
        def sort_key(variable: Variable) -> Tuple[int, int]:
            return (len(self.domains[variable]), -len(self.crossword.neighbors(variable)))
        
        return min(unassigned, key=sort_key)

    def backtrack(self, assignment: Assignment) -> Optional[Assignment]:
        """
        Using Backtracking Search with Forward Checking, return a complete assignment.
        """
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

# --- LLM Clue Generation ---

def generate_clues_with_llm(words: Set[str], api_key: str) -> Dict[str, str]:
    """
    Generates clues for a set of words using an LLM.
    Returns a dictionary {WORD: Clue}.
    """
    try:
        client = genai.Client(api_key=api_key)
        
        word_list = list(words)
        
        # Create a prompt for the LLM to generate clues in Portuguese
        prompt = f"""
        Você é um criador de palavras-cruzadas profissional.
        Para cada palavra na lista a seguir, crie uma pista concisa e criativa em PORTUGUÊS.
        O resultado DEVE ser um objeto JSON, onde a chave é a palavra em MAIÚSCULAS e o valor é a pista.
        NÃO inclua qualquer texto ou explicação fora do objeto JSON.

        Lista de Palavras: {word_list}
        """

        print("[INFO] A contactar a IA para gerar pistas usando gemini-2.5-flash...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Parse the JSON response
        clues_json = response.text
        clues_dict = json.loads(clues_json)
        
        # Ensure all keys are uppercase for consistency
        return {k.upper(): v for k, v in clues_dict.items()}
        
    except Exception as e:
        print(f"[ERRO LLM] Não foi possível gerar pistas. Verifique a sua ligação à internet ou a chave API. Detalhes: {e}")
        return {}


# --- CLI Functions ---

def select_file_from_list(prompt: str, search_path: str, extension_regex: str) -> str:
    """
    Lists files in the specified search path matching the regex and allows the user
    to select one by number.
    """
    current_dir = os.getcwd()
    full_search_path = os.path.abspath(search_path)
    
    files = []
    if os.path.isdir(full_search_path):
        # Lista ficheiros no diretório de pesquisa
        # O caminho de retorno será relativo ao diretório de pesquisa
        files = [
            os.path.join(search_path, f)
            for f in os.listdir(full_search_path)
            if re.match(extension_regex, f, re.IGNORECASE)
        ]
    
    if not files:
        print(f"\n[ERRO] Não foram encontrados ficheiros correspondentes a '{extension_regex}' no diretório '{search_path}'.")
        print("Por favor, digite o caminho completo do ficheiro.")
        # Fallback to manual input
        manual_input = input(f"Caminho para o ficheiro ({prompt}): ").strip()
        if os.path.exists(manual_input):
            return manual_input
        else:
            raise FileNotFoundError(f"O ficheiro '{manual_input}' não foi encontrado.")

    print(f"\n{prompt} - Ficheiros disponíveis em '{search_path}':")
    
    # Sort files alphabetically for a cleaner menu
    files.sort() 
    
    for i, file in enumerate(files):
        # Display only the filename for a cleaner menu
        display_name = os.path.basename(file)
        print(f"  [{i + 1}] {display_name}")
    
    while True:
        choice = input("Digite o NÚMERO do ficheiro ou o CAMINHO completo: ").strip()
        
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(files):
                return files[index] # Return the full relative path (e.g., data/structure/file.txt)
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
        # Get file paths interactively by selection
        structure_file = select_file_from_list(
            prompt="Ficheiro de ESTRUTURA", 
            search_path=os.path.join("data", "structure"), # Novo caminho de pesquisa
            extension_regex=r".*\.txt$" 
        )
        words_file = select_file_from_list(
            prompt="Ficheiro de VOCABULÁRIO", 
            search_path=os.path.join("data", "words"), # Novo caminho de pesquisa
            extension_regex=r".*\.txt$" 
        )
    except FileNotFoundError as e:
        print(f"\n[ERRO FATAL] {e}")
        return
    except Exception as e:
        print(f"\n[ERRO FATAL] Falha ao listar ficheiros: {e}")
        return

    # Hardcoded output file path
    output_image = OUTPUT_IMAGE_FILE

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
            words_used = {word.upper() for word in assignment.values()}
            clues = {}
            
            # Ask user if they want to generate clues
            generate_clues = input("\n[PERGUNTA] Deseja gerar pistas (clues) com a IA para as palavras usadas? (s/n): ").strip().lower()
            
            if generate_clues == 's':
                # NOVA PERGUNTA: Pede a chave de API diretamente
                api_key = input("Por favor, insira a sua Chave API da Google Gemini (AIza...): ").strip()
                if not api_key:
                    print("[AVISO] Chave API não fornecida. A ignorar a geração de pistas.")
                else:
                    clues = generate_clues_with_llm(words_used, api_key)
                
            print("\n[RESULTADO] Solução Encontrada! A imprimir no terminal:")
            creator.print(assignment, clues)
            
            # Save the output image automatically
            print(f"[INFO] A guardar a imagem do Crossword em: {output_image}")
            creator.save(assignment, output_image, clues)
            print("[INFO] Imagem e Pistas guardadas com sucesso.")

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
