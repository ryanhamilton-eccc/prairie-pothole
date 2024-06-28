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
        )

        # need to insert a fmt date time into each image
        s1obj = s1obj.map(self.insert_fmt_datetime)

        # convert to geopandas dataframe
        s1_gdf = s1obj.toGeoPandasDataFrame()[
            ["system:id", "system:time_start", "relativeOrbitNumber_start", "geometry"]
        ]
        s1_gdf = Sentinel1Extractor.insert_centroid_x_y(s1_gdf)
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
    def insert_centroid_x_y(df: gpd.GeoDataFrame):
        df["x"] = df.geometry.centroid.x
        df["y"] = df.geometry.centroid.y

        df["y"] = df["y"].apply(lambda x: float(f"{x:.2f}"))
        df["x"] = df["x"].apply(lambda x: float(f"{x:.2f}"))
        
        return df

    @staticmethod
    def localize_utc_time(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # date time conversion
        tf = TimezoneFinder()
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
        df["datedif"] = 0
        processed = []
        for _, group in df.groupby(["y", "relativeOrbitNumber_start", 'platform_number']):
            group["datedif"] = group["julian_date"] - group["julian_date"].shift(1)
            group["datedif"] = group["datedif"].fillna(0)
            processed.append(group)

        dfout = pd.concat(processed, ignore_index=True)[
            [
                "system:id",
                "y",
                "x",
                "relativeOrbitNumber_start",
                'platform_number',
                "timestamp",
                "year",
                "datedif",
                "geometry",
            ]
        ]
        return dfout