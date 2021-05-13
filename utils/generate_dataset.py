from typing import Tuple
import pandas as pd
import json
import ssl
import numpy as np
import datetime
import datetime
from scipy.spatial.distance import euclidean
from datetime import datetime, timedelta
import scipy.stats as stats

ssl._create_default_https_context = ssl._create_unverified_context


API_KEY = "ZRDS32VNQEEFSOF4"
CHANNEL_ID = "1361623"

fields = {
    "field2": "TEMP [C]",
    "field3": "Relative humidity",
    "field4": "PM1 [ug/m3]",
    "field5": "PM2.5 [ug/m3]",
    "field6": "PM10 [ug/m3]",
    "created_at": "Date/time"
}

new_fields = {v: k for (k, v) in zip(fields.keys(), fields.values())}


def get_thingspeak_data(id: str, api_key: str, nb_of_results: int = 8000, drop_entry_id: bool = True, save: bool = False) -> pd.DataFrame:
    time_zone = "UTC"
    url = f"https://thingspeak.com/channels/{id}/feed.csv?apikey={api_key}&results={nb_of_results}&timezone={time_zone}"

    df = pd.read_csv(url)
    df.replace(['None'], np.nan, inplace=True)
    df.rename(columns=fields, inplace=True)
    df["Date/time"] = pd.to_datetime(df["Date/time"])
    df["TEMP [C]"] = df["TEMP [C]"].astype("float32")
    df.set_index("Date/time", inplace=True)
    df.index = df.index.tz_convert("Europe/Paris")
    if save:
        df.to_csv('data/thingspeak_data.csv')
    df = df.assign(missing=np.nan)
    df.drop("missing", inplace=True, axis=1)
    df.drop("Relative humidity", axis=1, inplace=True)
    df.drop("PM1 [ug/m3]", axis=1, inplace=True)

    if drop_entry_id:
        df.drop('entry_id', axis=1, inplace=True)

    return df


def get_zue_data():
    df = pd.read_csv('data/nabel_data.csv', delimiter=";")
    df["Date/time"] = pd.to_datetime(df["Date/time"], format='%d.%m.%Y %H:%M')
    df["TEMP [C]"] = df["TEMP [C]"].astype("float32")
    df.set_index("Date/time", inplace=True)
    df.index = df.index.tz_localize(
        "Europe/Paris", ambiguous="NaT", nonexistent="shift_backward")
    df = df.assign(missing=np.nan)
    df.drop("missing", inplace=True, axis=1)

    return df


def extract_time_series(df: pd.DataFrame):
    pm10_series = df.loc[:, "PM10 [ug/m3]"]
    pm25_series = df.loc[:, "PM2.5 [ug/m3]"]
    temperature_series = df.loc[:, "TEMP [C]"]
    precipitation_series = df.loc[:, "PREC [mm]"]

    return temperature_series, precipitation_series, pm25_series, pm10_series


def merge_datasets(df_zue: pd.DataFrame, df_ts: pd.DataFrame, save_data=False) -> pd.DataFrame:

    # reorder the columns according to zue data
    # crop ts data that has no corresponding zue data
    # round the ts time indexes to 5 minutes
    ts = df_ts.copy()
    ts = ts[ts.index.notnull()]
    ts = ts[df_zue.columns[:3]]
    ts = ts.loc[:df_zue.index[-1]]
    ts.index = ts.index.round('5T')
    ts = ts.groupby(level=0).mean()
    start = ts.index[0]

    if save_data:
        ts.to_csv('data_v/ts.csv')

    # crop zue and save precipitations separately
    zue = df_zue.copy()
    zue = zue[zue.index.notnull()]
    zue = zue.loc[:ts.index[-1]]
    precipitations = zue["PREC [mm]"]
    zue.drop("PREC [mm]", axis=1, inplace=True)

    if save_data:
        zue.to_csv('data_v/zue.csv')

    # interpolate the pm10 zue data for which we have large missing intervals
    zue = interpolate_pm10(zue)

    if save_data:
        zue.to_csv('data_v/zue_pm10_inter.csv')

    # remove the outliers and interpolate their value with time
    zue = remove_outliers(zue, hours=5)
    ts = remove_outliers(ts, minutes=30)

    zue = zue.interpolate(method='time')
    ts = ts.interpolate(method='time')

    if save_data:
        zue.to_csv('data_v/zue_no_outliers.csv')
    if save_data:
        ts.to_csv('data_v/ts_no_outliers.csv')

    # linearly interpolate zue data for each 5mn and
    # separate between previous and overlapping data
    zue = zue.resample('5min').interpolate('linear')
    zue_prev = zue.loc[:start]
    zue_superpos = zue.loc[start:ts.index[-1]]

    if save_data:
        zue_superpos.to_csv('data_v/zue_superpos.csv')

    # scale our ts data according to the zue data
    h_mean_ts = pd.DataFrame().reindex_like(ts)
    for t in ts.index:
        t1 = t - timedelta(minutes=30)
        t2 = t + timedelta(minutes=30)
        h_mean_ts.loc[t] = ts.loc[t1:t2].mean(axis=0)

    if save_data:
        h_mean_ts.to_csv('data_v/h_mean_ts.csv')

    scaled_ts = zue_superpos * ts / h_mean_ts

    if save_data:
        scaled_ts.to_csv('data_v/scaled_ts.csv')

    # calculate our ts data variation around the zue data
    dist_ts = scaled_ts - zue_superpos

    #h = dist_ts.hist()
    # h.show()

    # calculate our variation properties (assumed normal from the histogram)
    means = dist_ts.mean(axis=0)
    covs = dist_ts.cov()

    # add random noise to zue data
    zue_prev += np.random.multivariate_normal(means, covs, zue_prev.shape[0])

    # create the result dataset
    result = pd.concat([zue_prev, scaled_ts])
    result["PREC [mm]"] = precipitations
    result = result.interpolate('time')
    # put all negative particule values at zero
    result[["PM10 [ug/m3]", "PM2.5 [ug/m3]"]
           ] = result[["PM10 [ug/m3]", "PM2.5 [ug/m3]"]].clip(lower=0)

    if save_data:
        result.to_csv('data_v/dataset.csv')

    return result


def get_dataset(save: bool = True) -> pd.DataFrame:
    df_zue = get_zue_data()
    df_ts = get_thingspeak_data(id=CHANNEL_ID, api_key=API_KEY, save=True)
    df = merge_datasets(df_ts=df_ts, df_zue=df_zue)
    if save:
        df.to_csv('data/dataset.csv')
    return df


def remove_outliers(df, param=1.6, hours=0, minutes=0):
    # we use a sliding window with std to detect and remove outliers
    for t in df.index:
        t1 = t - timedelta(hours=hours, minutes=minutes)
        t2 = t + timedelta(hours=hours, minutes=minutes)
        inter = df.loc[t1:t2]
        mean = inter.mean(axis=0)
        std = inter.std(axis=0)
        dist = np.abs(df.loc[t] - mean)
        df.loc[t] = df.loc[t].where(dist < param * std)

    return df


def interpolate_pm10(df):
    # we wanted to interpolate the large missing intervals with DTW but the results were inconclusive
    # due to the high correlation between pm10 and pm25 (~0.95) we decided to interpolate with a simple multiplication

    pm10_series = df["PM10 [ug/m3]"]
    pm25_series = df["PM2.5 [ug/m3]"]

    mean_factor = (pm10_series/pm25_series).mean(axis=0)

    # interpolate with multiplication of pm2.5
    pm10_na = pm10_series.isna()
    pm10_series[pm10_na] = mean_factor * pm25_series[pm10_na]

    df["PM10 [ug/m3]"] = pm10_series

    return df
