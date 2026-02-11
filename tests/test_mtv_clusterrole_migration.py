import pytest
from ocp_resources.config_map import ConfigMap
from ocp_resources.secret import Secret
from ocp_resources.virtual_machine import VirtualMachine
from pytest_testconfig import config as py_config

from utilities.clusterrole_utils import verify_configmap_migrated, verify_secret_migrated
from utilities.mtv_migration import (
    create_plan_resource,
    execute_migration,
    get_network_migration_map,
    get_storage_migration_map,
)
from utilities.resources import create_and_store_resource
from utilities.utils import get_value_from_py_config, populate_vm_ids


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
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            target_namespace=target_namespace,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            ocp_admin_client=ocp_admin_client,
            source_provider_inventory=source_provider_inventory,
            vms=vms,
        )
        network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            multus_network_name=multus_network_name,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            source_provider_inventory=source_provider_inventory,
            vms=vms,
        )
        populate_vm_ids(prepared_plan, source_provider_inventory)
        plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=storage_map,
            network_map=network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        execute_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            plan=plan_resource,
            target_namespace=target_namespace,
        )

        for vm_config in prepared_plan["virtual_machines"]:
            vm = VirtualMachine(
                client=ocp_admin_client,
                name=vm_config["name"],
                namespace=target_namespace,
            )
            assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
                f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
            )


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
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            target_namespace=target_namespace,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            ocp_admin_client=ocp_admin_client,
            source_provider_inventory=source_provider_inventory,
            vms=vms,
        )
        network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            multus_network_name=multus_network_name,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            source_provider_inventory=source_provider_inventory,
            vms=vms,
        )
        populate_vm_ids(prepared_plan, source_provider_inventory)
        plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=storage_map,
            network_map=network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        execute_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            plan=plan_resource,
            target_namespace=target_namespace,
        )

        for vm_config in prepared_plan["virtual_machines"]:
            vm = VirtualMachine(
                client=ocp_admin_client,
                name=vm_config["name"],
                namespace=target_namespace,
            )
            assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
                f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
            )


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

        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            target_namespace=target_namespace,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            ocp_admin_client=ocp_admin_client,
            source_provider_inventory=source_provider_inventory,
            vms=vms,
        )
        network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            multus_network_name=multus_network_name,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            source_provider_inventory=source_provider_inventory,
            vms=vms,
        )
        populate_vm_ids(prepared_plan, source_provider_inventory)
        plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=storage_map,
            network_map=network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        execute_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            plan=plan_resource,
            target_namespace=target_namespace,
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

        for vm_config in prepared_plan["virtual_machines"]:
            vm = VirtualMachine(
                client=ocp_admin_client,
                name=vm_config["name"],
                namespace=target_namespace,
            )
            assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
                f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
            )
