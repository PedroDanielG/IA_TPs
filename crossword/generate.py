import sys
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
        
        # Initialize domains: using words_by_length from the refactored Crossword (OPTIMIZATION)
        for var in self.crossword.variables:
            # Use the pre-filtered set of words for the correct length
            self.domains[var] = self.crossword.words_by_length.get(var.length, set()).copy()

    # ... (letter_grid, print, save methods remain largely the same, with type hints added)
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

    def print(self, assignment: Assignment) -> None:
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment: Assignment, filename: str) -> None:
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
            # Tenta carregar a fonte, senão usa a default
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
        Enforce arc consistency, and then solve the CSP.
        """
        self.ac3() # Run AC3 once before backtracking
        return self.backtrack(dict())

    def enforce_node_consistency(self) -> None:
        """
        This function is now largely redundant due to pre-filtering in __init__
        but is kept for completeness.
        """
        for variable in self.domains:
            self.domains[variable] = {
                word for word in self.domains[variable] if len(word) == variable.length
            }

    def revise(self, x: Variable, y: Variable) -> bool:
        """
        Make variable `x` arc consistent with variable `y`.
        Return True if a revision was made to the domain of `x`; return False otherwise.
        (OPTIMIZATION: Uses set comprehension for faster checking)
        """
        revised = False
        overlap = self.crossword.overlaps.get((x, y))
        
        if overlap is None:
            return False
        
        i, j = overlap  # i is index in x, j is index in y
        
        # Optimization: Find all characters present at position j in domain y
        # This is O(|D_y|)
        compatible_chars_y = {word_y[j] for word_y in self.domains[y]}
        
        words_to_remove = set()
        for word_x in self.domains[x]:
            # Check if word_x's character at position i is compatible with any char in y's domain
            # This check is O(1) due to the set lookup
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
                        # Only add the arc (z, x), not (x, z)
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
                        # This check is now faster due to the optimized revise logic
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
        (OPTIMIZATION: Uses Forward Checking instead of full AC3 at each step)
        """
        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)
        
        if var is None:
            return None
        
        # Try each value in the domain of var (ordered by LCV)
        for value in self.order_domain_values(var, assignment):
            
            # 1. Check local consistency (against already assigned neighbors)
            temp_assignment = assignment.copy()
            temp_assignment[var] = value
            if not self.consistent(temp_assignment):
                continue

            # 2. Forward Checking Setup: Save current domains to restore them on backtrack
            # We only need to save the domains of the unassigned neighbors of var
            old_domains: Domain = {
                v: self.domains[v].copy() 
                for v in self.crossword.variables
            }
            
            # Temporarily set the domain of the assigned variable to the chosen value
            self.domains[var] = {value}
            
            # Enforce consistency on unassigned neighbors (Forward Checking)
            is_consistent = True
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


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()