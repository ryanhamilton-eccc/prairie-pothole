from typing import Any

import ee
import geersd
from pph import datautils

def process_landsat(aoi, start, end):
    # landsat 5
    old_names = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
    new_name = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
    l5 = geersd.Landsat5SR().filterBounds(aoi).filterDate(start, end).filterClouds(1).select(
        old_names, new_name
    )
    
    # landsat 8
    l8 = geersd.Landsat8SR().filterBounds(aoi).filterDate(start, end).filterClouds(1).select("SR_B[2-7]")
    
    combine = l5.merge(l8) # type: ee.ImageCollection
    return combine


def fetch_l8sr_dataset(aoi, t1, t2, selector: Any = None, cloud_percent: float = -1, filter_funcs: ee.Filter = None) -> ee.ImageCollection | None:
    dataset = (
        geersd.Landsat8SR()
        .filterBounds(aoi)
        .filterDate(t1, t2)
    )
    
    if dataset.size().getInfo() == 0:
        return None
    
    if cloud_percent > -1:
        dataset = dataset.filterClouds(cloud_percent)
    
    
    dataset = dataset.applyScalingFactor().applyCloudMask()
    
    if selector:
        dataset = dataset.select(selector)
    
    if filter_funcs:
        dataset = dataset.filter(filter_funcs)
    
    return dataset


def fetch_l8_yearly_compsites(aoi, selectors: str, start_yyyy: int = 2017, end_yyyy: int = 2023, filter_func: ee.Filter = None) -> tuple[ee.Image, ee.Image, ee.Geometry]:
    """ Yearly Max Composite, Max Compsite, aoi """
    images = []
    # this handels accumulating the max images by year
    for year in range(start_yyyy, end_yyyy + 1):
        start, end = f"{year}-04-01", f"{year}-10-31"

        images.append(fetch_l8sr_dataset(aoi, start, end,  selector=selectors, filter_funcs=filter_func).max())
    
    # another loop to handle making the yearly max composite and one to 
    composite = None
    for image_max in images:
        if image_max is None:
            continue

        if composite is None:
            composite = image_max
        else:
            composite = composite.addBands(image_max)
    max_composite = ee.ImageCollection(images).max()
    return composite.clip(aoi), max_composite.clip(aoi), aoi


def fetch_ft_l8_timeseries(aoi, selector, start_yyyy: int = 2017, end_yyyy: int = 2023, filter_funcs: ee.Filter = None):
    selector = selector or "SR_B5"
    ts = fetch_l8sr_dataset(
        aoi=aoi,
        t1=start_yyyy, 
        t2=end_yyyy,
        selector=selector,
        filter_funcs=filter_funcs
    )
    return ts, aoi

# Moose Moose Mountain 

def fetch_moose_mnt_yrly_composites(selectors) -> tuple[ee.Image, ee.Geometry]:
    aoi = datautils.load_moose_mount_aoi()
    wrs_row = 25
    wrs_path = 34
    filter_func = ee.Filter([
        ee.Filter.eq('WRS_ROW', wrs_row),
        ee.Filter.eq('WRS_PATH', wrs_path)
    ])
    return fetch_l8_yearly_compsites(aoi, selectors=selectors, filter_func=filter_func)



def fetch_moose_mnt_time_series(selector: str) -> tuple[ee.ImageCollection]:
    aoi = datautils.load_moose_mount_aoi()
    wrs_row = 25
    wrs_path = 34
    filter_func = ee.Filter([
        ee.Filter.eq('WRS_ROW', wrs_row),
        ee.Filter.eq('WRS_PATH', wrs_path)
    ])
    return fetch_ft_l8_timeseries(aoi, selector, filter_funcs=filter_func)

