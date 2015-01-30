import os
import pandas as pd
from . import PIECES, LOSING_BADLY_THRESHOLD

PARENT_DIR = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
DATA_DIR = os.path.join(os.getcwd(), 'data/')
CHART_DIR = os.path.join(os.getcwd(), 'charts/')
GAME_LEVEL_DATASET_2014 = DATA_DIR + 'nfl_game_level.xlsx'
DOME_DATASET = DATA_DIR + 'nfl_home_stadiums.csv'

### handy lists of columns for looking at the data.
DRIVE_COLS = ['GameId', 'quarter', 'minute', 'second', 'drive_id', 'OffenseTeam', u'DefenseTeam', 'start_yardline',
              'first_downs', 'yards_zero_plus', 'yards_end_minus_start_zero_plus', 'end_yardline_zero_plus',
              'end_turnover', 'end_touchdown', 'end_field_goal_attempt']
PLAY_COLS = ['GameId', 'drive_id', 'play_id', 'Quarter', 'Minute', 'Second', 'OffenseTeam', u'DefenseTeam', 'Yards',
             'is_offensive_touchdown', 'is_field_goal', 'Down', 'ToGo']


def enrich_play_level_df(df):
    '''
    Add helpful columns - mostly boolean - to the drive level dataset, identifying play types and outcomes.
    Generate unique drive_ids grouping plays into drives.

    :param df: drive level data set from http://nflsavant.com/about.php
    :return: df
    '''
    df = df.sort_index(by=['GameId', 'Quarter', 'Minute', 'Second'], ascending=[True, True, False, False])
    df = df.reset_index().drop('index', axis=1)

    df['clock'] = 60 - (df.Quarter) * 15 + df.Minute + df.Second / 60.0
    df['clock_after_play'] = df.clock.shift(-1)

    # drop plays we obviously dont need
    # df = df[(df.PlayType != 'TIMEOUT')]
    df = df[(df.Description.notnull())]
    df = df[~(df.Description.str.contains('TWO-MINUTE WARNING'))]
    df = df[~(df.Description.str.contains('TIMEOUT')) |
            (df.Description.str.len() > 35)]  # some timeouts tacked onto play descriptions

    # Tag final play of half, so we'll know if a drive was censored by the clock
    df['is_end_of_quarter'] = (df.Description.str.contains(r'END.+QUARTER'))
    df['is_end_of_period'] = (df.Description.str.contains('END GAME')) | \
                             (df.Description.str.contains('END OF GAME')) | \
                             (df.Description.str.contains('END.+HALF')) | \
                             (df.Description.str.contains(r'END.+QUARTER')) & \
                             (df.Quarter.isin([2, 4]))
    df['is_final_play_of_half'] = df.is_end_of_period.shift(-1).fillna(False)

    # Some plays lack the OffenseTeam variable.  Interpolate it.
    df['Offense_ffill'] = df.OffenseTeam.fillna(method='ffill')
    df.OffenseTeam = df.OffenseTeam.fillna(method='backfill')
    df.loc[df.is_end_of_period, 'OffenseTeam'] = df.Offense_ffill  # don't backfill from other games!

    # Generate indicators we care about, using flags in dataset, PlayType column, and parsing of Description col.
    df.IsFumble = df.IsFumble.astype(bool)
    df.IsInterception = df.IsInterception.astype(bool)
    df['is_offensive_touchdown'] = (df.IsTouchdown == 1) & ~(df.IsFumble | df.IsInterception) & \
                                   (df.IsChallengeReversed != 1)
    df['is_punt'] = (df.PlayType == 'PUNT')
    df['is_kick_off'] = (df.PlayType == 'KICK OFF')
    df['is_field_goal'] = (df.PlayType == 'FIELD GOAL')
    df['is_field_goal_not_nullified'] = (df.PlayType == 'FIELD GOAL') & (df.IsPenaltyAccepted != 1)
    df['is_extra_point'] = (df.PlayType == 'EXTRA POINT')
    df['is_extra_point_successful'] = (df.is_extra_point) & (df.Description.str.contains('IS GOOD'))
    df['is_after_touchdown'] = (df.PlayType.isin(['EXTRA POINT', 'TWO-POINT CONVERSION']))
    df['is_time_out'] = (df.PlayType == 'TIMEOUT')
    df['is_no_play'] = (df.Description.str.contains('NO PLAY'))
    df['is_qb_kneel'] = (df.PlayType == 'QB KNEEL')
    df['is_missed_field_goal'] = (df.is_field_goal) & \
                                 (df.Description.str.contains('NO GOOD') | df.Description.str.contains('BLOCKED'))
    df['is_safety'] = (df.Description.str.contains('SAFETY'))
    df['is_turnover'] = (df.IsFumble | df.IsInterception) & (df.OffenseTeam != df.OffenseTeam.shift(-1))
    df['is_turnover_on_missed_fg'] = (df.is_missed_field_goal) & (df.OffenseTeam != df.OffenseTeam.shift(-1))
    df['is_turnover_on_downs'] = (df.Down == 4) & \
                                 (df.IsTouchdown == 0) & \
                                 (~df.is_field_goal) & \
                                 ~(df.is_punt) & \
                                 ~(df.is_turnover) & \
                                 (df.OffenseTeam != df.OffenseTeam.shift(-1))

    # penalties
    df['is_offensive_penalty'] = (df.IsPenaltyAccepted == 1) & (df.PenaltyTeam == df.OffenseTeam)
    df['is_defense_penalty'] = (df.IsPenaltyAccepted == 1) & (df.PenaltyTeam == df.DefenseTeam)

    # Break up plays into drives.
    df['new_drive'] = df.is_turnover.shift(1) | df.is_kick_off.shift(1) | \
                      df.is_punt.shift(1) | df.is_turnover_on_downs.shift(1) | df.is_turnover_on_missed_fg.shift(1)
    df.new_drive = df.new_drive.fillna(False)
    df['drive_id'] = df.new_drive.astype(int).cumsum()

    # Un-tag non-drive plays
    df['is_drive_play'] = ~(df.is_kick_off) & \
                          ~(df.is_end_of_quarter) & \
                          ~(df.is_after_touchdown) & \
                          ~(df.is_end_of_period)
    # ~(df.PlayType.isin(['NO PLAY']))
    df.loc[~df.is_drive_play, 'drive_id'] = None

    df['is_first_play_of_drive'] = (df.drive_id != df.drive_id.shift(1)) & (df.drive_id.notnull())
    df['is_last_play_of_drive'] = (df.drive_id != df.drive_id.shift(-1)) & (df.drive_id.notnull())
    df['yards_offensive'] = df.apply(offensive_yards, axis=1)
    df['yardline_after_play'] = df.apply(
        lambda x: x['YardLine'] if x['is_no_play'] else x['YardLine'] + x['yards_offensive'],
        axis=1)
    df['is_earned_first_down'] = (df.Down == 1) & \
                                 (df.yards_offensive.shift(1) > df.ToGo.shift(1)) & \
                                 (df.OffenseTeam.shift(1) == df.OffenseTeam)
    df['play_id'] = df.index
    return df


def merge_in_game_level_dataset(df, game_level_dataset):
    """
    Merge in home and away team data
    :param df:
    :param game_level_dataset:
    :return:
    """
    df_game = load_game_level_dataset(game_level_dataset)
    df = pd.merge(df, df_game, on='GameId', how='left')
    return df


def load_game_level_dataset(game_level_dataset):
    df_game = pd.read_excel(game_level_dataset)
    df_game = df_game[['GameId', 'hometeam', 'awayteam']]
    return df_game


def merge_team_indexes_with_game_level_df(df_game, teams):
    df_game = pd.merge(df_game, teams, left_on='hometeam', right_on='slug')
    df_game = df_game.rename(columns={'i': 'i_home'}).drop('slug', axis=1)
    df_game = pd.merge(df_game, teams, left_on='awayteam', right_on='slug')
    df_game = df_game.rename(columns={'i': 'i_away'}).drop('slug', axis=1)
    return df_game


def calculate_game_score_at_play_start(df):
    """
    :param df:
    :param game_level_dataset:
    :return:
    """
    points_on_play = pd.DataFrame(df.apply(points_scored, axis=1))
    df = df.join(points_on_play)

    df['home_points'] = (df.hometeam == df.OffenseTeam).astype(int) * df.points_o
    df['home_points'] += (df.hometeam == df.DefenseTeam).astype(int) * df.points_d
    df['away_points'] = (df.awayteam == df.OffenseTeam).astype(int) * df.points_o
    df['away_points'] += (df.awayteam == df.DefenseTeam).astype(int) * df.points_d

    g = df.groupby('GameId')

    df['home_score'] = g.home_points.cumsum()
    df['away_score'] = g.away_points.cumsum()

    return df


def generate_drive_df(df):
    """
    Generate a frame with drive-level stats and metadata.
    Drops a handful of drives that (due to errors in dataset and edge cases) have non-unique (offense, defense) teams
    :param df:
    :return: drive_df
    """
    g = df.groupby('drive_id')
    df_drive = pd.DataFrame({'end_touchdown': g.is_offensive_touchdown.max(),
                             'end_field_goal_attempt': g.is_field_goal_not_nullified.max(),
                             'end_turnover': g.is_turnover.max(),
                             'end_turnover_on_downs': g.is_turnover_on_downs.max(),
                             'end_turnover_missed_fg': g.is_turnover_on_missed_fg.max(),
                             'end_due_to_clock': g.is_final_play_of_half.max(),
                             'end_punt': g.is_punt.max(),
                             'end_safety': g.is_safety.max(),
                             'end_qb_kneel': g.is_qb_kneel.max(),
                             'yards': g.yards_offensive.sum(),
                             'first_downs': g.SeriesFirstDown.sum(),
                             'first_downs_earned': g.is_earned_first_down.sum(),
                             'first_play_of_drive': g.play_id.min(),
                             'last_play_of_drive': g.play_id.max()})
    df_drive['drive_id'] = df_drive.index

    # yardline, clock, score at drive start...
    drive_start = df[['Quarter', 'Minute', 'Second', 'play_id', 'YardLine', 'clock', 'home_score', 'away_score']]
    drive_start.columns = ['quarter', 'minute', 'second', 'play_id', 'start_yardline', 'start_clocktime',
                           'start_home_score', 'start_away_score']
    df_drive = pd.merge(df_drive, drive_start, left_on='first_play_of_drive', right_on='play_id', how='left')
    df_drive = df_drive.drop('play_id', axis=1)

    # ... and drive end.
    drive_end = df[['play_id', 'yardline_after_play', 'clock_after_play']]
    drive_end.columns = ['play_id', 'end_yardline', 'end_clocktime']
    df_drive = pd.merge(df_drive, drive_end, left_on='last_play_of_drive', right_on='play_id', how='left')
    df_drive = df_drive.drop('play_id', axis=1)
    df_drive['yards_end_minus_start'] = df_drive.end_yardline - df_drive.start_yardline
    df_drive['yards_end_minus_start_zero_plus'] = df_drive.yards_end_minus_start.apply(lambda x: max(0, x))
    df_drive['end_yardline_zero_plus'] = df_drive.apply(lambda x: max(x['start_yardline'], x['end_yardline']), axis=1)
    df_drive['elapsed_clock'] = df_drive.start_clocktime - df_drive.end_clocktime
    df_drive.loc[df_drive.elapsed_clock < -50, 'elapsed_clock'] = df_drive.start_clocktime

    #
    drive_teams_and_game = df[df.drive_id.notnull() &
                              (df.OffenseTeam != df.DefenseTeam) &
                              df.OffenseTeam.notnull() &
                              df.DefenseTeam.notnull()].drop_duplicates(
        subset=['GameId', 'drive_id', 'OffenseTeam', 'DefenseTeam'])
    drive_teams_and_game = drive_teams_and_game[
        ['GameId', 'drive_id', 'OffenseTeam', 'DefenseTeam', 'hometeam', 'awayteam']]

    dupes = drive_teams_and_game.drive_id.value_counts()
    dupes = dupes[dupes > 1].index.values

    print 'Dropping %s drives due to non-unique offense/defense teams.' % len(dupes)
    drive_teams_and_game = drive_teams_and_game[~drive_teams_and_game.drive_id.isin(dupes)]

    df_drive = pd.merge(drive_teams_and_game, df_drive, on='drive_id', how='left')
    return df_drive


def merge_stadium_dataset(df_drive):
    """
    :param df_game:
    :return:
    """
    df_s = pd.read_csv(DOME_DATASET)[['slug', 'has_dome']]
    df_s.columns = ['hometeam', 'has_dome']
    df_s.has_dome = df_s.has_dome.astype(bool)
    df_drive = pd.merge(df_drive, df_s, on='hometeam', how='left')
    return df_drive


def remove_unexplained_drives(df_drive):
    """
    Remove the handful of drives having no known outcome.  Caused by errors in dataset and edge cases.
    :param df_drive:
    :return: df_drive
    """
    df_drive['explained'] = df_drive.end_due_to_clock | df_drive.end_field_goal_attempt | \
                            df_drive.end_punt | df_drive.end_touchdown | \
                            df_drive.end_turnover | df_drive.end_turnover_missed_fg | \
                            df_drive.end_turnover_on_downs | df_drive.end_safety

    print 'dropping %s unexplained drives.' % df_drive[~df_drive.explained].shape[0]
    return df_drive[df_drive.explained]


def index_with_team_indexes(df_drive):
    """
    Assign each team an integer id number, and determine ids of home/away/attacking/defending teams
    :param df_drive:
    :return: df_drive
    """
    # alpha-sorted team slugs ('ARI', 'ATL', 'BAL'...)
    teams = pd.DataFrame({'slug': df_drive.OffenseTeam.unique()}).sort_index(by=['slug']).reset_index().drop('index', 1)
    teams['i'] = teams.index
    df_drive = pd.merge(df_drive, teams, left_on='hometeam', right_on='slug')
    df_drive = df_drive.rename(columns={'i': 'i_home'}).drop('slug', axis=1)
    df_drive = pd.merge(df_drive, teams, left_on='awayteam', right_on='slug')
    df_drive = df_drive.rename(columns={'i': 'i_away'}).drop('slug', axis=1)
    df_drive = pd.merge(df_drive, teams, left_on='OffenseTeam', right_on='slug')
    df_drive = df_drive.rename(columns={'i': 'i_attacking'}).drop('slug', axis=1)
    df_drive = pd.merge(df_drive, teams, left_on='DefenseTeam', right_on='slug')
    df_drive = df_drive.rename(columns={'i': 'i_defending'}).drop('slug', axis=1)
    return df_drive, teams


def offensive_yards(x):
    """
    Yards - including penalty yards - earned on a play.  Turnovers count as 0.
    :param x: row in play data frame
    :return: int
    """

    if x['PlayType'] == 'PUNT' or x['is_turnover']:
        return 0
    if x['IsPenaltyAccepted'] and x['PenaltyTeam'] == x['DefenseTeam']:
        return x['PenaltyYards'] + x['Yards']
    if x['IsPenaltyAccepted'] and x['PenaltyTeam'] == x['OffenseTeam']:
        if x['IsTouchdown']:
            return x['Yards']  # usually personal foul for excessive celebration, not relevant to drive
        # if 'FACE MASK' in x['Description']:
        return x['Yards'] - x['PenaltyYards']
        # return -1 * x['PenaltyYards']
    if x['is_no_play']:
        return 0
    return x['Yards']


def points_scored(x):
    """
    Calculate points scored by offense/defense on a given play.
    Known to be inaccurate in edge cases.

    :param x: row in play data frame
    :return: (offensive points, defensive points)
    """
    if x['IsTouchdown']:
        if x['is_turnover']:
            return pd.Series({'points_o': 0, 'points_d': 6})
        return pd.Series({'points_o': 6, 'points_d': 0})
    if x['is_extra_point_successful']:
        return pd.Series({'points_o': 1, 'points_d': 0})
    if x['IsTwoPointConversionSuccessful']:
        return pd.Series({'points_o': 2, 'points_d': 0})
    if x['is_field_goal'] and not x['is_missed_field_goal']:
        return pd.Series({'points_o': 3, 'points_d': 0})
    if x['is_safety']:
        return pd.Series({'points_o': 0, 'points_d': 2})
    return pd.Series({'points_o': 0, 'points_d': 0})


def enrich_drive_level_df(df_drive, losing_badly_threshold=LOSING_BADLY_THRESHOLD):
    """
    :param df_drive:
    :param losing_badly_threshold:
    :return: df_drive
    """
    df_drive['yards_zero_plus'] = df_drive.yards.apply(lambda x: max(0, x))
    df_drive['is_failure'] = (~df_drive.end_touchdown & ~df_drive.end_due_to_clock).astype(int)
    df_drive['is_censored'] = (df_drive.end_touchdown | df_drive.end_due_to_clock).astype(int)

    df_drive['is_failure_turnover'] = (df_drive.end_turnover).astype(int)
    df_drive['is_censored_turnover'] = (~(df_drive.end_turnover)).astype(int)

    df_drive['defending_team_is_home'] = (df_drive.DefenseTeam == df_drive.hometeam).astype(int)
    df_drive['offensive_team_is_home'] = (df_drive.OffenseTeam == df_drive.hometeam).astype(int)
    df_drive['two_minute_drill'] = ((df_drive.start_clocktime < 32) & (df_drive.start_clocktime > 30)) | \
                                   (df_drive.start_clocktime < 2)
    df_drive['thirty_seconds_drill'] = ((df_drive.start_clocktime < 30.5) & (df_drive.start_clocktime > 30)) | \
                                       (df_drive.start_clocktime < .5)
    df_drive['start_offense_score'] = (df_drive.hometeam == df_drive.OffenseTeam).astype(
        int) * df_drive.start_home_score
    df_drive['start_offense_score'] += (df_drive.awayteam == df_drive.OffenseTeam).astype(
        int) * df_drive.start_away_score
    df_drive['start_defense_score'] = (df_drive.hometeam == df_drive.DefenseTeam).astype(
        int) * df_drive.start_home_score
    df_drive['start_defense_score'] += (df_drive.awayteam == df_drive.DefenseTeam).astype(
        int) * df_drive.start_away_score
    df_drive['offense_losing_badly'] = (
                                           df_drive.start_defense_score - df_drive.start_offense_score) > losing_badly_threshold
    df_drive['offense_winning_greatly'] = (
                                              df_drive.start_offense_score - df_drive.start_defense_score) > losing_badly_threshold
    return df_drive


def generate_piecewise_df(df_drive):
    """
    Expand a drive level frame into a piecewise frame with all drives passing through or dying in that piece.
    :param df_drive:
    :return: df_pw
    """
    new_frames = []
    for i in range(len(PIECES) - 1):
        lower, upper = PIECES[i], PIECES[i + 1]
        df_piece = df_drive[(df_drive.start_yardline < upper) & (df_drive.end_yardline_zero_plus > lower)]
        df_piece['died_in_piece'] = (df_piece.end_yardline_zero_plus <= upper)
        df_piece['died_in_piece_ex_turnover'] = (df_piece.end_yardline_zero_plus <= upper) & ~(df_piece.end_turnover)
        df_piece['died_in_piece_turnover'] = (df_piece.end_yardline_zero_plus <= upper) & (df_piece.end_turnover)
        df_piece['exposure_start'] = df_piece.apply(lambda x: max(x['start_yardline'], lower), axis=1)
        df_piece['exposure_end'] = df_piece.apply(lambda x: min(x['end_yardline_zero_plus'], upper), axis=1)
        df_piece['exposure_yards'] = df_piece.exposure_end - df_piece.exposure_start
        df_piece['exposure_yards'] = df_piece.apply(lambda x: max(.01, x['exposure_yards']), axis=1)
        df_piece['piece_i'] = i
        df_piece['piece_lower'] = lower
        df_piece['piece_upper'] = upper
        new_frames.append(df_piece.copy())
    df_pw = pd.concat(new_frames, ignore_index=True)
    return df_pw


def generate_piecewise_counts_df(df_pw):
    g = df_pw.groupby(['piece_i',
                       'i_attacking', 'i_defending',
                       'i_home', 'i_away',
                       'defending_team_is_home',
                       'offense_losing_badly',
                       'offense_winning_greatly',
                       'two_minute_drill'])
    df = pd.DataFrame({'exposure_yards': g.exposure_yards.sum(),
                       'deaths': g.died_in_piece.sum(),
                       'deaths_turnover': g.died_in_piece_turnover.sum(),
                       'deaths_ex_turnover': g.died_in_piece_ex_turnover.sum(),
                       'N': g.size()
    })
    df = df.reset_index()
    for c in ['i_attacking', 'i_defending', 'i_home', 'i_away']:
        df[c] = df[c].astype(int)
    return df
