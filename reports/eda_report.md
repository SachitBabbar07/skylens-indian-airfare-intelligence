# Exploratory analysis
All figures use actual retained observations or fitted outputs. Each cohort has separate fare distributions, medians by airline/origin/route/class/journey-label/stops, fare versus lead-time/duration/distance/date, sparse-route histograms, holdout actual-vs-predicted plots, global/individual SHAP and lead-time SHAP dependence. Source targets are not mixed into a normalized INR chart.

Cabin medians distinguish premium products, so expensive business fares are not automatically invalid outliers. Airline/route medians remain confounded by itinerary mix. Sparse-route counts explain why observation coverage is larger than serving coverage. Actual-vs-predicted plots show large misses hidden by averages. Cabin lead time also tracks departure date from a single query snapshot, so a plot cannot prove a causal benefit of waiting.

True one-way versus return comparisons cannot be made without booking labels. Multi-year seasonal analysis is unsupported by these short windows. Network cabin remains Unspecified. Calendar-date plots are descriptive only. Price tails stay intact. Profiles and subgroup CSVs provide underlying counts and errors.
