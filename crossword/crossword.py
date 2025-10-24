from typing import Tuple, List, Set, Dict, Optional

class Variable:

    ACROSS = "across"
    DOWN = "down"

    def __init__(self, i: int, j: int, direction: str, length: int):
        """Create a new variable with starting point, direction, and length."""
        self.i = i
        self.j = j
        self.direction = direction
        self.length = length
        self.cells: List[Tuple[int, int]] = self._calculate_cells()

    def _calculate_cells(self) -> List[Tuple[int, int]]:
        """Calculate the list of (row, col) tuples this variable occupies."""
        cells = []
        for k in range(self.length):
            if self.direction == Variable.DOWN:
                cells.append((self.i + k, self.j))
            else:  # Variable.ACROSS
                cells.append((self.i, self.j + k))
        return cells

    def __hash__(self) -> int:
        return hash((self.i, self.j, self.direction, self.length))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Variable):
            return NotImplemented
        return (
            (self.i == other.i) and
            (self.j == other.j) and
            (self.direction == other.direction) and
            (self.length == other.length)
        )

    def __str__(self) -> str:
        return f"({self.i}, {self.j}) {self.direction} : {self.length}"

    def __repr__(self) -> str:
        return f"Variable({self.i}, {self.j}, {repr(self.direction)}, {self.length})"


class Crossword:

    def __init__(self, structure_file: str, words_file: str):

        # Determine structure of crossword
        with open(structure_file) as f:
            contents = f.read().splitlines()
            self.height = len(contents)
            self.width = max(len(line) for line in contents)

            # Structure is a 2D list of booleans: True for open cell, False for blocked
            self.structure: List[List[bool]] = [
                [
                    (contents[i][j] == "_") if j < len(contents[i]) else False
                    for j in range(self.width)
                ]
                for i in range(self.height)
            ]

        # Save vocabulary list and pre-filter by length (OPTIMIZATION)
        self.words: Set[str] = set()
        self.words_by_length: Dict[int, Set[str]] = {}
        with open(words_file) as f:
            for word in f.read().upper().splitlines():
                self.words.add(word)
                length = len(word)
                if length not in self.words_by_length:
                    self.words_by_length[length] = set()
                self.words_by_length[length].add(word)

        # Determine variable set (rest of the logic remains the same)
        self.variables: Set[Variable] = set()
        for i in range(self.height):
            for j in range(self.width):

                # Vertical words
                starts_word_down = (
                    self.structure[i][j]
                    and (i == 0 or not self.structure[i - 1][j])
                )
                if starts_word_down:
                    length = 1
                    for k in range(i + 1, self.height):
                        if self.structure[k][j]:
                            length += 1
                        else:
                            break
                    if length > 1:
                        self.variables.add(Variable(
                            i=i, j=j,
                            direction=Variable.DOWN,
                            length=length
                        ))

                # Horizontal words
                starts_word_across = (
                    self.structure[i][j]
                    and (j == 0 or not self.structure[i][j - 1])
                )
                if starts_word_across:
                    length = 1
                    for k in range(j + 1, self.width):
                        if self.structure[i][k]:
                            length += 1
                        else:
                            break
                    if length > 1:
                        self.variables.add(Variable(
                            i=i, j=j,
                            direction=Variable.ACROSS,
                            length=length
                        ))

        # Compute overlaps for each word (logic remains the same, but with type hints)
        self.overlaps: Dict[Tuple[Variable, Variable], Optional[Tuple[int, int]]] = {}
        for v1 in self.variables:
            for v2 in self.variables:
                if v1 == v2:
                    continue
                
                # Check for intersection of cells
                intersection = set(v1.cells).intersection(v2.cells)
                
                if not intersection:
                    self.overlaps[v1, v2] = None
                else:
                    # An intersection means they overlap at exactly one cell
                    intersecting_cell = intersection.pop()
                    self.overlaps[v1, v2] = (
                        v1.cells.index(intersecting_cell),
                        v2.cells.index(intersecting_cell)
                    )

    def neighbors(self, var: Variable) -> Set[Variable]:
        """Given a variable, return set of overlapping variables."""
        return set(
            v for v in self.variables
            if v != var and self.overlaps.get((v, var)) is not None
        )
