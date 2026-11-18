# Supervised fare prediction status

On 18 November 2026, the local quote store had zero verified targets. The DEL → IXC request for 25 November 2026, one adult, one-way Economy with IndiGo, has no approved model. The original cabin cohort contains zero DEL → IXC records. The original network cohort contains 24 DEL → IXC records, including one IndiGo record. The separate historical challenge contains 38, including three IndiGo records. Both network cohorts lack verified target semantics and cabin for this route. See the [target audit](price_target_reaudit_20261115.md).

The [India Cheap Flights Fare Index](https://indiacheapflights.com/press/) publishes CC BY 4.0 route aggregates in INR. Its 18 November JSON had 1,554 route rows. The DEL → IXC row reported 62 observations but exposed only summary statistics, with no carrier, flight or departure date fields. That row cannot train or independently test a fare for the selected flight. No index prices were imported into the quote store or fitted to the example.

The new offline candidate runner uses one-adult, one-way Economy quote totals with taxes and fees included. It validates the frozen split and source evidence, fits only the training window, and reports test error and baseline error by covered route and carrier. A software fixture exercised the runner. Fitting the actual workspace correctly stops at zero verified quotes. No customer model or accuracy figure has been published.

When a trained model cannot price an itinerary, Flights now shows matching provider fares in a separate category. [Flight search API](../docs/API_GUIDE.md#flight-search)
