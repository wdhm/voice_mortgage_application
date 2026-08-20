// Bank Alfa Mortgage AI Demo — infrastructure entrypoint (azd, subscription scope).
// Provisions everything into an existing resource group that already holds the
// Foundry (Azure AI Services) account, then grants the app's managed identity
// keyless access to that account.
targetScope = 'subscription'

@minLength(1)
@description('Name of the azd environment; used to derive a unique resource token.')
param environmentName string

@minLength(1)
@description('Azure region for all resources (e.g. swedencentral).')
param location string

@description('Existing resource group that holds the Foundry account and will host the app.')
param resourceGroupName string = 'rg-voice-mortgage-app'

@description('Existing Foundry / Azure AI Services account name to grant the app access to.')
param foundryAccountName string

@description('Foundry endpoint the app calls at runtime.')
param foundryEndpoint string = 'https://foundry-mortgage.cognitiveservices.azure.com/'

@description('Voice capability provider: "simulated" (deterministic, offline) or "foundry".')
param voiceProvider string = 'simulated'

@description('Document capability provider: "simulated" (deterministic, offline) or "foundry".')
param documentProvider string = 'simulated'

// azd populates this with the built image; the placeholder lets the template
// validate before the first `azd deploy`.
@description('Container image reference for the app.')
param appImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' existing = {
  name: resourceGroupName
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
    foundryAccountName: foundryAccountName
    foundryEndpoint: foundryEndpoint
    voiceProvider: voiceProvider
    documentProvider: documentProvider
    appImage: appImage
  }
}

output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.containerRegistryLoginServer
output SERVICE_APP_URI string = resources.outputs.appUri
