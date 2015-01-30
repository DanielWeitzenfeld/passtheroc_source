

#FIELD_GOAL_RANGE = 66 # In simulations, drives dying before this point will punt (regardless of game situation).
#PIECES = [0, 15, 40, 66, 99] # Divide the field up into chunks for piecewise exponential modeling.
#REDZONE_PIECE = 3
#PIECES = [0, 13, 66, 99]
#REDZONE_PIECE = 2

FIELD_GOAL_RANGE = 67
PIECES = [0, 13, 75, 99]
REDZONE_PIECE = 2

PUNT_DISTANCE = 38 # net of return
PUNT_CLOCK_TIME = 15./60
TOUCHDOWN_CLOCK_TIME = 15./60
FG_CLOCK_TIME = 15./60
LOSING_BADLY_THRESHOLD = 16
SIMULATION_TIE_BREAKER_COIN_FLIP_HOME_ADVANTAGE = .03


def piece_lengths(PIECES):
    return [PIECES[i + 1] - PIECES[i] for i in range(len(PIECES) - 1)]

PIECE_LENGTHS = piece_lengths(PIECES)