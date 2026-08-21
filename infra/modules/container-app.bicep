param containerAppName string
param location string
param tags object
param managedEnvironmentId string
param managedIdentityResourceId string
param registryLoginServer string
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param appPort int
param healthEndpoint string
param appInsightsConnectionString string
param appEnvironment string
param managedIdentityClientId string
param foundryAccountEndpoint string
param foundryProjectEndpoint string
param azureOpenAIEndpoint string
param azureOpenAIModel string
param voiceLiveModel string
param voiceLiveApiVersion string
param voiceLiveVoice string
param contentUnderstandingAnalyzerId string

var isPlaceholder = containerImage == 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
var effectivePort = isPlaceholder ? 80 : appPort

resource containerApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: effectivePort
        transport: 'auto'
      }
      registries: isPlaceholder ? [] : [
        {
          server: registryLoginServer
          identity: managedIdentityResourceId
        }
      ]
      secrets: isPlaceholder ? [] : []
    }
    template: {
      containers: [
        {
          name: 'mortgage-app'
          image: containerImage
          env: [
            {
              name: 'PORT'
              value: string(effectivePort)
            }
            {
              name: 'APP_ENV'
              value: appEnvironment
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentityClientId
            }
            {
              name: 'FOUNDRY_ACCOUNT_ENDPOINT'
              value: foundryAccountEndpoint
            }
            {
              name: 'FOUNDRY_PROJECT_ENDPOINT'
              value: foundryProjectEndpoint
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_MODEL'
              value: azureOpenAIModel
            }
            {
              name: 'AZURE_VOICELIVE_ENDPOINT'
              value: foundryAccountEndpoint
            }
            {
              name: 'AZURE_VOICELIVE_MODEL'
              value: voiceLiveModel
            }
            {
              name: 'AZURE_VOICELIVE_API_VERSION'
              value: voiceLiveApiVersion
            }
            {
              name: 'AZURE_VOICELIVE_VOICE'
              value: voiceLiveVoice
            }
            {
              name: 'CONTENTUNDERSTANDING_ENDPOINT'
              value: foundryAccountEndpoint
            }
            {
              name: 'CONTENTUNDERSTANDING_ANALYZER_ID'
              value: contentUnderstandingAnalyzerId
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
          ]
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: isPlaceholder ? '/' : healthEndpoint
                port: effectivePort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: isPlaceholder ? '/' : healthEndpoint
                port: effectivePort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 6
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
}

output containerAppId string = containerApp.id
output containerAppName string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn
