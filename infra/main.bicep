targetScope = 'subscription'

@minLength(1)
@maxLength(64)
param environmentName string

@minLength(1)
param location string

param sessionId string
param deployedBy string
param createdAt string
param deployerObjectId string

param resourceGroupName string
param containerAppsEnvironmentName string
param containerAppName string
param containerRegistryName string
param logAnalyticsName string
param applicationInsightsName string
param managedIdentityName string
param keyVaultName string
param foundryAccountName string
param foundryProjectName string

param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param appPort int
param healthEndpoint string
param appEnvironment string
param foundryAccountEndpoint string
param foundryProjectEndpoint string
param azureOpenAIEndpoint string
param azureOpenAIModel string = 'gpt-5.2'
param voiceLiveModel string
param voiceLiveApiVersion string = '2026-04-10'
param voiceLiveVoice string = 'en-US-Ava:DragonHDLatestNeural'
param contentUnderstandingAnalyzerId string

var tags = {
  'app-onboard-skill': 'true'
  'app-onboard-session-id': sessionId
  'created-at': createdAt
  environment: environmentName
  'deployed-by': deployedBy
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module logAnalytics './modules/log-analytics.bicep' = {
  name: 'log-analytics'
  scope: resourceGroup
  params: {
    workspaceName: logAnalyticsName
    location: location
    tags: tags
  }
}

module applicationInsights './modules/application-insights.bicep' = {
  name: 'application-insights'
  scope: resourceGroup
  params: {
    applicationInsightsName: applicationInsightsName
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.outputs.workspaceId
  }
}

module keyVault './modules/key-vault.bicep' = {
  name: 'key-vault'
  scope: resourceGroup
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: tags
  }
}

module containerRegistry './modules/container-registry.bicep' = {
  name: 'container-registry'
  scope: resourceGroup
  params: {
    registryName: containerRegistryName
    location: location
    tags: tags
  }
}

module managedIdentity './modules/managed-identity.bicep' = {
  name: 'managed-identity'
  scope: resourceGroup
  params: {
    identityName: managedIdentityName
    location: location
    tags: tags
  }
}

module containerAppsEnvironment './modules/container-app-environment.bicep' = {
  name: 'container-app-environment'
  scope: resourceGroup
  params: {
    environmentName: containerAppsEnvironmentName
    location: location
    tags: tags
    workspaceName: logAnalyticsName
    workspaceCustomerId: logAnalytics.outputs.workspaceCustomerId
  }
}

module foundry './modules/foundry-existing.bicep' = {
  name: 'foundry-existing'
  scope: resourceGroup
  params: {
    accountName: foundryAccountName
    projectName: foundryProjectName
  }
}

module containerApp './modules/container-app.bicep' = {
  name: 'container-app'
  scope: resourceGroup
  params: {
    containerAppName: containerAppName
    location: location
    tags: tags
    managedEnvironmentId: containerAppsEnvironment.outputs.environmentId
    managedIdentityResourceId: managedIdentity.outputs.identityId
    registryLoginServer: containerRegistry.outputs.loginServer
    containerImage: containerImage
    appPort: appPort
    healthEndpoint: healthEndpoint
    appInsightsConnectionString: applicationInsights.outputs.connectionString
    appEnvironment: appEnvironment
    managedIdentityClientId: managedIdentity.outputs.clientId
    foundryAccountEndpoint: foundryAccountEndpoint
    foundryProjectEndpoint: foundryProjectEndpoint
    azureOpenAIEndpoint: azureOpenAIEndpoint
    azureOpenAIModel: azureOpenAIModel
    voiceLiveModel: voiceLiveModel
    voiceLiveApiVersion: voiceLiveApiVersion
    voiceLiveVoice: voiceLiveVoice
    contentUnderstandingAnalyzerId: contentUnderstandingAnalyzerId
  }
}

module roleAssignments './modules/role-assignments.bicep' = {
  name: 'role-assignments'
  scope: resourceGroup
  params: {
    keyVaultName: keyVault.outputs.keyVaultName
    registryName: containerRegistry.outputs.registryName
    foundryAccountName: foundry.outputs.accountName
    appPrincipalId: managedIdentity.outputs.principalId
    deployerObjectId: deployerObjectId
  }
}

output containerAppName string = containerApp.outputs.containerAppName
output containerAppFqdn string = containerApp.outputs.fqdn
output containerRegistryName string = containerRegistry.outputs.registryName
output keyVaultName string = keyVault.outputs.keyVaultName
