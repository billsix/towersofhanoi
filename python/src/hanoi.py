import snoop

initial_peg: str = "1"
temporary_peg: str = "2"
goal_peg: str = "3"


def first_remap(s: str) -> str:
    result: str = ""
    c: str
    for c in s:
        # the temporary peg becomes the goal peg
        if c == temporary_peg:
            result += goal_peg
        # the goal peg becomes the temporary peg
        elif c == goal_peg:
            result += temporary_peg
        # the initial peg is unchanges
        else:
            result += c
    return result


def second_remap(s: str) -> str:
    result: str = ""
    c: str
    for c in s:
        # the initial peg becomes the temporary peg
        if c == initial_peg:
            result += temporary_peg
        # the temporary peg becomes the initial peg
        elif c == temporary_peg:
            result += initial_peg
        else:
            result += c
    return result


@snoop
def hanoi(n: int):
    moves: str = initial_peg + " -> " + goal_peg

    for x in range(2, n + 1):
        x_minus_1_i_to_t: str = first_remap(moves)
        big_peg_to_goal: str = initial_peg + " -> " + goal_peg
        x_minus_1_t_to_g: str = second_remap(moves)

        moves: str = x_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + x_minus_1_t_to_g
    print(moves)


@snoop
def hanoi_1(i: int, t: int, g: int) -> str:
    return str(i) + " -> " + str(g)


@snoop
def hanoi_2(i: int, t: int, g: int) -> str:
    two_minus_1_i_to_t: str = hanoi_1(i=i, t=g, g=t)
    big_peg_to_goal: str = initial_peg + " -> " + goal_peg
    two_minus_1_t_to_g: str = hanoi_1(i=t, t=i, g=g)

    moves: str = two_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + two_minus_1_t_to_g
    return moves


@snoop
def hanoi_3(i: int, t: int, g: int) -> str:
    three_minus_1_i_to_t: str = hanoi_2(i=i, t=g, g=t)
    big_peg_to_goal: str = initial_peg + " -> " + goal_peg
    three_minus_1_t_to_g: str = hanoi_2(i=t, t=i, g=g)

    moves: str = (
        three_minus_1_i_to_t + "\n" + big_peg_to_goal + "\n" + three_minus_1_t_to_g
    )
    return moves
