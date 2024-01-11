param
(
    [Parameter(Mandatory = $false)]
    [string] $ResourceGroupName='k8s-bootcamp',
    [Parameter(Mandatory = $false)]
    [string] $Name='k8s'
)

Connect-AzAccount -Identity | Out-Null


$erroractionpreference = "stop"


$aksCluster = Get-AzAksCluster -Name $Name -ResourceGroupName $ResourceGroupName
$aksResourceId = $aksCluster.Id
$aksResource = Get-AzResource -ResourceId $aksResourceId
$aksPowerState = $aksResource.Properties.powerState.code

Write-Output $aksPowerState

if ($aksPowerState -ne 'Stopped') {
  Write-Output "Stopping cluster..."
  Stop-AzAksCluster `
      -ResourceGroupName $ResourceGroupName `
      -Name $Name
}
