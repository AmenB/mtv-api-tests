import pytest
from exceptions.exceptions import MigrationPlanExecError
from ocp_resources.network_map import NetworkMap
from ocp_resources.plan import Plan
from ocp_resources.storage_map import StorageMap
from pytest_testconfig import config as py_config

from utilities.post_migration import verify_vms_running
from utilities.migration_utils import get_cutover_value
from utilities.mtv_migration import (
    create_plan_resource,
    execute_migration,
    get_network_migration_map,
    get_storage_migration_map,
)
from utilities.utils import get_value_from_py_config, populate_vm_ids


@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.incremental
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
@pytest.mark.usefixtures("cleanup_migrated_vms", "mtv_version_checker")
@pytest.mark.min_mtv_version("2.11.0")
class TestClusterroleColdMtvMigration:
    """Verify ClusterRole (forklift-migrator-role) without SCC fails cold migration."""

    storage_map: StorageMap
    network_map: NetworkMap
    plan_resource: Plan

    def test_create_storagemap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
    ):
        """Create StorageMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            vms=vms,
        )
        assert self.storage_map, "StorageMap creation failed"

    def test_create_networkmap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
        multus_network_name,
    ):
        """Create NetworkMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
            vms=vms,
        )
        assert self.network_map, "NetworkMap creation failed"

    def test_create_plan(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        target_namespace,
        source_provider_inventory,
    ):
        """Create MTV Plan CR resource."""
        populate_vm_ids(prepared_plan, source_provider_inventory)

        self.__class__.plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=self.storage_map,
            network_map=self.network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        assert self.plan_resource, "Plan creation failed"

    def test_migrate_vms(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
    ):
        """Execute migration, expecting failure without SCC binding."""
        with pytest.raises(MigrationPlanExecError):
            execute_migration(
                ocp_admin_client=ocp_admin_client,
                fixture_store=fixture_store,
                plan=self.plan_resource,
                target_namespace=target_namespace,
            )


@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.incremental
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
@pytest.mark.usefixtures("cleanup_migrated_vms", "mtv_version_checker")
@pytest.mark.min_mtv_version("2.11.0")
class TestClusterroleWarmMtvMigration:
    """Verify ClusterRole (forklift-migrator-role) without SCC fails warm migration."""

    storage_map: StorageMap
    network_map: NetworkMap
    plan_resource: Plan

    def test_create_storagemap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
    ):
        """Create StorageMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            vms=vms,
        )
        assert self.storage_map, "StorageMap creation failed"

    def test_create_networkmap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
        multus_network_name,
    ):
        """Create NetworkMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
            vms=vms,
        )
        assert self.network_map, "NetworkMap creation failed"

    def test_create_plan(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        target_namespace,
        source_provider_inventory,
    ):
        """Create MTV Plan CR resource."""
        populate_vm_ids(prepared_plan, source_provider_inventory)

        self.__class__.plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=self.storage_map,
            network_map=self.network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        assert self.plan_resource, "Plan creation failed"

    def test_migrate_vms(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
    ):
        """Execute warm migration, expecting failure without SCC binding."""
        with pytest.raises(MigrationPlanExecError):
            execute_migration(
                ocp_admin_client=ocp_admin_client,
                fixture_store=fixture_store,
                plan=self.plan_resource,
                target_namespace=target_namespace,
                cut_over=get_cutover_value(),
            )


@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.incremental
@pytest.mark.skipif(
    not get_value_from_py_config("remote_ocp_cluster"),
    reason="No remote OCP cluster provided",
)
@pytest.mark.parametrize(
    "class_plan_config",
    [pytest.param(py_config["tests_params"]["test_mtv_clusterrole_cold_migration_with_scc"])],
    indirect=True,
    ids=["MTV-3129-clusterrole-cold-with-scc"],
)
@pytest.mark.usefixtures("cleanup_migrated_vms", "mtv_version_checker")
@pytest.mark.min_mtv_version("2.11.0")
class TestClusterroleColdWithSccMigration:
    """Verify ClusterRole (forklift-migrator-role) with SCC binding succeeds cold migration."""

    storage_map: StorageMap
    network_map: NetworkMap
    plan_resource: Plan

    def test_create_storagemap(
        self,
        forklift_scc_binding,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
    ):
        """Create StorageMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            vms=vms,
        )
        assert self.storage_map, "StorageMap creation failed"

    def test_create_networkmap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
        multus_network_name,
    ):
        """Create NetworkMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
            vms=vms,
        )
        assert self.network_map, "NetworkMap creation failed"

    def test_create_plan(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        target_namespace,
        source_provider_inventory,
    ):
        """Create MTV Plan CR resource."""
        populate_vm_ids(prepared_plan, source_provider_inventory)

        self.__class__.plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=self.storage_map,
            network_map=self.network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        assert self.plan_resource, "Plan creation failed"

    def test_migrate_vms(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
    ):
        """Execute migration."""
        execute_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            plan=self.plan_resource,
            target_namespace=target_namespace,
        )

    def test_check_vms(
        self,
        ocp_admin_client,
        prepared_plan,
        target_namespace,
    ):
        """Validate migrated VMs are running."""
        verify_vms_running(
            ocp_admin_client=ocp_admin_client,
            prepared_plan=prepared_plan,
            target_namespace=target_namespace,
        )


@pytest.mark.remote
@pytest.mark.tier0
@pytest.mark.warm
@pytest.mark.incremental
@pytest.mark.skipif(
    not get_value_from_py_config("remote_ocp_cluster"),
    reason="No remote OCP cluster provided",
)
@pytest.mark.parametrize(
    "class_plan_config",
    [pytest.param(py_config["tests_params"]["test_mtv_clusterrole_warm_migration_with_scc"])],
    indirect=True,
    ids=["MTV-3129-clusterrole-warm-with-scc"],
)
@pytest.mark.usefixtures("cleanup_migrated_vms", "mtv_version_checker")
@pytest.mark.min_mtv_version("2.11.0")
class TestClusterroleWarmWithSccMigration:
    """Verify ClusterRole (forklift-migrator-role) with SCC binding succeeds warm migration."""

    storage_map: StorageMap
    network_map: NetworkMap
    plan_resource: Plan

    def test_create_storagemap(
        self,
        forklift_scc_binding,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
    ):
        """Create StorageMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.storage_map = get_storage_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            vms=vms,
        )
        assert self.storage_map, "StorageMap creation failed"

    def test_create_networkmap(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        source_provider_inventory,
        target_namespace,
        multus_network_name,
    ):
        """Create NetworkMap resource for migration."""
        vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
        self.__class__.network_map = get_network_migration_map(
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            source_provider_inventory=source_provider_inventory,
            ocp_admin_client=ocp_admin_client,
            target_namespace=target_namespace,
            multus_network_name=multus_network_name,
            vms=vms,
        )
        assert self.network_map, "NetworkMap creation failed"

    def test_create_plan(
        self,
        prepared_plan,
        fixture_store,
        ocp_admin_client,
        source_provider,
        clusterrole_destination_ocp_provider,
        target_namespace,
        source_provider_inventory,
    ):
        """Create MTV Plan CR resource."""
        populate_vm_ids(prepared_plan, source_provider_inventory)

        self.__class__.plan_resource = create_plan_resource(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            source_provider=source_provider,
            destination_provider=clusterrole_destination_ocp_provider,
            storage_map=self.storage_map,
            network_map=self.network_map,
            virtual_machines_list=prepared_plan["virtual_machines"],
            target_namespace=target_namespace,
            warm_migration=prepared_plan.get("warm_migration", False),
        )
        assert self.plan_resource, "Plan creation failed"

    def test_migrate_vms(
        self,
        fixture_store,
        ocp_admin_client,
        target_namespace,
    ):
        """Execute warm migration."""
        execute_migration(
            ocp_admin_client=ocp_admin_client,
            fixture_store=fixture_store,
            plan=self.plan_resource,
            target_namespace=target_namespace,
            cut_over=get_cutover_value(),
        )

    def test_check_vms(
        self,
        ocp_admin_client,
        prepared_plan,
        target_namespace,
    ):
        """Validate migrated VMs are running."""
        verify_vms_running(
            ocp_admin_client=ocp_admin_client,
            prepared_plan=prepared_plan,
            target_namespace=target_namespace,
        )
