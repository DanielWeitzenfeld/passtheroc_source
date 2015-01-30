import numpy as np


class ParamCalculator(object):
    """
    Some ex-turnover models break out the redzone, others don't.
    Some turnover models take into account defense takeaway propensity, others don't.
    The idea is to have one simulation function, and have these classes
    do the work of providing the appropriate parameters.
    """

    def __init__(self, ex_turnover, turnover):
        self.ex_turnover = ex_turnover
        self.turnover = turnover
        self.ex_t = {}
        self.t = {}
        self.i_home = None
        self.i_away = None

    def re_draw_sample(self):
        self.ex_t = self.re_draw_ex_turnover_sample()
        self.t = self.re_draw_turnover_sample()
        self.tack_on_median_team()

    def re_draw_ex_turnover_sample(self):
        num_samples = self.ex_turnover.atts.gettrace().shape[0]
        draw = np.random.randint(0, num_samples)
        return {'atts': self.ex_turnover.atts.gettrace()[draw, :],
                'atts_rz': self.ex_turnover.atts_rz.gettrace()[draw, :],
                'defs': self.ex_turnover.defs.gettrace()[draw, :],
                'defs_rz': self.ex_turnover.defs_rz.gettrace()[draw, :],
                'home': self.ex_turnover.home.gettrace()[draw, :],
                'baseline_hazards': self.ex_turnover.baseline_hazards.gettrace()[draw, :],
                'two_minute_drill': self.ex_turnover.two_minute_drill.gettrace()[draw],
                'offense_losing_badly': self.ex_turnover.offense_losing_badly.gettrace()[draw],
                'offense_winning_greatly': self.ex_turnover.offense_winning_greatly.gettrace()[draw]}

    def re_draw_turnover_sample(self):
        num_samples = self.turnover.atts.gettrace().shape[0]
        draw = np.random.randint(0, num_samples)
        return {'atts': self.turnover.atts.gettrace()[draw, :],
                'defs': self.turnover.defs.gettrace()[draw, :],
                'home': self.turnover.home.gettrace()[draw],
                'baseline_hazards': self.turnover.baseline_hazards.gettrace()[draw, :],
                'two_minute_drill': self.turnover.two_minute_drill.gettrace()[draw],
                'offense_losing_badly': self.turnover.offense_losing_badly.gettrace()[draw],
                'offense_winning_greatly': self.turnover.offense_winning_greatly.gettrace()[draw]}


    def tack_on_median_team(self):
        """
        Create a 33rd "team" representing the median team.  We'll use this median team to assess team quality and
        strength of schedule.
        :param ex_turnover_params:
        :param turnover_params:
        :return:
        """
        for team_specific_param in ['atts', 'atts_rz', 'defs', 'defs_rz', 'home']:
            if team_specific_param in self.ex_t:
                self.ex_t[team_specific_param] = np.append(self.ex_t[team_specific_param],
                                                           np.median(self.ex_t[team_specific_param]))

        for team_specific_param in ['atts', 'defs']:
            if team_specific_param in self.t:
                self.t[team_specific_param] = np.append(self.t[team_specific_param],
                                                        np.median(self.t[team_specific_param]))


    def home_xb(self):
        return self.ex_t['atts'][self.i_home] + self.ex_t['defs'][self.i_away]

    def home_xb_rz(self):
        return self.ex_t['atts_rz'][self.i_home] + self.ex_t['defs_rz'][self.i_away]

    def away_xb(self):
        return self.ex_t['atts'][self.i_away] + self.ex_t['defs'][self.i_home] + self.ex_t['home'][self.i_home]

    def away_xb_rz(self):
        return self.ex_t['atts_rz'][self.i_away] + self.ex_t['defs_rz'][self.i_home] + self.ex_t['home'][self.i_home]

    def home_turnover_xb(self):
        return self.t['atts'][self.i_home] + self.t['defs'][self.i_away]

    def away_turnover_xb(self):
        return self.t['atts'][self.i_away] + self.t['defs'][self.i_home] + self.t['home']

    def ex_t_offense_winning_greatly(self):
        return self.ex_t['offense_winning_greatly']

    def t_offense_winning_greatly(self):
        return self.t['offense_winning_greatly']

    def ex_t_offense_losing_badly(self):
        return self.ex_t['offense_losing_badly']

    def t_offense_losing_badly(self):
        return self.t['offense_losing_badly']

    def ex_t_two_minute_drill(self):
        return self.ex_t['two_minute_drill']

    def t_two_minute_drill(self):
        return self.t['two_minute_drill']

    def ex_t_baseline_hazards(self):
        return self.ex_t['baseline_hazards']

    def t_baseline_hazards(self):
        return self.t['baseline_hazards']


class ParamCalculatorNoTurnoverDefense(ParamCalculator):
    """
    No defense takeaway-propensity in the turnover model.
    """

    def __init__(self, ex_turnover, turnover):
        super(ParamCalculatorNoTurnoverDefense, self).__init__(ex_turnover, turnover)


    def re_draw_turnover_sample(self):
        num_samples = self.turnover.atts.gettrace().shape[0]
        draw = np.random.randint(0, num_samples)
        return {'atts': self.turnover.atts.gettrace()[draw, :],
                'home': self.turnover.home.gettrace()[draw],
                'baseline_hazards': self.turnover.baseline_hazards.gettrace()[draw, :],
                'two_minute_drill': self.turnover.two_minute_drill.gettrace()[draw],
                'offense_losing_badly': self.turnover.offense_losing_badly.gettrace()[draw],
                'offense_winning_greatly': self.turnover.offense_winning_greatly.gettrace()[draw]}

    def home_turnover_xb(self):
        return self.t['atts'][self.i_home]


    def away_turnover_xb(self):
        return self.t['atts'][self.i_away] + self.t['home']


class ParamCalculatorNoRZ(ParamCalculator):
    """
    Redzone is identical to other pieces in terms of team-specific attack/defense/params.
    """

    def __init__(self, ex_turnover, turnover):
        super(ParamCalculatorNoRZ, self).__init__(ex_turnover, turnover)

    def home_xb_rz(self):
        return self.home_xb()

    def away_xb_rz(self):
        return self.away_xb()

    def re_draw_ex_turnover_sample(self):
        num_samples = self.ex_turnover.atts.gettrace().shape[0]
        draw = np.random.randint(0, num_samples)
        return {'atts': self.ex_turnover.atts.gettrace()[draw, :],
                'defs': self.ex_turnover.defs.gettrace()[draw, :],
                'home': self.ex_turnover.home.gettrace()[draw, :],
                'baseline_hazards': self.ex_turnover.baseline_hazards.gettrace()[draw, :],
                'two_minute_drill': self.ex_turnover.two_minute_drill.gettrace()[draw],
                'offense_losing_badly': self.ex_turnover.offense_losing_badly.gettrace()[draw],
                'offense_winning_greatly': self.ex_turnover.offense_winning_greatly.gettrace()[draw]}


class ParamCalculatorNoRZNoTurnoverDefense(ParamCalculatorNoRZ, ParamCalculatorNoTurnoverDefense):
    def __init__(self, ex_turnover, turnover):
        super(ParamCalculatorNoRZNoTurnoverDefense, self).__init__(ex_turnover, turnover)


class ParamCalculatorNoRZNoTurnoverDefenseNeutralField(ParamCalculatorNoRZ, ParamCalculatorNoTurnoverDefense):
    def __init__(self, ex_turnover, turnover):
        super(ParamCalculatorNoRZNoTurnoverDefenseNeutralField, self).__init__(ex_turnover, turnover)

    def re_draw_ex_turnover_sample(self):
        num_samples = self.ex_turnover.atts.gettrace().shape[0]
        draw = np.random.randint(0, num_samples)
        return {'atts': self.ex_turnover.atts.gettrace()[draw, :],
                'defs': self.ex_turnover.defs.gettrace()[draw, :],
                'home': np.zeros(32),
                'baseline_hazards': self.ex_turnover.baseline_hazards.gettrace()[draw, :],
                'two_minute_drill': self.ex_turnover.two_minute_drill.gettrace()[draw],
                'offense_losing_badly': self.ex_turnover.offense_losing_badly.gettrace()[draw],
                'offense_winning_greatly': self.ex_turnover.offense_winning_greatly.gettrace()[draw]}

    def re_draw_turnover_sample(self):
        num_samples = self.turnover.atts.gettrace().shape[0]
        draw = np.random.randint(0, num_samples)
        return {'atts': self.turnover.atts.gettrace()[draw, :],
                'home': 0,
                'baseline_hazards': self.turnover.baseline_hazards.gettrace()[draw, :],
                'two_minute_drill': self.turnover.two_minute_drill.gettrace()[draw],
                'offense_losing_badly': self.turnover.offense_losing_badly.gettrace()[draw],
                'offense_winning_greatly': self.turnover.offense_winning_greatly.gettrace()[draw]}