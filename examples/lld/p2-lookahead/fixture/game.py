class Board:
    def __init__(self):
        self.cells = [[None] * 3 for _ in range(3)]

    def set_cell(self, row, col, symbol):
        self.cells[row][col] = symbol

    def empty_cells(self):
        return [(r, c) for r in range(3) for c in range(3) if self.cells[r][c] is None]

    def winner(self):
        lines = [[(r, c) for c in range(3)] for r in range(3)]
        lines += [[(r, c) for r in range(3)] for c in range(3)]
        lines += [[(i, i) for i in range(3)], [(i, 2 - i) for i in range(3)]]
        for line in lines:
            first = self.cells[line[0][0]][line[0][1]]
            if first and all(self.cells[r][c] == first for r, c in line):
                return first
        return None


def suggest_move(board, me, opponent):
    """Win if possible, else block, else first empty cell."""
    for symbol in (me, opponent):
        for r, c in board.empty_cells():
            board.set_cell(r, c, symbol)
            if board.winner() == symbol:
                return (r, c)
            board.set_cell(r, c, None)
    return board.empty_cells()[0]
