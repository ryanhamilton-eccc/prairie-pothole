from pathlib import Path

import ee
import geopandas as gpd

import geersd

from pph import fpcde


def load_moose_mount_aoi() -> ee.Geometry:
    shp_file = Path(__file__).parent.parent / "data/moose_mountain_FT_OPC_analysis_AOI_7year_L8.shp"
    gdf = gpd.read_file(shp_file, driver="ESRI Shapefile")
    gdf.set_crs(4326, inplace=True)
    return ee.FeatureCollection(gdf.__geo_interface__).geometry()


# DATA EXTRACTION HELPERS

def s1_collection_to_geodataframe(aoi, start, end) -> gpd.GeoDataFrame:
    return fpcde.Sentinel1Extractor().extract_and_process(aoi, (start, end))


def l8_collection_to_geodataframe(start, end, aoi, cloud_percent: float = -1):
    ic = geersd.Landsat8SR().filterBounds(aoi).filterDate(start, end)
    
    if cloud_percent > 0:
        ic = ic.filterClouds(cloud_percent)

    ic = ic.map(lambda x: x.set('date', x.date().format('YYYY-MM-dd')))

    gdf = ic.toGeoPandasDataFrame()
    
    column_names = [
        'date',
        'system:id',
        'system:time_end',
        'system:time_start',
        'CLOUD_COVER',
        'UTM_ZONE', 
        'WRS_PATH',
        'WRS_ROW', 
        'WRS_TYPE',
        'geometry',
    ]
    
    gdfout = gdf[column_names]
    gdfout.set_crs(4326, inplace=True)
    gdfout[['Year', 'Month', 'Day']] = gdfout['date'].str.split('-', expand=True)
    gdfout[['Year', 'Month', 'Day']] = gdfout[['Year', 'Month', 'Day']].astype(int)
    return gdfout


# EE IO / Export Helpers

def ee_l8_image_to_gdrive(image, region, folder, filename):
    task = ee.batch.Export.image.toDrive(
        image=image,
        region=region,
        scale=30,
        folder=folder,
        description="moose-mountain-export",
        fileNamePrefix=filename,
        crs='EPSG:4326',
        maxPixels=1e13,
        skipEmptyTiles=True
        )

    return task