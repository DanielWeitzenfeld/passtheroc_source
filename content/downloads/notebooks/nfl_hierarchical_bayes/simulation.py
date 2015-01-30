import numpy as np
import pandas as pd

from . import PIECES, FIELD_GOAL_RANGE, PUNT_DISTANCE, LOSING_BADLY_THRESHOLD, \
    SIMULATION_TIE_BREAKER_COIN_FLIP_HOME_ADVANTAGE, REDZONE_PIECE, PIECE_LENGTHS, PUNT_CLOCK_TIME, \
    TOUCHDOWN_CLOCK_TIME, FG_CLOCK_TIME
from elapsed_time import drive_time_elapsed

MEDIAN_I = 32


def simulate_median_team_playing_schedule(season_df, teams, ex_turnover, turnover, param_calculator, n_per):
    """

    :param season_df:
    :param teams:
    :param ex_turnover:
    :param turnover:
    :param n_per:
    :return:
    """
    results = []
    teams_with_median = teams.copy()
    teams_with_median.loc[32, 'slug'] = 'MED'
    teams_with_median.loc[32, 'i'] = 32
    for i, row in teams.iterrows():
        print row['slug']
        df = season_df[(season_df.i_home == i) | (season_df.i_away == i)].copy()
        df.loc[df.i_home == i, 'i_home'] = MEDIAN_I
        df.loc[df.i_away == i, 'i_away'] = MEDIAN_I
        df2 = simulate_n_seasons(df, teams_with_median, ex_turnover, turnover, param_calculator, n_per)
        df2 = df2[df2.slug == 'MED']
        df2['schedule'] = row['slug']
        results.append(df2)
    return pd.concat(results, ignore_index=True)


def simulate_everyone_playing_median_team(teams, ex_turnover, turnover, param_calculator, n_per=100):
    """

    :param teams:
    :param ex_turnover:
    :param turnover:
    :param n_per:
    :return:
    """
    results = []
    for i, row in teams.iterrows():
        print row['slug']
        results.append(simulate_playing_median_team(i, teams, ex_turnover, turnover, param_calculator, n_per))
    return pd.concat(results, ignore_index=True)


def simulate_playing_median_team(i, teams, ex_turnover, turnover, param_calculator, n=100):
    """

    :param i:
    :param teams:
    :param ex_turnover:
    :param turnover:
    :param param_calculator:
    :param n:
    :return:
    """
    game_1 = {'hometeam': teams.slug[i],
              'awayteam': 'MED',
              'i_home': i,
              'i_away': MEDIAN_I}
    game_2 = {'hometeam': 'MED',
              'awayteam': teams.slug[i],
              'i_home': MEDIAN_I,
              'i_away': i}
    season_df = pd.DataFrame([game_1, game_2])
    return simulate_n_seasons(season_df, teams, ex_turnover, turnover, param_calculator, n=n)


def winner(x, home_advantage=SIMULATION_TIE_BREAKER_COIN_FLIP_HOME_ADVANTAGE):
    if x['home_score'] > x['away_score']:
        return x['hometeam']
    elif x['home_score'] < x['away_score']:
        return x['awayteam']
    return x['hometeam'] if x['coinflip'] > .5 - home_advantage else x['awayteam']


def simulate_n_seasons(season_df, teams, ex_turnover, turnover, param_calculator, n=100, collect_drives=False,
                       verbose=False):
    season_tables = []
    drives = []
    for i in range(n):
        if verbose and i and not i % 50:
            print '%s seasons simulated.' % i
        season_i, drive_stats = simulate_season(season_df, ex_turnover, turnover, param_calculator)
        # coinflip for ties
        season_i['coinflip'] = np.random.random(size=season_i.shape[0])
        season_i['winner'] = season_i.apply(winner, axis=1)
        season_i['home_win'] = (season_i.winner == season_i.hometeam).astype(int)
        season_i['home_loss'] = (season_i.winner == season_i.awayteam).astype(int)
        season_i['away_win'] = (season_i.winner == season_i.awayteam).astype(int)
        season_i['away_loss'] = (season_i.winner == season_i.hometeam).astype(int)
        season_table = create_season_table(season_i, teams)
        season_table['iteration'] = i
        season_tables.append(season_table)

        if collect_drives:
            drives += drive_stats

    df = pd.concat(season_tables, ignore_index=True)

    if collect_drives:
        df_drive = pd.DataFrame(drives)
        return df, df_drive
    else:
        return df


def create_season_table(season, teams):
    """
    Using a season dataframe output by simulate_season(), create a summary dataframe with wins, losses, goals for, etc.

    """
    g = season.groupby('i_home')
    home = pd.DataFrame({'home_yards': g.home_yards.sum(),
                         'home_yards_allowed': g.away_yards.sum(),
                         'home_wins': g.home_win.sum(),
                         'home_losses': g.home_loss.sum(),
                         'home_turnovers': g.home_turnovers.sum(),
                         'home_takeaways': g.away_turnovers.sum(),
                         'home_points': g.home_score.sum(),
                         'home_possessions': g.home_possessions.sum()
    })
    g = season.groupby('i_away')
    away = pd.DataFrame({'away_yards': g.away_yards.sum(),
                         'away_yards_allowed': g.home_yards.sum(),
                         'away_wins': g.away_win.sum(),
                         'away_losses': g.away_loss.sum(),
                         'away_turnovers': g.away_turnovers.sum(),
                         'away_takeaways': g.home_turnovers.sum(),
                         'away_points': g.away_score.sum(),
                         'away_possessions': g.away_possessions.sum()
    })
    df = home.join(away)
    df['wins'] = df.home_wins + df.away_wins
    df['losses'] = df.home_losses + df.away_losses
    df['yards'] = df.home_yards + df.away_yards
    df['yards_allowed'] = df.home_yards_allowed + df.away_yards_allowed
    df['turnovers'] = df.home_turnovers + df.away_turnovers
    df['takeaways'] = df.home_takeaways + df.away_takeaways
    df['points'] = df.home_points + df.away_points
    df['possessions'] = df.home_possessions + df.away_possessions
    df = pd.merge(teams, df, left_on='i', right_index=True, how='outer')
    return df


def simulate_season(season_df, ex_turnover, turnover, param_calculator):
    """
    Simulate a season once, using one random draw from the mcmc chain.
    """
    pc = param_calculator(ex_turnover, turnover)

    # for data collection
    season_simul = season_df.copy()
    stat_cols = []
    for pos in ['home', 'away']:
        for stat in ['score', 'yards', 'turnovers', 'possessions']:
            stat_cols.append('%s_%s' % (pos, stat))
    for col in stat_cols:
        season_simul[col] = None

    # simulate each game
    drives = []
    for i, row in season_simul.iterrows():
        i_home, i_away = row['i_home'], row['i_away']
        pc.i_home = i_home
        pc.i_away = i_away
        pc.re_draw_sample()
        results, drive_stats = simulate_game(pc)
        for c in stat_cols:
            season_simul.loc[i, c] = results[c]
        drives += drive_stats
    return season_simul, drives


def current_piece(yardline):
    for i in range(len(PIECES)):
        if PIECES[0] <= yardline < PIECES[i + 1]:
            return i
    raise Exception


def piece_lengths(PIECES):
    return [PIECES[i + 1] - PIECES[i] for i in range(len(PIECES) - 1)]


def simulate_game_n_times(pc, n=10000):
    results = []
    for i in range(n):
        pc.re_draw_sample()
        game_results, drive_stats = simulate_game(pc)
        game_results['i_home'] = pc.i_home
        game_results['i_away'] = pc.i_away
        results.append(game_results)
    return pd.DataFrame(results)


def simulate_game(params, verbose=False):
    """
    Simulate a set of drives using params drawn from posterior distributions.
    This is big and needs to be broken up.  #todo

    :param ex_turnover_params: dictionary of params drawn from ex_turnover posterior
    :param turnover_params: dictionary of params drawn from turnover posterior
    :param i_home: int team index of home team
    :param i_away: int team index of away team
    :param verbose: bool
    :return: game_stats dict and drive_stats list of dicts
    """
    i_home = params.i_home
    i_away = params.i_away


    # data collection
    score = {'home': 0, 'away': 0}
    offensive_yards = {'home': 0, 'away': 0}
    turnovers = {'home': 0, 'away': 0}
    possessions = {'home': 0, 'away': 0}
    drives = []

    clock = 60
    yardline = 20

    possession = 'home' if np.random.random() > .5 else 'away'
    defending = 'home' if possession == 'away' else 'away'

    first_half_possession = possession
    hit_halftime = False
    while clock > 0:  # BEGIN NEW DRIVE

        # new drive
        drive_in_progress = True
        possessions[possession] += 1
        drive_start = yardline
        total_drive_yards = 0
        outcome = None
        this_drive = {'start_yardline': yardline,
                      'i_home': i_home,
                      'i_away': i_away,
                      'i_attacking': i_home if possession == 'home' else i_away,
                      'i_defending': i_away if possession == 'home' else i_home,
                      'score_home': score['home'],
                      'score_away': score['away'],
                      'score_attacking': score['home'] if possession == 'home' else score['away'],
                      'score_defending': score['away'] if possession == 'home' else score['home'],
                      'start_clocktime': clock,
                      'two_minute_drill': 30 < clock < 32 or clock < 2
        }
        this_drive['offense_winning_greatly'] = (this_drive['score_attacking'] - this_drive[
            'score_defending']) > LOSING_BADLY_THRESHOLD
        this_drive['offense_losing_badly'] = (this_drive['score_defending'] - this_drive[
            'score_attacking']) > LOSING_BADLY_THRESHOLD

        if verbose:
            print '%s has the ball at the %s yardline with %s remaining.' % (possession, yardline, clock)

        while drive_in_progress:  # BEGIN NEW INTERVAL

            piece = current_piece(yardline)
            piece_start = PIECES[piece]
            piece_end = PIECES[piece + 1]

            # base xb for team and piece
            if piece == REDZONE_PIECE:
                xb = params.home_xb_rz() if possession == 'home' else params.away_xb_rz()
            else:
                xb = params.home_xb() if possession == 'home' else params.away_xb()
            xb_turn = params.home_turnover_xb() if possession == 'home' else params.away_turnover_xb()

            # amend xb for drive-specific situations
            if score[possession] - score[defending] > LOSING_BADLY_THRESHOLD:
                xb += params.ex_t_offense_winning_greatly()
                xb_turn += params.t_offense_winning_greatly()
            if score[defending] - score[possession] > LOSING_BADLY_THRESHOLD:
                xb += params.ex_t_offense_losing_badly()
                xb_turn += params.t_offense_losing_badly()
            if 30 < clock < 32 or clock < 2:
                xb += params.ex_t_two_minute_drill()
                xb_turn += params.t_two_minute_drill()

            # piece-specific baseline, and exp
            hazard = (params.ex_t_baseline_hazards()[piece]) * np.exp(xb)
            hazard_turnover = (params.t_baseline_hazards()[piece]) * np.exp(xb_turn)
            total_hazard = hazard + hazard_turnover

            # did they survive this piece?
            yards_survived = np.random.exponential(1. / total_hazard)


            # print '%s yards' % yards_survived

            if (yards_survived + yardline) > piece_end:  # survival to the next piece
                total_drive_yards += (piece_end - yardline)
                if piece == REDZONE_PIECE:
                    drive_in_progress = False
                    score[possession] += 7
                    clock -= TOUCHDOWN_CLOCK_TIME
                    yardline = 20
                    outcome = 'touchdown'
                    if verbose:
                        print '%s scored a touchdown.' % possession
                else:  # on to the next piece
                    if verbose:
                        print '%s advanced to the next piece by surviving %s yards' % (possession, yards_survived)
                    yardline = piece_end + .01
            else:  # drive death
                drive_in_progress = False
                total_drive_yards += yards_survived
                # was it 'normal' drive death, or death-by-turnover?
                p_turnover = hazard_turnover / (hazard_turnover + hazard)
                if np.random.random() < p_turnover:  # turnover
                    turnovers[possession] += 1
                    outcome = 'turnover'
                    if verbose:
                        print 'Turnover: %s gave away the ball at the %s yardline.' % (
                            possession, yards_survived + yardline)
                    yardline = 100 - (yards_survived + yardline)
                else:
                    # Punt or field goal?
                    if yards_survived + yardline > FIELD_GOAL_RANGE:  # field goal
                        clock -= FG_CLOCK_TIME
                        score[possession] += 3
                        outcome = 'field_goal'
                        if verbose:
                            print '%s kicked a field goal from the %s yardline' % (
                                possession, yardline + yards_survived)
                        yardline = 20
                    else:  # punt
                        clock -= PUNT_CLOCK_TIME
                        outcome = 'punt'
                        punt_to_yardline = 100 - (yardline + yards_survived + PUNT_DISTANCE)
                        punt_to_yardline = 20 if punt_to_yardline < 2 else punt_to_yardline  # cut down on coffin corner punts
                        if verbose:
                            print '%s punted from the %s yardline to the %s yardline.' % (
                                possession, yardline + yards_survived, punt_to_yardline)
                        yardline = punt_to_yardline

        if verbose:
            print '  -- total drive yards: %s' % total_drive_yards
        clock -= drive_time_elapsed(total_drive_yards)
        offensive_yards[possession] += total_drive_yards
        this_drive['end_clocktime'] = clock
        this_drive['end_yardline'] = drive_start + total_drive_yards
        this_drive['outcome'] = outcome
        this_drive['end_field_goal_attempt'] = outcome == 'field_goal'
        this_drive['end_touchdown'] = outcome == 'touchdown'
        drives.append(this_drive)

        # ALWAYS flip posession
        possession = 'away' if possession == 'home' else 'home'

        # handle the clock
        if clock < 30.5 and not hit_halftime:
            hit_halftime = True
            clock = 30
            possession = 'away' if first_half_possession == 'home' else 'home'
            yardline = 20

    game_stats = {'home_score': score['home'], 'away_score': score['away'],
                  'home_yards': offensive_yards['home'], 'away_yards': offensive_yards['away'],
                  'home_turnovers': turnovers['home'], 'away_turnovers': turnovers['away'],
                  'home_possessions': possessions['home'], 'away_possessions': possessions['away']}

    return game_stats, drives

