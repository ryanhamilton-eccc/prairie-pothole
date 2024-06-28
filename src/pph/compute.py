import ee
import geeft


# Fourier Transform Computaion
def compute_fourier(dataset, dependent: str) -> ee.Image:
    return geeft.compute(dataset=dataset, dependent=dependent, modes=2)


# PCA Computation

def center_image(image, region, scale, band_names):
    mean_dict = image.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=scale, maxPixels=1e9
    )
    means = mean_dict.toImage(band_names)
    return image.subtract(means)


def get_names(prefix, sequence: ee.List):
    return ee.List(sequence).map(
        lambda x: ee.String(prefix).cat(ee.Number(x).int())
    )


def compute_pca(dataset, region, scale: int = 30):
       
    band_names = dataset.bandNames()
    n_bands = ee.List.sequence(1, band_names.size())
    
    centered = center_image(dataset, region, scale, band_names)
    
    # Collapse bands into 1D array
    arrays = centered.toArray()

    # Compute the covariance of the bands within the region.
    covar = arrays.reduceRegion(
        reducer=ee.Reducer.centeredCovariance(),
        geometry=region,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True
    )

    # Get the 'array' covariance result and cast to an array.
    # This represents the band-to-band covariance within the region.
    covar_array = ee.Array(covar.get('array'))

    # Perform an eigen analysis and slice apart the values and vectors.
    eigens = covar_array.eigen()

    # This is a P-length vector of Eigenvalues.
    eigen_values = eigens.slice(1, 0, 1)
    # This is a PxP matrix with eigenvectors in rows.
    eigen_vectors = eigens.slice(1, 1)

    # Convert the array image to 2D arrays for matrix computations.
    array_image = arrays.toArray(1)

    # Left multiply the image array by the matrix of eigenvectors.
    principal_components = ee.Image(eigen_vectors).matrixMultiply(array_image)

    # Turn the square roots of the Eigenvalues into a P-band image.
    sd_names = get_names('sd', n_bands)
    sd_image = (
        ee.Image(eigen_values.sqrt())
        .arrayProject([0])
        .arrayFlatten([sd_names])
    )

    # Turn the PCs into a P-band image, normalized by SD.
    return (
        # Throw out an an unneeded dimension, [[]] -> [].
        principal_components.arrayProject([0])
        # Make the one band array image a multi-band image, [] -> image.
        .arrayFlatten([get_names('pc', n_bands)])
        # Normalize the PCs by their SDs.
        .divide(sd_image)
    )
    