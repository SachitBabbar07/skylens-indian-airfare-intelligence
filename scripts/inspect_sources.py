from discover import OUT, fetch
import concurrent.futures, json
refs=['shubhambathwal/flight-price-prediction','yashdharme36/airfare-ml-predicting-flight-fares','iamavyukt/goibibo-flight-data','shraddha4ever20/indian-domestic-flights-dataset-20192025','andrewgeorgeissac/flight-price-data-of-indian-cities-makemytrip','sumitjaiswar/indian-domestic-flights-data','dhairya903/flights-dataset','nikhilmittal/flight-fare-prediction-mh','orhfusion/flight-price-dataset']
for ref in refs:
    name='kaggle_'+ref.replace('/','__')
    try:
        import urllib.request
        data=json.load(urllib.request.urlopen('https://www.kaggle.com/api/v1/datasets/view/'+ref,timeout=40))
        (OUT/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        print(json.dumps({'ref':ref,**{k:data.get(k) for k in ['title','subtitle','description','licenses','lastUpdated','files','resources','totalBytes','ownerName','currentVersionNumber','usabilityRating']}},ensure_ascii=True))
    except Exception as e: print(ref,str(e))
