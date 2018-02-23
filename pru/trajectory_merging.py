# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Common trajectory merging functions.
"""

import pandas as pd


def read_dataframe_with_new_ids(filename, ids_df, *, date_fields=['TIME_SOURCE']):
    """
    Reads items (flights, events or positions) from filename into a pandas
    Dataframe and merges with ids_df Dataframe on FLIGHT_ID.

    Returns a pandas DataFrame containing items (events or positions) with the
    new flight ids in the NEW_FLIGHT_ID column.
    """
    df = pd.read_csv(filename, parse_dates=date_fields)
    return pd.merge(ids_df, df, left_index=True, right_on='FLIGHT_ID')


def replace_old_flight_ids(df):
    """
    Replace FLIGHT_ID column values with NEW_FLIGHT_ID column values.
    """
    df.drop(labels='FLIGHT_ID', axis='columns', inplace=True)
    df.rename(index=str, columns={'NEW_FLIGHT_ID': 'FLIGHT_ID'}, inplace=True)
