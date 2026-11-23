from game import Board, suggest_move


def test_takes_winning_move():
    b = Board()
    b.set_cell(0, 0, "X"); b.set_cell(0, 1, "X")
    assert suggest_move(b, "X", "O") == (0, 2)


def test_blocks_opponent():
    b = Board()
    b.set_cell(1, 0, "O"); b.set_cell(1, 1, "O")
    assert suggest_move(b, "X", "O") == (1, 2)
