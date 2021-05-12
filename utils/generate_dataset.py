from typing import Tuple
import pandas as pd
import json
import ssl
import numpy as np
import datetime

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


def merge_datasets(df_zue: pd.DataFrame, df_ts: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([df_zue, df_ts])


def get_dataset(save: bool = True) -> pd.DataFrame:
    df_zue = get_zue_data()
    df_ts = get_thingspeak_data(id=CHANNEL_ID, api_key=API_KEY, save=True)
    df = merge_datasets(df_ts=df_ts, df_zue=df_zue)
    if save:
        df.to_csv('data/dataset.csv')
    return df
