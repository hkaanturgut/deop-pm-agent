// Cosmos DB — Serverless NoSQL for tasks, projects, clients

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Managed Identity principal ID for RBAC')
param managedIdentityPrincipalId string

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${baseName}-cosmos'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    disableLocalAuth: true
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

// Database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: 'deop-pm-db'
  properties: {
    resource: {
      id: 'deop-pm-db'
    }
  }
}

// Tasks container — partitioned by client_id
resource tasksContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'tasks'
  properties: {
    resource: {
      id: 'tasks'
      partitionKey: {
        paths: ['/client_id']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
        compositeIndexes: [
          [
            { path: '/client_id', order: 'ascending' }
            { path: '/due_date', order: 'ascending' }
          ]
          [
            { path: '/project_id', order: 'ascending' }
            { path: '/status', order: 'ascending' }
          ]
        ]
      }
    }
  }
}

// Projects container — partitioned by client_id
resource projectsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'projects'
  properties: {
    resource: {
      id: 'projects'
      partitionKey: {
        paths: ['/client_id']
        kind: 'Hash'
        version: 2
      }
    }
  }
}

// Clients container — partitioned by id
resource clientsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'clients'
  properties: {
    resource: {
      id: 'clients'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
        version: 2
      }
    }
  }
}

// Grant Managed Identity Cosmos DB Built-in Data Contributor role
resource cosmosRbac 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, managedIdentityPrincipalId, 'CosmosDataContributor')
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmosAccount.id
  }
}

output endpoint string = cosmosAccount.properties.documentEndpoint
output name string = cosmosAccount.name
