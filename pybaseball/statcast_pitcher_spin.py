"""Statcast Pitcher Spin

These calculations are based on the work by Prof. Alan Nathan of the University
of Illinois. 

Article: http://baseball.physics.illinois.edu/trackman/SpinAxis.pdf
Excel Workbook: http://baseball.physics.illinois.edu/trackman/MovementSpinEfficiencyTemplate-v2.xlsx
"""

from pybaseball import statcast_pitcher
import pandas as pd
import numpy as np

K = .005153  # Environmental Constant
SIG_DIG = 4
DISTANCE_FROM_HOME_TO_MOUND = 60.5
DISTANCE_TO_PLATE_AT_VELOCITY_CAPTURE = 50
Y_VALUE_AT_FINAL_MEASUREMENT = 17/12
GRAVITATIONAL_ACCELERATION = 32.174


def statcast_pitcher_spin(start_dt=None, end_dt=None, player_id=None):
    pitcher_data = statcast_pitcher(start_dt, end_dt, player_id)

    spin_df = pitcher_data[[
        'release_extension', 'vx0', 'vy0', 'vz0', 'ax',
        'ay', 'az', 'release_spin_rate']].copy()

    spin_df = find_intermediate_values(spin_df)

    pitcher_data[['Mx', 'Mz', 'phi', 'theta']] = spin_df[[
        'Mx', 'Mz', 'phi', 'theta']].copy()

    return pitcher_data

# def get_statcast_pither_test_data():
# 	df = pd.read_csv("tests/statcast_pitching_test_data.csv")
# 	return df


def find_intermediate_values(spin_df):
    """Calls each intermediate function in sequence"""
    spin_df = find_release_point(spin_df)
    spin_df = find_release_time(spin_df)
    spin_df = find_release_velocity_components(spin_df)
    spin_df = find_flight_time(spin_df)
    spin_df = find_average_velocity_components(spin_df)
    spin_df = find_average_velocity(spin_df)
    spin_df = find_average_drag(spin_df)
    spin_df = find_magnus_acceleration_magnitude(spin_df)
    spin_df = find_average_magnus_acceleration(spin_df)
    spin_df = find_magnus_magnitude(spin_df)
    spin_df = find_phi(spin_df)
    spin_df = find_lift_coefficient(spin_df)
    spin_df = find_spin_factor(spin_df)
    spin_df = find_transverse_spin(spin_df)
    spin_df = find_spin_efficiency(spin_df)
    spin_df = find_theta(spin_df)

    return spin_df


def find_release_point(df):
    df['yR'] = (DISTANCE_FROM_HOME_TO_MOUND - df['release_extension']).round(SIG_DIG)
    return df


def find_release_time(df):
    df['tR'] = time_duration(
        df['yR'],
        df['vy0'],
        df['ay'],
        DISTANCE_TO_PLATE_AT_VELOCITY_CAPTURE,
        False).round(SIG_DIG)
    return df


def find_release_velocity_components(df):
    df['vxR'] = (df['vx0'] + (df['ax'] * df['tR'])).round(SIG_DIG)
    df['vyR'] = (df['vy0'] + (df['ay'] * df['tR'])).round(SIG_DIG)
    df['vzR'] = (df['vz0'] + (df['az'] * df['tR'])).round(SIG_DIG)
    return df


def find_flight_time(df):
    df['tf'] = time_duration(
        df['yR'],
        df['vyR'],
        df['ay'],
        Y_VALUE_AT_FINAL_MEASUREMENT,
        True).round(SIG_DIG)
    return df


def find_average_velocity_components(df):
    df['vxbar'] = (2*df['vxR'] + df['ax']*df['tf'])/2
    df['vybar'] = (2*df['vyR'] + df['ay']*df['tf'])/2
    df['vzbar'] = (2*df['vzR'] + df['az']*df['tf'])/2

    df['vxbar'] = df['vxbar'].round(SIG_DIG)
    df['vybar'] = df['vybar'].round(SIG_DIG)
    df['vzbar'] = df['vzbar'].round(SIG_DIG)
    return df


def find_average_velocity(df):
    df['vbar'] = three_comp_average(df['vxbar'], df['vybar'], df['vzbar']).round(SIG_DIG)
    return df


def find_average_drag(df):
    df['adrag'] = (-(df['ax']*df['vxbar'] + df['ay']*df['vybar'] + (df['az'] + GRAVITATIONAL_ACCELERATION)*df['vzbar'])/ df['vbar']).round(SIG_DIG)
    return df


def find_magnus_acceleration_magnitude(df):
    df['amagx'] = (df['ax'] + df['adrag']*df['vxbar']/df['vbar']).round(SIG_DIG)
    df['amagy'] = (df['ay'] + df['adrag']*df['vybar']/df['vbar']).round(SIG_DIG)
    df['amagz'] = (df['az'] + df['adrag']*df['vzbar']/df['vbar'] + GRAVITATIONAL_ACCELERATION).round(SIG_DIG)
    return df


def find_average_magnus_acceleration(df):
    df['amag'] = three_comp_average(df['amagx'], df['amagy'], df['amagz']).round(SIG_DIG)
    return df


def find_magnus_magnitude(df):
    df['Mx'] = (6 * df['amagx'] * (df['tf']**2)).round(SIG_DIG)
    df['Mz'] = (6 * df['amagz'] * (df['tf']**2)).round(SIG_DIG)
    return df


def find_phi(df):
    df['phi'] = np.where(
        df['amagz'] > 0,
        np.arctan2(df['amagz'], df['amagx'])*180/np.pi,
        360 + np.arctan2(df['amagz'], df['amagx'])*180/np.pi) + 90

    df['phi'] = df['phi'].round(0).astype('int64')
    return df


def find_lift_coefficient(df):
    df['Cl'] = (df['amag']/(K*df['vbar']**2)).round(SIG_DIG)
    return df


def find_spin_factor(df):
    """Function to find spin factor

    Spin Factor formula was derived from a regression of experimental data. The
    formula below appears in the excel worksheet cited at the top of the file.
    No explanation is given for the constant values included.
    """
    df['S'] = (0.166*np.log(0.336/(0.336-df['Cl']))).round(SIG_DIG)
    return df


def find_transverse_spin(df):
    df['spinT'] = (78.92*df['S']*df['vbar']).round(1)
    return df


def find_spin_efficiency(df):
    df['spin eff'] = special_round(df['spinT']/df['release_spin_rate'], 2)
    return df


def find_theta(df):
    df['theta'] = df['spin eff'].where(
        (df['spin eff'] >= -1.0) & (df['spin eff'] <= 1.0),
        np.nan)
    df['theta'] = df['theta'].where(
        df['theta'].isna(),
        np.arccos(df['theta']) * 180/np.pi).round(0)
    return df


# HELPERS
def special_round(series, digit):
    """Manual rounding function for pd.Series

    pd.round has errors rounding with floating point numbers in some cases. 
    This function is a workaround for those cases.

    series = (pd.Series) series to be rounded
    digit = (int) what number of digits to be rounded

    Returns the rounded pd.series
    """

    series = series * 10**digit
    series = np.where(series >= 0, series + .5, series - .5)
    series = series.astype('int64').astype('float64')
    series = series / 10**digit
    return series


def time_duration(s, v, acc, adj, forward):
    """
        Finds flight time given an original position, velocity, accelaration, and target position.

        Direction does not affect the time duration. It helps assign a positive or negative
        value to the flight time.

        s = (pd.Series) spacial point at known time
        v = (pd.Series) velocity at known time
        acc = (pd.Series) acceleration
        adj = (pd.Series) spatial difference between known and unknown points
        forward = (bool) indicating whether space_diff is in the positive or negative y direction
    """
    return (-v - np.sqrt(v**2 - 2*acc*((1 if forward else -1) * (s-adj)))) / acc


def three_comp_average(comp1, comp2, comp3):
    return np.sqrt(comp1**2 + comp2**2 + comp3**2)
