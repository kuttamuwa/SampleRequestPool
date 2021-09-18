// YOU HAVE TO ADD GLOBALID TO YOUR LAYER FIRST !

var hatguid = $feature.GLOBALID  // my edited layer

var request_pool = FeatureSetByName($datastore, "SDE.REQUEST_POOL",  // CHECK HERE
    ["SERVICE_NAME", "SERVICE_URL", "PARAMS", "STATUS"])

var service_name = "line_" + hatguid

// CHANGE HERE
var service_url = "https://localhost:6443/arcgis/rest/services/MyToolbox/GPServer/MyKMToolbox/submitJob"

return {
    'result': $feature,
    'edit': [
        {
        'className': 'SDE.REQUEST_POOL',  // CHECK HERE
        'adds': [
            {
            "attributes":
                {
                    "SERVICE_NAME": service_name,
                    "SERVICE_URL": service_url,
                    "PARAMS": "line_id=" + hatguid,
                    "STATUS": "WAITING",
                    "CREATED_DATE": Date()
                },
        }]
    }]
}