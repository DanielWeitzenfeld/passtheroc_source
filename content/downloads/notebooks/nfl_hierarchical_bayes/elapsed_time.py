import statsmodels.api as sm
from patsy import dmatrices

# Simple linear model to estimate elapsed time of a drive, as a function of drive length in yards.
#

MINUTES_PER_YARD = 0
MINUTES_INTERCEPT = 0
READY_TO_USE = False


def set_elapsed_time_per_yard(df_drive):
    y, X = dmatrices('elapsed_clock ~ yards_end_minus_start_zero_plus', data=df_drive, return_type='dataframe')
    model = sm.OLS(y, X)
    results = model.fit()
    global MINUTES_PER_YARD
    MINUTES_PER_YARD = results.params['yards_end_minus_start_zero_plus']
    global MINUTES_INTERCEPT
    MINUTES_INTERCEPT = results.params['Intercept']
    global READY_TO_USE
    READY_TO_USE = True
    return


def drive_time_elapsed(drive_length):
    if READY_TO_USE:
        return MINUTES_INTERCEPT + MINUTES_PER_YARD * drive_length
    else:
        print 'Run set_elapsed_time_per_yard() first to fit model.'
        raise Exception
