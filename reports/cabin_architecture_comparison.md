# Cabin architecture comparison
This additional diagnostic uses training and validation partitions only, with the same selected hyperparameters. The final test is not evaluated or used to revise the frozen model. It is a post-hoc research comparison, not part of the original model-selection claim. Pooled and separate models use identical validation rows for each class. No return/one-way specialized model can be compared because booking journey types remain unverified. First is still excluded as sparse.

architecture,class,training_rows,n,mae,rmse,r2,median_absolute_error,mape_percent,p90_absolute_error
pooled,Business,267288,12788,5340.21015548124,8557.314948735344,0.578386433075736,2860.158093730992,10.528075123304964,13022.91568718752
class_specific,Business,74509,12788,4751.384470917778,7957.138144712805,0.6354531577540008,2356.3584228463587,9.21176044147995,12139.982462555365
pooled,Economy,267288,25231,1284.6592583617635,2103.22588943709,0.6904686375929155,743.9208525544764,14.164166563641414,3016.414447316085
class_specific,Economy,149682,25231,1247.58191083286,2067.500557788132,0.7008947114313031,696.4907335772041,13.661970089929923,2996.5623940938513
pooled,Premium Economy,267288,6661,1672.2290952832645,3044.7289560226454,0.5730954572619573,745.0528674831039,10.994984411238969,4298.930772905202
class_specific,Premium Economy,43097,6661,1339.921541582753,2733.4717498193154,0.655917423983462,432.2018245275194,8.618520403573356,3862.144997801739

The deployed research artifact stays the previously selected pooled model. Separate-class results identify an improvement candidate that would require a fresh untouched evaluation before promotion, avoiding retrospective selection on an already-opened holdout.
