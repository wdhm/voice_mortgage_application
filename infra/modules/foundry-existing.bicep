param accountName string
param projectName string

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2026-07-01' existing = {
  name: accountName
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' existing = {
  parent: foundryAccount
  name: projectName
}

output accountId string = foundryAccount.id
output accountName string = foundryAccount.name
output projectId string = foundryProject.id
output projectName string = foundryProject.name
