// Azure Bot Service with Teams channel

@description('Base name for resources')
param baseName string

@description('Azure region — Bot Service uses global')
param location string

@description('Resource tags')
param tags object

@description('Bot App ID (Entra ID application)')
param botAppId string

@description('Display name in Teams')
param botDisplayName string

@description('App Service messaging endpoint')
param appServiceEndpoint string

resource botService 'Microsoft.BotService/botServices@2022-09-15' = {
  name: '${baseName}-bot'
  location: 'global'
  tags: tags
  kind: 'azurebot'
  sku: {
    name: 'F0'
  }
  properties: {
    displayName: botDisplayName
    endpoint: '${appServiceEndpoint}/api/messages'
    msaAppId: botAppId
    msaAppType: 'SingleTenant'
    msaAppTenantId: subscription().tenantId
  }
}

// Teams channel
resource teamsChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: botService
  name: 'MsTeamsChannel'
  location: 'global'
  properties: {
    channelName: 'MsTeamsChannel'
    properties: {
      isEnabled: true
    }
  }
}

output name string = botService.name
