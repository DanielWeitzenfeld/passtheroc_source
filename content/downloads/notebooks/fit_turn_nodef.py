import os
import sys


CHART_DIR = os.path.join(os.getcwd(), 'charts/')
sys.path.append(os.getcwd())

import math
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import pymc as pm

CODE_DIR = os.path.join(os.getcwd(), 'code/')
DATA_DIR = os.path.join(os.getcwd(), 'data/')
DPI = 300
WIDECHARTWIDTH = 10
WIDECHARTHEIGHT = 6
SAVECHARTS = False


import nfl_hierarchical_bayes
from nfl_hierarchical_bayes import data_prep, simulation_pwexp, elapsed_time, REDZONE_PIECE


df = pd.read_csv(DATA_DIR + 'pbp-2014-bugfixed.csv')
df = data_prep.enrich_play_level_df(df)
df = data_prep.merge_in_game_level_dataset(df, data_prep.GAME_LEVEL_DATASET_2014)
df = data_prep.calculate_game_score_at_play_start(df)
df_drive = data_prep.generate_drive_df(df)
df_drive, teams = data_prep.index_with_team_indexes(df_drive)
df_drive = data_prep.remove_unexplained_drives(df_drive)
df_drive = data_prep.enrich_drive_level_df(df_drive)

print 'Dropping %s drives due to their beginning with <30 seconds left in half' % \
      df_drive[(df_drive.thirty_seconds_drill)].shape[0]
df_drive = df_drive[~(df_drive.thirty_seconds_drill)]

print 'Dropping %s drives due to the ending with qb kneel' % df_drive[(df_drive.end_qb_kneel)].shape[0]
df_drive = df_drive[~(df_drive.end_qb_kneel)]

df_pw = data_prep.generate_piecewise_df(df_drive)
df_counts = data_prep.generate_piecewise_counts_df(df_pw)

observed_drive_deaths_ex_turnover = df_counts.deaths_ex_turnover.values
observed_exposures = df_counts.exposure_yards.values
piece_i = df_counts.piece_i.values
red_zone = (df_counts.piece_i == REDZONE_PIECE).astype(int).values
not_red_zone = (df_counts.piece_i != REDZONE_PIECE).astype(int).values
attacking_team = df_counts.i_attacking.values
defending_team = df_counts.i_defending.values
defending_team_is_home = df_counts.defending_team_is_home.values
offense_is_losing_badly = df_counts.offense_losing_badly.astype(int).values
offense_is_winning_greatly = df_counts.offense_winning_greatly.astype(int).values
drive_is_two_minute_drill = df_counts.two_minute_drill.astype(int).values
num_teams = len(df_counts.i_home.unique())
num_obs = len(drive_is_two_minute_drill)
num_pieces = len(df_counts.piece_i.unique())

observed_drive_deaths_turnover = df_counts.deaths_turnover.values

g = df_counts.groupby('piece_i')
baseline_starting_vals = g.deaths_turnover.sum() / g.exposure_yards.sum()


def turnover_piecewise_exponential_model():
    # hyperpriors for team-level distributions
    std_dev_att = pm.Uniform('std_dev_att', lower=0, upper=50)

    # priors on coefficients
    baseline_hazards = pm.Normal('baseline_hazards', 0, .0001, size=num_pieces, value=baseline_starting_vals.values)
    two_minute_drill = pm.Normal('two_minute_drill', 0, .0001, value=-.01)
    offense_losing_badly = pm.Normal('offense_losing_badly', 0, .0001, value=-.01)
    offense_winning_greatly = pm.Normal('offense_winning_greatly', 0, .0001, value=.01)
    home = pm.Normal('home', 0, .0001, value=-.01)

    @pm.deterministic(plot=False)
    def tau_att(std_dev_att=std_dev_att):
        return std_dev_att ** -2

    # team-specific parameters
    atts_star = pm.Normal("atts_star",
                          mu=0,
                          tau=tau_att,
                          size=num_teams,
                          value=np.zeros(num_teams))


    # trick to code the sum to zero contraint
    @pm.deterministic
    def atts(atts_star=atts_star):
        atts = atts_star.copy()
        atts = atts - np.mean(atts_star)
        return atts


    @pm.deterministic
    def lambdas(attacking_team=attacking_team,
                defending_team=defending_team,
                defending_team_is_home=defending_team_is_home,
                two_minute_drill=two_minute_drill,
                drive_is_two_minute_drill=drive_is_two_minute_drill,
                offense_losing_badly=offense_losing_badly,
                offense_is_losing_badly=offense_is_losing_badly,
                offense_winning_greatly=offense_winning_greatly,
                offense_is_winning_greatly=offense_is_winning_greatly,
                home=home,
                atts=atts,
                baseline_hazards=baseline_hazards,
                observed_exposures=observed_exposures,
                piece_i=piece_i):
        return observed_exposures * baseline_hazards[piece_i] * \
               np.exp(home * defending_team_is_home + \
                      two_minute_drill * drive_is_two_minute_drill + \
                      offense_losing_badly * offense_is_losing_badly + \
                      offense_winning_greatly * offense_is_winning_greatly + \
                      atts[attacking_team])


    drive_deaths = pm.Poisson("drive_deaths", lambdas,
                              value=observed_drive_deaths_turnover, observed=True)

    @pm.potential
    def limit_sd(std_dev_att=std_dev_att):
        if std_dev_att < 0:
            return -np.inf
        return 0

    @pm.potential
    def limit_tau(tau_att=tau_att):
        if tau_att > 10000:
            return -np.inf
        return 0


    return locals()


turnover = pm.MCMC(turnover_piecewise_exponential_model(),
                   db='pickle', dbname=DATA_DIR + 'turnover_nodef.pickle')
turnover.sample(100000, 70000, 40)
