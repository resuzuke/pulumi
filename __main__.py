"""A Python Pulumi program"""

import base64

import pulumi
import pulumi_local
import pulumi_azure_native as azure_native
import pulumi_azuread as azuread
import pulumi_random as random
from pulumi_azure_native import storage
from pulumi_azure_native import resources
import pulumi_azure_native.authorization as authorization
import pulumi_tls as tls

config = pulumi.Config()

resource_group = resources.ResourceGroup("k8s")


subscription = azure_native.authorization.get_client_config().subscription_id


ssh_key = tls.PrivateKey("ssh-key", algorithm="RSA", rsa_bits=4096)

# Create an AD service principal
ad_app = azuread.Application("aks", display_name="aks")
ad_sp = azuread.ServicePrincipal("aksSp", client_id=ad_app.client_id)

# Generate random password
password = random.RandomPassword("password", length=20, special=True)

# Create the Service Principal Password
ad_sp_password = azuread.ServicePrincipalPassword("aksSpPassword",
                                                  service_principal_id=ad_sp.id,
#                                                  value=password.result,
                                                  end_date="2099-01-01T00:00:00Z")


managed_cluster_name = config.get("managedClusterName")
if managed_cluster_name is None:
    managed_cluster_name = "azure-native-aks"

managed_cluster = azure_native.containerservice.ManagedCluster(
    managed_cluster_name,
    resource_group_name=resource_group.name,
    agent_pool_profiles=[{
        "name": "default",
        "count" : 1,
        "min_count": 1,
        "max_count": 3,
        "max_pods": 110,
        "enable_auto_scaling": True,
        "mode": "System",
        "node_labels": {},
        "os_disk_size_gb": 30,
        "os_type": "Linux",
        "type": "VirtualMachineScaleSets",
        "vm_size": "Standard_B2s",
    }],
    enable_rbac=True,
    kubernetes_version="1.28.3",
    linux_profile={
        "admin_username": "testuser",
        "ssh": {
            "public_keys": [{
                "key_data": ssh_key.public_key_openssh,
            }],
        },
    },
    auto_scaler_profile=azure_native.containerservice.ManagedClusterPropertiesAutoScalerProfileArgs(
      skip_nodes_with_local_storage="false",
      skip_nodes_with_system_pods="false",
    ),
    dns_prefix=resource_group.name,
    service_principal_profile={
      "client_id": ad_app.client_id,
      "secret": ad_sp_password.value
    },
    node_resource_group=f"MC_azure-native-go_{managed_cluster_name}_westus",
)

#agent_pool = azure_native.containerservice.AgentPool("agentPool",
#    agent_pool_name="agentpool1",
#    count=1,
#    min_count=1,
#    max_count=3,
#    orchestrator_version="",
#    os_disk_size_gb=64,
#    os_disk_type="Ephemeral",
#    os_type="Linux",
#    resource_group_name=resource_group.name,
#    resource_name_=managed_cluster.name,
#    vm_size="Standard_B2s")

creds = azure_native.containerservice.list_managed_cluster_user_credentials_output(
    resource_group_name=resource_group.name,
    resource_name=managed_cluster.name)
#################################

automation_account = azure_native.automation.AutomationAccount("automationAccount",
    automation_account_name="myAutomationAccount9",
    name="myAutomationAccount9",
    resource_group_name=resource_group.name,
    sku=azure_native.automation.SkuArgs(
        name="Free",
    ),
    identity=azure_native.automation.IdentityArgs(
        type="SystemAssigned",
    ),
    )

role_assignment = authorization.RoleAssignment("roleAssignment",
    scope=pulumi.Output.concat("/subscriptions/", subscription),
    role_assignment_name=random.RandomUuid("testRandomUuid"),
    principal_type="ServicePrincipal",
    principal_id=automation_account.identity.principal_id,
    role_definition_id=pulumi.Output.concat("/subscriptions/", subscription,
                                            "/providers/Microsoft.Authorization/roleDefinitions/",
                                            "8e3af657-a8ff-443c-a75c-2fe8c4bcb635")  # The role definition ID for Owner role
)

role_assignment2 = authorization.RoleAssignment("roleAssignment2",
    scope=pulumi.Output.concat("/subscriptions/", subscription, "/resourceGroups/", resource_group.name),
    role_assignment_name=random.RandomUuid("testRandomUuid2"),
    principal_type="ServicePrincipal",
    principal_id=automation_account.identity.principal_id,
    role_definition_id=pulumi.Output.concat("/subscriptions/", subscription,
                                            "/providers/Microsoft.Authorization/roleDefinitions/",
                                            "8e3af657-a8ff-443c-a75c-2fe8c4bcb635")  # The role definition ID for Owner role
)

example_file =  pulumi_local.get_file(filename=f"{path['module']}/stop-cluster.ps1")


runbook = azure_native.automation.Runbook("runbook",
    automation_account_name=automation_account.name,
    description="Description of the Runbook",
    location=resource_group.location,
    log_activity_trace=1,
    log_progress=True,
    log_verbose=False,
    name="stop-k8s-cluster",
    resource_group_name=resource_group.name,
    runbook_name="stop-k8s-cluster",
    runbook_type="PowerShell",
    content=example_file.content
)



########################

# Export kubeconfig
encoded = creds.kubeconfigs[0].value
kubeconfig = encoded.apply(
    lambda enc: base64.b64decode(enc).decode())
pulumi.export("kubeconfig", kubeconfig)
