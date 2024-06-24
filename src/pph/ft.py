import ee
import geeft

from pph.core import process_landsat


class FourierTransform:
    def compute(self, aoi: ee.Geometry, dependent: str = None, start: str = None, end: str = None):
        dependent = dependent or 'SR_B5' # NIR
        start = start or '1984'
        end = end or "2022"
        
        dataset = process_landsat(aoi, '1984', '2022')
        ft = geeft.compute(dataset=dataset, dependent=dependent, modes=2)
        return ft
