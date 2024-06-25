from __future__ import annotations

import ee
import geopandas as gpd
import pandas as pd

from geersd import Sentinel1
from timezonefinder import TimezoneFinder



class Sentinel1Extractor:
    def extract_and_process(
        self, aoi, dates: tuple[str, str],
    ):
        """extracts and converts Sentinel 1 to geopandas dataframe"""
        s1obj = (
            Sentinel1()
            .filterBounds(aoi)
            .filterDate(*dates)
            .filterIWMode()
            .filterVV()
            .filterVH()
            .filterAsc()
            .filter(ee.Filter.eq('platform_number', 'B'))
        )

        # need to insert a fmt date time into each image
        s1obj = s1obj.map(self.insert_fmt_datetime)

        # convert to geopandas dataframe
        s1_gdf = s1obj.toGeoPandasDataFrame()[
            ["system:id", "system:time_start", "relativeOrbitNumber_start", "geometry"]
        ]
        s1_gdf = Sentinel1Extractor.localize_utc_time(s1_gdf)
        s1_gdf = Sentinel1Extractor.compute_date_differential(s1_gdf)
        s1_gdf["timestamp"] = s1_gdf["timestamp"].astype(str)
        return s1_gdf

    @staticmethod
    def insert_fmt_datetime(image: ee.Image) -> ee.Image:
        """set a meta prop called fmt_date fmt: YYYY-MM-dd"""
        date = ee.Image(image).date().format("YYYY-MM-dd")
        return image.set("fmt_date", date)

    @staticmethod
    def localize_utc_time(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # date time conversion
        tf = TimezoneFinder()
        df["x"] = df.geometry.centroid.x
        df["y"] = df.geometry.centroid.y
        df["timezone"] = df.apply(
            lambda x: tf.timezone_at(lng=x["x"], lat=x["y"]), axis=1
        )
        df["utc"] = df["system:time_start"] / 1000.0
        df["timestamp"] = pd.to_datetime(df["utc"], unit="s")
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        df["timestamp"] = df.apply(
            lambda row: row["timestamp"].tz_convert(row["timezone"]), axis=1
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df["year"] = df["timestamp"].dt.year
        df["julian_date"] = df["timestamp"].dt.dayofyear
        return df

    @staticmethod
    def compute_date_differential(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        df["y"] = df["y"].apply(lambda x: float(f"{x:.2f}"))
        df["x"] = df["x"].apply(lambda x: float(f"{x:.2f}"))
        df["datedif"] = 0
        processed = []
        for _, group in df.groupby(["y", "relativeOrbitNumber_start"]):
            group["datedif"] = group["julian_date"] - group["julian_date"].shift(1)
            group["datedif"] = group["datedif"].fillna(0)
            processed.append(group)

        dfout = pd.concat(processed, ignore_index=True)[
            [
                "system:id",
                "y",
                "x",
                "relativeOrbitNumber_start",
                "timestamp",
                "year",
                "datedif",
                "geometry",
            ]
        ]
        return dfout


def fetch_s1_tiles():
    """ """
    # time stamps need to be with in 04-01, 10-31 for any given year
    # need the pph aoi / region
    gdfs = []
    for i in range(2017, 2022):
        dates = (f"{i}-04-01", f"{i}-10-31")
        extractor = Sentinel1Extractor().extract_and_process(aoi=None, dates=dates)


def compute_intersect():
    pass