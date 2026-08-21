param applicationInsightsName string
param location string
param tags object
param workspaceResourceId string

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    IngestionMode: 'LogAnalytics'
    WorkspaceResourceId: workspaceResourceId
  }
}

output applicationInsightsId string = applicationInsights.id
output connectionString string = applicationInsights.properties.ConnectionString
