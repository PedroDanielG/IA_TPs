import sys
from collections import deque

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
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

    def print(self, assignment):
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

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
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
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
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
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for variable in self.domains:
            # Remove words that don't match the variable's length
            words_to_remove = []
            for word in self.domains[variable]:
                if len(word) != variable.length:
                    words_to_remove.append(word)
            
            for word in words_to_remove:
                self.domains[variable].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps[x, y]
        
        # If there's no overlap, no revision needed
        if overlap is None:
            return False
        
        i, j = overlap  # i is index in x, j is index in y
        
        words_to_remove = []
        for word_x in self.domains[x]:
            # Check if there's any word in y's domain that's compatible
            compatible = False
            for word_y in self.domains[y]:
                if word_x[i] == word_y[j]:
                    compatible = True
                    break
            
            if not compatible:
                words_to_remove.append(word_x)
        
        for word in words_to_remove:
            self.domains[x].remove(word)
            revised = True
        
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            # Create all possible arcs
            queue = deque()
            for x in self.crossword.variables:
                for y in self.crossword.variables:
                    if x != y and self.crossword.overlaps[x, y] is not None:
                        queue.append((x, y))
        else:
            queue = deque(arcs)
        
        while queue:
            x, y = queue.popleft()
            
            if self.revise(x, y):
                # If domain of x becomes empty, no solution exists
                if len(self.domains[x]) == 0:
                    return False
                
                # Add arcs (z, x) for each neighbor z of x (except y)
                for z in self.crossword.neighbors(x):
                    if z != y:
                        queue.append((z, x))
        
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check if all values are distinct
        values = list(assignment.values())
        if len(values) != len(set(values)):
            return False
        
        # Check if every value is the correct length
        for variable, word in assignment.items():
            if len(word) != variable.length:
                return False
        
        # Check for conflicts between neighboring variables
        for variable in assignment:
            for neighbor in self.crossword.neighbors(variable):
                if neighbor in assignment:
                    overlap = self.crossword.overlaps[variable, neighbor]
                    if overlap is not None:
                        i, j = overlap
                        if assignment[variable][i] != assignment[neighbor][j]:
                            return False
        
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        def count_eliminations(value):
            """Count how many values this choice eliminates from neighbors"""
            eliminations = 0
            
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in assignment:  # Only consider unassigned neighbors
                    overlap = self.crossword.overlaps[var, neighbor]
                    if overlap is not None:
                        i, j = overlap
                        
                        # Count how many values in neighbor's domain would be eliminated
                        for neighbor_value in self.domains[neighbor]:
                            if value[i] != neighbor_value[j]:
                                eliminations += 1
            
            return eliminations
        
        # Sort values by number of eliminations (ascending order)
        return sorted(self.domains[var], key=count_eliminations)

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned = [v for v in self.crossword.variables if v not in assignment]
        
        if not unassigned:
            return None
        
        # Sort by: 1) fewest remaining values, 2) highest degree (most neighbors)
        def sort_key(variable):
            return (len(self.domains[variable]), -len(self.crossword.neighbors(variable)))
        
        return min(unassigned, key=sort_key)

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # Check if assignment is complete
        if self.assignment_complete(assignment):
            return assignment
        
        # Select an unassigned variable
        var = self.select_unassigned_variable(assignment)
        
        if var is None:
            return None
        
        # Try each value in the domain of var
        for value in self.order_domain_values(var, assignment):
            # Create new assignment with this value
            new_assignment = assignment.copy()
            new_assignment[var] = value
            
            # Check if this assignment is consistent
            if self.consistent(new_assignment):
                # Make inference by enforcing arc consistency
                # Save current domains
                old_domains = {}
                for variable in self.domains:
                    old_domains[variable] = self.domains[variable].copy()
                
                # Remove the chosen value from var's domain temporarily
                self.domains[var] = {value}
                
                # Create arcs from neighbors to var
                arcs = [(neighbor, var) for neighbor in self.crossword.neighbors(var)]
                
                # Check if arc consistency can be maintained
                if self.ac3(arcs):
                    result = self.backtrack(new_assignment)
                    if result is not None:
                        return result
                
                # Restore domains if backtracking
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