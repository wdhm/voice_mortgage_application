// Resource-group–scoped resources for the Bank Alfa Mortgage AI Demo.
// One Azure Container App (system for REST + WebSocket + built SPA), its
// registry/observability dependencies, and keyless access to the existing
// Foundry account via a user-assigned managed identity.
targetScope = 'resourceGroup'

param location string
param resourceToken string
param tags object
param foundryAccountName string
param foundryEndpoint string
param voiceProvider string
param documentProvider string
param appImage string

// Built-in role definition IDs.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

// --- Managed identity the app runs as (image pull + keyless Foundry auth) ---
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-mortgage-${resourceToken}'
  location: location
  tags: tags
}

// --- Observability ---
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-mortgage-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// --- Container registry (azd pushes the built image here) ---
resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: 'acrmortgage${resourceToken}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

// --- Keyless access to the existing Foundry (Azure AI Services) account ---
resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryAccountName
}

resource foundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, identity.id, cognitiveServicesUserRoleId)
  scope: foundry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
  }
}

// --- Container Apps environment ---
resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-mortgage-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// --- The app: single replica, external HTTPS ingress on 8000 ---
resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-mortgage-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'app' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: identity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'app'
          image: appImage
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            { name: 'APP_HOST', value: '0.0.0.0' }
            { name: 'APP_PORT', value: '8000' }
            { name: 'VOICE_PROVIDER', value: voiceProvider }
            { name: 'DOCUMENT_PROVIDER', value: documentProvider }
            { name: 'FOUNDRY_ENDPOINT', value: foundryEndpoint }
            { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPull
  ]
}

output containerRegistryLoginServer string = registry.properties.loginServer
output appUri string = 'https://${app.properties.configuration.ingress.fqdn}'
