import geersd



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