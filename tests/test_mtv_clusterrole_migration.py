import pytest
from ocp_resources.config_map import ConfigMap
from ocp_resources.secret import Secret
from pytest_testconfig import config as py_config

from utilities.clusterrole_utils import (
    run_clusterrole_migration,
    verify_configmap_migrated,
    verify_secret_migrated,
    verify_vms_running,
)
from utilities.migration_utils import get_cutover_value
from utilities.resources import create_and_store_resource
from utilities.utils import get_value_from_py_config


@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.skipif(
    not get_value_from_py_config("remote_ocp_cluster"),
    reason="No remote OCP cluster provided",
)
@pytest.mark.parametrize(
    "class_plan_config",
    [pytest.param(py_config["tests_params"]["test_mtv_clusterrole_cold_migration"])],
    indirect=True,
    ids=["MTV-3129-clusterrole-cold"],
)
@pytest.mark.usefixtures("cleanup_migrated_vms")
class TestClusterroleColdMtvMigration:
    """Verify ClusterRole (forklift-migrator-role) with cold migration."""

    def test_mtv_clusterrole_cold_migration(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
        clusterrole_destination_ocp_provider,
        prepared_plan,
        source_provider,
        multus_network_name,
        source_provider_inventory,
    ):
        """
        Uses a single token-based OCP provider (clusterrole_destination_ocp_provider).
        Steps: ClusterRole/SA/token/provider by fixture; create NetworkMap and StorageMap;
        create Plan, run migration, verify VMs running.
        """
        run_clusterrole_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            prepared_plan=prepared_plan,
            source_provider_inventory=source_provider_inventory,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
        )
        verify_vms_running(
            ocp_admin_client=ocp_admin_client,
            prepared_plan=prepared_plan,
            target_namespace=target_namespace,
        )

<<<<<<< HEAD
        for vm_config in prepared_plan["virtual_machines"]:
            vm = VirtualMachine(
                client=ocp_admin_client,
                name=vm_config["name"],
                namespace=target_namespace,
            )
            assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
                f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
            )

=======
>>>>>>> 629918e (refactor: Address CodeRabbit review for MTV-3129 ClusterRole tests)

@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.skipif(
    not get_value_from_py_config("remote_ocp_cluster"),
    reason="No remote OCP cluster provided",
)
@pytest.mark.parametrize(
    "class_plan_config",
    [pytest.param(py_config["tests_params"]["test_mtv_clusterrole_warm_migration"])],
    indirect=True,
    ids=["MTV-3129-clusterrole-warm"],
)
@pytest.mark.usefixtures("cleanup_migrated_vms")
class TestClusterroleWarmMtvMigration:
    """Verify ClusterRole (forklift-migrator-role) with warm migration."""

    def test_mtv_clusterrole_warm_migration(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
        clusterrole_destination_ocp_provider,
        prepared_plan,
        source_provider,
        multus_network_name,
        source_provider_inventory,
    ):
        """
        Uses a single token-based OCP provider (clusterrole_destination_ocp_provider).
        Steps: ClusterRole/SA/token/provider by fixture; create NetworkMap and StorageMap;
        create Plan, run warm migration, verify VMs running.
        """
        run_clusterrole_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            prepared_plan=prepared_plan,
            source_provider_inventory=source_provider_inventory,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
            cut_over=get_cutover_value(),
        )
        verify_vms_running(
            ocp_admin_client=ocp_admin_client,
            prepared_plan=prepared_plan,
            target_namespace=target_namespace,
        )

<<<<<<< HEAD
        for vm_config in prepared_plan["virtual_machines"]:
            vm = VirtualMachine(
                client=ocp_admin_client,
                name=vm_config["name"],
                namespace=target_namespace,
            )
            assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
                f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
            )

=======
>>>>>>> 629918e (refactor: Address CodeRabbit review for MTV-3129 ClusterRole tests)

@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.skipif(
    not get_value_from_py_config("remote_ocp_cluster"),
    reason="No remote OCP cluster provided",
)
@pytest.mark.parametrize(
    "class_plan_config",
    [pytest.param(py_config["tests_params"]["test_mtv_clusterrole_configmap_secret_migration"])],
    indirect=True,
    ids=["MTV-3129-clusterrole-configmap-secret"],
)
@pytest.mark.usefixtures("cleanup_migrated_vms")
class TestClusterroleConfigmapSecretMigration:
    """Verify ClusterRole with ConfigMap/Secret migration."""

    def test_mtv_clusterrole_configmap_secret_migration(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
        clusterrole_destination_ocp_provider,
        prepared_plan,
        source_provider,
        multus_network_name,
        source_provider_inventory,
        source_vms_namespace,
    ):
        """
        Creates ConfigMap and Secret in source namespace, migrates VM, verifies both
        were migrated to target namespace using verify_configmap_migrated and verify_secret_migrated.
        """
        if source_vms_namespace is None:
            pytest.skip(
                "source_vms_namespace is None: test requires an OpenShift source provider"
            )

        configmap_name = f"{fixture_store['session_uuid']}-test-configmap"
        create_and_store_resource(
            client=ocp_admin_client,
            fixture_store=fixture_store,
            resource=ConfigMap,
            namespace=source_vms_namespace,
            name=configmap_name,
            data={"key1": "value1", "key2": "value2"},
        )

        secret_name = f"{fixture_store['session_uuid']}-test-secret"
        create_and_store_resource(
            client=ocp_admin_client,
            fixture_store=fixture_store,
            resource=Secret,
            namespace=source_vms_namespace,
            name=secret_name,
            string_data={"username": "testuser", "password": "testpass"},
        )

        run_clusterrole_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            prepared_plan=prepared_plan,
            source_provider_inventory=source_provider_inventory,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
        )

        verify_configmap_migrated(
            client=ocp_admin_client,
            source_namespace=source_vms_namespace,
            target_namespace=target_namespace,
            configmap_name=configmap_name,
        )

        verify_secret_migrated(
            client=ocp_admin_client,
            source_namespace=source_vms_namespace,
            target_namespace=target_namespace,
            secret_name=secret_name,
        )

<<<<<<< HEAD
        for vm_config in prepared_plan["virtual_machines"]:
            vm = VirtualMachine(
                client=ocp_admin_client,
                name=vm_config["name"],
                namespace=target_namespace,
            )
            assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
                f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
            )
=======
        verify_vms_running(
            ocp_admin_client=ocp_admin_client,
            prepared_plan=prepared_plan,
            target_namespace=target_namespace,
        )
>>>>>>> 629918e (refactor: Address CodeRabbit review for MTV-3129 ClusterRole tests)
